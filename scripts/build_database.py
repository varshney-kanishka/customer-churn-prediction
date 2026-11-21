"""Build the repeatable SQLite database used by the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import (
    create_schema,
    get_connection,
    load_customers,
    load_model_metrics,
    load_risk_scores,
    load_tier_summary,
)
from src.utils import DATA_PROCESSED_DIR, DATABASE_PATH, METRICS_DIR, PREDICTIONS_DIR, get_logger


LOGGER = get_logger(__name__)


def _flatten_metrics() -> pd.DataFrame:
    """Flatten Phase 4 CV and Phase 5 test metrics into table rows."""
    phase4 = json.loads((METRICS_DIR / "model_metrics.json").read_text(encoding="utf-8"))
    evaluation = json.loads((METRICS_DIR / "evaluation_metrics.json").read_text(encoding="utf-8"))
    rows = []
    for model_name, values in phase4["models"].items():
        for metric, details in values["cross_validation"].items():
            rows.append({"model_name": model_name, "metric": metric, "value": details["mean"], "split": "CV"})
    for model_name, values in evaluation["models"].items():
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            rows.append({"model_name": model_name, "metric": metric, "value": values[metric], "split": "test"})
    return pd.DataFrame(rows)


def _add_score_sources(scores: pd.DataFrame) -> pd.DataFrame:
    """Label risk scores as OOF or test using the persisted Phase 4 split."""
    split = json.loads((DATA_PROCESSED_DIR / "train_test_indices.json").read_text(encoding="utf-8"))
    customers = pd.read_csv(DATA_PROCESSED_DIR / "telco_churn_cleaned.csv")
    train_ids = set(customers.loc[split["train_indices"], "customerID"])
    enriched = scores.copy()
    enriched["source"] = enriched["customerID"].map(
        lambda customer_id: "out-of-fold" if customer_id in train_ids else "test"
    )
    return enriched


def _tier_summary() -> pd.DataFrame:
    """Build tier profiles from the customer and risk-score source files."""
    customers = pd.read_csv(DATA_PROCESSED_DIR / "telco_churn_cleaned.csv")
    scores = pd.read_csv(PREDICTIONS_DIR / "customer_risk_scores.csv")
    joined = scores.merge(
        customers[["customerID", "tenure", "MonthlyCharges", "Contract", "InternetService", "PaymentMethod"]],
        on="customerID",
        validate="one_to_one",
    )
    rows = []
    for tier in ["Low", "Medium", "High"]:
        group = joined[joined["risk_tier"] == tier]
        rows.append(
            {
                "risk_tier": tier,
                "customers": len(group),
                "actual_churn_rate": group["actual_churn"].eq("Yes").mean() * 100,
                "average_tenure": group["tenure"].mean(),
                "average_monthly_charges": group["MonthlyCharges"].mean(),
                "common_contract": group["Contract"].mode().iat[0],
                "common_internet_service": group["InternetService"].mode().iat[0],
                "common_payment_method": group["PaymentMethod"].mode().iat[0],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    """Rebuild the SQLite database from current project outputs."""
    cleaned = pd.read_csv(DATA_PROCESSED_DIR / "telco_churn_cleaned.csv")
    scores = _add_score_sources(pd.read_csv(PREDICTIONS_DIR / "customer_risk_scores.csv"))
    metrics = _flatten_metrics()
    tiers = _tier_summary()
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(DATABASE_PATH) as connection:
        connection.execute("DROP TABLE IF EXISTS risk_scores")
        connection.execute("DROP TABLE IF EXISTS model_metrics")
        connection.execute("DROP TABLE IF EXISTS tier_summary")
        connection.execute("DROP TABLE IF EXISTS customers")
        create_schema(connection)
        counts = {
            "customers": load_customers(connection, cleaned),
            "risk_scores": load_risk_scores(connection, scores),
            "model_metrics": load_model_metrics(connection, metrics),
            "tier_summary": load_tier_summary(connection, tiers),
        }
    for table, count in counts.items():
        print(f"{table}: {count}")
    print(f"Database saved to: {DATABASE_PATH}")
    LOGGER.info("Database rebuild completed")


if __name__ == "__main__":
    main()