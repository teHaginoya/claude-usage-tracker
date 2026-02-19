# =============================================================================
# tab_tools.py - Tab3: ツール分析
# =============================================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from helpers import apply_plotly, section
from queries import get_tool_stats, get_tool_trend
from demo_data import demo_tools, demo_tool_trend


def render_tools(team_id: str, days: int):
    section("ツール利用分析")

    tool_df = get_tool_stats(team_id, days)
    if tool_df.empty:
        tool_df = demo_tools()
    tool_df.columns = [c.upper() for c in tool_df.columns]

    c1, c2 = st.columns([3, 2])

    # ── 水平棒グラフ ─────────────────────────────────────────────
    with c1:
        fig = go.Figure(go.Bar(
            x=tool_df["TOTAL_COUNT"],
            y=tool_df["TOOL_NAME"],
            orientation="h",
            marker=dict(
                color=tool_df["TOTAL_COUNT"],
                colorscale=[[0, "#ccfbf1"], [0.5, "#14b8a6"], [1, "#0d9488"]],
                showscale=False,
            ),
            text=tool_df["TOTAL_COUNT"],
            textposition="outside",
            textfont=dict(size=10, color="#64748b"),
        ))
        fig.update_layout(
            title_text="ツール利用ランキング",
            yaxis={"categoryorder": "total ascending"},
        )
        fig = apply_plotly(fig, 400)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 成功率テーブル ───────────────────────────────────────────
    with c2:
        section("成功率")
        rows_html = ""
        for _, row in tool_df.head(10).iterrows():
            name  = str(row.get("TOOL_NAME",    "—"))
            tot   = int(row.get("TOTAL_COUNT",   0))
            rate  = row.get("SUCCESS_RATE", None)

            if rate is None or str(rate) == "nan":
                rate_html = '<span style="color:var(--text-muted)">—</span>'
                bar_pct, bar_color = 0, "#e2e8f0"
            else:
                rate = float(rate)
                bar_pct   = rate
                bar_color = "#16a34a" if rate >= 90 else "#f59e0b" if rate >= 70 else "#e11d48"
                rate_html = (
                    f'<span style="color:{bar_color};font-family:var(--mono-font)">'
                    f"{rate:.1f}%</span>"
                )

            rows_html += f"""
            <tr>
                <td class="user-name" style="font-size:0.78rem">{name}</td>
                <td class="num-cell">{tot:,}</td>
                <td style="min-width:80px">
                    {rate_html}
                    <div class="progress-track" style="margin-top:0.25rem">
                        <div class="progress-fill"
                             style="width:{bar_pct}%;background:{bar_color}">
                        </div>
                    </div>
                </td>
            </tr>"""

        st.markdown(
            f'<div style="background:var(--bg-card);border:1px solid var(--border);'
            f'border-radius:10px;overflow:hidden">'
            f'<table class="rank-table">'
            f"<thead><tr>"
            f"<th>ツール</th>"
            f'<th style="text-align:right">実行数</th>'
            f"<th>成功率</th>"
            f"</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True,
        )

    # ── 日次トレンド ─────────────────────────────────────────────
    section("ツール利用トレンド（上位5）")
    trend = get_tool_trend(team_id, days)
    if trend.empty:
        trend = demo_tool_trend(days)
    trend.columns = [c.upper() for c in trend.columns]

    fig3 = px.line(
        trend, x="EVENT_DATE", y="CNT", color="TOOL_NAME",
        color_discrete_sequence=["#f59e0b", "#0d9488", "#8b5cf6", "#3b82f6", "#16a34a"],
        labels={"EVENT_DATE": "", "CNT": "実行数", "TOOL_NAME": "ツール"},
    )
    fig3.update_layout(
        title_text="Top 5 ツール 日次推移",
        legend=dict(orientation="h", y=1.1, x=0),
    )
    fig3 = apply_plotly(fig3, 240)
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
