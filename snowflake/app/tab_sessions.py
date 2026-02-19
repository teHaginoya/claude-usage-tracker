# =============================================================================
# tab_sessions.py - Tab4: セッション分析
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from helpers import apply_plotly, kpi_card, section
from queries import get_session_kpi, get_stop_reason_data, get_limit_hit_by_hour
from demo_data import demo_session_kpi, demo_stop_reason, demo_limit_by_hour


def render_sessions(team_id: str, days: int):
    section("セッション分析")

    # ── KPI ──────────────────────────────────────────────────────
    kpi_df = get_session_kpi(team_id, days)
    if kpi_df.empty:
        kpi_df = demo_session_kpi()
    kpi_df.columns = [c.upper() for c in kpi_df.columns]
    kpi = kpi_df.iloc[0]

    def _si(key, d=0):
        """NaN / None を含む値を安全に int へ変換する"""
        try:
            return int(kpi.get(key, d))
        except (TypeError, ValueError):
            return d

    total_sess  = _si("TOTAL_SESSIONS",  0)
    _avg_raw    = kpi.get("AVG_DURATION_MIN", 0.0)
    avg_dur     = float(_avg_raw) if not pd.isna(_avg_raw) else 0.0
    lim_stopped = _si("LIMIT_STOPPED",   0)
    nrm_stopped = _si("NORMAL_STOPPED",  0)
    lim_pct     = round(lim_stopped / total_sess * 100, 1) if total_sess > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("総セッション数", total_sess, 0.0, "var(--accent-teal)"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(
            kpi_card("平均セッション長", avg_dur, 0.0, "var(--accent-blue)",
                     value_fmt=(f"{avg_dur:.1f}"
                                f"<span style='font-size:0.9rem;color:var(--text-muted)'> 分</span>")),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(kpi_card("正常終了", nrm_stopped, 0.0, "var(--accent-green)"),
                    unsafe_allow_html=True)
    with c4:
        extra = (f'<div class="limit-badge">利用制限率 {lim_pct}%</div>'
                 if lim_stopped > 0 else "")
        st.markdown(kpi_card("制限終了", lim_stopped, 0.0, "var(--negative)",
                             extra_html=extra), unsafe_allow_html=True)

    # ── チャート ──────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        stop_df = get_stop_reason_data(team_id, days)
        if stop_df.empty:
            stop_df = demo_stop_reason()
        stop_df.columns = [c.upper() for c in stop_df.columns]

        label_map = {"normal": "正常終了", "usage_limit": "利用制限", "unknown": "不明"}
        color_map = {"正常終了": "#16a34a", "利用制限": "#e11d48", "不明": "#94a3b8"}
        labels = [label_map.get(str(x), str(x)) for x in stop_df["STOP_REASON"]]
        colors = [color_map.get(l, "#8b5cf6") for l in labels]

        fig = go.Figure(go.Pie(
            labels=labels, values=stop_df["SESSION_COUNT"],
            hole=0.62,
            marker=dict(colors=colors, line=dict(color="#ffffff", width=3)),
            textinfo="label+percent",
            textfont=dict(size=11, color="#0f172a"),
        ))
        fig.update_layout(
            title_text="停止理由の内訳",
            annotations=[dict(
                text=f"{total_sess}<br><span style='font-size:10px'>Sessions</span>",
                x=0.5, y=0.5, font_size=15, showarrow=False,
                font=dict(color="#0f172a"),
            )],
            showlegend=True,
            legend=dict(orientation="h", y=-0.1, x=0.1),
        )
        fig = apply_plotly(fig, 300)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        lim_hr = get_limit_hit_by_hour(team_id, days)
        if lim_hr.empty:
            lim_hr = demo_limit_by_hour()
        lim_hr.columns = [c.upper() for c in lim_hr.columns]

        # 0-23 全時間を保証
        all_hours = pd.DataFrame({"HOUR_OF_DAY": list(range(24))})
        lim_hr = all_hours.merge(lim_hr, on="HOUR_OF_DAY", how="left").fillna(0)

        # ヒットあり/なしで色分け
        bar_colors = [
            "#e11d48" if v > 0 else "#e2e8f0"
            for v in lim_hr["LIMIT_HITS"]
        ]
        fig2 = go.Figure(go.Bar(
            x=lim_hr["HOUR_OF_DAY"],
            y=lim_hr["LIMIT_HITS"],
            marker=dict(color=bar_colors, line=dict(width=0)),
            hovertemplate="%{x}時: %{y}件<extra></extra>",
        ))
        fig2.update_layout(
            title_text="制限ヒット 時間帯別",
            xaxis=dict(
                tickmode="array",
                tickvals=list(range(0, 24, 3)),
                ticktext=[f"{h:02d}h" for h in range(0, 24, 3)],
                title="",
            ),
            yaxis=dict(title="", dtick=1),
            bargap=0.2,
        )
        fig2 = apply_plotly(fig2, 300)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
