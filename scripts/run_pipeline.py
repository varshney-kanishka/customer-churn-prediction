"""Run the implemented project stages in order.

This is the final repeatable workflow. Phase 6 dashboard serving remains a
manual command because it is an interactive process.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import RAW_DATASET_PATH, get_logger


LOGGER = get_logger(__name__)


def run_stage(name: str, script_name: str) -> None:
    """Run one project script and stop with a clear error if it fails."""
    LOGGER.info("Starting stage: %s", name)
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script_name)], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            f"Stage '{name}' failed with exit code {result.returncode}. "
            f"Review the output above before continuing."
        )
    LOGGER.info("Completed stage: %s", name)


def main() -> int:
    """Run validation, cleaning, modeling, evaluation, segmentation, and database stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Reuse existing models and skip the train_models stage.",
    )
    args = parser.parse_args()
    if not RAW_DATASET_PATH.is_file():
        print(
            "Raw dataset is missing. Download the IBM Telco Customer Churn CSV "
            "and place it at data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv."
        )
        return 1

    stages = [
        ("validate data", "validate_data.py"),
        ("clean data", "clean_data.py"),
    ]
    if not args.skip_training:
        stages.append(("train models", "train_models.py"))
    stages.extend(
        [
            ("evaluate models", "evaluate_models.py"),
            ("segment customers", "segment_customers.py"),
            ("build database", "build_database.py"),
        ]
    )
    try:
        for name, script_name in stages:
            run_stage(name, script_name)
    except RuntimeError as error:
        LOGGER.error("Pipeline stopped: %s", error)
        return 1
    LOGGER.info("Pipeline completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())