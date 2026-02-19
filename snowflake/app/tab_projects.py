# =============================================================================
# tab_projects.py - Tab5: プロジェクト分析
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from helpers import apply_plotly, section
from queries import get_project_ranking


def render_projects(team_id: str, days: int):
    section("プロジェクト別分析")

    proj_df = get_project_ranking(team_id, days)
    if proj_df.empty:
        st.info("期間内のプロジェクトデータがありません")
        return
    proj_df.columns = [c.upper() for c in proj_df.columns]
    col_name = "PROJECT_NAME" if "PROJECT_NAME" in proj_df.columns else proj_df.columns[0]

    # ── 水平棒グラフ ─────────────────────────────────────────────
    fig = go.Figure(go.Bar(
        x=proj_df["EVENT_COUNT"],
        y=proj_df[col_name],
        orientation="h",
        marker=dict(
            color=proj_df["EVENT_COUNT"],
            colorscale=[[0, "#dbeafe"], [0.5, "#3b82f6"], [1, "#1d4ed8"]],
            showscale=False,
        ),
        text=proj_df["EVENT_COUNT"],
        textposition="outside",
        textfont=dict(size=10, color="#64748b"),
        customdata=proj_df[["USER_COUNT", "MSG_COUNT"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "イベント数: %{x:,}<br>"
            "ユーザー数: %{customdata[0]}<br>"
            "メッセージ: %{customdata[1]:,}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title_text="プロジェクト別イベント数",
        yaxis={"categoryorder": "total ascending"},
    )
    fig = apply_plotly(fig, 380)
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 統計テーブル ─────────────────────────────────────────────
    section("プロジェクト統計")
    rows_html = ""
    for _, row in proj_df.iterrows():
        full_name = str(row.get(col_name, "—"))
        short = full_name.split("/")[-1] if "/" in full_name else full_name
        ec  = int(row.get("EVENT_COUNT",  0))
        uc  = int(row.get("USER_COUNT",   0))
        mc  = int(row.get("MSG_COUNT",    0))
        sk  = int(row.get("SKILL_COUNT",  0))
        mcp = int(row.get("MCP_COUNT",    0))
        rows_html += f"""
        <tr>
            <td class="user-name" style="font-size:0.78rem"
                title="{full_name}">{short}</td>
            <td class="num-cell highlight">{ec:,}</td>
            <td class="num-cell">{uc}</td>
            <td class="num-cell">{mc:,}</td>
            <td class="num-cell">{sk}</td>
            <td class="num-cell">{mcp}</td>
        </tr>"""

    st.markdown(
        f'<div style="background:var(--bg-card);border:1px solid var(--border);'
        f'border-radius:10px;overflow:hidden">'
        f'<table class="rank-table">'
        f"<thead><tr>"
        f"<th>プロジェクト</th>"
        f'<th style="text-align:right">イベント ↓</th>'
        f'<th style="text-align:right">ユーザー</th>'
        f'<th style="text-align:right">メッセージ</th>'
        f'<th style="text-align:right">Skill</th>'
        f'<th style="text-align:right">MCP</th>'
        f"</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>",
        unsafe_allow_html=True,
    )
