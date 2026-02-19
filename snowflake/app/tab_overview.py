# =============================================================================
# tab_overview.py - Tab1: 概要
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from helpers import apply_plotly, calc_change, kpi_card, section
from queries import get_kpi_overview, get_timeline_data, get_heatmap_data
from demo_data import demo_kpi_overview, demo_timeline, demo_heatmap


def render_overview(team_id: str, days: int):
    # ── KPI データ取得 ────────────────────────────────────────────
    kpi_raw = get_kpi_overview(team_id, days)
    if kpi_raw.empty:
        kpi = demo_kpi_overview()
    else:
        r = kpi_raw.iloc[0]
        kpi = {k.upper(): (int(v) if str(v) not in ("nan", "None") else 0)
               for k, v in r.items()}

    active = int(kpi.get("ACTIVE_USERS", 0))
    total  = int(kpi.get("TOTAL_USERS",  1)) or 1
    pct    = round(active / total * 100)
    limit_hits = int(kpi.get("LIMIT_HITS", 0))

    # ── KPI カード ────────────────────────────────────────────────
    section("Overview")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        ch = calc_change(kpi.get("MSG_COUNT", 0), kpi.get("PREV_MSG", 0))
        st.markdown(kpi_card("メッセージ数", kpi.get("MSG_COUNT", 0), ch,
                             "var(--accent-amber)"), unsafe_allow_html=True)

    with c2:
        ch = calc_change(kpi.get("SESS_COUNT", 0), kpi.get("PREV_SESS", 0))
        st.markdown(kpi_card("セッション数", kpi.get("SESS_COUNT", 0), ch,
                             "var(--accent-teal)"), unsafe_allow_html=True)

    with c3:
        extra = (
            f'<div class="progress-track">'
            f'<div class="progress-fill" style="width:{pct}%"></div></div>'
            f'<div class="progress-label"><span>普及率</span><span>{pct}%</span></div>'
        )
        ch = calc_change(active, kpi.get("PREV_USERS", 0))
        st.markdown(
            kpi_card("アクティブユーザー", active, ch, "var(--accent-blue)",
                     value_fmt=(f"{active} <span style='font-size:1rem;"
                                f"font-weight:400;color:var(--text-muted)'>/ {total}</span>"),
                     extra_html=extra),
            unsafe_allow_html=True,
        )

    with c4:
        ch = calc_change(kpi.get("SKILL_COUNT", 0), kpi.get("PREV_SKILL", 0))
        st.markdown(kpi_card("Skill実行", kpi.get("SKILL_COUNT", 0), ch,
                             "var(--accent-violet)", badge="Skill"), unsafe_allow_html=True)

    with c5:
        ch = calc_change(kpi.get("MCP_COUNT", 0), kpi.get("PREV_MCP", 0))
        st.markdown(kpi_card("MCP呼び出し", kpi.get("MCP_COUNT", 0), ch,
                             "var(--accent-green)", badge="MCP"), unsafe_allow_html=True)

    with c6:
        extra_l = (
            f'<div class="limit-badge">⚡ 利用制限ヒット</div>'
            if limit_hits > 0 else ""
        )
        st.markdown(kpi_card("利用制限ヒット", limit_hits, 0.0, "var(--negative)",
                             extra_html=extra_l), unsafe_allow_html=True)

    # ── 日次推移 + ヒートマップ ───────────────────────────────────
    section("利用推移 / 時間帯ヒートマップ")
    cl, cr = st.columns([3, 2])

    with cl:
        tl = get_timeline_data(team_id, days)
        if tl.empty:
            tl = demo_timeline(days)
        tl.columns = [c.upper() for c in tl.columns]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tl["EVENT_DATE"], y=tl["MESSAGES"],
            name="メッセージ", line=dict(color="#f59e0b", width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.15)",
        ))
        fig.add_trace(go.Scatter(
            x=tl["EVENT_DATE"], y=tl["SESSIONS"],
            name="セッション", line=dict(color="#0d9488", width=1.5, dash="dot"),
        ))
        if "LIMIT_HITS" in tl.columns and tl["LIMIT_HITS"].sum() > 0:
            max_lim = max(int(tl["LIMIT_HITS"].max()), 1)
            fig.add_trace(go.Bar(
                x=tl["EVENT_DATE"], y=tl["LIMIT_HITS"],
                name="制限ヒット", marker_color="rgba(225,29,72,0.3)",
                yaxis="y2",
            ))
            fig.update_layout(
                yaxis2=dict(
                    overlaying="y", side="right", showgrid=False,
                    range=[0, max_lim * 8],
                    showticklabels=False,
                ),
            )
        fig.update_layout(title_text="日次利用推移", legend=dict(orientation="h", y=1.12, x=0))
        fig = apply_plotly(fig, 280)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with cr:
        hm = get_heatmap_data(team_id, days)
        if hm.empty:
            hm = demo_heatmap()
        hm.columns = [c.upper() for c in hm.columns]

        dow_labels = ["日", "月", "火", "水", "木", "金", "土"]
        pivot = hm.pivot_table(
            index="DOW", columns="HOUR_OF_DAY",
            values="EVENT_COUNT", aggfunc="sum", fill_value=0,
        )
        pivot.index = [dow_labels[i] if i < 7 else str(i) for i in pivot.index]

        fig2 = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"{h:02d}h" for h in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[[0, "#e8edf5"], [0.3, "#bae6fd"], [0.65, "#0d9488"], [1, "#f59e0b"]],
            showscale=False,
            hoverongaps=False,
            hovertemplate="曜日: %{y}<br>時刻: %{x}<br>件数: %{z}<extra></extra>",
        ))
        fig2.update_layout(
            title_text="時間帯 × 曜日ヒートマップ",
            xaxis=dict(side="bottom"),
        )
        fig2.update_xaxes(
            tickvals=[f"{h:02d}h" for h in range(0, 24, 4)],
            ticktext=[f"{h:02d}h" for h in range(0, 24, 4)],
        )
        fig2 = apply_plotly(fig2, 280)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── AI Insights ───────────────────────────────────────────────
    section("AI Insights", "自動生成インサイト")

    msg_ch   = calc_change(kpi.get("MSG_COUNT",   0), kpi.get("PREV_MSG",   0))
    mcp_ch   = calc_change(kpi.get("MCP_COUNT",   0), kpi.get("PREV_MCP",   0))

    def _insight(cls, tag, title, desc):
        return (
            f'<div class="insight-card {cls}">'
            f'<div class="insight-tag">{tag}</div>'
            f'<div class="insight-title">{title}</div>'
            f'<div class="insight-desc">{desc}</div>'
            f"</div>"
        )

    i1 = _insight(
        "trend-up" if msg_ch >= 0 else "trend-down",
        "TREND UP"  if msg_ch >= 0 else "TREND DOWN",
        f"メッセージ数 {msg_ch:+.0f}%",
        f"前期比 {msg_ch:+.1f}% の変化が見られます。継続的に推移を観察しましょう。",
    )
    i2 = _insight(
        "trend-up" if mcp_ch > 5 else "usecase",
        "MCP ADOPTION" if mcp_ch > 5 else "USECASE",
        f"MCP活用が{mcp_ch:+.0f}%" if mcp_ch > 5 else "コード生成が主要用途",
        "MCP活用が急速に拡大しています。" if mcp_ch > 5
        else "Write / Edit ツールが多用され、コード生成が中心です。",
    )
    i3 = _insight(
        "power-user", "POWER USER", "上位ユーザーが利用を牽引",
        "少数のパワーユーザーがチーム全体の利用をリードしています。スキル共有が効果的です。",
    )
    i4 = _insight(
        "trend-down" if limit_hits > 10 else "neutral",
        "USAGE LIMIT",
        f"制限ヒット {limit_hits} 件",
        "利用計画の見直しや計画的な利用を促進しましょう。" if limit_hits > 0
        else "制限ヒットはありません。良好な利用状況です。",
    )
    i5 = _insight(
        "neutral", "ADOPTION", f"普及率 {pct}%",
        f"チームの {pct}% がアクティブです。"
        + ("未利用メンバーへの展開機会があります。" if pct < 80
           else "高い普及率を維持しています。"),
    )
    st.markdown(
        f'<div class="insight-row">{i1}{i2}{i3}{i4}{i5}</div>',
        unsafe_allow_html=True,
    )
