"""Validation checks for the raw Telco customer churn dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd


EXPECTED_COLUMNS = [
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]

NUMERIC_COLUMNS = ["tenure", "MonthlyCharges", "SeniorCitizen"]
TARGET_COLUMN = "Churn"

EXPECTED_CATEGORIES = {
    "gender": ["Female", "Male"],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["Yes", "No", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["Yes", "No", "No internet service"],
    "OnlineBackup": ["Yes", "No", "No internet service"],
    "DeviceProtection": ["Yes", "No", "No internet service"],
    "TechSupport": ["Yes", "No", "No internet service"],
    "StreamingTV": ["Yes", "No", "No internet service"],
    "StreamingMovies": ["Yes", "No", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
    "Churn": ["Yes", "No"],
}


def _json_value(value: Any) -> Any:
    """Convert pandas and NumPy scalar values into JSON-compatible values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def check_shape(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Return the number of rows and columns in the DataFrame."""
    return {"rows": int(dataframe.shape[0]), "columns": int(dataframe.shape[1])}


def check_columns(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Compare loaded column names with the expected schema."""
    actual = list(dataframe.columns)
    missing = [column for column in EXPECTED_COLUMNS if column not in actual]
    unexpected = [column for column in actual if column not in EXPECTED_COLUMNS]
    return {
        "expected": EXPECTED_COLUMNS,
        "actual": actual,
        "missing": missing,
        "unexpected": unexpected,
    }


def check_data_types(dataframe: pd.DataFrame) -> dict[str, str]:
    """Return the dtype pandas assigned to every loaded column."""
    return {column: str(dtype) for column, dtype in dataframe.dtypes.items()}


def check_missing_values(dataframe: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    """Return null counts and percentages for every column."""
    row_count = len(dataframe)
    return {
        column: {
            "count": int(dataframe[column].isna().sum()),
            "percentage": round(
                float(dataframe[column].isna().mean() * 100) if row_count else 0.0,
                4,
            ),
        }
        for column in dataframe.columns
    }


def check_blank_strings(dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Count blank or whitespace-only string values without changing the data."""
    results: dict[str, dict[str, Any]] = {}
    for column in dataframe.columns:
        blank_count = int(
            dataframe[column].map(
                lambda value: isinstance(value, str) and not value.strip()
            ).sum()
        )
        results[column] = {
            "count": blank_count,
            "percentage": round(float(blank_count / len(dataframe) * 100), 4)
            if len(dataframe)
            else 0.0,
        }

    total_charges_conversion = {"failed_count": 0, "can_convert_to_numeric": True}
    if "TotalCharges" in dataframe.columns:
        converted = pd.to_numeric(dataframe["TotalCharges"], errors="coerce")
        failed = converted.isna() & dataframe["TotalCharges"].notna()
        total_charges_conversion = {
            "failed_count": int(failed.sum()),
            "can_convert_to_numeric": bool(not failed.any()),
            "blank_string_count": results["TotalCharges"]["count"],
        }
    results["TotalCharges_numeric_conversion"] = total_charges_conversion
    return results


def check_duplicates(dataframe: pd.DataFrame) -> dict[str, int]:
    """Count duplicate rows and duplicate customer IDs."""
    duplicate_customer_ids = 0
    if "customerID" in dataframe.columns:
        duplicate_customer_ids = int(dataframe["customerID"].duplicated(keep=False).sum())
    return {
        "duplicate_rows": int(dataframe.duplicated().sum()),
        "duplicate_customer_id_rows": duplicate_customer_ids,
    }


def check_target(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report Churn values, counts, and class percentages."""
    if TARGET_COLUMN not in dataframe.columns:
        return {"present": False, "unique_values": [], "counts": {}, "percentages": {}}
    counts = dataframe[TARGET_COLUMN].value_counts(dropna=False)
    total = len(dataframe)
    return {
        "present": True,
        "unique_values": [_json_value(value) for value in counts.index],
        "counts": {str(_json_value(value)): int(count) for value, count in counts.items()},
        "percentages": {
            str(_json_value(value)): round(float(count / total * 100), 4)
            if total
            else 0.0
            for value, count in counts.items()
        },
    }


def check_numeric_columns(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report numeric summaries and values below the valid minimum of zero."""
    results: dict[str, Any] = {}
    for column in NUMERIC_COLUMNS:
        if column not in dataframe.columns:
            results[column] = {"present": False}
            continue
        series = pd.to_numeric(dataframe[column], errors="coerce")
        negative_values = series[series < 0].dropna()
        results[column] = {
            "present": True,
            "min": _json_value(series.min()),
            "max": _json_value(series.max()),
            "mean": round(float(series.mean()), 6) if not series.dropna().empty else None,
            "negative_count": int(negative_values.count()),
            "negative_values": [_json_value(value) for value in negative_values.unique()],
        }
    return results


def check_categorical_columns(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report category counts and values outside the documented categories."""
    results: dict[str, Any] = {}
    for column, expected in EXPECTED_CATEGORIES.items():
        if column not in dataframe.columns:
            results[column] = {"present": False}
            continue
        counts = dataframe[column].value_counts(dropna=False)
        actual_values = [_json_value(value) for value in counts.index]
        unexpected = [value for value in actual_values if value not in expected and value is not None]
        normalized: dict[str, list[Any]] = {}
        for value in actual_values:
            if isinstance(value, str):
                normalized.setdefault(value.strip().lower(), []).append(value)
        inconsistent_spellings = [values for values in normalized.values() if len(set(values)) > 1]
        results[column] = {
            "present": True,
            "expected_values": expected,
            "unique_values": actual_values,
            "counts": {str(value): int(count) for value, count in counts.items()},
            "unexpected_values": unexpected,
            "inconsistent_spellings": inconsistent_spellings,
        }
    return results


def _overall_status(results: dict[str, Any]) -> tuple[str, list[str]]:
    """Determine the overall status and concise issues from individual checks."""
    issues: list[str] = []
    if results["columns"]["missing"] or results["columns"]["unexpected"]:
        issues.append("Column names do not match the expected schema.")
    if not results["target"]["present"]:
        issues.append("The Churn target column is missing.")
    if any(item["negative_count"] for item in results["numeric_columns"].values() if item["present"]):
        issues.append("One or more numeric columns contain negative values.")
    if any(item["count"] for item in results["missing_values"].values()):
        issues.append("Missing values are present.")
    if any(
        details["count"]
        for column, details in results["blank_strings"].items()
        if column != "TotalCharges_numeric_conversion"
    ):
        issues.append("Blank or whitespace-only strings are present.")
    if results["blank_strings"]["TotalCharges_numeric_conversion"]["failed_count"]:
        issues.append("Some TotalCharges values cannot be converted to numbers.")
    if results["duplicates"]["duplicate_rows"]:
        issues.append("Duplicate rows are present.")
    if results["duplicates"]["duplicate_customer_id_rows"]:
        issues.append("Duplicate customerID values are present.")
    if any(
        details.get("unexpected_values") or details.get("inconsistent_spellings")
        for details in results["categorical_columns"].values()
        if details["present"]
    ):
        issues.append("Unexpected or inconsistently spelled categorical values are present.")

    blocking = bool(
        results["columns"]["missing"]
        or results["columns"]["unexpected"]
        or not results["target"]["present"]
        or any(item["negative_count"] for item in results["numeric_columns"].values() if item["present"])
    )
    if blocking:
        return "FAIL", issues
    return ("PASS WITH WARNINGS", issues) if issues else ("PASS", issues)


def validate_dataset(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Run all Phase 2 checks and return JSON-serializable results."""
    results: dict[str, Any] = {
        "shape": check_shape(dataframe),
        "columns": check_columns(dataframe),
        "data_types": check_data_types(dataframe),
        "missing_values": check_missing_values(dataframe),
        "blank_strings": check_blank_strings(dataframe),
        "duplicates": check_duplicates(dataframe),
        "target": check_target(dataframe),
        "numeric_columns": check_numeric_columns(dataframe),
        "categorical_columns": check_categorical_columns(dataframe),
    }
    status, issues = _overall_status(results)
    results["overall_status"] = status
    results["issues"] = issues
    return results