"""Phase 1 verification. Standard library only, so it runs before packages are installed.
Run from the project root:  python scripts/verify_setup.py
Writes outputs/reports/setup_report.md."""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results = []


def add(name, status, detail=""):
    results.append((name, status, detail))


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return out.returncode, (out.stdout + out.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


v = sys.version_info
add("Python version", "PASS" if (3, 10) <= v[:2] <= (3, 12) else "FAIL",
    f"{v.major}.{v.minor}.{v.micro} (3.11 preferred; 3.10-3.12 expected compatible)")

code, out = run([sys.executable, "-m", "pip", "--version"])
add("pip available", "PASS" if code == 0 else "FAIL", out.splitlines()[0] if out else "")

git = shutil.which("git")
if git:
    _, ver = run(["git", "--version"])
    add("Git available", "PASS", ver)
    code, _ = run(["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"])
    add("Git repository", "PASS" if code == 0 else "PENDING",
        "initialized" if code == 0 else "not initialized: run `git init`")
else:
    add("Git available", "FAIL", "git not found on PATH")

add("Project root", "PASS" if (ROOT / "README.md").exists() else "FAIL", str(ROOT))
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
add("Virtual environment active", "PASS" if in_venv else "PENDING", sys.prefix)
add(".venv folder exists", "PASS" if (ROOT / ".venv").exists() else "PENDING", "")

dirs = ["data/raw", "data/processed", "notebooks", "src", "dashboard", "tests", "outputs/figures",
        "outputs/reports", "outputs/metrics", "outputs/predictions", "models", "reports", "scripts"]
missing = [d for d in dirs if not (ROOT / d).is_dir()]
add("Folder structure", "PASS" if not missing else "FAIL", ", ".join(missing) or "all present")

files = ["README.md", "requirements.txt", ".gitignore", "src/__init__.py", "src/utils.py",
         "dashboard/app.py", "scripts/run_pipeline.py", "reports/final_project_report.md",
         "notebooks/customer_churn_eda.ipynb"]
missing = [f for f in files if not (ROOT / f).is_file()]
add("Config/initial files", "PASS" if not missing else "FAIL", ", ".join(missing) or "all present")

ds = ROOT / "data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv"
if ds.is_file():
    try:
        with open(ds, encoding="utf-8") as f:
            header = f.readline().strip()
        add("Dataset", "PASS", f"readable; header starts: {header[:60]}")
    except Exception as exc:  # noqa: BLE001
        add("Dataset", "FAIL", f"exists but unreadable: {exc}")
else:
    add("Dataset", "PENDING", "missing: download from Kaggle into data/raw/")

pkgs = ["pandas", "numpy", "matplotlib", "seaborn", "sklearn", "xgboost", "streamlit",
        "plotly", "joblib", "pytest", "jupyter_core"]
for p in pkgs:
    try:
        m = importlib.import_module(p)
        add(f"import {p}", "PASS", getattr(m, "__version__", ""))
    except Exception as exc:  # noqa: BLE001
        add(f"import {p}", "PENDING", f"not importable ({type(exc).__name__})")

lines = ["# Setup Report", "", "| Check | Status | Detail |", "|---|---|---|"]
lines += [f"| {n} | {s} | {d} |" for n, s, d in results]
report = "\n".join(lines)
print(report)
out_dir = ROOT / "outputs" / "reports"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "setup_report.md").write_text(report, encoding="utf-8")
