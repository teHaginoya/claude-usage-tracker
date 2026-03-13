# =============================================================================
# tab_roi.py - Tab7: 導入効果
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from helpers import apply_plotly, calc_change, kpi_card, section
from queries import (
    get_roi_kpi, get_productivity_trend,
    get_user_efficiency, get_weekly_feature_mix,
)

# === ROI 試算の前提パラメータ ===
MINUTES_SAVED_PER_TOOL_EXEC = 2    # ツール実行1回あたりの推定節約分数
WORK_HOURS_PER_MONTH = 160         # 1人月 = 160時間


def _safe(val, default=0):
    try:
        v = float(val)
        return default if str(v) == "nan" else v
    except (TypeError, ValueError):
        return default


def _depth_score(skill_u, mcp_u, sa_u, cmd_u, total_u):
    """AI活用深度スコア (0-100)"""
    if total_u == 0:
        return 0.0
    return round(
        (skill_u / total_u * 0.3
         + mcp_u / total_u * 0.3
         + sa_u / total_u * 0.2
         + cmd_u / total_u * 0.2) * 100, 1
    )


_EMPTY = (
    '<div style="display:flex;align-items:center;justify-content:center;'
    'min-height:{h}px;background:var(--bg-card);border:1px solid var(--border);'
    'border-radius:var(--radius-lg);color:var(--accent-blue);'
    'font-size:0.875rem;box-shadow:var(--shadow-sm);">'
    '{msg}</div>'
)


