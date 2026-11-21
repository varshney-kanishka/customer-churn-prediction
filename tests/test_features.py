"""Tests for Phase 4 features using hand-written test fixtures only."""

import pandas as pd

from src.features import ADD_ON_COLUMNS, create_engineered_features, prepare_features


def feature_fixture() -> pd.DataFrame:
    """Return a tiny fixture used only by feature tests."""
    values = {
        "customerID": ["A", "B"],
        "Churn": ["No", "Yes"],
        "churn_flag": [0, 1],
        "tenure": [0, 12],
        "TotalCharges": [0.0, 120.0],
        "InternetService": ["No", "DSL"],
        "PhoneService": ["No", "Yes"],
        "SeniorCitizen": [0, 1],
        "MonthlyCharges": [20.0, 30.0],
    }
    for column in ADD_ON_COLUMNS:
        values[column] = ["No internet service", "Yes"]
    return pd.DataFrame(values)


def test_engineered_features_handle_zero_tenure_without_infinity() -> None:
    """Zero tenure receives a safe average charge and a valid tenure group."""
    engineered = create_engineered_features(feature_fixture())
    assert engineered.loc[0, "average_monthly_charge"] == 0.0
    assert engineered.loc[0, "tenure_group"] == "0-12 months"
    assert engineered.loc[1, "average_monthly_charge"] == 10.0


def test_add_on_and_service_flags_use_existing_categories() -> None:
    """Add-on, internet, and phone flags reflect the source categories."""
    engineered = create_engineered_features(feature_fixture())
    assert engineered["add_on_count"].tolist() == [0, 6]
    assert engineered["has_internet"].tolist() == [0, 1]
    assert engineered["has_phone"].tolist() == [0, 1]


def test_prepare_features_drops_identifiers_and_target_duplicates() -> None:
    """The feature matrix excludes customerID, Churn, and churn_flag."""
    features, target = prepare_features(feature_fixture())
    assert target.tolist() == [0, 1]
    assert not {"customerID", "Churn", "churn_flag"}.intersection(features.columns)
    assert "No internet service" in features["OnlineSecurity"].tolist()