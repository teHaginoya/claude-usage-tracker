# =============================================================================
# tab_users.py - Tab2: ユーザー + ユーザー詳細パネル
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from helpers import apply_plotly, kpi_card, section, time_ago, rank_icon
from queries import get_user_stats, get_user_detail_timeline, get_user_top_tools
from demo_data import demo_users, demo_user_timeline, demo_user_top_tools


def render_users(team_id: str, days: int):
    section("ユーザー別利用状況")

    df = get_user_stats(team_id, days)
    if df.empty:
        df = demo_users()
    df.columns = [c.upper() for c in df.columns]

    # ── ランキングテーブル ────────────────────────────────────────
    rows_html = ""
    for i, row in df.iterrows():
        rank = i + 1
        uid  = str(row.get("USER_ID",       "—"))
        name = str(row.get("DISPLAY_NAME",  uid))
        ago  = time_ago(row.get("LAST_ACTIVE"))
        sk   = int(row.get("SKILL_COUNT",    0))
        sa   = int(row.get("SUBAGENT_COUNT", 0))
        mc   = int(row.get("MCP_COUNT",      0))
        ms   = int(row.get("MESSAGE_COUNT",  0))
        se   = int(row.get("SESSION_COUNT",  0))
        lh   = int(row.get("LIMIT_HITS",     0))
        tot  = int(row.get("TOTAL_COUNT",    0))

        tags = ""
        if sk > 0: tags += '<span class="tag-pill tag-skill">skill</span> '
        if sa > 0: tags += '<span class="tag-pill tag-subagent">agent</span> '
        if mc > 0: tags += '<span class="tag-pill tag-mcp">mcp</span> '

        limit_cell = (
            f'<span style="color:var(--negative);font-family:var(--mono-font)">{lh}</span>'
            if lh > 0
            else '<span style="color:var(--text-muted)">—</span>'
        )

        rows_html += f"""
        <tr>
            <td><span class="rank-icon">{rank_icon(rank)}</span></td>
            <td>
                <div class="user-name">{name}</div>
                <div class="user-time">{ago}&nbsp;&nbsp;{tags}</div>
            </td>
            <td class="num-cell">{ms:,}</td>
            <td class="num-cell">{se}</td>
            <td class="num-cell">{sk}</td>
            <td class="num-cell">{mc}</td>
            <td class="num-cell">{limit_cell}</td>
            <td class="num-cell highlight">{tot:,}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:var(--bg-card);border:1px solid var(--border);
                border-radius:10px;overflow:hidden">
    <table class="rank-table">
        <thead>
            <tr>
                <th style="width:3rem">#</th>
                <th>ユーザー</th>
                <th style="text-align:right">メッセージ</th>
                <th style="text-align:right">セッション</th>
                <th style="text-align:right">Skill</th>
                <th style="text-align:right">MCP</th>
                <th style="text-align:right">制限ヒット</th>
                <th style="text-align:right">合計 ↓</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    </div>""", unsafe_allow_html=True)

    # ── ユーザー詳細 ─────────────────────────────────────────────
    section("ユーザー詳細")
    user_options = ["(選択してください)"] + df["DISPLAY_NAME"].tolist()
    sel = st.selectbox("詳細を見るユーザーを選択", user_options,
                       label_visibility="collapsed")

    if sel and sel != "(選択してください)":
        matched = df[df["DISPLAY_NAME"] == sel]
        if not matched.empty:
            render_user_detail(team_id, str(matched.iloc[0]["USER_ID"]),
                               sel, days, matched.iloc[0])


# =============================================================================
# ユーザー詳細パネル
# =============================================================================

def render_user_detail(team_id: str, user_id: str, display_name: str, days: int, summary):
    st.markdown(
        f'<div class="detail-panel">'
        f'<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:var(--accent-amber);margin-bottom:0.75rem">'
        f"USER DETAIL — {display_name}</div></div>",
        unsafe_allow_html=True,
    )

    # 4 KPI
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("メッセージ数", int(summary.get("MESSAGE_COUNT", 0)),
                             0.0, "var(--accent-amber)"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("セッション数", int(summary.get("SESSION_COUNT", 0)),
                             0.0, "var(--accent-teal)"), unsafe_allow_html=True)
    with c3:
        lh    = int(summary.get("LIMIT_HITS", 0))
        extra = f'<div class="limit-badge">⚡ 制限ヒット</div>' if lh > 0 else ""
        st.markdown(kpi_card("制限ヒット", lh, 0.0, "var(--negative)",
                             extra_html=extra), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Skill実行", int(summary.get("SKILL_COUNT", 0)),
                             0.0, "var(--accent-violet)", badge="Skill"),
                    unsafe_allow_html=True)

    # 日次推移 + Top ツール
    tl = get_user_detail_timeline(team_id, user_id, days)
    if tl.empty:
        tl = demo_user_timeline(days)
    tl.columns = [c.upper() for c in tl.columns]

    top_tools = get_user_top_tools(team_id, user_id, days)
    if top_tools.empty:
        top_tools = demo_user_top_tools()
    top_tools.columns = [c.upper() for c in top_tools.columns]
    tc1 = top_tools.columns[0]  # ツール名列
    tc2 = top_tools.columns[1]  # 件数列

    dc, tc = st.columns([3, 2])

    with dc:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tl["EVENT_DATE"], y=tl["MESSAGES"],
            name="メッセージ", line=dict(color="#f59e0b", width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
        ))
        if "LIMIT_HITS" in tl.columns:
            fig.add_trace(go.Bar(
                x=tl["EVENT_DATE"], y=tl["LIMIT_HITS"],
                name="制限ヒット", marker_color="rgba(244,63,94,0.5)",
            ))
        fig.update_layout(title_text="日次利用推移",
                          legend=dict(orientation="h", y=1.1, x=0))
        fig = apply_plotly(fig, 240)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tc:
        fig2 = go.Figure(go.Bar(
            x=top_tools[tc2], y=top_tools[tc1],
            orientation="h", marker_color="#8b5cf6",
            text=top_tools[tc2], textposition="outside",
            textfont=dict(size=10, color="#8899b8"),
        ))
        fig2.update_layout(
            title_text="Top ツール使用",
            yaxis={"categoryorder": "total ascending"},
        )
        fig2 = apply_plotly(fig2, 240)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
