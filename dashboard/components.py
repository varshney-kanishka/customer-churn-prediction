"""Reusable UI components for the CHURNIQ customer intelligence dashboard."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


def render_page_header(
    title: str,
    db_path: Path,
    is_loaded: bool = True,
) -> None:
    """Render the standard top header on every page with compact aligned status and refresh."""
    header_col, meta_col = st.columns([3, 2], vertical_alignment="center")

    with header_col:
        st.markdown(
            f"""
            <div>
                <h1 style="font-size: 1.55rem; font-weight: 700; color: #0F172A; margin: 0; letter-spacing: -0.02em;">{title}</h1>
                <p style="font-size: 0.825rem; color: #64748B; margin: 0.2rem 0 0 0;">Predict, analyze and reduce customer churn.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with meta_col:
        status_html = (
            '<span class="status-pill status-pill-green"><span class="status-dot status-dot-green"></span>Active</span>'
            if is_loaded
            else '<span class="status-pill status-pill-red"><span class="status-dot status-dot-red"></span>Offline</span>'
        )

        db_time_str = "Unavailable"
        if db_path.exists():
            mod_time = datetime.datetime.fromtimestamp(db_path.stat().st_mtime)
            db_time_str = mod_time.strftime("%b %d, %H:%M")

        pill_col, btn_col = st.columns([4, 1], vertical_alignment="center")
        with pill_col:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.65rem;">
                    {status_html}
                    <span class="db-timestamp" style="white-space: nowrap;">Database built: {db_time_str}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button("Refresh", key="hdr_refresh_btn", help="Clear cached database tables and reload", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)


def render_kpi_card(
    label: str,
    value: str,
    caption: str,
) -> None:
    """Render a single styled metric card with clear hierarchy."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            <div class="kpi-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(customers: pd.DataFrame) -> None:
    """Render primary portfolio KPI cards and monthly recurring charge metrics."""
    total_customers = len(customers)
    churned_customers = int(customers["churn_flag"].sum())
    churn_rate = customers["churn_flag"].mean() * 100
    retention_rate = (1.0 - customers["churn_flag"].mean()) * 100
    avg_mrc = customers["MonthlyCharges"].mean()
    total_mrc = customers["MonthlyCharges"].sum()
    churned_mrc = customers.loc[customers["churn_flag"] == 1, "MonthlyCharges"].sum()
    churned_mrc_pct = (churned_mrc / total_mrc * 100) if total_mrc > 0 else 0.0

    cols = st.columns(5)
    with cols[0]:
        render_kpi_card(
            label="Total customers",
            value=f"{total_customers:,}",
            caption="Customers in dataset",
        )
    with cols[1]:
        render_kpi_card(
            label="Churned customers",
            value=f"{churned_customers:,}",
            caption=f"of {total_customers:,} customers",
        )
    with cols[2]:
        render_kpi_card(
            label="Churn rate",
            value=f"{churn_rate:.1f}%",
            caption="Portfolio rate",
        )
    with cols[3]:
        render_kpi_card(
            label="Retention rate",
            value=f"{retention_rate:.1f}%",
            caption=f"{total_customers - churned_customers:,} retained",
        )
    with cols[4]:
        render_kpi_card(
            label="Avg monthly charge",
            value=f"${avg_mrc:,.1f}",
            caption=f"${total_mrc:,.0f} MRC",
        )

    # Secondary strip for MRC impact
    st.markdown("<div style='margin-top: 0.65rem;'></div>", unsafe_allow_html=True)
    mrc_cols = st.columns(3)
    with mrc_cols[0]:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 0.55rem 0.9rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);">
                <span style="font-size: 0.78rem; font-weight: 500; color: #64748B;">Total Portfolio MRC</span>
                <span style="font-size: 0.95rem; font-weight: 700; color: #0F172A;">${total_mrc:,.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with mrc_cols[1]:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 0.55rem 0.9rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);">
                <span style="font-size: 0.78rem; font-weight: 500; color: #64748B;">Churned Customer MRC</span>
                <span style="font-size: 0.95rem; font-weight: 700; color: #DC2626;">${churned_mrc:,.0f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with mrc_cols[2]:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 0.55rem 0.9rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);">
                <span style="font-size: 0.78rem; font-weight: 500; color: #64748B;">Churned MRC Share</span>
                <span style="font-size: 0.95rem; font-weight: 700; color: #DC2626;">{churned_mrc_pct:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<div style='margin-bottom: 1.15rem;'></div>", unsafe_allow_html=True)


def render_tier_card(
    tier: str,
    customers: int,
    share: float,
    churn_rate: float,
    color: str,
    avg_tenure: float,
    avg_mrc: float,
) -> None:
    """Render a dedicated metric card for a risk tier."""
    pill_class = f"tier-pill-{tier.lower()}"
    dot_class = "status-dot-green" if tier == "Low" else ("status-dot-red" if tier == "High" else "")
    dot_style = "background-color: #F59E0B;" if tier == "Medium" else ""

    dot_html = (
        f'<span class="status-dot {dot_class}"></span>'
        if dot_class
        else f'<span class="status-dot" style="{dot_style}"></span>'
    )

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-top: 3px solid {color}; border-radius: 12px; padding: 1.15rem 1.25rem; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03); min-height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <span class="tier-pill {pill_class}">{dot_html}{tier} Risk Tier</span>
                <span style="font-size: 0.75rem; font-weight: 500; color: #64748B;">{share:.1f}% share</span>
            </div>
            <div>
                <div style="font-size: 1.75rem; font-weight: 700; color: #0F172A; line-height: 1.15;">{customers:,}</div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 0.2rem;">Avg tenure {avg_tenure:.1f} mo &bull; Avg ${avg_mrc:,.1f}/mo</div>
            </div>
            <div style="margin-top: 0.65rem; padding-top: 0.55rem; border-top: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.78rem; color: #64748B;">Observed Churn Rate</span>
                <span style="font-size: 0.95rem; font-weight: 700; color: {color};">{churn_rate:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_card(title: str, body: str) -> None:
    """Render an executive insight callout card."""
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">{title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Render standardized footer across all pages."""
    st.markdown(
        """
        <div class="churniq-footer">
            <strong>CHURNIQ</strong> &nbsp;|&nbsp; Built with Streamlit, scikit-learn, XGBoost and SQLite &nbsp;|&nbsp; Public demonstration dataset
        </div>
        """,
        unsafe_allow_html=True,
    )
