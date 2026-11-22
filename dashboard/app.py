"""SQLite-backed Streamlit dashboard for customer churn intelligence (CHURNIQ)."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.components import (
    render_footer,
    render_insight_card,
    render_kpi_row,
    render_page_header,
)
from dashboard.styles import (
    ACCENT_BLUE,
    ACCENT_TEAL,
    STATUS_COLORS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TIER_COLORS,
    apply_plotly_theme,
    inject_custom_css,
)
from src.database import (
    get_connection,
    read_customers,
    read_model_metrics,
    read_risk_scores,
    read_tier_summary,
)
from src.utils import DATABASE_PATH, FIGURES_DIR, OUTPUTS_DIR


PAGES = [
    "Overview",
    "Churn analysis",
    "Model performance",
    "Risk segments",
    "High-risk customers",
    "Recommendations",
]

PAGE_ICONS = {
    "Overview": ":material/dashboard:",
    "Churn analysis": ":material/analytics:",
    "Model performance": ":material/batch_prediction:",
    "Risk segments": ":material/pie_chart:",
    "High-risk customers": ":material/warning:",
    "Recommendations": ":material/lightbulb:",
}

st.set_page_config(
    page_title="CHURNIQ | Customer Churn Intelligence",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global CSS styling
inject_custom_css()


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
    """Render executive overview with KPI cards, distribution charts, and live insights."""
    render_page_header("Portfolio Overview", DATABASE_PATH, is_loaded=True)

    # 1. Primary Portfolio KPIs
    render_kpi_row(customers)

    # 2. First Chart Row: Retention vs Churn Donut & Risk Tier Distribution
    chart_row1_col1, chart_row1_col2 = st.columns(2)

    with chart_row1_col1:
        churn_counts = customers["churn_flag"].value_counts().rename(index={0: "Retained", 1: "Churned"})
        churn_df = churn_counts.reset_index()
        churn_df.columns = ["Status", "Customers"]
        churn_rate = customers["churn_flag"].mean() * 100

        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=churn_df["Status"],
                    values=churn_df["Customers"],
                    hole=0.62,
                    marker=dict(colors=[STATUS_COLORS["Retained"], STATUS_COLORS["Churned"]]),
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>Customers: %{value:,}<br>Share: %{percent}<extra></extra>",
                    textfont=dict(size=12, color="#FFFFFF"),
                    sort=False,
                )
            ]
        )
        fig_donut.add_annotation(
            text=f"<b>{churn_rate:.1f}%</b><br><span style='font-size:11px;color:#667085;'>Churn Rate</span>",
            x=0.5,
            y=0.5,
            font=dict(size=18, color=TEXT_PRIMARY, family="Inter, sans-serif"),
            showarrow=False,
        )
        apply_plotly_theme(fig_donut, height=340, title="Observed Churn vs Retention")
        st.plotly_chart(fig_donut, width="stretch")

    with chart_row1_col2:
        tier_chart_df = tier_summary.copy()
        tier_chart_df["share"] = tier_chart_df["customers"] / tier_chart_df["customers"].sum() * 100
        tier_chart_df["label"] = tier_chart_df.apply(
            lambda r: f"{int(r['customers']):,} ({r['share']:.1f}%)", axis=1
        )
        fig_tiers = go.Figure(
            data=[
                go.Bar(
                    x=tier_chart_df["risk_tier"],
                    y=tier_chart_df["customers"],
                    text=tier_chart_df["label"],
                    textposition="auto",
                    marker=dict(color=[TIER_COLORS.get(t, ACCENT_BLUE) for t in tier_chart_df["risk_tier"]]),
                    hovertemplate="<b>%{x} Tier</b><br>Customers: %{y:,}<br>Actual Churn Rate: %{customdata:.1f}%<extra></extra>",
                    customdata=tier_chart_df["actual_churn_rate"],
                )
            ]
        )
        apply_plotly_theme(fig_tiers, height=340, title="Customer Count by Risk Tier", show_legend=False)
        fig_tiers.update_xaxes(
            title="Risk Tier",
            categoryorder="array",
            categoryarray=["Low", "Medium", "High"],
        )
        fig_tiers.update_yaxes(title="Customers")
        st.plotly_chart(fig_tiers, width="stretch")

    # 3. Second Chart Row: Churn by Tenure Cohort & Churn by Contract
    chart_row2_col1, chart_row2_col2 = st.columns(2)

    with chart_row2_col1:
        cust_tenure = customers.copy()
        cust_tenure["tenure_group"] = pd.cut(
            cust_tenure["tenure"],
            bins=[-1, 12, 24, 48, 72],
            labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months"],
        )
        tenure_summary = (
            cust_tenure.groupby("tenure_group", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        tenure_summary["churn_rate"] *= 100
        tenure_summary["label"] = tenure_summary.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_tenure = go.Figure(
            data=[
                go.Bar(
                    x=tenure_summary["tenure_group"],
                    y=tenure_summary["churn_rate"],
                    text=tenure_summary["label"],
                    textposition="auto",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Cohort Size: %{customdata:,}<extra></extra>",
                    customdata=tenure_summary["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_tenure, height=340, title="Churn Rate by Tenure Cohort", show_legend=False)
        fig_tenure.update_xaxes(title="Tenure Cohort")
        fig_tenure.update_yaxes(title="Observed Churn Rate (%)")
        st.plotly_chart(fig_tenure, width="stretch")

    with chart_row2_col2:
        contract_summary = (
            customers.groupby("Contract", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        contract_summary["churn_rate"] *= 100
        contract_order = ["Month-to-month", "One year", "Two year"]
        contract_summary["Contract"] = pd.Categorical(
            contract_summary["Contract"], categories=contract_order, ordered=True
        )
        contract_summary = contract_summary.sort_values("Contract")
        contract_summary["label"] = contract_summary.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_contract = go.Figure(
            data=[
                go.Bar(
                    x=contract_summary["Contract"],
                    y=contract_summary["churn_rate"],
                    text=contract_summary["label"],
                    textposition="auto",
                    marker=dict(color=["#DC2626", "#F59E0B", "#16A34A"]),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=contract_summary["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_contract, height=340, title="Churn Rate by Contract Commitment", show_legend=False)
        fig_contract.update_xaxes(title="Contract Type")
        fig_contract.update_yaxes(title="Observed Churn Rate (%)")
        st.plotly_chart(fig_contract, width="stretch")

    # 4. Live Data-Driven Key Insights Section
    st.markdown(
        """
        <div style="margin-top: 1.5rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Key Business Insights</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">Empirical patterns computed dynamically from current portfolio data</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Compute insights from live data
    m2m_row = contract_summary[contract_summary["Contract"] == "Month-to-month"].iloc[0]
    two_yr_row = contract_summary[contract_summary["Contract"] == "Two year"].iloc[0]
    m2m_mult = m2m_row["churn_rate"] / two_yr_row["churn_rate"] if two_yr_row["churn_rate"] > 0 else 0

    high_tier_row = tier_summary[tier_summary["risk_tier"] == "High"].iloc[0]
    high_count = int(high_tier_row["customers"])
    high_share = high_count / len(customers) * 100
    high_churn = high_tier_row["actual_churn_rate"]

    t0_12_rate = tenure_summary.loc[tenure_summary["tenure_group"] == "0-12 months", "churn_rate"].values[0]
    t49_72_rate = tenure_summary.loc[tenure_summary["tenure_group"] == "49-72 months", "churn_rate"].values[0]

    churned_mrc = customers.loc[customers["churn_flag"] == 1, "MonthlyCharges"].sum()
    total_mrc = customers["MonthlyCharges"].sum()
    mrc_share = (churned_mrc / total_mrc * 100) if total_mrc > 0 else 0

    ins_cols = st.columns(4)
    with ins_cols[0]:
        render_insight_card(
            title="Contract Duration Gap",
            body=f"Month-to-month subscribers churn at <strong>{m2m_row['churn_rate']:.1f}%</strong>, compared to just <strong>{two_yr_row['churn_rate']:.1f}%</strong> on two-year agreements ({m2m_mult:.1f}x difference).",
        )
    with ins_cols[1]:
        render_insight_card(
            title="High-Risk Exposure",
            body=f"The High-risk segment concentrates <strong>{high_count:,} accounts</strong> ({high_share:.1f}% of base) with an observed churn rate of <strong>{high_churn:.1f}%</strong>.",
        )
    with ins_cols[2]:
        render_insight_card(
            title="First-Year Attrition",
            body=f"Early-tenure customers (0–12 months) show <strong>{t0_12_rate:.1f}%</strong> churn, dropping to <strong>{t49_72_rate:.1f}%</strong> for accounts over 4 years old.",
        )
    with ins_cols[3]:
        render_insight_card(
            title="Monthly Revenue Risk",
            body=f"Churned accounts represent <strong>${churned_mrc:,.0f}</strong> in Monthly Recurring Charges, accounting for <strong>{mrc_share:.1f}%</strong> of total portfolio MRC.",
        )

    # 5. Tier Profile Summary Table
    st.markdown(
        """
        <div style="margin-top: 1.75rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Risk Tier Profiles</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">Segment characteristics ranked by model risk score thresholds</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    st.caption("Risk score is produced by a class-weighted model and ranks customers for review; it is not a calibrated probability.")
    st.caption("Privacy note: this dashboard shows customer IDs from a public demonstration dataset only.")


def render_churn_analysis(customers: pd.DataFrame) -> None:
    """Render filterable churn rates for contract, service, payment, and tenure."""
    render_page_header("Churn Analysis", DATABASE_PATH, is_loaded=True)

    with st.sidebar:
        st.markdown("<h4 style='color: #F8FAFC; margin-top: 0.5rem;'>Filters</h4>", unsafe_allow_html=True)
        contract_filter = st.multiselect(
            "Contract",
            sorted(customers["Contract"].unique()),
            default=sorted(customers["Contract"].unique()),
            key="churn_contract_filter",
        )
        internet_filter = st.multiselect(
            "Internet service",
            sorted(customers["InternetService"].unique()),
            default=sorted(customers["InternetService"].unique()),
            key="churn_internet_filter",
        )

    filtered = customers[customers["Contract"].isin(contract_filter) & customers["InternetService"].isin(internet_filter)].copy()
    filtered["tenure_group"] = pd.cut(
        filtered["tenure"],
        bins=[-1, 12, 24, 48, 72],
        labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months"],
    )
    dimensions = ["Contract", "InternetService", "PaymentMethod", "tenure_group"]
    for start in range(0, len(dimensions), 2):
        cells = st.columns(2)
        for cell, column in zip(cells, dimensions[start : start + 2]):
            rates = filtered.groupby(column, observed=False)["churn_flag"].agg(customers="size", churn_rate="mean").reset_index()
            rates["churn_rate"] *= 100
            display_rates = rates.rename(columns={"customers": "Customers", "churn_rate": "Churn rate (%)"}).copy()
            display_rates["Customers"] = display_rates["Customers"].astype(int)
            display_rates["Churn rate (%)"] = display_rates["Churn rate (%)"].round(1)
            figure = px.bar(
                display_rates,
                x=column,
                y="Churn rate (%)",
                title=f"Churn Rate by {column}",
                labels={"Churn rate (%)": "Churn rate (%)", column: column},
                text_auto=".1f",
                color_discrete_sequence=[ACCENT_BLUE],
            )
            apply_plotly_theme(figure, height=330, title=f"Churn Rate by {column}")
            cell.plotly_chart(figure, width="stretch")


def render_model_performance(metrics: pd.DataFrame) -> None:
    """Render model metrics and saved ROC/precision-recall figures."""
    render_page_header("Model Performance", DATABASE_PATH, is_loaded=True)

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
    render_page_header("Risk Segments", DATABASE_PATH, is_loaded=True)

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
        fig_cust = px.bar(
            tier_display,
            x="Risk tier",
            y="Customers",
            color="Risk tier",
            title="Customers by Risk Tier",
            labels={"Customers": "Customers", "Risk tier": "Risk tier"},
            color_discrete_map=TIER_COLORS,
            category_orders={"Risk tier": ["Low", "Medium", "High"]},
        )
        apply_plotly_theme(fig_cust, height=340, title="Customers by Risk Tier")
        left.plotly_chart(fig_cust, width="stretch")
    with right:
        fig_rate = px.bar(
            tier_display,
            x="Risk tier",
            y="Actual churn rate (%)",
            color="Risk tier",
            title="Observed Churn Rate by Risk Tier",
            labels={"Actual churn rate (%)": "Actual churn rate (%)", "Risk tier": "Risk tier"},
            color_discrete_map=TIER_COLORS,
            category_orders={"Risk tier": ["Low", "Medium", "High"]},
            text_auto=".1f",
        )
        apply_plotly_theme(fig_rate, height=340, title="Observed Churn Rate by Risk Tier")
        right.plotly_chart(fig_rate, width="stretch")

    st.dataframe(tier_display, width="stretch", hide_index=True)


def render_high_risk_customers(customers: pd.DataFrame, risk_scores: pd.DataFrame) -> None:
    """Render filterable customer-level risk scores and a CSV download."""
    render_page_header("High-Risk Customers", DATABASE_PATH, is_loaded=True)
    st.caption("Risk score ranks customers for review; it is not a calibrated probability of churn.")

    data = risk_scores.merge(customers, on="customerID", how="left", validate="one_to_one")
    with st.sidebar:
        st.markdown("<h4 style='color: #F8FAFC; margin-top: 0.5rem;'>Filters</h4>", unsafe_allow_html=True)
        tiers = st.multiselect("Risk tier", ["High", "Medium", "Low"], default=["High"], key="risk_tier_filter")
        contracts = st.multiselect("Contract", sorted(data["Contract"].unique()), default=sorted(data["Contract"].unique()), key="risk_contract_filter")
        tenure_range = st.slider("Tenure (months)", 0, 72, (0, 72), key="risk_tenure_filter")
        charge_range = st.slider(
            "Monthly charges",
            float(data["MonthlyCharges"].min()),
            float(data["MonthlyCharges"].max()),
            (float(data["MonthlyCharges"].min()), float(data["MonthlyCharges"].max())),
            key="risk_charge_filter",
        )

    filtered = data[
        data["risk_tier"].isin(tiers)
        & data["Contract"].isin(contracts)
        & data["tenure"].between(*tenure_range)
        & data["MonthlyCharges"].between(*charge_range)
    ].sort_values("risk_score", ascending=False)

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
    st.download_button(
        "Download filtered customer list",
        data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="filtered_customer_risk_scores.csv",
        mime="text/csv",
    )
    st.caption("Privacy note: customer IDs shown here come from a public demonstration dataset.")


def render_recommendations() -> None:
    """Render the real recommendations report."""
    render_page_header("Strategic Recommendations", DATABASE_PATH, is_loaded=True)

    report_path = (OUTPUTS_DIR.parent / "reports" / "business_recommendations.md").resolve()
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.error("Recommendations report is missing. Run the Phase 5 workflow first.")


def main() -> None:
    """Run the dashboard application."""
    if not DATABASE_PATH.exists():
        st.error("The dashboard database is missing. Run `python scripts/build_database.py`, then refresh.")
        st.stop()

    try:
        customers, risk_scores, metrics, tier_summary = load_dashboard_tables(str(DATABASE_PATH))
    except Exception as error:  # noqa: BLE001
        st.error(f"The dashboard could not read the SQLite database: {error}")
        st.info("Run `python scripts/build_database.py` to rebuild the database.")
        st.stop()

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.6rem 0 1.25rem 0; border-bottom: 1px solid #1F2A37; margin-bottom: 0.75rem;">
                <div style="font-size: 1.45rem; font-weight: 800; letter-spacing: 0.04em; color: #FFFFFF;">
                    CHURN<span style="color: #2563EB;">IQ</span>
                </div>
                <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.2rem;">
                    Customer Churn Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigation",
            PAGES,
            format_func=lambda p: f"{PAGE_ICONS.get(p, '')} {p}",
            label_visibility="collapsed",
        )

        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        st.caption("Public demonstration dataset")

    # Render selected section
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

    # Standardized Footer across all sections
    render_footer()


if __name__ == "__main__":
    main()
