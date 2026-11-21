"""Feature engineering for the cleaned Telco churn dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd


ADD_ON_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]

REQUIRED_COLUMNS = {
    "customerID",
    "Churn",
    "churn_flag",
    "tenure",
    "TotalCharges",
    "InternetService",
    "PhoneService",
    *ADD_ON_COLUMNS,
}


def create_engineered_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add a small set of non-learned features without changing the input.

    The tenure group makes the EDA finding easier to represent. The add-on
    count, service flags, and average monthly charge summarize existing
    columns without using the target or fitting on the full dataset.
    """
    missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing_columns:
        raise ValueError(f"Missing columns required for feature engineering: {missing_columns}")

    engineered = dataframe.copy(deep=True)
    engineered["tenure_group"] = pd.cut(
        engineered["tenure"],
        bins=[-1, 12, 24, 48, 72],
        labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months"],
    )
    engineered["add_on_count"] = engineered[ADD_ON_COLUMNS].eq("Yes").sum(axis=1)
    tenure = pd.to_numeric(engineered["tenure"], errors="coerce")
    total_charges = pd.to_numeric(engineered["TotalCharges"], errors="coerce")
    safe_tenure = tenure.where(tenure.ne(0))
    engineered["average_monthly_charge"] = (
        total_charges.divide(safe_tenure).fillna(0.0)
    )
    engineered["has_internet"] = engineered["InternetService"].ne("No").astype(int)
    engineered["has_phone"] = engineered["PhoneService"].eq("Yes").astype(int)
    return engineered


def prepare_features(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Create model features and return them with the churn target.

    ``customerID`` is an identifier with no stable predictive meaning, and
    text ``Churn`` duplicates the numeric target. Both are removed to prevent
    leakage. ``churn_flag`` itself is also removed from the feature matrix.
    """
    engineered = create_engineered_features(dataframe)
    target = pd.to_numeric(engineered["churn_flag"], errors="raise").astype(int)
    features = engineered.drop(columns=["customerID", "Churn", "churn_flag"])
    return features, target


def identify_feature_columns(features: pd.DataFrame) -> dict[str, list[str]]:
    """Identify numeric and categorical columns for the preprocessor."""
    numeric_columns = features.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = features.select_dtypes(include=["object", "category"]).columns.tolist()
    return {"numeric": numeric_columns, "categorical": categorical_columns}


def feature_documentation() -> dict[str, str]:
    """Return beginner-friendly reasons for each engineered feature."""
    return {
        "tenure_group": "Groups tenure to represent the strong EDA pattern without using churn.",
        "add_on_count": "Counts subscribed add-on services to summarize service adoption.",
        "average_monthly_charge": "Divides TotalCharges by tenure; zero-tenure customers safely receive 0.0.",
        "has_internet": "Flags InternetService values other than No.",
        "has_phone": "Flags customers whose PhoneService is Yes.",
        "No internet service / No phone service": "These remain categorical values and are one-hot encoded as distinct categories.",
    }