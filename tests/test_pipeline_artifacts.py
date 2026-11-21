"""Integration checks for generated artifacts.

These tests skip clearly when a fresh clone has not generated local data.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.features import prepare_features


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "telco_churn_cleaned.csv"
RISK_PATH = ROOT / "outputs" / "predictions" / "customer_risk_scores.csv"
SPLIT_PATH = ROOT / "data" / "processed" / "train_test_indices.json"
MODEL_PATHS = [
    ROOT / "models" / "logistic_regression.joblib",
    ROOT / "models" / "random_forest.joblib",
    ROOT / "models" / "xgboost.joblib",
]


def _require_artifacts() -> None:
    """Skip integration checks when generated local artifacts are absent."""
    missing = [path for path in [DATA_PATH, RISK_PATH, SPLIT_PATH, *MODEL_PATHS] if not path.exists()]
    if missing:
        pytest.skip("Generated local artifacts are absent; run the project pipeline first.")


def test_saved_models_reload_and_predict() -> None:
    """Each saved pipeline predicts on rows from the persisted test split."""
    _require_artifacts()
    dataframe = pd.read_csv(DATA_PATH)
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    features, _ = prepare_features(dataframe.loc[split["test_indices"][:3]])
    for path in MODEL_PATHS:
        predictions = joblib.load(path).predict(features)
        assert len(predictions) == 3


def test_risk_scores_cover_customers_without_duplicates_and_rise_by_tier() -> None:
    """Risk scores cover every customer and observed churn rises by tier."""
    _require_artifacts()
    customers = pd.read_csv(DATA_PATH)
    risk_scores = pd.read_csv(RISK_PATH)
    assert len(risk_scores) == len(customers)
    assert not risk_scores["customerID"].duplicated().any()
    rates = risk_scores.groupby("risk_tier", observed=False)["actual_churn"].apply(
        lambda values: values.eq("Yes").mean()
    ).reindex(["Low", "Medium", "High"])
    assert rates.is_monotonic_increasing