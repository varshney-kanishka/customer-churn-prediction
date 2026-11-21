"""Tests for Phase 2 validation checks using small test fixtures only."""

import pandas as pd

from src.data_validation import (
    check_blank_strings,
    check_columns,
    check_duplicates,
    check_missing_values,
    check_numeric_columns,
    check_shape,
    check_target,
    validate_dataset,
)


def validation_fixture() -> pd.DataFrame:
    """Return a tiny hand-written DataFrame used only as a test fixture."""
    return pd.DataFrame(
        {
            "customerID": ["A", "A", "B"],
            "TotalCharges": [" ", "12.5", "not-a-number"],
            "tenure": [0, 1, -1],
            "MonthlyCharges": [10.0, 20.0, 30.0],
            "SeniorCitizen": [0, 1, 0],
            "Churn": ["No", "Yes", "Maybe"],
        }
    )


def test_shape_and_columns_report_actual_schema() -> None:
    """Shape and schema checks report actual values rather than assumptions."""
    dataframe = validation_fixture()
    assert check_shape(dataframe) == {"rows": 3, "columns": 6}
    columns = check_columns(dataframe)
    assert columns["actual"] == list(dataframe.columns)
    assert "gender" in columns["missing"]


def test_missing_and_blank_values_are_counted() -> None:
    """Missing and whitespace-only values are reported separately."""
    dataframe = validation_fixture()
    dataframe.loc[2, "TotalCharges"] = None
    missing = check_missing_values(dataframe)
    blanks = check_blank_strings(dataframe)
    assert missing["TotalCharges"]["count"] == 1
    assert blanks["TotalCharges"]["count"] == 1
    assert blanks["TotalCharges_numeric_conversion"]["failed_count"] == 1


def test_total_charges_conversion_failures_are_reported() -> None:
    """Non-numeric TotalCharges values are counted without being changed."""
    result = check_blank_strings(validation_fixture())
    assert result["TotalCharges_numeric_conversion"]["failed_count"] == 2


def test_duplicates_and_numeric_impossible_values_are_reported() -> None:
    """Duplicate IDs and negative numeric values are visible in the report."""
    dataframe = validation_fixture()
    duplicates = check_duplicates(dataframe)
    numeric = check_numeric_columns(dataframe)
    assert duplicates["duplicate_customer_id_rows"] == 2
    assert numeric["tenure"]["negative_count"] == 1


def test_target_reports_values_counts_and_percentages() -> None:
    """The target check reports every observed class and its balance."""
    result = check_target(validation_fixture())
    assert result["unique_values"] == ["No", "Yes", "Maybe"]
    assert result["counts"]["No"] == 1
    assert result["percentages"]["Yes"] == 33.3333


def test_validation_result_is_json_serializable_and_fails_blocking_data() -> None:
    """The combined result is serializable and flags schema/range problems."""
    import json

    result = validate_dataset(validation_fixture())
    json.dumps(result)
    assert result["overall_status"] == "FAIL"
    assert result["issues"]