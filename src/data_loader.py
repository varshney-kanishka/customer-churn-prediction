"""Load the raw Telco customer churn dataset without changing its values."""

from pathlib import Path

import pandas as pd

from src.utils import RAW_DATASET_PATH, get_logger


LOGGER = get_logger(__name__)


def load_raw_data(path: str | Path | None = None) -> pd.DataFrame:
    """Read the raw CSV as-is and return it as a DataFrame.

    Args:
        path: Optional CSV path. The project raw-data path is used by default.

    Raises:
        FileNotFoundError: If the requested CSV does not exist.
    """
    dataset_path = Path(path) if path is not None else RAW_DATASET_PATH
    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Raw dataset not found at {dataset_path}. "
            "Download the IBM Telco Customer Churn CSV and place it at "
            "data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv."
        )

    dataframe = pd.read_csv(dataset_path)
    LOGGER.info(
        "Loaded raw dataset from %s: %d rows, %d columns",
        dataset_path,
        len(dataframe),
        len(dataframe.columns),
    )
    return dataframe