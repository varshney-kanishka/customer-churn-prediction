"""Tests for evaluation metrics using hand-computed test fixtures only."""

import numpy as np
import pandas as pd

from src.evaluation import classification_metrics, choose_threshold, threshold_table


def test_classification_metrics_match_hand_computed_values() -> None:
    """Perfectly separated probabilities produce the expected metrics."""
    target = pd.Series([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.4, 0.6, 0.9])
    metrics = classification_metrics(target, probabilities, threshold=0.5)
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc"] == 1.0
    assert metrics["confusion_matrix"] == {
        "true_negative": 2,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 2,
    }


def test_threshold_selection_uses_highest_f1_then_recall() -> None:
    """Threshold selection chooses the best supplied training result."""
    table = threshold_table(pd.Series([0, 1]), np.array([0.2, 0.8]), [0.2, 0.5])
    assert choose_threshold(table) == 0.5