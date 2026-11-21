"""Tests for raw data loading using temporary test fixtures only."""

import pandas as pd
import pytest

from src.data_loader import load_raw_data


def test_missing_file_error_includes_download_instructions(tmp_path) -> None:
    """A missing raw file explains where the real dataset belongs."""
    with pytest.raises(FileNotFoundError, match="Download the IBM Telco Customer Churn CSV"):
        load_raw_data(tmp_path / "missing.csv")


def test_load_raw_data_preserves_values_as_loaded(tmp_path) -> None:
    """Loading does not strip or clean source text."""
    source = tmp_path / "fixture.csv"
    source.write_text("name,value\n  A  ,1\n", encoding="utf-8")
    dataframe = load_raw_data(source)
    assert dataframe.loc[0, "name"] == "  A  "
    assert dataframe.loc[0, "value"] == 1
    assert list(dataframe.columns) == ["name", "value"]