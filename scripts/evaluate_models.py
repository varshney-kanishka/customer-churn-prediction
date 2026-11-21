"""Evaluate saved churn models, choose a threshold, and report drivers."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import (
    classification_metrics,
    choose_threshold,
    cost_scenarios,
    curve_data,
    logistic_driver_table,
    permutation_driver_table,
    threshold_table,
)
from src.features import prepare_features
from src.segmentation import out_of_fold_train_probabilities
from src.utils import DATA_PROCESSED_DIR, FIGURES_DIR, METRICS_DIR, MODELS_DIR, OUTPUTS_DIR, get_logger


LOGGER = get_logger(__name__)
DATA_PATH = DATA_PROCESSED_DIR / "telco_churn_cleaned.csv"
SPLIT_PATH = DATA_PROCESSED_DIR / "train_test_indices.json"
PHASE4_METRICS_PATH = METRICS_DIR / "model_metrics.json"
OUTPUT_PATH = METRICS_DIR / "evaluation_metrics.json"
REPORT_PATH = OUTPUTS_DIR / "reports" / "model_evaluation_report.md"
FINAL_MODEL_NAME = "XGBoost"
MODEL_PATHS = {
    "Logistic Regression": MODELS_DIR / "logistic_regression.joblib",
    "Random Forest": MODELS_DIR / "random_forest.joblib",
    "XGBoost": MODELS_DIR / "xgboost.joblib",
}
THRESHOLD_CANDIDATES = [round(value, 2) for value in np.arange(0.20, 0.81, 0.05)]

# These are editable placeholders for scenario analysis, not company facts.
COST_ASSUMPTIONS = [
    {"offer_cost": 10.0, "retained_customer_value": 100.0},
    {"offer_cost": 25.0, "retained_customer_value": 250.0},
    {"offer_cost": 50.0, "retained_customer_value": 500.0},
]


def _load_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, list[int], list[int]]:
    """Load cleaned data and the exact Phase 4 split."""
    dataframe = pd.read_csv(DATA_PATH)
    features, target = prepare_features(dataframe)
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    return dataframe, features, target, split["train_indices"], split["test_indices"]


def _markdown_table(dataframe: pd.DataFrame) -> list[str]:
    """Convert a small DataFrame to Markdown table lines."""
    display_data = dataframe.copy()
    headers = [str(column) for column in display_data.columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend(
        "| " + " | ".join(str(row[column]) for column in display_data.columns) + " |"
        for _, row in display_data.iterrows()
    )
    return lines


def _save_roc_plot(curves: dict[str, dict[str, np.ndarray]]) -> None:
    """Save one ROC chart for all saved models."""
    figure, axis = plt.subplots(figsize=(8, 6))
    for model_name, curve in curves.items():
        axis.plot(
            curve["false_positive_rate"],
            curve["true_positive_rate"],
            label=f"{model_name} (AUC={curve['roc_auc']:.3f})",
        )
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    axis.set_title("ROC Curves on the Held-Out Test Set")
    axis.set_xlabel("False positive rate")
    axis.set_ylabel("True positive rate")
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "model_roc_curves.png", dpi=150)
    plt.close(figure)


def _save_pr_plot(curves: dict[str, dict[str, np.ndarray]]) -> None:
    """Save one precision-recall chart for all saved models."""
    figure, axis = plt.subplots(figsize=(8, 6))
    for model_name, curve in curves.items():
        axis.plot(
            curve["recall"],
            curve["precision"],
            label=f"{model_name} (AP={curve['pr_auc']:.3f})",
        )
    axis.set_title("Precision-Recall Curves on the Held-Out Test Set")
    axis.set_xlabel("Recall")
    axis.set_ylabel("Precision")
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "model_precision_recall_curves.png", dpi=150)
    plt.close(figure)


def _save_confusion_matrix(metrics: dict[str, Any]) -> None:
    """Save the final-model confusion matrix at the chosen threshold."""
    matrix = metrics["confusion_matrix"]
    values = np.array(
        [[matrix["true_negative"], matrix["false_positive"]], [matrix["false_negative"], matrix["true_positive"]]]
    )
    figure, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(values, cmap="Blues")
    figure.colorbar(image, ax=axis)
    axis.set_title(f"{FINAL_MODEL_NAME} Confusion Matrix at Threshold {metrics['threshold']:.2f}")
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("Actual label")
    axis.set_xticks([0, 1], ["No churn", "Churn"])
    axis.set_yticks([0, 1], ["No churn", "Churn"])
    for row in range(2):
        for column in range(2):
            axis.text(column, row, values[row, column], ha="center", va="center")
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "final_model_confusion_matrix.png", dpi=150)
    plt.close(figure)


def _save_calibration_plot(target: pd.Series, probabilities: np.ndarray) -> None:
    """Save a reliability diagram for the final model."""
    observed, predicted = calibration_curve(target, probabilities, n_bins=10, strategy="uniform")
    figure, axis = plt.subplots(figsize=(7, 6))
    axis.plot(predicted, observed, marker="o", label=FINAL_MODEL_NAME)
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
    axis.set_title(f"Calibration Curve for {FINAL_MODEL_NAME}")
    axis.set_xlabel("Mean predicted churn probability")
    axis.set_ylabel("Observed churn frequency")
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "final_model_calibration_curve.png", dpi=150)
    plt.close(figure)


def _save_threshold_plot(table: pd.DataFrame, selected_threshold: float) -> None:
    """Save precision, recall, and F1 across OOF-selected thresholds."""
    figure, axis = plt.subplots(figsize=(8, 5))
    for metric in ["precision", "recall", "f1"]:
        axis.plot(table["threshold"], table[metric], marker="o", label=metric.title())
    axis.axvline(selected_threshold, linestyle="--", color="black", label=f"Chosen={selected_threshold:.2f}")
    axis.set_title("Training OOF Threshold Analysis")
    axis.set_xlabel("Decision threshold")
    axis.set_ylabel("Score")
    axis.set_ylim(0, 1)
    axis.legend()
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "threshold_analysis.png", dpi=150)
    plt.close(figure)


def _write_report(
    metrics: dict[str, Any],
    threshold_data: pd.DataFrame,
    logistic_drivers: pd.DataFrame,
    tree_drivers: pd.DataFrame,
    scenario_data: list[dict[str, float]],
) -> None:
    """Write the evaluation findings and limitations to Markdown."""
    comparison = []
    for name, result in metrics["models"].items():
        comparison.append(
            {
                "Model": name,
                "Accuracy": f"{result['accuracy']:.3f}",
                "Precision": f"{result['precision']:.3f}",
                "Recall": f"{result['recall']:.3f}",
                "F1": f"{result['f1']:.3f}",
                "ROC-AUC": f"{result['roc_auc']:.3f}",
                "PR-AUC": f"{result['pr_auc']:.3f}",
            }
        )
    chosen = metrics["final_model_threshold_metrics"]
    lines = [
        "# Model Evaluation Report",
        "",
        f"Final model: **{FINAL_MODEL_NAME}**",
        f"Chosen threshold: **{metrics['chosen_threshold']:.2f}**, selected from training out-of-fold predictions.",
        "",
        "## Held-Out Test Comparison",
        "",
        *_markdown_table(pd.DataFrame(comparison)),
        "",
        "The CV ROC-AUC differences from Phase 4 were smaller than their fold standard deviations, so the models are statistically indistinguishable by that measure. XGBoost was retained because it had the best held-out ROC-AUC (0.845), recall (0.799), and F1 (0.625), which fit a retention workflow that values finding churners. This is a practical choice, not proof that XGBoost is universally superior.",
        "",
        "## Chosen Threshold",
        "",
        "The threshold was selected by maximizing F1 on five-fold out-of-fold training predictions. The test set was not used for threshold selection.",
        "",
        *_markdown_table(threshold_data.round(3)),
        "",
        f"At the chosen threshold, the test set produced accuracy {chosen['accuracy']:.3f}, precision {chosen['precision']:.3f}, recall {chosen['recall']:.3f}, F1 {chosen['f1']:.3f}, and PR-AUC {chosen['pr_auc']:.3f}.",
        "",
        "### Editable Placeholder Cost Scenarios",
        "",
        "Offer cost and retained-customer value are assumptions, not facts from this dataset. The net value below is only a scenario calculation based on true positives and all offers made.",
        "",
        *_markdown_table(pd.DataFrame(scenario_data).round(2)),
        "",
        "## Churn Drivers",
        "",
        "### Logistic Regression Coefficients",
        "",
        "Positive coefficients increase estimated churn odds; odds ratios above 1 indicate higher odds and values below 1 indicate lower odds relative to the encoded baseline.",
        "",
        *_markdown_table(logistic_drivers.round(3)),
        "",
        "### XGBoost Permutation Importance",
        "",
        "Permutation importance measures the test ROC-AUC decrease when one raw feature is shuffled. It is an association measure, not proof of cause.",
        "",
        *_markdown_table(tree_drivers.round(4)),
        "",
        "The logistic and tree views should be compared as complementary evidence. Correlated service and billing fields can cause their rankings to differ, and neither ranking establishes causation.",
        "",
        "## Limitations",
        "",
        "- Threshold and segmentation decisions are not substitutes for cost-sensitive validation with real business data.",
        "- This is one historical snapshot; customer behavior and service policies may change.",
        "- No calibration tuning, causal analysis, or Phase 6 dashboard/database work was performed.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Evaluate the saved models and write Phase 5 evaluation artifacts."""
    dataframe, features, target, train_indices, test_indices = _load_context()
    train_features, test_features = features.loc[train_indices], features.loc[test_indices]
    train_target, test_target = target.loc[train_indices], target.loc[test_indices]
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    models = {name: joblib.load(path) for name, path in MODEL_PATHS.items()}
    test_probabilities: dict[str, np.ndarray] = {}
    model_metrics: dict[str, Any] = {}
    curves: dict[str, dict[str, np.ndarray]] = {}
    for model_name, model in models.items():
        probabilities = model.predict_proba(test_features)[:, 1]
        test_probabilities[model_name] = probabilities
        model_metrics[model_name] = classification_metrics(test_target, probabilities)
        curve = curve_data(test_target, probabilities)
        curves[model_name] = {
            **curve,
            "roc_auc": model_metrics[model_name]["roc_auc"],
            "pr_auc": model_metrics[model_name]["pr_auc"],
        }

    _save_roc_plot(curves)
    _save_pr_plot(curves)

    final_model = models[FINAL_MODEL_NAME]
    oof_probabilities = out_of_fold_train_probabilities(final_model, train_features, train_target)
    threshold_data = threshold_table(train_target, oof_probabilities, THRESHOLD_CANDIDATES)
    selected_threshold = choose_threshold(threshold_data)
    final_threshold_metrics = classification_metrics(
        test_target, test_probabilities[FINAL_MODEL_NAME], selected_threshold
    )
    _save_threshold_plot(threshold_data, selected_threshold)
    _save_confusion_matrix(final_threshold_metrics)
    _save_calibration_plot(test_target, test_probabilities[FINAL_MODEL_NAME])

    logistic_drivers = logistic_driver_table(models["Logistic Regression"])
    tree_drivers = permutation_driver_table(final_model, test_features, test_target)
    scenarios = cost_scenarios(final_threshold_metrics, COST_ASSUMPTIONS)
    phase4_metrics = json.loads(PHASE4_METRICS_PATH.read_text(encoding="utf-8"))
    metrics = {
        "final_model": FINAL_MODEL_NAME,
        "chosen_threshold": selected_threshold,
        "models": model_metrics,
        "phase4_cross_validation": {
            name: values["cross_validation"]
            for name, values in phase4_metrics["models"].items()
        },
        "final_model_threshold_metrics": final_threshold_metrics,
        "threshold_table_training_oof": threshold_data.to_dict(orient="records"),
        "cost_assumptions": scenarios,
        "logistic_drivers": logistic_drivers.to_dict(orient="records"),
        "tree_permutation_drivers": tree_drivers.to_dict(orient="records"),
    }
    OUTPUT_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    _write_report(metrics, threshold_data, logistic_drivers, tree_drivers, scenarios)
    print(f"Final model: {FINAL_MODEL_NAME}")
    print(f"Chosen OOF threshold: {selected_threshold:.2f}")
    print(pd.DataFrame(model_metrics).T[["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]].round(3).to_string())
    print(f"Evaluation metrics saved to: {OUTPUT_PATH}")
    print(f"Evaluation report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()