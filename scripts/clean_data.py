"""Clean the raw dataset and save a processed copy and cleaning report."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_cleaning import build_cleaning_report, clean_data
from src.data_loader import load_raw_data
from src.utils import DATA_PROCESSED_DIR, OUTPUTS_DIR, get_logger


LOGGER = get_logger(__name__)
REPORT_PATH = OUTPUTS_DIR / "reports" / "data_cleaning_report.md"
OUTPUT_PATH = DATA_PROCESSED_DIR / "telco_churn_cleaned.csv"


def _write_report(report: dict[str, object], path: Path) -> None:
    """Write the cleaning summary as a readable Markdown report."""
    changes = report["changes"]
    lines = [
        "# Data Cleaning Report",
        "",
        f"Rows before: **{report['rows_before']}**",
        f"Rows after: **{report['rows_after']}**",
        f"Columns before: **{report['columns_before']}**",
        f"Columns after: **{report['columns_after']}**",
        "",
        "## Changes Made",
        "",
        f"- Text cells stripped: {changes['whitespace_cells_stripped']}",
        f"- TotalCharges conversion details: `{json.dumps(changes['total_charges'])}`",
        f"- Exact duplicate rows removed: {changes['exact_duplicate_rows_removed']}",
        f"- Customer ID check: `{json.dumps(changes['customer_id_check'])}`",
        f"- Churn flag check: `{json.dumps(changes['churn_flag'])}`",
        f"- Numeric range check: `{json.dumps(changes['numeric_range_check'])}`",
        "",
        "## Decisions and Reasons",
        "",
    ]
    lines.extend(f"- {decision}" for decision in report["decisions"])
    lines.extend(["", "## Remaining Issues", ""])
    if report["remaining_issues"]:
        lines.extend(f"- {issue}" for issue in report["remaining_issues"])
    else:
        lines.append("- None found by the Phase 3 cleaning checks.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Load, clean, save, and report on the dataset."""
    raw_data = load_raw_data()
    cleaned_data = clean_data(raw_data)
    report = build_cleaning_report(raw_data, cleaned_data)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned_data.to_csv(OUTPUT_PATH, index=False)
    _write_report(report, REPORT_PATH)
    print(f"Rows: {report['rows_before']} -> {report['rows_after']}")
    print(f"Columns: {report['columns_before']} -> {report['columns_after']}")
    print(f"TotalCharges filled: {report['changes']['total_charges']['filled_zero_tenure_count']}")
    print(f"Exact duplicate rows removed: {report['changes']['exact_duplicate_rows_removed']}")
    print(f"Cleaned data saved to: {OUTPUT_PATH}")
    print(f"Cleaning report saved to: {REPORT_PATH}")
    LOGGER.info("Cleaning completed")


if __name__ == "__main__":
    main()