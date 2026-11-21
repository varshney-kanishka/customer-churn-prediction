"""SQLite schema, loading, and read-query helpers for the churn dashboard."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Iterator

import pandas as pd

from src.utils import DATABASE_PATH


CUSTOMER_COLUMNS = [
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
    "churn_flag",
]


@contextmanager
def get_connection(path: str | Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with foreign keys enabled and safe cleanup."""
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the four dashboard tables and useful indexes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customerID TEXT PRIMARY KEY,
            gender TEXT NOT NULL,
            SeniorCitizen INTEGER NOT NULL CHECK (SeniorCitizen IN (0, 1)),
            Partner TEXT NOT NULL,
            Dependents TEXT NOT NULL,
            tenure INTEGER NOT NULL,
            PhoneService TEXT NOT NULL,
            MultipleLines TEXT NOT NULL,
            InternetService TEXT NOT NULL,
            OnlineSecurity TEXT NOT NULL,
            OnlineBackup TEXT NOT NULL,
            DeviceProtection TEXT NOT NULL,
            TechSupport TEXT NOT NULL,
            StreamingTV TEXT NOT NULL,
            StreamingMovies TEXT NOT NULL,
            Contract TEXT NOT NULL,
            PaperlessBilling TEXT NOT NULL,
            PaymentMethod TEXT NOT NULL,
            MonthlyCharges REAL NOT NULL,
            TotalCharges REAL NOT NULL,
            Churn TEXT NOT NULL CHECK (Churn IN ('Yes', 'No')),
            churn_flag INTEGER NOT NULL CHECK (churn_flag IN (0, 1))
        );

        CREATE TABLE IF NOT EXISTS risk_scores (
            customerID TEXT PRIMARY KEY,
            risk_score REAL NOT NULL,
            risk_tier TEXT NOT NULL CHECK (risk_tier IN ('Low', 'Medium', 'High')),
            actual_churn TEXT NOT NULL CHECK (actual_churn IN ('Yes', 'No')),
            source TEXT NOT NULL CHECK (source IN ('out-of-fold', 'test')),
            FOREIGN KEY (customerID) REFERENCES customers(customerID)
        );

        CREATE TABLE IF NOT EXISTS model_metrics (
            model_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            split TEXT NOT NULL CHECK (split IN ('CV', 'test')),
            PRIMARY KEY (model_name, metric, split)
        );

        CREATE TABLE IF NOT EXISTS tier_summary (
            risk_tier TEXT PRIMARY KEY CHECK (risk_tier IN ('Low', 'Medium', 'High')),
            customers INTEGER NOT NULL,
            actual_churn_rate REAL NOT NULL,
            average_tenure REAL NOT NULL,
            average_monthly_charges REAL NOT NULL,
            common_contract TEXT NOT NULL,
            common_internet_service TEXT NOT NULL,
            common_payment_method TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_risk_scores_tier ON risk_scores(risk_tier);
        CREATE INDEX IF NOT EXISTS idx_risk_scores_score ON risk_scores(risk_score);
        CREATE INDEX IF NOT EXISTS idx_customers_contract ON customers(Contract);
        CREATE INDEX IF NOT EXISTS idx_customers_internet ON customers(InternetService);
        """
    )


def load_customers(connection: sqlite3.Connection, dataframe: pd.DataFrame) -> int:
    """Load cleaned customer attributes using parameterized inserts."""
    missing = [column for column in CUSTOMER_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Customer data is missing columns: {missing}")
    query = """
        INSERT INTO customers (
            customerID, gender, SeniorCitizen, Partner, Dependents, tenure,
            PhoneService, MultipleLines, InternetService, OnlineSecurity,
            OnlineBackup, DeviceProtection, TechSupport, StreamingTV,
            StreamingMovies, Contract, PaperlessBilling, PaymentMethod,
            MonthlyCharges, TotalCharges, Churn, churn_flag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    records = dataframe[CUSTOMER_COLUMNS].itertuples(index=False, name=None)
    connection.executemany(query, records)
    return len(dataframe)


def load_risk_scores(connection: sqlite3.Connection, dataframe: pd.DataFrame) -> int:
    """Load customer risk scores with their OOF/test source labels."""
    query = """
        INSERT INTO risk_scores
            (customerID, risk_score, risk_tier, actual_churn, source)
        VALUES (?, ?, ?, ?, ?)
    """
    records = dataframe[
        ["customerID", "churn_probability", "risk_tier", "actual_churn", "source"]
    ].itertuples(index=False, name=None)
    connection.executemany(query, records)
    return len(dataframe)


def load_model_metrics(connection: sqlite3.Connection, dataframe: pd.DataFrame) -> int:
    """Load flattened model metrics for CV and held-out test splits."""
    query = """
        INSERT INTO model_metrics (model_name, metric, value, split)
        VALUES (?, ?, ?, ?)
    """
    records = dataframe[["model_name", "metric", "value", "split"]].itertuples(
        index=False, name=None
    )
    connection.executemany(query, records)
    return len(dataframe)


def load_tier_summary(connection: sqlite3.Connection, dataframe: pd.DataFrame) -> int:
    """Load one summary row per risk tier."""
    query = """
        INSERT INTO tier_summary
            (risk_tier, customers, actual_churn_rate, average_tenure,
             average_monthly_charges, common_contract, common_internet_service,
             common_payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    records = dataframe[
        [
            "risk_tier",
            "customers",
            "actual_churn_rate",
            "average_tenure",
            "average_monthly_charges",
            "common_contract",
            "common_internet_service",
            "common_payment_method",
        ]
    ].itertuples(index=False, name=None)
    connection.executemany(query, records)
    return len(dataframe)


def _read_query(connection: sqlite3.Connection, query: str, parameters: tuple = ()) -> pd.DataFrame:
    """Run a fixed query with parameters and return a DataFrame."""
    return pd.read_sql_query(query, connection, params=parameters)


def read_customers(connection: sqlite3.Connection) -> pd.DataFrame:
    """Read all cleaned customer attributes."""
    return _read_query(connection, "SELECT * FROM customers ORDER BY customerID")


def read_risk_scores(connection: sqlite3.Connection) -> pd.DataFrame:
    """Read all customer risk scores."""
    return _read_query(connection, "SELECT * FROM risk_scores ORDER BY risk_score DESC")


def read_model_metrics(connection: sqlite3.Connection) -> pd.DataFrame:
    """Read model metrics for comparison tables."""
    return _read_query(
        connection,
        "SELECT model_name, metric, value, split FROM model_metrics ORDER BY model_name, split, metric",
    )


def read_tier_summary(connection: sqlite3.Connection) -> pd.DataFrame:
    """Read risk-tier profiles in business order."""
    return _read_query(
        connection,
        """
        SELECT risk_tier, customers, actual_churn_rate, average_tenure,
               average_monthly_charges, common_contract,
               common_internet_service, common_payment_method
        FROM tier_summary
        ORDER BY CASE risk_tier WHEN 'Low' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
        """,
    )


def read_churn_by_dimension(
    connection: sqlite3.Connection, dimension: str
) -> pd.DataFrame:
    """Read churn rates for one approved dashboard dimension."""
    queries = {
        "Contract": "SELECT Contract AS category, COUNT(*) AS customers, AVG(churn_flag) * 100 AS churn_rate FROM customers GROUP BY Contract ORDER BY churn_rate DESC",
        "InternetService": "SELECT InternetService AS category, COUNT(*) AS customers, AVG(churn_flag) * 100 AS churn_rate FROM customers GROUP BY InternetService ORDER BY churn_rate DESC",
        "PaymentMethod": "SELECT PaymentMethod AS category, COUNT(*) AS customers, AVG(churn_flag) * 100 AS churn_rate FROM customers GROUP BY PaymentMethod ORDER BY churn_rate DESC",
        "tenure_group": """
            SELECT CASE
                WHEN tenure <= 12 THEN '0-12 months'
                WHEN tenure <= 24 THEN '13-24 months'
                WHEN tenure <= 48 THEN '25-48 months'
                ELSE '49-72 months'
            END AS category,
            COUNT(*) AS customers, AVG(churn_flag) * 100 AS churn_rate
            FROM customers GROUP BY category ORDER BY churn_rate DESC
        """,
    }
    if dimension not in queries:
        raise ValueError(f"Unsupported churn dimension: {dimension}")
    return _read_query(connection, queries[dimension])