"""Create OOF-based customer churn probabilities and risk tiers."""

import json
from pathlib import Path
import sys

import joblib
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features import prepare_features
from src.segmentation import build_risk_scores
from src.utils import DATA_PROCESSED_DIR, FIGURES_DIR, METRICS_DIR, MODELS_DIR, OUTPUTS_DIR, PREDICTIONS_DIR, get_logger


LOGGER = get_logger(__name__)
DATA_PATH = DATA_PROCESSED_DIR / "telco_churn_cleaned.csv"
SPLIT_PATH = DATA_PROCESSED_DIR / "train_test_indices.json"
EVALUATION_PATH = METRICS_DIR / "evaluation_metrics.json"
MODEL_PATH = MODELS_DIR / "xgboost.joblib"
OUTPUT_PATH = PREDICTIONS_DIR / "customer_risk_scores.csv"
REPORT_PATH = OUTPUTS_DIR / "reports" / "risk_segmentation_report.md"
FINAL_MODEL_NAME = "XGBoost"


def main() -> None:
    """Build, profile, and save one risk score for every customer."""
    dataframe = pd.read_csv(DATA_PATH)
    features, target = prepare_features(dataframe)
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    selected_threshold = float(evaluation["chosen_threshold"])
    # Medium/high is a transparent business-review boundary above the selected
    # intervention threshold; its observed tier rates are checked below.
    medium_high_cutoff = 0.60
    model = joblib.load(MODEL_PATH)
    risk_scores = build_risk_scores(
        dataframe,
        features,
        target,
        split["train_indices"],
        split["test_indices"],
        model,
        selected_threshold,
        medium_high_cutoff,
    )
    # Profile by customerID so the saved scores can be joined safely to attributes.
    customer_attributes = dataframe.set_index("customerID")
    risk_with_attributes = risk_scores.join(
        customer_attributes[["tenure", "MonthlyCharges", "Contract", "InternetService", "PaymentMethod"]],
        on="customerID",
    )
    profiles = []
    for tier in ["Low", "Medium", "High"]:
        group = risk_with_attributes[risk_with_attributes["risk_tier"] == tier]
        profiles.append(
            {
                "risk_tier": tier,
                "customers": int(len(group)),
                "actual_churn_rate": round(float(group["actual_churn"].eq("Yes").mean() * 100), 2),
                "average_tenure": round(float(group["tenure"].mean()), 2),
                "average_monthly_charges": round(float(group["MonthlyCharges"].mean()), 2),
                "common_contract": str(group["Contract"].mode().iat[0]),
                "common_internet_service": str(group["InternetService"].mode().iat[0]),
                "common_payment_method": str(group["PaymentMethod"].mode().iat[0]),
            }
        )
    profile_table = pd.DataFrame(profiles)
    if not profile_table["actual_churn_rate"].is_monotonic_increasing:
        raise ValueError("Observed churn rate did not increase from Low to High risk.")

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    risk_scores.to_csv(OUTPUT_PATH, index=False)
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].bar(profile_table["risk_tier"], profile_table["customers"], color=["#2a9d8f", "#e9c46a", "#e76f51"])
    axes[0].set_title("Customers by Risk Tier")
    axes[0].set_xlabel("Risk tier")
    axes[0].set_ylabel("Customers")
    axes[1].bar(profile_table["risk_tier"], profile_table["actual_churn_rate"], color=["#2a9d8f", "#e9c46a", "#e76f51"])
    axes[1].set_title("Observed Churn Rate by Risk Tier")
    axes[1].set_xlabel("Risk tier")
    axes[1].set_ylabel("Actual churn rate (%)")
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "risk_tier_profile.png", dpi=150)
    plt.close(figure)

    lines = [
        "# Risk Segmentation Report",
        "",
        f"Final model: **{FINAL_MODEL_NAME}**",
        f"Low/Medium cutoff: **{selected_threshold:.2f}** from training OOF threshold analysis.",
        f"Medium/High cutoff: **{medium_high_cutoff:.2f}**, an explicit review boundary whose observed tier rates are checked below.",
        "",
        "Training customers use out-of-fold probabilities so a customer's own training label is not used by the model that scores it. Test customers use the final saved model because they were held out during training.",
        "",
        "## Tier Profile",
        "",
        "| " + " | ".join(profile_table.columns) + " |",
        "|" + "|".join(["---"] * len(profile_table.columns)) + "|",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in profile_table.itertuples(index=False, name=None))
    lines.extend(
        [
            "",
            f"Observed churn rates rise from Low ({profile_table.iloc[0]['actual_churn_rate']:.2f}%) to Medium ({profile_table.iloc[1]['actual_churn_rate']:.2f}%) to High ({profile_table.iloc[2]['actual_churn_rate']:.2f}%).",
            "",
            f"Saved {len(risk_scores):,} customer scores to `{OUTPUT_PATH}`.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(profile_table.to_string(index=False))
    print(f"Risk scores saved to: {OUTPUT_PATH}")
    print(f"Risk segmentation report saved to: {REPORT_PATH}")
    LOGGER.info("Risk segmentation completed")


if __name__ == "__main__":
    main()