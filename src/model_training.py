"""Training, cross-validation, tuning, and test evaluation for churn models."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier


RANDOM_STATE = 42
SCORING = {
    "roc_auc": "roc_auc",
    "f1": "f1",
    "precision": "precision",
    "recall": "recall",
}
MODEL_FILENAMES = {
    "Logistic Regression": "logistic_regression.joblib",
    "Random Forest": "random_forest.joblib",
    "XGBoost": "xgboost.joblib",
}


def create_preprocessor(
    numeric_columns: list[str], categorical_columns: list[str]
) -> ColumnTransformer:
    """Create the numeric scaler and categorical one-hot encoder."""
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), numeric_columns),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_columns,
            ),
        ],
        remainder="drop",
    )


def build_model_pipeline(
    model_name: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    scale_pos_weight: float,
) -> Pipeline:
    """Build a complete preprocessing-and-model pipeline."""
    models: dict[str, Any] = {
        "Logistic Regression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1
        ),
        "XGBoost": XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
    }
    if model_name not in models:
        raise ValueError(f"Unknown model name: {model_name}")
    return Pipeline(
        steps=[
            ("preprocessor", create_preprocessor(numeric_columns, categorical_columns)),
            ("model", models[model_name]),
        ]
    )


def parameter_grid(model_name: str) -> dict[str, list[Any]]:
    """Return a small tuning grid that is searched on training data only."""
    grids = {
        "Logistic Regression": {"model__C": [0.1, 1.0, 10.0]},
        "Random Forest": {
            "model__n_estimators": [150, 250],
            "model__max_depth": [None, 10],
            "model__min_samples_leaf": [1, 2],
        },
        "XGBoost": {
            "model__n_estimators": [150, 250],
            "model__max_depth": [3, 5],
            "model__learning_rate": [0.05, 0.1],
        },
    }
    if model_name not in grids:
        raise ValueError(f"Unknown model name: {model_name}")
    return grids[model_name]


def tune_model(
    pipeline: Pipeline, model_name: str, features: pd.DataFrame, target: pd.Series
) -> GridSearchCV:
    """Tune one pipeline using only the supplied training data."""
    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid(model_name),
        scoring="roc_auc",
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE),
        n_jobs=-1,
        refit=True,
    )
    search.fit(features, target)
    return search


def cross_validation_metrics(
    estimator: Pipeline, features: pd.DataFrame, target: pd.Series
) -> dict[str, dict[str, float]]:
    """Calculate mean and standard deviation of five-fold training CV metrics."""
    results = cross_validate(
        estimator=estimator,
        X=features,
        y=target,
        scoring=SCORING,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
        n_jobs=-1,
        return_train_score=False,
    )
    return {
        metric: {
            "mean": round(float(np.mean(results[f"test_{metric}"])), 6),
            "std": round(float(np.std(results[f"test_{metric}"])), 6),
        }
        for metric in SCORING
    }


def evaluate_test_set(
    estimator: Pipeline, features: pd.DataFrame, target: pd.Series
) -> dict[str, Any]:
    """Evaluate a fitted pipeline once on the untouched test set."""
    predictions = estimator.predict(features)
    probabilities = estimator.predict_proba(features)[:, 1]
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions, labels=[0, 1]
    ).ravel()
    return {
        "accuracy": round(float(accuracy_score(target, predictions)), 6),
        "precision": round(float(precision_score(target, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(target, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(target, predictions, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(target, probabilities)), 6),
        "confusion_matrix": {
            "true_negative": int(true_negative),
            "false_positive": int(false_positive),
            "false_negative": int(false_negative),
            "true_positive": int(true_positive),
        },
    }