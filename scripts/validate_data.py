"""Run raw-data validation and save Markdown and JSON reports."""

import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_loader import load_raw_data
from src.data_validation import validate_dataset
from src.utils import OUTPUTS_DIR, get_logger


LOGGER = get_logger(__name__)
REPORT_DIR = OUTPUTS_DIR / "reports"


def _finding_lines(results: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Build the report summary table from validation results."""
    missing_count = sum(item["count"] for item in results["missing_values"].values())
    blank_count = sum(
        item["count"]
        for name, item in results["blank_strings"].items()
        if name != "TotalCharges_numeric_conversion"
    )
    total_conversion = results["blank_strings"]["TotalCharges_numeric_conversion"]
    return [
        ("Shape", "PASS", f"{results['shape']['rows']} rows and {results['shape']['columns']} columns."),
        (
            "Column names",
            "PASS" if not results["columns"]["missing"] and not results["columns"]["unexpected"] else "FAIL",
            f"Missing: {results['columns']['missing'] or 'none'}; unexpected: {results['columns']['unexpected'] or 'none'}.",
        ),
        ("Data types", "PASS", f"Loaded dtypes: {results['data_types']}"),
        (
            "Missing values",
            "WARNING" if missing_count else "PASS",
            f"{missing_count} missing values across all columns.",
        ),
        (
            "Blank strings",
            "WARNING" if blank_count or total_conversion["failed_count"] else "PASS",
            f"{blank_count} blank strings; TotalCharges conversion failures: {total_conversion['failed_count']}.",
        ),
        (
            "Duplicates",
            "WARNING" if any(results["duplicates"].values()) else "PASS",
            f"Duplicate rows: {results['duplicates']['duplicate_rows']}; duplicate customerID rows: {results['duplicates']['duplicate_customer_id_rows']}.",
        ),
        (
            "Churn target",
            "PASS" if results["target"]["present"] else "FAIL",
            f"Values and balance: {results['target']}.",
        ),
        (
            "Numeric columns",
            "FAIL" if any(item.get("negative_count", 0) for item in results["numeric_columns"].values()) else "PASS",
            f"Summaries: {results['numeric_columns']}.",
        ),
        (
            "Categorical columns",
            "WARNING"
            if any(
                item.get("unexpected_values") or item.get("inconsistent_spellings")
                for item in results["categorical_columns"].values()
            )
            else "PASS",
            f"Unique values and counts: {results['categorical_columns']}.",
        ),
        ("Overall", results["overall_status"].replace("PASS WITH WARNINGS", "WARNING"), results["overall_status"]),
    ]


def _write_markdown(results: dict[str, Any], path: Path) -> None:
    """Write a readable Markdown validation report."""
    lines = [
        "# Data Validation Report",
        "",
        f"Overall status: **{results['overall_status']}**",
        "",
        "| Check | Status | Finding |",
        "|---|---|---|",
    ]
    for check, status, finding in _finding_lines(results):
        lines.append(f"| {check} | {status} | {finding} |")
    lines.extend(["", "## Issues to handle in Phase 3 (Data Cleaning)"])
    if results["issues"]:
        lines.extend(f"- {issue}" for issue in results["issues"])
    else:
        lines.append("- No issues were found by these checks.")
    lines.extend(["", "## Detailed Results", "", "```json", json.dumps(results, indent=2), "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Load, validate, and save the raw dataset reports."""
    dataframe = load_raw_data()
    results = validate_dataset(dataframe)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "data_validation_report.json"
    markdown_path = REPORT_DIR / "data_validation_report.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    _write_markdown(results, markdown_path)
    print(f"Validation status: {results['overall_status']}")
    print(f"Rows: {results['shape']['rows']}; columns: {results['shape']['columns']}")
    print(f"Reports saved: {markdown_path} and {json_path}")
    LOGGER.info("Validation reports written to %s", REPORT_DIR)


if __name__ == "__main__":
    main()