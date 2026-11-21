"""Out-of-fold churn probabilities and customer risk tiers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_predict


RANDOM_STATE = 42


def assign_risk_tier(
    probabilities: pd.Series | np.ndarray,
    low_medium_cutoff: float,
    medium_high_cutoff: float,
) -> pd.Series:
    """Assign Low, Medium, or High tiers from two probability cutoffs."""
    if not 0 <= low_medium_cutoff < medium_high_cutoff <= 1:
        raise ValueError("Risk cutoffs must satisfy 0 <= low < medium < high <= 1.")
    values = pd.Series(probabilities)
    return pd.Series(
        pd.cut(
            values,
            bins=[-np.inf, low_medium_cutoff, medium_high_cutoff, np.inf],
            labels=["Low", "Medium", "High"],
            include_lowest=True,
        ),
        index=values.index,
        name="risk_tier",
    )


def out_of_fold_train_probabilities(
    model: Any, features: pd.DataFrame, target: pd.Series
) -> np.ndarray:
    """Generate training probabilities without fitting any row's own label."""
    cross_validator = StratifiedKFold(
        n_splits=5, shuffle=True, random_state=RANDOM_STATE
    )
    return cross_val_predict(
        clone(model),
        features,
        target,
        cv=cross_validator,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]


def build_risk_scores(
    dataframe: pd.DataFrame,
    features: pd.DataFrame,
    target: pd.Series,
    train_indices: list[int],
    test_indices: list[int],
    model: Any,
    low_medium_cutoff: float,
    medium_high_cutoff: float,
) -> pd.DataFrame:
    """Create one risk score per customer using OOF train and final test scores."""
    train_features = features.loc[train_indices]
    train_target = target.loc[train_indices]
    train_probabilities = out_of_fold_train_probabilities(
        model, train_features, train_target
    )
    test_probabilities = model.predict_proba(features.loc[test_indices])[:, 1]
    probability_by_index = pd.Series(index=train_indices + test_indices, dtype=float)
    probability_by_index.loc[train_indices] = train_probabilities
    probability_by_index.loc[test_indices] = test_probabilities
    result = dataframe.loc[probability_by_index.index, ["customerID", "Churn"]].copy()
    result["churn_probability"] = probability_by_index
    result["risk_tier"] = assign_risk_tier(
        result["churn_probability"], low_medium_cutoff, medium_high_cutoff
    ).to_numpy()
    result = result.rename(columns={"Churn": "actual_churn"})
    return result.reset_index(drop=True)


def profile_risk_tiers(dataframe: pd.DataFrame, risk_scores: pd.DataFrame) -> pd.DataFrame:
    """Summarize tier size, observed churn, and customer characteristics."""
    joined = risk_scores.join(
        dataframe[["tenure", "MonthlyCharges", "Contract", "InternetService", "PaymentMethod"]],
        how="left",
    )
    profiles = []
    for tier in ["Low", "Medium", "High"]:
        group = joined[joined["risk_tier"] == tier]
        profiles.append(
            {
                "risk_tier": tier,
                "customers": int(len(group)),
                "actual_churn_rate": round(float(group["actual_churn"].eq("Yes").mean() * 100), 2)
                if len(group)
                else 0.0,
                "average_tenure": round(float(group["tenure"].mean()), 2) if len(group) else 0.0,
                "average_monthly_charges": round(float(group["MonthlyCharges"].mean()), 2)
                if len(group)
                else 0.0,
                "common_contract": str(group["Contract"].mode().iat[0]) if len(group) else "",
                "common_internet_service": str(group["InternetService"].mode().iat[0])
                if len(group)
                else "",
                "common_payment_method": str(group["PaymentMethod"].mode().iat[0])
                if len(group)
                else "",
            }
        )
    return pd.DataFrame(profiles)