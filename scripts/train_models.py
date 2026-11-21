"""Train and evaluate the Phase 4 churn models."""

import json
from pathlib import Path
import sys
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features import feature_documentation, identify_feature_columns, prepare_features
from src.model_training import (
    MODEL_FILENAMES,
    RANDOM_STATE,
    build_model_pipeline,
    cross_validation_metrics,
    evaluate_test_set,
    tune_model,
)
from src.utils import DATA_PROCESSED_DIR, METRICS_DIR, MODELS_DIR, OUTPUTS_DIR, get_logger


LOGGER = get_logger(__name__)
DATA_PATH = DATA_PROCESSED_DIR / "telco_churn_cleaned.csv"
SPLIT_PATH = DATA_PROCESSED_DIR / "train_test_indices.json"
METRICS_PATH = METRICS_DIR / "model_metrics.json"
REPORT_PATH = OUTPUTS_DIR / "reports" / "model_training_report.md"


def _write_split_indices(train_features: pd.DataFrame, test_features: pd.DataFrame) -> None:
    """Save the exact split indices for reuse by later phases."""
    SPLIT_PATH.write_text(
        json.dumps(
            {
                "random_state": RANDOM_STATE,
                "test_size": 0.2,
                "train_indices": [int(index) for index in train_features.index],
                "test_indices": [int(index) for index in test_features.index],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _comparison_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Build compact rows for console and Markdown comparison tables."""
    rows = []
    for model_name, values in metrics["models"].items():
        cv = values["cross_validation"]
        test = values["test"]
        rows.append(
            {
                "Model": model_name,
                "CV ROC-AUC": f"{cv['roc_auc']['mean']:.3f} +/- {cv['roc_auc']['std']:.3f}",
                "CV F1": f"{cv['f1']['mean']:.3f} +/- {cv['f1']['std']:.3f}",
                "Test Accuracy": f"{test['accuracy']:.3f}",
                "Test Precision": f"{test['precision']:.3f}",
                "Test Recall": f"{test['recall']:.3f}",
                "Test F1": f"{test['f1']:.3f}",
                "Test ROC-AUC": f"{test['roc_auc']:.3f}",
            }
        )
    return rows


def _write_report(metrics: dict[str, Any]) -> None:
    """Write training decisions, metrics, and limitations to Markdown."""
    rows = _comparison_rows(metrics)
    headers = list(rows[0])
    lines = [
        "# Model Training Report",
        "",
        "## Decisions",
        "",
        "- The target is `churn_flag`; `customerID`, text `Churn`, and the target duplicate were excluded to prevent leakage.",
        "- Feature engineering uses only existing row values. The train/test split was made before fitting the scaler or encoder.",
        "- Numeric columns use `StandardScaler`; categorical columns use `OneHotEncoder(handle_unknown='ignore')`.",
        "- `No internet service` and `No phone service` remain distinct categorical values and are one-hot encoded separately.",
        "- Tuning and five-fold cross-validation used training rows only. The test set was evaluated once after final fitting.",
        "- Accuracy is not sufficient for this 26.54% churn class: recall shows how many churners are found, while precision shows how many flagged customers really churn.",
        "",
        "## Feature Reasons",
        "",
    ]
    lines.extend(f"- `{name}`: {reason}" for name, reason in feature_documentation().items())
    lines.extend(["", "## Model Comparison", "", "| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"])
    lines.extend("| " + " | ".join(row[header] for header in headers) + " |" for row in rows)
    lines.extend(
        [
            "",
            "## Limitations for Phase 5",
            "",
            "- These are basic tuned models; no threshold optimization, calibration, error analysis, or business recommendation was performed.",
            "- Cross-validation metrics describe training-fold performance, while the single test evaluation is the held-out estimate.",
            "- Correlated service and billing variables may make individual model effects difficult to interpret causally.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run feature preparation, split, tuning, evaluation, and artifact saving."""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {DATA_PATH}. Run scripts/clean_data.py first."
        )
    dataframe = pd.read_csv(DATA_PATH)
    features, target = prepare_features(dataframe)
    feature_columns = identify_feature_columns(features)

    # Split before fitting any learned preprocessing to prevent test leakage.
    train_features, test_features, train_target, test_target = train_test_split(
        features,
        target,
        test_size=0.2,
        stratify=target,
        random_state=RANDOM_STATE,
    )
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    _write_split_indices(train_features, test_features)
    negative_count = int((train_target == 0).sum())
    positive_count = int((train_target == 1).sum())
    scale_pos_weight = negative_count / positive_count

    metrics: dict[str, Any] = {
        "split": {
            "random_state": RANDOM_STATE,
            "test_size": 0.2,
            "train_rows": len(train_features),
            "test_rows": len(test_features),
            "train_churn_counts": {"0": negative_count, "1": positive_count},
            "test_churn_counts": {
                "0": int((test_target == 0).sum()),
                "1": int((test_target == 1).sum()),
            },
        },
        "feature_columns": feature_columns,
        "scale_pos_weight": scale_pos_weight,
        "models": {},
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    for model_name in MODEL_FILENAMES:
        LOGGER.info("Tuning %s on training data", model_name)
        pipeline = build_model_pipeline(
            model_name,
            feature_columns["numeric"],
            feature_columns["categorical"],
            scale_pos_weight,
        )
        search = tune_model(pipeline, model_name, train_features, train_target)
        final_pipeline = search.best_estimator_
        cv_metrics = cross_validation_metrics(final_pipeline, train_features, train_target)
        final_pipeline.fit(train_features, train_target)
        test_metrics = evaluate_test_set(final_pipeline, test_features, test_target)
        model_path = MODELS_DIR / MODEL_FILENAMES[model_name]
        joblib.dump(final_pipeline, model_path)
        metrics["models"][model_name] = {
            "best_params": search.best_params_,
            "best_training_cv_roc_auc": round(float(search.best_score_), 6),
            "cross_validation": cv_metrics,
            "test": test_metrics,
            "model_path": str(model_path),
        }

    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    _write_report(metrics)
    comparison = pd.DataFrame(_comparison_rows(metrics))
    print(comparison.to_string(index=False))
    print(f"Metrics saved to: {METRICS_PATH}")
    print(f"Training report saved to: {REPORT_PATH}")
    print(f"Split indices saved to: {SPLIT_PATH}")


if __name__ == "__main__":
    main()