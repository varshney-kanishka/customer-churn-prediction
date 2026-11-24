"""Centralized styling system, color palette, custom CSS, and Plotly templates."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# Color Palette
PRIMARY_NAVY = "#101828"
NAVY_SIDEBAR = "#101828"
ACCENT_BLUE = "#2563EB"
ACCENT_TEAL = "#14B8A6"
BG_LIGHT = "#F8FAFC"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E5E7EB"
TEXT_PRIMARY = "#101828"
TEXT_MUTED = "#667085"

# Fixed Risk-Tier Colors
TIER_COLORS = {
    "Low": "#16A34A",       # Green
    "Medium": "#F59E0B",    # Amber
    "High": "#DC2626",      # Red
}

# Churn Status Colors
STATUS_COLORS = {
    "Retained": "#14B8A6",  # Teal
    "Churned": "#DC2626",   # Red / Coral
    "No": "#14B8A6",
    "Yes": "#DC2626",
}

FONT_FAMILY = "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def apply_plotly_theme(
    fig: go.Figure,
    height: int = 360,
    title: str | None = None,
    show_legend: bool = True,
) -> go.Figure:
    """Apply consistent SaaS theme to any Plotly chart."""
    layout_updates = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": dict(family=FONT_FAMILY, color=TEXT_PRIMARY, size=12),
        "height": height,
        "margin": dict(l=24, r=24, t=54 if title else 24, b=32),
        "showlegend": show_legend,
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_MUTED),
        ),
        "hoverlabel": dict(
            bgcolor="#FFFFFF",
            bordercolor=BORDER_COLOR,
            font=dict(family=FONT_FAMILY, size=12, color=TEXT_PRIMARY),
        ),
    }

    if title:
        layout_updates["title"] = dict(
            text=f"<b>{title}</b>",
            font=dict(size=15, color=TEXT_PRIMARY, family=FONT_FAMILY),
            x=0.0,
            xanchor="left",
            y=0.96,
        )

    fig.update_layout(**layout_updates)
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        gridwidth=1,
        zeroline=True,
        zerolinecolor="#E2E8F0",
        tickfont=dict(size=11, color=TEXT_MUTED, family=FONT_FAMILY),
        title_font=dict(size=12, color=TEXT_PRIMARY, family=FONT_FAMILY),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        gridwidth=1,
        zeroline=True,
        zerolinecolor="#E2E8F0",
        tickfont=dict(size=11, color=TEXT_MUTED, family=FONT_FAMILY),
        title_font=dict(size=12, color=TEXT_PRIMARY, family=FONT_FAMILY),
    )
    return fig


def inject_custom_css() -> None:
    """Inject custom CSS for typography, layout, sidebar, and cards."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Base Typography & Background */
        html, body, [class*="css"] {{
            font-family: {FONT_FAMILY} !important;
            color: {TEXT_PRIMARY};
        }}
        .stApp {{
            background-color: {BG_LIGHT};
        }}

        /* Container Padding */
        .block-container {{
            max-width: 1400px;
            padding-top: 1.25rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

        /* Hide Streamlit Clutter */
        #MainMenu {{visibility: hidden;}}
        header [data-testid="stToolbar"] {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        /* Hide Heading Anchor / Link Icons */
        [data-testid="stHeaderActionElements"],
        .header-anchor,
        a.header-anchor,
        a[data-testid="stHeaderAnchor"],
        [data-testid="stMarkdownContainer"] a.header-anchor,
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {{
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }}

        /* Sidebar Styling (Dark Navy #101828) */
        section[data-testid="stSidebar"] {{
            background-color: {NAVY_SIDEBAR} !important;
            border-right: 1px solid #1F2A37;
        }}
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
            gap: 0.6rem;
        }}
        section[data-testid="stSidebar"] * {{
            color: #F8FAFC;
        }}

        /* Sidebar Navigation: Robust styling using stable data-testid & role attributes.
           Streamlit nests (1) the circular radio indicator and (2) stMarkdownContainer
           inside an inner flex div. Targeting '> div > div:first-child' hides solely
           the circular radio mark without collapsing the label or Material icon text. */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {{
            gap: 0.35rem !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"] > div > div:first-child,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]),
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div > div:first-child,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div > div:not([data-testid="stMarkdownContainer"]),
        section[data-testid="stSidebar"] div[data-testid="stRadio"] input[type="radio"],
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stWidgetSelection"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            opacity: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            pointer-events: none !important;
        }}

        /* Navigation Label & Material Icon Container */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stMarkdownContainer"],
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] {{
            display: flex !important;
            align-items: center !important;
            visibility: visible !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{
            margin: 0 !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            line-height: 1.4 !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] span {{
            vertical-align: middle !important;
        }}

        /* Inactive Navigation Items: plain text, subtle hover state */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"],
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label {{
            display: flex !important;
            align-items: center !important;
            padding: 0.55rem 0.85rem !important;
            border-radius: 8px !important;
            border-left: 3px solid transparent !important;
            background-color: transparent !important;
            cursor: pointer !important;
            transition: background-color 0.15s ease, border-left-color 0.15s ease, color 0.15s ease !important;
            margin: 0 !important;
            width: 100% !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"] p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"] span,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label span {{
            color: #94A3B8 !important;
            transition: color 0.15s ease-in-out !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {{
            background-color: rgba(255, 255, 255, 0.05) !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:hover p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:hover span,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover span {{
            color: #F8FAFC !important;
        }}

        /* Active Navigation Item: highlighted background #1E293B + blue left accent bar */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked),
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"][data-selected="true"],
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked),
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-selected="true"] {{
            background-color: #1E293B !important;
            border-left: 3px solid {ACCENT_BLUE} !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) span,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"][data-selected="true"] p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stRadioOption"][data-selected="true"] span,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) span,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-selected="true"] p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-selected="true"] span {{
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }}

        section[data-testid="stSidebar"] hr {{
            border-color: #1F2A37 !important;
            margin: 0.8rem 0;
        }}
        section[data-testid="stSidebar"] .stMultiSelect label,
        section[data-testid="stSidebar"] .stSlider label {{
            color: #CBD5E1 !important;
            font-size: 0.825rem !important;
            font-weight: 500 !important;
        }}

        /* KPI Card Component: Equal Fixed Height & Overflow Protection */
        .kpi-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 14px;
            padding: 1.15rem 1.15rem;
            box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 125px;
            height: 125px;
            box-sizing: border-box;
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }}
        .kpi-card:hover {{
            box-shadow: 0 4px 6px -1px rgba(16, 24, 40, 0.1);
        }}
        .kpi-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }}
        .kpi-label {{
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: none;
            letter-spacing: 0.01em;
            color: {TEXT_MUTED};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .kpi-value {{
            font-size: 1.85rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}
        .kpi-caption {{
            font-size: 0.78rem;
            color: {TEXT_MUTED};
            margin-top: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Section Cards & Containers */
        .section-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
            margin-bottom: 1.25rem;
        }}

        /* Insight Card Component */
        .insight-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-left: 4px solid {ACCENT_BLUE};
            border-radius: 10px;
            padding: 1rem 1.25rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            height: 100%;
        }}
        .insight-title {{
            font-size: 0.875rem;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            margin-bottom: 0.35rem;
        }}
        .insight-body {{
            font-size: 0.825rem;
            color: #475467;
            line-height: 1.5;
        }}

        /* Header Components */
        .page-header-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid {BORDER_COLOR};
        }}
        .page-header-title {{
            font-size: 1.75rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .page-header-subtitle {{
            font-size: 0.9rem;
            color: {TEXT_MUTED};
            margin-top: 0.25rem;
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        /* Status Pills */
        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .status-pill-green {{
            background-color: #DCFCE7;
            color: #15803D;
            border: 1px solid #BBF7D0;
        }}
        .status-pill-red {{
            background-color: #FEE2E2;
            color: #B91C1C;
            border: 1px solid #FECACA;
        }}
        .status-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-dot-green {{ background-color: #16A34A; }}
        .status-dot-red {{ background-color: #DC2626; }}

        .db-timestamp {{
            font-size: 0.8rem;
            color: {TEXT_MUTED};
            font-weight: 500;
        }}

        /* Recommendations View: Styled Cards & Limited Width */
        .rec-container {{
            max-width: 920px;
            margin: 0 auto;
        }}
        .rec-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-left: 4px solid {ACCENT_BLUE};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
        }}
        .rec-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.65rem;
        }}
        .rec-title-group {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            flex-wrap: wrap;
        }}
        .rec-badge {{
            background-color: #EFF6FF;
            color: {ACCENT_BLUE};
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            border: 1px solid #DBEAFE;
        }}
        .rec-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        .rec-stat-badge {{
            background-color: #F8FAFC;
            color: #475467;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            border: 1px solid {BORDER_COLOR};
        }}
        .rec-body {{
            font-size: 0.885rem;
            color: #374151;
            line-height: 1.6;
        }}
        .rec-body code {{
            background: #F1F5F9;
            color: #0F172A;
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
            font-size: 0.825rem;
            font-family: monospace;
        }}

        /* Note & Limitations Cards */
        .rec-note-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #64748B;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-top: 1.25rem;
            margin-bottom: 1rem;
        }}
        .rec-note-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.4rem;
        }}
        .rec-note-body {{
            font-size: 0.85rem;
            color: #475467;
            line-height: 1.55;
        }}
        .rec-limitations-card {{
            background: #FFFBEB;
            border: 1px solid #FDE68A;
            border-left: 4px solid #F59E0B;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }}
        .rec-limitations-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: #92400E;
            margin-bottom: 0.5rem;
        }}
        .rec-limitations-list {{
            margin: 0;
            padding-left: 1.25rem;
            font-size: 0.85rem;
            color: #78350F;
            line-height: 1.6;
        }}

        /* Responsive & Accessibility Enhancements */
        @media (max-width: 900px) {{
            .block-container {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }}
            .page-header-container {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.75rem;
            }}
            .header-meta {{
                flex-wrap: wrap;
            }}
            .kpi-card {{
                min-height: 110px;
                height: auto;
            }}
            .rec-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}

        /* Contain horizontal scroll at the page root, ensure table containers scroll internally */
        .stApp {{
            overflow-x: hidden;
        }}
        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {{
            max-width: 100% !important;
            overflow-x: auto !important;
        }}

        /* Footer */
        .churniq-footer {{
            border-top: 1px solid {BORDER_COLOR};
            padding-top: 1.5rem;
            margin-top: 3rem;
            text-align: center;
            color: {TEXT_MUTED};
            font-size: 0.825rem;
            letter-spacing: 0.01em;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
