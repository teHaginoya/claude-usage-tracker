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
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#64748b", family="DM Mono, monospace", size=11),
    colorway=["#f59e0b", "#0d9488", "#8b5cf6", "#3b82f6", "#16a34a", "#e11d48"],
    margin=dict(l=4, r=4, t=36, b=4),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        font=dict(size=10, color="#64748b"),
    ),
)


def apply_plotly(fig, height=280):
    fig.update_layout(**PLOTLY_BASE, height=height)
    fig.update_layout(hoverlabel=dict(
        bgcolor="#1e293b",
        bordercolor="#334155",
        font=dict(color="#f1f5f9", size=12),
    ))
    fig.update_xaxes(
        showgrid=True, gridcolor="#e2e8f0",
        linecolor="#dde3ed", zeroline=False,
        tickfont=dict(size=10, color="#94a3b8"),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#e2e8f0",
        linecolor="#dde3ed", zeroline=False,
        tickfont=dict(size=10, color="#94a3b8"),
    )
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
        f'<span style="font-family:var(--mono-font);color:var(--text-muted);font-size:0.8rem">{r}</span>',
    )

# =============================================================================
# HTML コンポーネント
# =============================================================================

def sparkbars(heights=None, color="var(--accent-teal)"):
    if heights is None:
        heights = [25, 40, 30, 55, 45, 68, 60, 78]
    bars = "".join(
        f'<span style="height:{h}%;background:{color}"></span>' for h in heights
    )
    return f'<div class="kpi-sparkbar">{bars}</div>'


# CSS変数 → hex（スパークバー・グロー用）
_ACCENT_HEX = {
    "var(--accent-teal)":   "#0d9488",
    "var(--accent-amber)":  "#f59e0b",
    "var(--accent-violet)": "#8b5cf6",
    "var(--accent-blue)":   "#3b82f6",
    "var(--accent-green)":  "#16a34a",
    "var(--negative)":      "#e11d48",
}

_GLOW_HEX = {
    "var(--accent-teal)":   "rgba(13,148,136,0.07)",
    "var(--accent-amber)":  "rgba(245,158,11,0.07)",
    "var(--accent-violet)": "rgba(139,92,246,0.07)",
    "var(--accent-blue)":   "rgba(59,130,246,0.07)",
    "var(--accent-green)":  "rgba(22,163,74,0.07)",
    "var(--negative)":      "rgba(225,29,72,0.07)",
}


def kpi_card(label, value, change_val, accent, badge=None, extra_html="", value_fmt=None):
    change_text, change_cls = fmt_change(change_val)
    badge_html = (
        f'<span class="badge">{badge}</span>'
        if badge else ""
    )
    sc   = _ACCENT_HEX.get(accent, "#2dd4bf")
    glow = _GLOW_HEX.get(accent, "rgba(45,212,191,0.07)")
    if value_fmt:
        val_str = value_fmt
    elif isinstance(value, float):
        val_str = f"{value:,.1f}"
    else:
        val_str = f"{int(value or 0):,}"
    return (
        f'<div class="kpi-card" style="--accent-color:{accent};--glow-color:{glow}">'
        f'<div class="kpi-label">{label}{badge_html}</div>'
        f'<div class="kpi-value">{val_str}</div>'
        f'<div class="kpi-change {change_cls}">{change_text}'
        f'<span class="period">前期比</span></div>'
        f"{sparkbars(color=sc)}"
        f"{extra_html}"
        f"</div>"
    )


def section(title, sub=""):
    sub_html = (
        f'<span class="section-sub">{sub}</span>'
        if sub else ""
    )
    st.markdown(
        f'<div class="section-header">{title}{sub_html}</div>',
        unsafe_allow_html=True,
    )
