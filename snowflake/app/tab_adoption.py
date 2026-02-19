# =============================================================================
# tab_adoption.py - Tab6: 普及・定着分析
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from helpers import apply_plotly, section
from queries import get_monthly_active, get_feature_adoption
from demo_data import demo_monthly, demo_feature_adoption


def render_adoption(team_id: str, days: int):
    section("普及・定着分析")

    # ── 月次アクティブユーザー ────────────────────────────────────
    monthly = get_monthly_active(team_id)
    if monthly.empty:
        monthly = demo_monthly()
    monthly.columns = [c.upper() for c in monthly.columns]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["MONTH"], y=monthly["ACTIVE_USERS"],
        name="月次アクティブユーザー",
        line=dict(color="#f59e0b", width=2.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.15)",
        marker=dict(size=6, color="#f59e0b"),
    ))
    fig.add_trace(go.Bar(
        x=monthly["MONTH"], y=monthly["SESSIONS"],
        name="セッション数",
        marker_color="rgba(13,148,136,0.25)",
        yaxis="y2",
    ))
    fig.update_layout(
        title_text="月次アクティブユーザー推移",
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(color="#0d9488", size=9)),
        legend=dict(orientation="h", y=1.1, x=0),
    )
    fig = apply_plotly(fig, 280)
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 機能普及率 ───────────────────────────────────────────────
    section("機能普及率")
    fa_df = get_feature_adoption(team_id, days)
    if fa_df.empty:
        fa_df = demo_feature_adoption()
    fa_df.columns = [c.upper() for c in fa_df.columns]
    fa = fa_df.iloc[0]

    total = int(fa.get("TOTAL_USERS", 1)) or 1
    features = [
        ("Skill",    int(fa.get("SKILL_USERS",    0)), "#0d9488", "var(--accent-teal)"),
        ("MCP",      int(fa.get("MCP_USERS",      0)), "#8b5cf6", "var(--accent-violet)"),
        ("Subagent", int(fa.get("SUBAGENT_USERS", 0)), "#16a34a", "var(--accent-green)"),
        ("Command",  int(fa.get("COMMAND_USERS",  0)), "#3b82f6", "var(--accent-blue)"),
    ]

    ca, cb = st.columns([2, 3])

    with ca:
        bars_html = ""
        for fname, count, hex_color, _ in features:
            pct = round(count / total * 100)
            bars_html += (
                f'<div style="margin-bottom:1rem">'
                f'<div style="display:flex;justify-content:space-between;'
                f'margin-bottom:0.3rem">'
                f'<span style="font-size:0.78rem;font-weight:600;'
                f'color:var(--text-primary)">{fname}</span>'
                f'<span style="font-family:var(--mono-font);font-size:0.78rem;'
                f'color:{hex_color}">{count}/{total} ({pct}%)</span>'
                f"</div>"
                f'<div class="progress-track" style="height:8px">'
                f'<div class="progress-fill" style="width:{pct}%;background:{hex_color}">'
                f"</div></div></div>"
            )
        st.markdown(f'<div class="chart-wrap">{bars_html}</div>', unsafe_allow_html=True)

    with cb:
        feat_names  = [f[0] for f in features]
        feat_pcts   = [round(f[1] / total * 100) for f in features]
        feat_colors = [f[2] for f in features]

        fig2 = go.Figure(go.Bar(
            y=feat_names, x=feat_pcts,
            orientation="h",
            marker=dict(color=feat_colors),
            text=[f"{p}%" for p in feat_pcts],
            textposition="outside",
            textfont=dict(size=11, color="#8b949e"),
        ))
        fig2.update_layout(
            title_text="機能活用率 (%)",
            xaxis=dict(range=[0, 115], title=""),
            yaxis={"categoryorder": "total ascending"},
        )
        fig2 = apply_plotly(fig2, 240)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 未使用者サマリー ─────────────────────────────────────────
    section("未使用者サマリー")
    cols = st.columns(4)
    for (fname, count, hex_color, accent), col in zip(features, cols):
        non = total - count
        with col:
            st.markdown(
                f'<div class="kpi-card" style="--accent-color:{accent}">'
                f'<div class="kpi-label">{fname} 未使用者</div>'
                f'<div class="kpi-value" style="font-size:1.5rem">{non}</div>'
                f'<div class="kpi-change neu" style="font-size:0.7rem">'
                f"/ {total} 名中</div></div>",
                unsafe_allow_html=True,
            )
