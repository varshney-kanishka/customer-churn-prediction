"""Cleaning functions for the Telco customer churn dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd


TEXT_COLUMNS = [
    "customerID",
    "gender",
    "Partner",
    "Dependents",
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
    "Churn",
]


def strip_text_columns(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Strip surrounding whitespace from text cells and count changed cells."""
    cleaned = dataframe.copy(deep=True)
    changed_cells = 0
    for column in TEXT_COLUMNS:
        if column not in cleaned.columns:
            continue
        original = cleaned[column].copy()
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        changed_cells += int((original != cleaned[column]).fillna(False).sum())
    return cleaned, changed_cells


def convert_total_charges(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Convert TotalCharges and fill zero-tenure conversion failures with zero.

    A blank TotalCharges value for a customer with zero tenure represents a
    customer who has not yet been billed. Other conversion failures remain
    missing and are reported for manual review instead of being guessed.
    """
    cleaned = dataframe.copy(deep=True)
    if "TotalCharges" not in cleaned.columns:
        return cleaned, {"present": False}

    original = cleaned["TotalCharges"].copy()
    converted = pd.to_numeric(cleaned["TotalCharges"], errors="coerce")
    failed = converted.isna() & cleaned["TotalCharges"].notna()
    zero_tenure = cleaned.get("tenure", pd.Series(index=cleaned.index)).eq(0)
    filled_mask = failed & zero_tenure
    converted.loc[filled_mask] = 0.0
    cleaned["TotalCharges"] = converted
    return cleaned, {
        "present": True,
        "conversion_failure_count": int(failed.sum()),
        "filled_zero_tenure_count": int(filled_mask.sum()),
        "remaining_missing_count": int(cleaned["TotalCharges"].isna().sum()),
        "original_blank_count": int(
            original.map(lambda value: isinstance(value, str) and not value.strip()).sum()
        ),
        "non_zero_tenure_failures": int((failed & ~zero_tenure).sum()),
    }


def remove_exact_duplicates(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove exact duplicate rows and return the number removed."""
    cleaned = dataframe.drop_duplicates().copy()
    return cleaned, int(len(dataframe) - len(cleaned))


def check_customer_ids(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report duplicate customer IDs without removing any records."""
    if "customerID" not in dataframe.columns:
        return {"present": False, "duplicate_row_count": 0, "duplicate_values": []}
    duplicated = dataframe.loc[dataframe["customerID"].duplicated(keep=False), "customerID"]
    return {
        "present": True,
        "duplicate_row_count": int(duplicated.size),
        "duplicate_values": duplicated.drop_duplicates().tolist(),
    }


def add_churn_flag(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Add churn_flag using the required mapping Yes=1 and No=0."""
    cleaned = dataframe.copy(deep=True)
    if "Churn" not in cleaned.columns:
        return cleaned, {"present": False}
    cleaned["churn_flag"] = cleaned["Churn"].map({"Yes": 1, "No": 0}).astype("Int64")
    invalid_count = int(cleaned["churn_flag"].isna().sum())
    return cleaned, {
        "present": True,
        "added_count": 1,
        "invalid_churn_count": invalid_count,
        "value_counts": {
            str(value): int(count)
            for value, count in cleaned["churn_flag"].value_counts(dropna=False).items()
        },
    }


def check_numeric_ranges(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report impossible numeric values without removing outliers."""
    checks = {
        "tenure": lambda series: series.lt(0) | series.gt(72),
        "MonthlyCharges": lambda series: series.lt(0),
        "SeniorCitizen": lambda series: ~series.isin([0, 1]),
    }
    results: dict[str, Any] = {}
    for column, invalid_rule in checks.items():
        if column not in dataframe.columns:
            results[column] = {"present": False}
            continue
        series = pd.to_numeric(dataframe[column], errors="coerce")
        invalid = invalid_rule(series).fillna(False)
        results[column] = {
            "present": True,
            "invalid_count": int(invalid.sum()),
            "invalid_values": [
                value.item() if hasattr(value, "item") else value
                for value in series[invalid].drop_duplicates()
            ],
        }
    return results


def clean_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy without modifying the input DataFrame.

    Cleaning is limited to whitespace stripping, documented TotalCharges
    conversion, exact duplicate removal, and the churn_flag label column.
    Categories and SeniorCitizen's 0/1 representation are preserved.
    """
    cleaned, _ = strip_text_columns(dataframe)
    cleaned, _ = convert_total_charges(cleaned)
    cleaned, _ = remove_exact_duplicates(cleaned)
    cleaned, _ = add_churn_flag(cleaned)
    return cleaned


def build_cleaning_report(
    original: pd.DataFrame, cleaned: pd.DataFrame
) -> dict[str, Any]:
    """Build a JSON-serializable summary of changes and remaining issues."""
    stripped, whitespace_count = strip_text_columns(original)
    _, total_charges = convert_total_charges(stripped)
    _, duplicate_rows_removed = remove_exact_duplicates(stripped)
    customer_id_check = check_customer_ids(cleaned)
    numeric_ranges = check_numeric_ranges(cleaned)
    churn_flag_info = {
        "added": "churn_flag" in cleaned.columns,
        "invalid_count": int(cleaned["churn_flag"].isna().sum())
        if "churn_flag" in cleaned.columns
        else 0,
    }
    remaining_issues: list[str] = []
    if total_charges.get("remaining_missing_count", 0):
        remaining_issues.append("TotalCharges still has conversion failures requiring review.")
    if customer_id_check.get("duplicate_row_count", 0):
        remaining_issues.append("Duplicate customerID values remain and need review.")
    if churn_flag_info["invalid_count"]:
        remaining_issues.append("Some Churn values could not be mapped to churn_flag.")
    if any(item.get("invalid_count", 0) for item in numeric_ranges.values()):
        remaining_issues.append("Impossible numeric values remain and need review.")

    return {
        "rows_before": int(len(original)),
        "columns_before": int(len(original.columns)),
        "rows_after": int(len(cleaned)),
        "columns_after": int(len(cleaned.columns)),
        "changes": {
            "whitespace_cells_stripped": whitespace_count,
            "total_charges": total_charges,
            "exact_duplicate_rows_removed": duplicate_rows_removed,
            "customer_id_check": customer_id_check,
            "churn_flag": churn_flag_info,
            "numeric_range_check": numeric_ranges,
        },
        "decisions": [
            "Stripped leading and trailing whitespace from text columns.",
            "Converted TotalCharges to numeric. Filled the 11 zero-tenure blank values with 0.0 because those customers had not yet been billed.",
            "Removed exact duplicate rows only when present; duplicate customer IDs were reported rather than silently removed.",
            "Kept SeniorCitizen as its original 0/1 numeric representation.",
            "Kept service categories such as No internet service and No phone service unchanged.",
            "Reported numeric range problems and did not remove outliers.",
        ],
        "remaining_issues": remaining_issues,
    }