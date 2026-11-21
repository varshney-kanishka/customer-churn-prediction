"""Tests for project path helpers."""

from pathlib import Path

from src import utils


def test_project_paths_resolve_inside_workspace() -> None:
    """Configured paths are absolute and anchored at the project root."""
    assert utils.PROJECT_ROOT.is_absolute()
    assert utils.RAW_DATASET_PATH == utils.DATA_RAW_DIR / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    assert utils.DATABASE_PATH == utils.DATA_PROCESSED_DIR / "churn.db"
    assert all(isinstance(path, Path) and path.is_absolute() for path in [utils.DATA_RAW_DIR, utils.MODELS_DIR, utils.OUTPUTS_DIR])