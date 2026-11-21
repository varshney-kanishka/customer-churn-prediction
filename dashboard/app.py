"""SQLite-backed Streamlit dashboard for customer churn analysis."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection, read_customers, read_model_metrics, read_risk_scores, read_tier_summary
from src.utils import DATABASE_PATH, FIGURES_DIR, OUTPUTS_DIR


PAGES = ["Overview", "Churn analysis", "Model performance", "Risk segments", "High-risk customers", "Recommendations"]
TIER_COLORS = {"Low": "#2a9d8f", "Medium": "#e9c46a", "High": "#e76f51"}

st.set_page_config(page_title="Customer Churn Intelligence", page_icon="C", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1400px; padding-top: 2rem; }
    [data-testid="stMetricValue"] { color: #0f766e; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_dashboard_tables(database_path: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load dashboard tables from SQLite and cache the result."""
    with get_connection(database_path) as connection:
        return (
            read_customers(connection),
            read_risk_scores(connection),
            read_model_metrics(connection),
            read_tier_summary(connection),
        )


def render_overview(customers: pd.DataFrame, tier_summary: pd.DataFrame) -> None:
    """Render portfolio KPIs and observed churn distribution."""
    st.header("Portfolio overview")
    cards = st.columns(4)
    cards[0].metric("Total customers", f"{len(customers):,}")
    cards[1].metric("Observed churn", f"{customers['churn_flag'].mean() * 100:.1f}%")
    cards[2].metric("Average tenure", f"{customers['tenure'].mean():.1f} months")
    cards[3].metric("Average monthly charges", f"${customers['MonthlyCharges'].mean():,.1f}")
    left, right = st.columns(2)
    with left:
        churn = customers.groupby("Churn", as_index=False).size().rename(columns={"size": "customers"})
        figure = px.bar(churn, x="Churn", y="customers", color="Churn", title="Observed Churn Distribution", labels={"customers": "Customers", "Churn": "Observed churn"}, color_discrete_map={"No": "#2a9d8f", "Yes": "#e76f51"})
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(tier_summary, x="risk_tier", y="customers", color="risk_tier", title="Customers per Risk Tier", labels={"customers": "Customers", "risk_tier": "Risk tier"}, color_discrete_map=TIER_COLORS, category_orders={"risk_tier": ["Low", "Medium", "High"]})
        st.plotly_chart(figure, width="stretch")
    st.caption("Risk score is produced by a class-weighted model and ranks customers for review; it is not a calibrated probability.")
    tier_display = tier_summary.rename(columns={
        "risk_tier": "Risk tier",
        "customers": "Customers",
        "actual_churn_rate": "Actual churn rate (%)",
        "average_tenure": "Avg tenure (months)",
        "average_monthly_charges": "Avg monthly charges ($)",
        "common_contract": "Most common contract",
        "common_internet_service": "Most common internet service",
        "common_payment_method": "Most common payment method",
    }).copy()
    tier_display["Customers"] = tier_display["Customers"].astype(int)
    tier_display["Actual churn rate (%)"] = tier_display["Actual churn rate (%)"].round(1)
    tier_display["Avg tenure (months)"] = tier_display["Avg tenure (months)"].round(1)
    tier_display["Avg monthly charges ($)"] = tier_display["Avg monthly charges ($)"].round(1)
    st.dataframe(tier_display, width="stretch", hide_index=True)
    st.caption("Privacy note: this dashboard shows customer IDs from a public demonstration dataset only.")


