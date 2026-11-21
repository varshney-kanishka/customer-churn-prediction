"""SQLite tests using temporary in-memory test fixtures only."""

import sqlite3

import pandas as pd
import pytest

from src.database import (
    create_schema,
    get_connection,
    load_customers,
    read_customers,
    read_churn_by_dimension,
)


def customer_fixture() -> pd.DataFrame:
    """Return a tiny hand-written customer fixture used only in tests."""
    return pd.DataFrame(
        {
            "customerID": ["A", "B"],
            "gender": ["Female", "Male"],
            "SeniorCitizen": [0, 1],
            "Partner": ["Yes", "No"],
            "Dependents": ["No", "Yes"],
            "tenure": [10, 20],
            "PhoneService": ["Yes", "Yes"],
            "MultipleLines": ["No", "Yes"],
            "InternetService": ["DSL", "Fiber optic"],
            "OnlineSecurity": ["Yes", "No"],
            "OnlineBackup": ["No", "Yes"],
            "DeviceProtection": ["No", "Yes"],
            "TechSupport": ["Yes", "No"],
            "StreamingTV": ["No", "Yes"],
            "StreamingMovies": ["No", "Yes"],
            "Contract": ["Month-to-month", "Two year"],
            "PaperlessBilling": ["Yes", "No"],
            "PaymentMethod": ["Electronic check", "Mailed check"],
            "MonthlyCharges": [50.0, 70.0],
            "TotalCharges": [500.0, 1400.0],
            "Churn": ["Yes", "No"],
            "churn_flag": [1, 0],
        }
    )


def test_schema_loads_fixture_and_reads_parameterized_dimension() -> None:
    """The schema accepts fixtures and approved dimension queries return rows."""
    with get_connection(":memory:") as connection:
        create_schema(connection)
        assert load_customers(connection, customer_fixture()) == 2
        assert len(read_customers(connection)) == 2
        result = read_churn_by_dimension(connection, "Contract")
        assert set(result["category"]) == {"Month-to-month", "Two year"}


def test_foreign_key_blocks_unknown_risk_customer() -> None:
    """Risk rows cannot reference a customer absent from the customers table."""
    with get_connection(":memory:") as connection:
        create_schema(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO risk_scores VALUES (?, ?, ?, ?, ?)",
                ("missing", 0.9, "High", "Yes", "test"),
            )