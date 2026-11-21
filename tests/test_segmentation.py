"""Tests for risk segmentation using small hand-written fixtures only."""

import pandas as pd
import pytest

from src.segmentation import assign_risk_tier, profile_risk_tiers


def risk_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return tiny risk and customer fixtures used only for tests."""
    risk_scores = pd.DataFrame(
        {
            "customerID": ["A", "B", "C", "D", "E", "F"],
            "churn_probability": [0.1, 0.2, 0.4, 0.5, 0.8, 0.9],
            "actual_churn": ["No", "No", "No", "Yes", "Yes", "Yes"],
        }
    )
    customer_data = pd.DataFrame(
        {
            "tenure": [5, 10, 20, 25, 40, 50],
            "MonthlyCharges": [20, 30, 40, 50, 60, 70],
            "Contract": ["Month-to-month"] * 6,
            "InternetService": ["DSL"] * 6,
            "PaymentMethod": ["Mailed check"] * 6,
        }
    )
    return risk_scores, customer_data


def test_assign_risk_tier_uses_ordered_cutoffs() -> None:
    """Probabilities are assigned to the expected ordered tiers."""
    tiers = assign_risk_tier([0.1, 0.3, 0.7], 0.25, 0.6)
    assert tiers.tolist() == ["Low", "Medium", "High"]


def test_assign_risk_tier_rejects_invalid_cutoffs() -> None:
    """Invalid cutoff order is rejected instead of silently mislabelled."""
    with pytest.raises(ValueError):
        assign_risk_tier([0.2], 0.7, 0.6)


def test_profile_reports_rising_churn_rate() -> None:
    """Tier profiling reports the expected increasing observed churn rate."""
    risk_scores, customer_data = risk_fixture()
    risk_scores["risk_tier"] = assign_risk_tier(
        risk_scores["churn_probability"], 0.3, 0.6
    )
    profile = profile_risk_tiers(customer_data, risk_scores)
    assert profile["actual_churn_rate"].tolist() == [0.0, 50.0, 100.0]