def render_churn_analysis(customers: pd.DataFrame) -> None:
    """Render filterable churn rates for contract, service, payment, and tenure."""
    st.header("Churn analysis")
    with st.sidebar:
        st.subheader("Churn filters")
        contract_filter = st.multiselect("Contract", sorted(customers["Contract"].unique()), default=sorted(customers["Contract"].unique()), key="churn_contract_filter")
        internet_filter = st.multiselect("Internet service", sorted(customers["InternetService"].unique()), default=sorted(customers["InternetService"].unique()), key="churn_internet_filter")
    filtered = customers[customers["Contract"].isin(contract_filter) & customers["InternetService"].isin(internet_filter)].copy()
    filtered["tenure_group"] = pd.cut(filtered["tenure"], bins=[-1, 12, 24, 48, 72], labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months"])
    dimensions = ["Contract", "InternetService", "PaymentMethod", "tenure_group"]
    for start in range(0, len(dimensions), 2):
        cells = st.columns(2)
        for cell, column in zip(cells, dimensions[start : start + 2]):
            rates = filtered.groupby(column, observed=False)["churn_flag"].agg(customers="size", churn_rate="mean").reset_index()
            rates["churn_rate"] *= 100
            display_rates = rates.rename(columns={"customers": "Customers", "churn_rate": "Churn rate (%)"}).copy()
            display_rates["Customers"] = display_rates["Customers"].astype(int)
            display_rates["Churn rate (%)"] = display_rates["Churn rate (%)"].round(1)
            figure = px.bar(display_rates, x=column, y="Churn rate (%)", title=f"Churn Rate by {column}", labels={"Churn rate (%)": "Churn rate (%)", column: column}, text_auto=".1f")
            cell.plotly_chart(figure, width="stretch")


def render_model_performance(metrics: pd.DataFrame) -> None:
    """Render model metrics and saved ROC/precision-recall figures."""
    st.header("Model performance")
    test_metrics = metrics[metrics["split"] == "test"].pivot(index="model_name", columns="metric", values="value").reset_index()
    test_metrics = test_metrics.rename(columns={
        "model_name": "Model",
        "accuracy": "Accuracy",
        "precision": "Precision",
        "recall": "Recall",
        "f1": "F1",
        "roc_auc": "ROC-AUC",
        "pr_auc": "PR-AUC",
    })
    display_metrics = test_metrics.copy()
    for column in ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC"]:
        if column in display_metrics:
            display_metrics[column] = display_metrics[column].round(3)
    st.dataframe(display_metrics, width="stretch", hide_index=True)
    st.info("XGBoost is the selected final model for retention-oriented review. Its test ROC-AUC was 0.845 versus 0.841 for Logistic Regression and 0.840 for Random Forest. Phase 4 cross-validation differences were within fold-level variation, so this is a practical choice rather than a statistically clear winner.")
    left, right = st.columns(2)
    with left:
        figure_path = FIGURES_DIR / "model_roc_curves.png"
        if figure_path.exists():
            st.image(str(figure_path), caption="ROC curves")
        else:
            st.warning("ROC figure is missing. Run scripts/evaluate_models.py.")
    with right:
        figure_path = FIGURES_DIR / "model_precision_recall_curves.png"
        if figure_path.exists():
            st.image(str(figure_path), caption="Precision-recall curves")
        else:
            st.warning("Precision-recall figure is missing. Run scripts/evaluate_models.py.")


def render_risk_segments(tier_summary: pd.DataFrame) -> None:
    """Render tier sizes, observed rates, and profiles."""
    st.header("Risk segments")
    tier_display = tier_summary.rename(columns={
        "risk_tier": "Risk tier",
        "customers": "Customers",
        "actual_churn_rate": "Actual churn rate (%)",
        "average_tenure": "Avg tenure (months)",
        "average_monthly_charges": "Avg monthly charges ($)",
        "common_contract": "Most common contract",
        "common_internet_service": "Most common internet service",
        "common_payment_method": "Most common payment method",
    }).copy()
    tier_display["Customers"] = tier_display["Customers"].astype(int)
    tier_display["Actual churn rate (%)"] = tier_display["Actual churn rate (%)"].round(1)
    tier_display["Avg tenure (months)"] = tier_display["Avg tenure (months)"].round(1)
    tier_display["Avg monthly charges ($)"] = tier_display["Avg monthly charges ($)"].round(1)
    left, right = st.columns(2)
    with left:
        figure = px.bar(tier_display, x="Risk tier", y="Customers", color="Risk tier", title="Customers by Risk Tier", labels={"Customers": "Customers", "Risk tier": "Risk tier"}, color_discrete_map=TIER_COLORS, category_orders={"Risk tier": ["Low", "Medium", "High"]})
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(tier_display, x="Risk tier", y="Actual churn rate (%)", color="Risk tier", title="Observed Churn Rate by Risk Tier", labels={"Actual churn rate (%)": "Actual churn rate (%)", "Risk tier": "Risk tier"}, color_discrete_map=TIER_COLORS, category_orders={"Risk tier": ["Low", "Medium", "High"]}, text_auto=".1f")
        st.plotly_chart(figure, width="stretch")
    st.dataframe(tier_display, width="stretch", hide_index=True)


def render_high_risk_customers(customers: pd.DataFrame, risk_scores: pd.DataFrame) -> None:
    """Render filterable customer-level risk scores and a CSV download."""
    st.header("High-risk customer list")
    st.caption("Risk score ranks customers for review; it is not a calibrated probability of churn.")
    data = risk_scores.merge(customers, on="customerID", how="left", validate="one_to_one")
    with st.sidebar:
        tiers = st.multiselect("Risk tier", ["High", "Medium", "Low"], default=["High"], key="risk_tier_filter")
        contracts = st.multiselect("Contract", sorted(data["Contract"].unique()), default=sorted(data["Contract"].unique()), key="risk_contract_filter")
        tenure_range = st.slider("Tenure (months)", 0, 72, (0, 72), key="risk_tenure_filter")
        charge_range = st.slider("Monthly charges", float(data["MonthlyCharges"].min()), float(data["MonthlyCharges"].max()), (float(data["MonthlyCharges"].min()), float(data["MonthlyCharges"].max())), key="risk_charge_filter")
    filtered = data[data["risk_tier"].isin(tiers) & data["Contract"].isin(contracts) & data["tenure"].between(*tenure_range) & data["MonthlyCharges"].between(*charge_range)].sort_values("risk_score", ascending=False)
    display_columns = ["customerID", "risk_score", "risk_tier", "actual_churn", "Contract", "tenure", "MonthlyCharges", "InternetService", "PaymentMethod"]
    display_table = filtered[display_columns].rename(columns={
        "customerID": "Customer ID",
        "risk_score": "Risk score",
        "risk_tier": "Risk tier",
        "actual_churn": "Actual churn",
        "Contract": "Contract",
        "tenure": "Tenure (months)",
        "MonthlyCharges": "Monthly charges ($)",
        "InternetService": "Internet service",
        "PaymentMethod": "Payment method",
    }).copy()
    display_table["Risk score"] = display_table["Risk score"].round(3)
    display_table["Tenure (months)"] = display_table["Tenure (months)"].astype(int)
    display_table["Monthly charges ($)"] = display_table["Monthly charges ($)"].round(1)
    st.write(f"Showing {len(filtered):,} customers")
    st.dataframe(display_table, width="stretch", hide_index=True)
    st.download_button("Download filtered customer list", data=filtered[display_columns].to_csv(index=False).encode("utf-8"), file_name="filtered_customer_risk_scores.csv", mime="text/csv")
    st.caption("Privacy note: customer IDs shown here come from a public demonstration dataset.")


def render_recommendations() -> None:
    """Render the real recommendations report."""
    st.header("Recommendations")
    report_path = (OUTPUTS_DIR.parent / "reports" / "business_recommendations.md").resolve()
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.error("Recommendations report is missing. Run the Phase 5 workflow first.")


def main() -> None:
    """Run the dashboard application."""
    st.title("Customer Churn Intelligence")
    st.caption("SQLite-backed analysis of real project outputs")
    if not DATABASE_PATH.exists():
        st.error("The dashboard database is missing. Run `python scripts/build_database.py`, then refresh.")
        st.stop()
    try:
        customers, risk_scores, metrics, tier_summary = load_dashboard_tables(str(DATABASE_PATH))
    except Exception as error:  # noqa: BLE001
        st.error(f"The dashboard could not read the SQLite database: {error}")
        st.info("Run `python scripts/build_database.py` to rebuild the database.")
        st.stop()
    with st.sidebar:
        st.header("Dashboard navigation")
        page = st.radio("Section", PAGES)
    if page == "Overview":
        render_overview(customers, tier_summary)
    elif page == "Churn analysis":
        render_churn_analysis(customers)
    elif page == "Model performance":
        render_model_performance(metrics)
    elif page == "Risk segments":
        render_risk_segments(tier_summary)
    elif page == "High-risk customers":
        render_high_risk_customers(customers, risk_scores)
    else:
        render_recommendations()


if __name__ == "__main__":
    main()