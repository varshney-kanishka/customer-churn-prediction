"""Tests for Phase 3 cleaning using hand-written test fixtures only."""

import pandas as pd

from src.data_cleaning import (
    add_churn_flag,
    check_customer_ids,
    clean_data,
    convert_total_charges,
    remove_exact_duplicates,
    strip_text_columns,
)


def cleaning_fixture() -> pd.DataFrame:
    """Return a tiny DataFrame used only as a cleaning test fixture."""
    return pd.DataFrame(
        {
            "customerID": [" A ", " A ", "B"],
            "Churn": [" No ", " No ", "Yes"],
            "TotalCharges": [" ", "10.0", "25.0"],
            "tenure": [0, 1, 2],
            "SeniorCitizen": [0, 0, 1],
        }
    )


def test_clean_data_does_not_modify_input_and_strips_text() -> None:
    """Cleaning returns a new DataFrame and strips text values."""
    dataframe = cleaning_fixture()
    original = dataframe.copy(deep=True)
    cleaned = clean_data(dataframe)
    pd.testing.assert_frame_equal(dataframe, original)
    assert cleaned.loc[0, "customerID"] == "A"
    assert cleaned.loc[0, "Churn"] == "No"


def test_zero_tenure_total_charges_are_filled_and_converted() -> None:
    """Zero-tenure blank billing values become numeric zero."""
    cleaned, details = convert_total_charges(cleaning_fixture())
    assert cleaned.loc[0, "TotalCharges"] == 0.0
    assert str(cleaned["TotalCharges"].dtype) == "float64"
    assert details["filled_zero_tenure_count"] == 1


def test_exact_duplicates_are_removed_but_duplicate_ids_are_reported() -> None:
    """Exact duplicates are removed while ID checks remain explicit."""
    dataframe = cleaning_fixture()
    deduplicated, removed = remove_exact_duplicates(dataframe)
    assert removed == 0
    assert check_customer_ids(deduplicated)["duplicate_row_count"] == 2


def test_churn_flag_maps_yes_and_no() -> None:
    """Churn remains text and receives the requested numeric flag."""
    cleaned = clean_data(cleaning_fixture())
    assert cleaned["churn_flag"].tolist() == [0, 0, 1]
    assert cleaned["Churn"].tolist() == ["No", "No", "Yes"]


def test_whitespace_function_reports_changed_cells() -> None:
    """The whitespace step reports how many cells it changed."""
    cleaned, changed = strip_text_columns(cleaning_fixture())
    assert changed == 4
    assert cleaned.loc[0, "customerID"] == "A"