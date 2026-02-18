# =============================================================================
# helpers.py - 共通ユーティリティ / Plotly設定 / Snowflake セッション
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session
from datetime import datetime

# =============================================================================
# Snowflake セッション
# =============================================================================

@st.cache_resource
def get_session():
    return get_active_session()

# =============================================================================
# Plotly ベース設定
# =============================================================================

PLOTLY_BASE = dict(
    paper_bgcolor="#141c2e",
    plot_bgcolor="#141c2e",
    font=dict(color="#8899b8", family="DM Mono, monospace", size=11),
    colorway=["#f59e0b", "#14b8a6", "#8b5cf6", "#3b82f6", "#22c55e", "#f43f5e"],
    margin=dict(l=4, r=4, t=32, b=4),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        font=dict(size=10, color="#8899b8"),
    ),
)


def apply_plotly(fig, height=280):
    fig.update_layout(**PLOTLY_BASE, height=height)
    fig.update_xaxes(showgrid=True, gridcolor="#1f2d4a", linecolor="#1f2d4a")
    fig.update_yaxes(showgrid=True, gridcolor="#1f2d4a", linecolor="#1f2d4a")
    return fig

# =============================================================================
# 計算ヘルパー
# =============================================================================

def calc_change(cur, prev):
    cur  = cur  or 0
    prev = prev or 0
    if prev == 0:
        return 100.0 if cur > 0 else 0.0
    return round((cur - prev) / prev * 100, 1)


def fmt_change(ch):
    if ch > 0:
        return f"▲ +{ch}%", "pos"
    elif ch < 0:
        return f"▼ {ch}%", "neg"
    return "— 0%", "neu"


def time_ago(dt):
    if pd.isna(dt):
        return "—"
    now = datetime.now()
    try:
        diff = now - pd.to_datetime(dt).replace(tzinfo=None)
    except Exception:
        return "—"
    if diff.days > 0:
        return f"{diff.days}日前"
    h = diff.seconds // 3600
    if h > 0:
        return f"{h}時間前"
    m = diff.seconds // 60
    return f"{m}分前" if m > 0 else "今"


def rank_icon(r):
    icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    return icons.get(
        r,
        f'<span style="font-family:var(--mono-font);color:var(--text-muted)">{r}</span>',
    )

# =============================================================================
# HTML コンポーネント
# =============================================================================

def sparkbars(heights=None, color="var(--accent-teal)"):
    if heights is None:
        heights = [30, 45, 35, 60, 50, 70, 65]
    bars = "".join(
        f'<span style="height:{h}%;background:{color}"></span>' for h in heights
    )
    return f'<div class="kpi-sparkbar">{bars}</div>'


_ACCENT_HEX = {
    "var(--accent-teal)":   "#14b8a6",
    "var(--accent-amber)":  "#f59e0b",
    "var(--accent-violet)": "#8b5cf6",
    "var(--accent-blue)":   "#3b82f6",
    "var(--accent-green)":  "#22c55e",
    "var(--negative)":      "#f43f5e",
}


def kpi_card(label, value, change_val, accent, badge=None, extra_html="", value_fmt=None):
    change_text, change_cls = fmt_change(change_val)
    badge_html = (
        f'<span class="badge" style="background:rgba(255,255,255,0.08);'
        f'color:var(--text-muted)">{badge}</span>'
        if badge else ""
    )
    sc = _ACCENT_HEX.get(accent, "#14b8a6")
    if value_fmt:
        val_str = value_fmt
    elif isinstance(value, float):
        val_str = f"{value:,.1f}"
    else:
        val_str = f"{int(value or 0):,}"
    return (
        f'<div class="kpi-card" style="--accent-color:{accent}">'
        f'<div class="kpi-label">{label}{badge_html}</div>'
        f'<div class="kpi-value">{val_str}</div>'
        f'<div class="kpi-change {change_cls}">{change_text}'
        f'<span style="color:var(--text-muted);font-weight:400">前期比</span></div>'
        f"{sparkbars(color=sc)}"
        f"{extra_html}"
        f"</div>"
    )


def section(title, sub=""):
    sub_html = (
        f' <span style="font-size:0.65rem;font-weight:400;text-transform:none;'
        f'letter-spacing:0;color:var(--text-muted)">{sub}</span>'
        if sub else ""
    )
    st.markdown(
        f'<div class="section-header">{title}{sub_html}</div>',
        unsafe_allow_html=True,
    )
