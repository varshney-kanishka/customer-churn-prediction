"""Evaluation helpers for saved churn pipelines and held-out predictions."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def classification_metrics(
    target: pd.Series, probabilities: np.ndarray, threshold: float = 0.5
) -> dict[str, Any]:
    """Calculate classification metrics from probabilities at one threshold."""
    predictions = (probabilities >= threshold).astype(int)
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions, labels=[0, 1]
    ).ravel()
    return {
        "threshold": round(float(threshold), 6),
        "accuracy": round(float(accuracy_score(target, predictions)), 6),
        "precision": round(float(precision_score(target, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(target, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(target, predictions, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(target, probabilities)), 6),
        "pr_auc": round(float(average_precision_score(target, probabilities)), 6),
        "confusion_matrix": {
            "true_negative": int(true_negative),
            "false_positive": int(false_positive),
            "false_negative": int(false_negative),
            "true_positive": int(true_positive),
        },
    }


def curve_data(target: pd.Series, probabilities: np.ndarray) -> dict[str, np.ndarray]:
    """Return ROC and precision-recall curve coordinates."""
    false_positive_rate, true_positive_rate, roc_thresholds = roc_curve(target, probabilities)
    precision, recall, pr_thresholds = precision_recall_curve(target, probabilities)
    return {
        "false_positive_rate": false_positive_rate,
        "true_positive_rate": true_positive_rate,
        "roc_thresholds": roc_thresholds,
        "precision": precision,
        "recall": recall,
        "pr_thresholds": pr_thresholds,
    }


def threshold_table(
    target: pd.Series, probabilities: np.ndarray, thresholds: list[float]
) -> pd.DataFrame:
    """Evaluate precision, recall, and F1 at candidate thresholds."""
    rows = []
    for threshold in thresholds:
        metrics = classification_metrics(target, probabilities, threshold)
        rows.append(
            {
                "threshold": metrics["threshold"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
            }
        )
    return pd.DataFrame(rows)


def choose_threshold(table: pd.DataFrame) -> float:
    """Choose the F1-maximizing threshold using training OOF predictions only."""
    best = table.sort_values(["f1", "recall", "threshold"], ascending=[False, False, True]).iloc[0]
    return float(best["threshold"])


def readable_feature_names(model: Any) -> list[str]:
    """Return readable transformed feature names from a saved pipeline."""
    names = model.named_steps["preprocessor"].get_feature_names_out()
    return [name.replace("numeric__", "").replace("categorical__", "") for name in names]


def logistic_driver_table(model: Any, top_n: int = 10) -> pd.DataFrame:
    """Return the strongest logistic coefficients and their odds ratios."""
    estimator = model.named_steps["model"]
    names = readable_feature_names(model)
    coefficients = estimator.coef_[0]
    table = pd.DataFrame(
        {
            "feature": names,
            "coefficient": coefficients,
            "odds_ratio": np.exp(coefficients),
            "absolute_coefficient": np.abs(coefficients),
        }
    ).sort_values("absolute_coefficient", ascending=False)
    return table.head(top_n).drop(columns=["absolute_coefficient"]).reset_index(drop=True)


def permutation_driver_table(
    model: Any,
    features: pd.DataFrame,
    target: pd.Series,
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank raw input features by test-set permutation importance."""
    importance = permutation_importance(
        model,
        features,
        target,
        scoring="roc_auc",
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
    )
    table = pd.DataFrame(
        {
            "feature": features.columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    return table.head(top_n).reset_index(drop=True)


def cost_scenarios(
    metrics: dict[str, Any],
    assumptions: list[dict[str, float]],
) -> list[dict[str, float]]:
    """Calculate placeholder net values from a threshold confusion matrix.

    This is a scenario calculator, not a financial estimate. It assumes a
    retained value for each true positive and an offer cost for each offer.
    """
    matrix = metrics["confusion_matrix"]
    rows = []
    for assumption in assumptions:
        offers = matrix["true_positive"] + matrix["false_positive"]
        net_value = (
            assumption["retained_customer_value"] * matrix["true_positive"]
            - assumption["offer_cost"] * offers
        )
        rows.append(
            {
                **assumption,
                "offers": float(offers),
                "placeholder_net_value": round(float(net_value), 2),
            }
        )
    return rows