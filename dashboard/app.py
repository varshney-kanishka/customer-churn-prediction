"""SQLite-backed Streamlit dashboard for customer churn intelligence (CHURNIQ)."""

from __future__ import annotations

from pathlib import Path
import re
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
    render_tier_card,
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
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
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
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
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
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_BLUE),
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
    """Render filterable churn rates across contract, service, payment, tenure, charges, and demographics."""
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

    filtered = customers[
        customers["Contract"].isin(contract_filter) & customers["InternetService"].isin(internet_filter)
    ].copy()

    if filtered.empty:
        st.warning("No customers match the selected contract and internet service filters.")
        return

    st.caption(
        f"Analyzing churn drivers across {len(filtered):,} matching customers "
        f"({len(filtered)/len(customers)*100:.1f}% of total portfolio)."
    )

    filtered["tenure_group"] = pd.cut(
        filtered["tenure"],
        bins=[-1, 12, 24, 48, 72],
        labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months"],
    )
    charge_bins = [-1, 35, 70, 90, 200]
    charge_labels = ["$0-$35 (Basic)", "$35-$70 (Mid)", "$70-$90 (High)", "$90+ (Premium)"]
    filtered["charge_band"] = pd.cut(
        filtered["MonthlyCharges"],
        bins=charge_bins,
        labels=charge_labels,
    )

    # Row 1: Contract Commitment & Internet Service
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        contract_rates = (
            filtered.groupby("Contract", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        contract_rates["churn_rate"] *= 100
        contract_order = ["Month-to-month", "One year", "Two year"]
        contract_rates["Contract"] = pd.Categorical(
            contract_rates["Contract"], categories=contract_order, ordered=True
        )
        contract_rates = contract_rates.sort_values("Contract")
        contract_rates["label"] = contract_rates.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_contract = go.Figure(
            data=[
                go.Bar(
                    x=contract_rates["Contract"],
                    y=contract_rates["churn_rate"],
                    text=contract_rates["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=contract_rates["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_contract, height=340, title="Churn Rate by Contract Commitment", show_legend=False)
        fig_contract.update_xaxes(title="Contract Type")
        fig_contract.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_contract, width="stretch")
        st.caption("Month-to-month contracts have the highest attrition; multi-year commitments show strong retention.")

    with row1_col2:
        internet_rates = (
            filtered.groupby("InternetService", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        internet_rates["churn_rate"] *= 100
        internet_rates = internet_rates.sort_values("churn_rate", ascending=False)
        internet_rates["label"] = internet_rates.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_internet = go.Figure(
            data=[
                go.Bar(
                    x=internet_rates["InternetService"],
                    y=internet_rates["churn_rate"],
                    text=internet_rates["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=internet_rates["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_internet, height=340, title="Churn Rate by Internet Service", show_legend=False)
        fig_internet.update_xaxes(title="Internet Service")
        fig_internet.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_internet, width="stretch")
        st.caption("Fiber optic accounts show higher churn compared to DSL or telephone-only subscriptions.")

    # Row 2: Payment Method & Tenure Cohort
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        pay_rates = (
            filtered.groupby("PaymentMethod", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        pay_rates["churn_rate"] *= 100
        pay_rates = pay_rates.sort_values("churn_rate", ascending=False)
        pay_rates["label"] = pay_rates.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )
        pay_colors = [
            "#DC2626" if "electronic check" in str(m).lower() else ACCENT_BLUE
            for m in pay_rates["PaymentMethod"]
        ]

        fig_pay = go.Figure(
            data=[
                go.Bar(
                    x=pay_rates["PaymentMethod"],
                    y=pay_rates["churn_rate"],
                    text=pay_rates["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    textfont=dict(size=10),
                    marker=dict(color=pay_colors),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=pay_rates["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_pay, height=340, title="Churn Rate by Payment Method", show_legend=False)
        fig_pay.update_xaxes(title="Payment Method", tickangle=-15)
        fig_pay.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_pay, width="stretch")
        st.caption("Electronic check payment exhibits the highest friction and attrition compared to automated methods.")

    with row2_col2:
        tenure_rates = (
            filtered.groupby("tenure_group", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        tenure_rates["churn_rate"] *= 100
        tenure_rates["label"] = tenure_rates.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_tenure = go.Figure(
            data=[
                go.Bar(
                    x=tenure_rates["tenure_group"],
                    y=tenure_rates["churn_rate"],
                    text=tenure_rates["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=tenure_rates["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_tenure, height=340, title="Churn Rate by Tenure Cohort", show_legend=False)
        fig_tenure.update_xaxes(title="Tenure Group")
        fig_tenure.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_tenure, width="stretch")
        st.caption("New customers in their first 12 months churn at the highest rate, dropping as accounts mature.")

    # Row 3: Monthly Charges Bands & Demographic Grouped Bar
    row3_col1, row3_col2 = st.columns(2)

    with row3_col1:
        charge_rates = (
            filtered.groupby("charge_band", observed=False)["churn_flag"]
            .agg(customers="size", churn_rate="mean")
            .reset_index()
        )
        charge_rates["churn_rate"] *= 100
        charge_rates["label"] = charge_rates.apply(
            lambda r: f"{r['churn_rate']:.1f}% ({r['customers']:,})", axis=1
        )

        fig_charge = go.Figure(
            data=[
                go.Bar(
                    x=charge_rates["charge_band"],
                    y=charge_rates["churn_rate"],
                    text=charge_rates["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="<b>%{x}</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=charge_rates["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_charge, height=340, title="Churn Rate by Monthly Charges Band", show_legend=False)
        fig_charge.update_xaxes(title="Monthly Charges Band")
        fig_charge.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_charge, width="stretch")
        st.caption("Higher monthly recurring charges ($70+) correlate with increased customer attrition.")

    with row3_col2:
        demo_categories = ["Senior Citizen", "Partner", "Dependents"]

        sr_no_mask = filtered["SeniorCitizen"] == 0
        sr_yes_mask = filtered["SeniorCitizen"] == 1
        sr_no_rate = (filtered.loc[sr_no_mask, "churn_flag"].mean() * 100) if sr_no_mask.sum() > 0 else 0
        sr_yes_rate = (filtered.loc[sr_yes_mask, "churn_flag"].mean() * 100) if sr_yes_mask.sum() > 0 else 0
        sr_no_count = int(sr_no_mask.sum())
        sr_yes_count = int(sr_yes_mask.sum())

        pt_no_mask = filtered["Partner"] == "No"
        pt_yes_mask = filtered["Partner"] == "Yes"
        pt_no_rate = (filtered.loc[pt_no_mask, "churn_flag"].mean() * 100) if pt_no_mask.sum() > 0 else 0
        pt_yes_rate = (filtered.loc[pt_yes_mask, "churn_flag"].mean() * 100) if pt_yes_mask.sum() > 0 else 0
        pt_no_count = int(pt_no_mask.sum())
        pt_yes_count = int(pt_yes_mask.sum())

        dp_no_mask = filtered["Dependents"] == "No"
        dp_yes_mask = filtered["Dependents"] == "Yes"
        dp_no_rate = (filtered.loc[dp_no_mask, "churn_flag"].mean() * 100) if dp_no_mask.sum() > 0 else 0
        dp_yes_rate = (filtered.loc[dp_yes_mask, "churn_flag"].mean() * 100) if dp_yes_mask.sum() > 0 else 0
        dp_no_count = int(dp_no_mask.sum())
        dp_yes_count = int(dp_yes_mask.sum())

        no_rates = [sr_no_rate, pt_no_rate, dp_no_rate]
        no_counts = [sr_no_count, pt_no_count, dp_no_count]
        yes_rates = [sr_yes_rate, pt_yes_rate, dp_yes_rate]
        yes_counts = [sr_yes_count, pt_yes_count, dp_yes_count]

        fig_demo = go.Figure(
            data=[
                go.Bar(
                    name="No / Non-Senior",
                    x=demo_categories,
                    y=no_rates,
                    text=[f"{r:.1f}%" for r in no_rates],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=ACCENT_TEAL),
                    hovertemplate="<b>%{x} (No / Non-Senior)</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=no_counts,
                ),
                go.Bar(
                    name="Yes / Senior",
                    x=demo_categories,
                    y=yes_rates,
                    text=[f"{r:.1f}%" for r in yes_rates],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color="#DC2626"),
                    hovertemplate="<b>%{x} (Yes / Senior)</b><br>Churn Rate: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=yes_counts,
                ),
            ]
        )
        apply_plotly_theme(fig_demo, height=340, title="Churn Rate by Demographic Segments", show_legend=True)
        fig_demo.update_layout(barmode="group")
        fig_demo.update_xaxes(title="Demographic Attribute")
        fig_demo.update_yaxes(title="Churn Rate (%)")
        st.plotly_chart(fig_demo, width="stretch")
        st.caption("Senior citizens and customers without partners or dependents exhibit higher churn risk.")


def render_model_performance(metrics: pd.DataFrame) -> None:
    """Render model comparison table, grouped benchmark chart, ROC/PR figures, and final confusion matrix."""
    render_page_header("Model Performance", DATABASE_PATH, is_loaded=True)

    # 1. Honest statistical note
    st.info(
        "XGBoost is the retained final model for retention-oriented review. Held-out test ROC-AUC was 0.845 "
        "versus 0.841 for Logistic Regression and 0.840 for Random Forest. Cross-validation differences across "
        "all three models were within fold-level standard deviations (CV std ~0.012), meaning held-out differences "
        "are within cross-validation noise rather than establishing one model as statistically superior."
    )

    # 2. Extract held-out test split metrics
    test_metrics = (
        metrics[metrics["split"] == "test"]
        .pivot(index="model_name", columns="metric", values="value")
        .reset_index()
    )
    metric_cols = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    available_cols = [c for c in metric_cols if c in test_metrics.columns]

    rename_map = {
        "model_name": "Model",
        "accuracy": "Accuracy",
        "precision": "Precision",
        "recall": "Recall",
        "f1": "F1",
        "roc_auc": "ROC-AUC",
        "pr_auc": "PR-AUC",
    }
    table_df = test_metrics.rename(columns=rename_map)
    display_cols = ["Model"] + [rename_map[c] for c in available_cols]
    table_df = table_df[display_cols].copy()

    model_order = ["Logistic Regression", "Random Forest", "XGBoost"]
    table_df["Model"] = pd.Categorical(table_df["Model"], categories=model_order, ordered=True)
    table_df = table_df.sort_values("Model").reset_index(drop=True)

    st.markdown(
        """
        <div style="margin-top: 1rem; margin-bottom: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Model Comparison (Held-Out Test Set)</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">Evaluated on 1,409 customer accounts (20% test split). Highlighting indicates highest metric value as a visual aid only.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    numeric_sub = display_cols[1:]
    styled_df = table_df.style.highlight_max(subset=numeric_sub, color="#DCFCE7", axis=0).format(
        {c: "{:.3f}" for c in numeric_sub}
    )
    st.dataframe(styled_df, width="stretch", hide_index=True)

    # 3. Grouped Bar Chart Comparing the Models
    chart_metrics = ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]
    chart_metrics = [m for m in chart_metrics if m in table_df.columns]

    model_colors = {
        "Logistic Regression": "#64748B",
        "Random Forest": ACCENT_TEAL,
        "XGBoost": ACCENT_BLUE,
    }

    fig_compare = go.Figure()
    for model_name in model_order:
        row = table_df[table_df["Model"] == model_name]
        if not row.empty:
            vals = [float(row[m].values[0]) for m in chart_metrics]
            fig_compare.add_trace(
                go.Bar(
                    name=model_name,
                    x=chart_metrics,
                    y=vals,
                    text=[f"{v:.3f}" for v in vals],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    textfont=dict(size=9),
                    marker=dict(color=model_colors.get(model_name, ACCENT_BLUE)),
                    hovertemplate=f"<b>{model_name}</b><br>%{{x}}: %{{y:.3f}}<extra></extra>",
                )
            )

    apply_plotly_theme(fig_compare, height=350, title="Benchmark Comparison Across Evaluation Metrics", show_legend=True)
    fig_compare.update_layout(barmode="group")
    fig_compare.update_xaxes(title="Metric")
    fig_compare.update_yaxes(title="Score", range=[0.4, 0.95])
    st.plotly_chart(fig_compare, width="stretch")
    st.caption("Differences between all three models are within cross-validation variance; XGBoost provides strong recall (0.799) for retention targeting.")

    # 4. Evaluation Curves and Final Model Confusion Matrix
    st.markdown(
        """
        <div style="margin-top: 1.5rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Diagnostic Curves & Classification Breakdown</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">ROC discrimination, Precision-Recall tradeoff, and final XGBoost confusion matrix</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    curve_col1, curve_col2, matrix_col = st.columns([1, 1, 1])

    with curve_col1:
        roc_path = FIGURES_DIR / "model_roc_curves.png"
        if roc_path.exists():
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #101828; margin-bottom: 0.5rem;">ROC Curves</div>
                """,
                unsafe_allow_html=True,
            )
            st.image(str(roc_path), caption="Receiver Operating Characteristic across models")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("ROC curves figure missing from outputs/figures/.")

    with curve_col2:
        pr_path = FIGURES_DIR / "model_precision_recall_curves.png"
        if pr_path.exists():
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #101828; margin-bottom: 0.5rem;">Precision-Recall Curves</div>
                """,
                unsafe_allow_html=True,
            )
            st.image(str(pr_path), caption="Precision-Recall trade-off across models")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Precision-Recall curves figure missing from outputs/figures/.")

    with matrix_col:
        cm_path = FIGURES_DIR / "final_model_confusion_matrix.png"
        if cm_path.exists():
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #101828; margin-bottom: 0.5rem;">XGBoost Confusion Matrix</div>
                """,
                unsafe_allow_html=True,
            )
            st.image(str(cm_path), caption="Final XGBoost test split confusion matrix (threshold = 0.5)")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Confusion matrix figure missing from outputs/figures/.")


def render_risk_segments(tier_summary: pd.DataFrame) -> None:
    """Render risk tier cards, churn progression, customer volume share, profiles, and live insights."""
    render_page_header("Risk Segments", DATABASE_PATH, is_loaded=True)

    tier_df = tier_summary.copy()
    total_customers = int(tier_df["customers"].sum())
    tier_df["share"] = tier_df["customers"] / total_customers * 100

    # 1. Tier Metric Cards (3 Columns)
    tier_cols = st.columns(3)
    for idx, row in tier_df.iterrows():
        tier = row["risk_tier"]
        tier_color = TIER_COLORS.get(tier, ACCENT_BLUE)
        with tier_cols[idx]:
            render_tier_card(
                tier=tier,
                customers=int(row["customers"]),
                share=float(row["share"]),
                churn_rate=float(row["actual_churn_rate"]),
                color=tier_color,
                avg_tenure=float(row["average_tenure"]),
                avg_mrc=float(row["average_monthly_charges"]),
            )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # 2. Charts Row: Actual Churn Rate per Tier & Customer Volume Share
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        tier_df["label"] = tier_df.apply(
            lambda r: f"{r['actual_churn_rate']:.1f}% ({int(r['customers']):,})", axis=1
        )
        fig_rate = go.Figure(
            data=[
                go.Bar(
                    x=tier_df["risk_tier"],
                    y=tier_df["actual_churn_rate"],
                    text=tier_df["label"],
                    textposition="outside",
                    textangle=0,
                    constraintext="none",
                    marker=dict(color=[TIER_COLORS.get(t, ACCENT_BLUE) for t in tier_df["risk_tier"]]),
                    hovertemplate="<b>%{x} Risk Tier</b><br>Observed Churn: %{y:.1f}%<br>Customers: %{customdata:,}<extra></extra>",
                    customdata=tier_df["customers"],
                )
            ]
        )
        apply_plotly_theme(fig_rate, height=340, title="Observed Churn Rate by Risk Tier", show_legend=False)
        fig_rate.update_xaxes(
            title="Risk Tier",
            categoryorder="array",
            categoryarray=["Low", "Medium", "High"],
        )
        fig_rate.update_yaxes(title="Observed Churn Rate (%)")
        st.plotly_chart(fig_rate, width="stretch")
        st.caption("Monotonically rising churn rates confirm that risk score thresholds effectively segment customer risk.")

    with chart_col2:
        fig_share = go.Figure(
            data=[
                go.Pie(
                    labels=tier_df["risk_tier"],
                    values=tier_df["customers"],
                    hole=0.62,
                    marker=dict(colors=[TIER_COLORS.get(t, ACCENT_BLUE) for t in tier_df["risk_tier"]]),
                    textinfo="label+percent",
                    hovertemplate="<b>%{label} Tier</b><br>Customers: %{value:,}<br>Portfolio Share: %{percent}<extra></extra>",
                    textfont=dict(size=12, color="#FFFFFF"),
                    sort=False,
                )
            ]
        )
        fig_share.add_annotation(
            text=f"<b>{total_customers:,}</b><br><span style='font-size:11px;color:#667085;'>Total</span>",
            x=0.5,
            y=0.5,
            font=dict(size=18, color=TEXT_PRIMARY, family="Inter, sans-serif"),
            showarrow=False,
        )
        apply_plotly_theme(fig_share, height=340, title="Customer Share by Risk Tier")
        st.plotly_chart(fig_share, width="stretch")
        st.caption("High-risk customers represent nearly one-third of the portfolio, requiring prioritized intervention.")

    # 3. Dynamic Business Insights Generated from Live Data
    st.markdown(
        """
        <div style="margin-top: 1.5rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Risk Tier Empirical Insights</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">Observed behavioral profiles and contrast between risk cohorts</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    low_row = tier_df[tier_df["risk_tier"] == "Low"].iloc[0]
    med_row = tier_df[tier_df["risk_tier"] == "Medium"].iloc[0]
    high_row = tier_df[tier_df["risk_tier"] == "High"].iloc[0]

    high_mult = high_row["actual_churn_rate"] / low_row["actual_churn_rate"] if low_row["actual_churn_rate"] > 0 else 0
    tenure_ratio = low_row["average_tenure"] / high_row["average_tenure"] if high_row["average_tenure"] > 0 else 0

    ins_cols = st.columns(3)
    with ins_cols[0]:
        render_insight_card(
            title="Tier Stratification Efficacy",
            body=f"Observed churn rises from <strong>{low_row['actual_churn_rate']:.1f}%</strong> in the Low tier to <strong>{high_row['actual_churn_rate']:.1f}%</strong> in the High tier (a <strong>{high_mult:.1f}x spread</strong>), validating model ranking power.",
        )
    with ins_cols[1]:
        render_insight_card(
            title="Tenure Disparity",
            body=f"Low-tier customers average <strong>{low_row['average_tenure']:.1f} months</strong> of tenure ({tenure_ratio:.1f}x longer), whereas High-risk accounts average only <strong>{high_row['average_tenure']:.1f} months</strong>.",
        )
    with ins_cols[2]:
        render_insight_card(
            title="High-Risk Cohort Profile",
            body=f"High-risk customers most commonly have <strong>{high_row['common_contract']}</strong> contracts, use <strong>{high_row['common_internet_service']}</strong>, and pay via <strong>{high_row['common_payment_method']}</strong> with ${high_row['average_monthly_charges']:.1f} avg charges.",
        )

    # 4. Tier Profile Summary Table
    st.markdown(
        """
        <div style="margin-top: 1.75rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #101828; margin: 0;">Comprehensive Risk Tier Profiles</h3>
            <p style="font-size: 0.825rem; color: #667085; margin: 0.15rem 0 0 0;">Attribute averages and most frequent configurations per segment</p>
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


def render_high_risk_customers(customers: pd.DataFrame, risk_scores: pd.DataFrame) -> None:
    """Render filterable customer-level risk scores and a CSV download."""
    render_page_header("High-Risk Customers", DATABASE_PATH, is_loaded=True)
    st.caption("Risk score ranks customers for review; it is not a calibrated probability of churn.")

    data = risk_scores.merge(customers, on="customerID", how="left", validate="one_to_one")
    with st.sidebar:
        st.markdown("<h4 style='color: #F8FAFC; margin-top: 0.5rem;'>Filters</h4>", unsafe_allow_html=True)
        search_id = st.text_input(
            "Search Customer ID",
            placeholder="e.g. 7590-VHVEG",
            key="risk_search_id",
            help="Filter by specific customer ID prefix or substring",
        )
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

    mask = (
        data["risk_tier"].isin(tiers)
        & data["Contract"].isin(contracts)
        & data["tenure"].between(*tenure_range)
        & data["MonthlyCharges"].between(*charge_range)
    )
    if search_id.strip():
        mask &= data["customerID"].str.contains(search_id.strip(), case=False, na=False)

    filtered = data[mask].sort_values("risk_score", ascending=False)

    display_columns = [
        "customerID",
        "risk_score",
        "risk_tier",
        "actual_churn",
        "Contract",
        "tenure",
        "MonthlyCharges",
        "InternetService",
        "PaymentMethod",
    ]
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
    display_table["Tenure (months)"] = display_table["Tenure (months)"].astype(int)
    display_table["Monthly charges ($)"] = display_table["Monthly charges ($)"].round(1)

    column_config = {
        "Customer ID": st.column_config.TextColumn("Customer ID", help="Demonstration customer identifier", width="medium"),
        "Risk score": st.column_config.ProgressColumn(
            "Risk score",
            help="Model risk score (0.0 to 1.0; ranks customers for review, not a calibrated probability)",
            format="%.3f",
            min_value=0.0,
            max_value=1.0,
            width="medium",
        ),
        "Risk tier": st.column_config.TextColumn("Risk tier", help="Assigned risk tier: Low (#16A34A), Medium (#F59E0B), or High (#DC2626)", width="small"),
        "Actual churn": st.column_config.TextColumn("Actual churn", help="Observed outcome in public demonstration data", width="small"),
        "Contract": st.column_config.TextColumn("Contract", width="medium"),
        "Tenure (months)": st.column_config.NumberColumn("Tenure (months)", help="Account tenure in months", format="%d", width="small"),
        "Monthly charges ($)": st.column_config.NumberColumn("Monthly charges ($)", help="Monthly recurring charges (MRC)", format="$%.1f", width="medium"),
        "Internet service": st.column_config.TextColumn("Internet service", width="medium"),
        "Payment method": st.column_config.TextColumn("Payment method", width="medium"),
    }

    st.write(f"Showing **{len(filtered):,}** customers")
    st.dataframe(
        display_table,
        column_config=column_config,
        width="stretch",
        hide_index=True,
        height=520,
    )
    st.download_button(
        "Download filtered customer list",
        data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="filtered_customer_risk_scores.csv",
        mime="text/csv",
    )
    st.caption("Privacy note: customer IDs shown here come from a public demonstration dataset.")


def render_recommendations() -> None:
    """Render the business recommendations report as styled cards in a width-limited container."""
    render_page_header("Strategic Recommendations", DATABASE_PATH, is_loaded=True)

    report_path = (OUTPUTS_DIR.parent / "reports" / "business_recommendations.md").resolve()
    if not report_path.exists():
        st.error("Recommendations report is missing. Run the Phase 5 workflow first.")
        return

    content = report_path.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## )", content)

    # Supporting numbers mapped to recommendations
    supporting_metrics = {
        1: "57.83% High-Tier Churn &bull; 2,236 Accounts",
        2: "47.44% First-Year Churn &bull; 13.8 Mo Avg Tenure",
        3: "42.71% Month-to-Month Churn (vs 2.83% Two-Year)",
        4: "45.29% Electronic Check Churn (vs 15.24% Auto Credit Card)",
        5: "41.64% No TechSupport &bull; 41.77% No OnlineSecurity",
    }

    # Width-limited container layout
    st.markdown('<div class="rec-container">', unsafe_allow_html=True)

    # Preamble / Context card
    if len(sections) > 0:
        preamble_lines = sections[0].strip().split("\n")
        preamble_text = "\n".join([line for line in preamble_lines if not line.startswith("#")]).strip()
        if preamble_text:
            st.info(preamble_text)

    # Render recommendations 1 to 5 as styled cards
    for section in sections[1:]:
        lines = section.strip().split("\n")
        header = lines[0].replace("## ", "").strip()
        body = "\n".join(lines[1:]).strip()

        # Check if recommendation 1-5
        rec_match = re.match(r"^(\d+)\.\s*(.*)", header)
        if rec_match:
            rec_num = int(rec_match.group(1))
            rec_title = rec_match.group(2)
            stat_badge = supporting_metrics.get(rec_num, "")

            # Convert markdown inline code `code` to <code>code</code> without altering wording
            body_html = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)

            st.markdown(
                f"""
                <div class="rec-card">
                    <div class="rec-header">
                        <div class="rec-title-group">
                            <span class="rec-badge">Recommendation {rec_num}</span>
                            <span class="rec-title">{rec_title}</span>
                        </div>
                        <span class="rec-stat-badge">{stat_badge}</span>
                    </div>
                    <div class="rec-body">{body_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Cost Assumption Note" in header:
            body_html = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)
            st.markdown(
                f"""
                <div class="rec-note-card">
                    <div class="rec-note-title">Cost Assumption Note</div>
                    <div class="rec-note-body">{body_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Limitations" in header:
            # Format bullet points
            bullet_items = [
                f"<li>{line.lstrip('- ').strip()}</li>"
                for line in body.split("\n")
                if line.strip().startswith("-")
            ]
            bullets_html = "".join(bullet_items)
            st.markdown(
                f"""
                <div class="rec-limitations-card">
                    <div class="rec-limitations-title">Analytical Scope &amp; Governance Limitations</div>
                    <ul class="rec-limitations-list">
                        {bullets_html}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


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