def render_roi(team_id: str, days: int):
    # ── KPI データ ─────────────────────────────────────────────────
    kpi_raw = get_roi_kpi(team_id, days)
    if kpi_raw.empty:
        st.markdown(_EMPTY.format(h=400, msg="導入効果データがありません"),
                    unsafe_allow_html=True)
        return

    r = kpi_raw.iloc[0]
    k = {c.upper(): _safe(v) for c, v in r.items()}

    tool_execs    = k.get("TOOL_EXECS", 0)
    active_users  = max(k.get("ACTIVE_USERS", 1), 1)
    total_users   = max(k.get("TOTAL_USERS", 1), 1)
    total_events  = k.get("TOTAL_EVENTS", 0)
    tool_success  = k.get("TOOL_SUCCESS", 0)
    tool_total    = max(k.get("TOOL_TOTAL", 1), 1)
    feat_total    = max(k.get("FEAT_TOTAL", 1), 1)

    hours_saved     = round(tool_execs * MINUTES_SAVED_PER_TOOL_EXEC / 60, 1)
    events_per_user = round(total_events / active_users, 1)
    success_rate    = round(tool_success / tool_total * 100, 1)
    depth           = _depth_score(
        k.get("SKILL_USERS", 0), k.get("MCP_USERS", 0),
        k.get("SA_USERS", 0),    k.get("CMD_USERS", 0),
        feat_total,
    )

    # 前期間
    prev_tool_execs  = k.get("PREV_TOOL_EXECS", 0)
    prev_hours       = round(prev_tool_execs * MINUTES_SAVED_PER_TOOL_EXEC / 60, 1)
    prev_active      = max(k.get("PREV_ACTIVE_USERS", 1), 1)
    prev_events_user = round(k.get("PREV_TOTAL_EVENTS", 0) / prev_active, 1)
    prev_tool_total  = max(k.get("PREV_TOOL_TOTAL", 1), 1)
    prev_success     = round(k.get("PREV_TOOL_SUCCESS", 0) / prev_tool_total * 100, 1)
    prev_depth       = _depth_score(
        k.get("PREV_SKILL_USERS", 0), k.get("PREV_MCP_USERS", 0),
        k.get("PREV_SA_USERS", 0),    k.get("PREV_CMD_USERS", 0),
        max(k.get("PREV_FEAT_TOTAL", 1), 1),
    )

    # ── KPI カード ─────────────────────────────────────────────────
    section("導入効果サマリー",
            f"ツール実行1回 = {MINUTES_SAVED_PER_TOOL_EXEC}分の時間節約として試算")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(kpi_card(
            "推定時間削減", hours_saved,
            calc_change(hours_saved, prev_hours), "var(--accent-amber)",
            value_fmt=(f"{hours_saved:,.1f}"
                       "<span style='font-size:0.9rem;color:var(--text-muted)'> h</span>"),
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(kpi_card(
            "ユーザー当たり操作数", events_per_user,
            calc_change(events_per_user, prev_events_user), "var(--accent-teal)",
        ), unsafe_allow_html=True)

    with c3:
        st.markdown(kpi_card(
            "ツール成功率", success_rate,
            calc_change(success_rate, prev_success), "var(--accent-green)",
            value_fmt=(f"{success_rate:.1f}"
                       "<span style='font-size:0.9rem;color:var(--text-muted)'>%</span>"),
        ), unsafe_allow_html=True)

    with c4:
        st.markdown(kpi_card(
            "AI活用深度", depth,
            calc_change(depth, prev_depth), "var(--accent-violet)",
            value_fmt=(f"{depth:.0f}"
                       "<span style='font-size:0.9rem;color:var(--text-muted)'> / 100</span>"),
        ), unsafe_allow_html=True)

    # ── チャート行1: 生産性トレンド / ユーザー効率 ──────────────────
    st.markdown('<div style="margin-top:1.25rem"></div>', unsafe_allow_html=True)
    section("生産性トレンド / ユーザー効率比較")
    cl, cr = st.columns([3, 2])

    with cl:
        prod_df = get_productivity_trend(team_id, days)
        if prod_df.empty:
            st.markdown(_EMPTY.format(h=340, msg="生産性トレンドデータがありません"),
                        unsafe_allow_html=True)
        else:
            prod_df.columns = [c.upper() for c in prod_df.columns]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=prod_df["EVENT_DATE"], y=prod_df["TOOL_EXECS"],
                name="ツール実行数",
                line=dict(color="#f59e0b", width=2),
                fill="tozeroy", fillcolor="rgba(245,158,11,0.12)",
            ))
            fig.add_trace(go.Scatter(
                x=prod_df["EVENT_DATE"], y=prod_df["TOOLS_PER_USER"],
                name="ユーザー当たり",
                line=dict(color="#0d9488", width=2, dash="dot"),
                yaxis="y2",
                marker=dict(size=4),
            ))
            max_tpu = max(float(prod_df["TOOLS_PER_USER"].max()), 1)
            fig.update_layout(
                title_text="生産性トレンド: ツール実行数 / ユーザー当たり効率",
                yaxis2=dict(
                    overlaying="y", side="right", showgrid=False,
                    range=[0, max_tpu * 1.5],
                    title="per user",
                    tickfont=dict(size=9, color="#0d9488"),
                ),
                legend=dict(orientation="h", x=0.95, y=1.12,
                            xanchor="right", yanchor="top",
                            bgcolor="rgba(255,255,255,0.85)"),
            )
            fig = apply_plotly(fig, 340)
            fig.update_layout(margin=dict(t=40, r=50))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

    with cr:
        eff_df = get_user_efficiency(team_id, days)
        if eff_df.empty:
            st.markdown(_EMPTY.format(h=340, msg="ユーザー効率データがありません"),
                        unsafe_allow_html=True)
        else:
            eff_df.columns = [c.upper() for c in eff_df.columns]
            max_sess = max(int(eff_df["SESSIONS"].max()), 1)
            sizes = (eff_df["SESSIONS"] / max_sess * 30 + 8).tolist()

            # Y軸の範囲: データが少ない時に狭くなりすぎないよう下限を確保
            y_min = float(eff_df["TOTAL_EVENTS"].min())
            y_max = float(eff_df["TOTAL_EVENTS"].max())
            y_span = max(y_max - y_min, y_max * 0.3, 10)
            y_lo = max(y_min - y_span * 0.3, 0)
            y_hi = y_max + y_span * 0.3

            x_min = float(eff_df["MESSAGES"].min())
            x_max = float(eff_df["MESSAGES"].max())
            x_span = max(x_max - x_min, x_max * 0.3, 5)
            x_lo = max(x_min - x_span * 0.3, 0)
            x_hi = x_max + x_span * 0.3

            fig2 = go.Figure(go.Scatter(
                x=eff_df["MESSAGES"], y=eff_df["TOTAL_EVENTS"],
                mode="markers+text",
                text=eff_df["DISPLAY_NAME"],
                textposition="top center",
                textfont=dict(size=9, color="#64748b"),
                marker=dict(
                    size=sizes,
                    color=eff_df["ADVANCED_FEATURES"],
                    colorscale=[[0, "#e0f2fe"], [0.5, "#0d9488"], [1, "#f59e0b"]],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="高度<br>機能", font=dict(size=7)),
                        thickness=6, len=0.45,
                        tickfont=dict(size=7),
                        xpad=2, x=1.01,
                    ),
                    line=dict(width=1, color="white"),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "メッセージ: %{x}<br>"
                    "総操作: %{y}<br>"
                    "<extra></extra>"
                ),
            ))
            fig2.update_layout(
                title_text="ユーザー効率マップ",
                xaxis=dict(title=dict(text="メッセージ数", font=dict(size=10)),
                           tickfont=dict(size=8), range=[x_lo, x_hi]),
                yaxis=dict(title=dict(text="総操作数", font=dict(size=10)),
                           tickfont=dict(size=8), range=[y_lo, y_hi]),
            )
            fig2 = apply_plotly(fig2, 340)
            fig2.update_layout(margin=dict(t=32, b=44, l=44, r=52))
            st.plotly_chart(fig2, use_container_width=True,
                            config={"displayModeBar": False})

    # ── チャート行2: 機能活用ミックス ──────────────────────────────
    st.markdown('<div style="margin-top:2.5rem"></div>', unsafe_allow_html=True)
    section("機能活用の成熟度")

    mix_df = get_weekly_feature_mix(team_id, days)
    if mix_df.empty:
        st.markdown(_EMPTY.format(h=300, msg="機能活用データがありません"),
                    unsafe_allow_html=True)
    else:
        mix_df.columns = [c.upper() for c in mix_df.columns]
        fig3 = go.Figure()
        traces = [
            ("BASIC_TOOLS", "基本ツール", "#3b82f6", "rgba(59,130,246,0.15)"),
            ("MESSAGES",    "メッセージ", "#f59e0b", "rgba(245,158,11,0.15)"),
            ("SKILLS",      "Skill",     "#0d9488", "rgba(13,148,136,0.15)"),
            ("MCP",         "MCP",       "#8b5cf6", "rgba(139,92,246,0.15)"),
        ]
        for col, name, color, fill in traces:
            if col in mix_df.columns:
                fig3.add_trace(go.Scatter(
                    x=mix_df["WEEK_START"], y=mix_df[col],
                    name=name, stackgroup="one", groupnorm="percent",
                    line=dict(width=0.5, color=color),
                    fillcolor=fill,
                ))
        fig3.update_layout(
            title_text="機能活用ミックス推移 (週次・構成比%)",
            yaxis=dict(title="構成比 (%)", range=[0, 100]),
            legend=dict(orientation="h", y=-0.18, x=0, xanchor="left"),
        )
        fig3 = apply_plotly(fig3, 300)
        fig3.update_layout(margin=dict(b=80, r=20))
        st.plotly_chart(fig3, use_container_width=True,
                        config={"displayModeBar": False})

    # ── ROI 試算 Insight カード ────────────────────────────────────
    st.markdown('<div style="margin-top:1.25rem"></div>', unsafe_allow_html=True)
    section("ROI 試算", "保守的試算 — 実際の効果はさらに大きい可能性があります")

    annual_hours  = hours_saved * (365 / max(days, 1))
    fte           = annual_hours / WORK_HOURS_PER_MONTH
    per_user_hrs  = hours_saved / active_users
    scaled_annual = annual_hours * (total_users / active_users)
    scaled_fte    = scaled_annual / WORK_HOURS_PER_MONTH
    pct           = round(active_users / total_users * 100)

    def _insight(cls, tag, title, desc):
        return (
            f'<div class="insight-card {cls}">'
            f'<div class="insight-tag">{tag}</div>'
            f'<div class="insight-title">{title}</div>'
            f'<div class="insight-desc">{desc}</div>'
            f"</div>"
        )

    i1 = _insight(
        "trend-up", "TIME SAVINGS",
        f"期間内 約 {hours_saved:,.0f} 時間の削減効果",
        f"ツール実行 {int(tool_execs):,} 回 x {MINUTES_SAVED_PER_TOOL_EXEC}分 = {hours_saved:,.0f} 時間。"
        f"開発者 {int(active_users)} 名で一人当たり {per_user_hrs:,.1f} 時間の生産性向上。",
    )
    i2 = _insight(
        "power-user", "ANNUAL PROJECTION",
        f"年間換算 約 {annual_hours:,.0f} 時間 ({fte:,.1f} 人月相当)",
        f"現在ペースを年間換算すると {annual_hours:,.0f} 時間。"
        f"エンジニア 1人月 = {WORK_HOURS_PER_MONTH}h として"
        f" {fte:,.1f} 人月の効率化に相当します。",
    )
    i3 = _insight(
        "usecase", "SCALING POTENTIAL",
        f"全社展開で年間 {scaled_fte:,.1f} 人月相当の効率化",
        f"現在の普及率 {pct}% ({int(active_users)}/{int(total_users)}名)。"
        f"全ユーザー展開で年間 {scaled_annual:,.0f} 時間"
        f" ({scaled_fte:,.1f} 人月) の効果が期待されます。",
    )
    st.markdown(
        f'<div class="insight-row">{i1}{i2}{i3}</div>',
        unsafe_allow_html=True,
    )
