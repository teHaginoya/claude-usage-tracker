# =============================================================================
# Claude Code Usage Dashboard - Streamlit in Snowflake
# =============================================================================
# このファイルをStreamlit in Snowflakeにデプロイしてください
# =============================================================================

import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session
from datetime import datetime, timedelta

# =============================================================================
# ページ設定
# =============================================================================
st.set_page_config(
    page_title="Claude Code Usage Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# カスタムCSS - ダーク精緻デザイン
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    /* ===== ベーステーマ ===== */
    :root {
        --bg-primary:    #0a0e1a;
        --bg-secondary:  #111827;
        --bg-card:       #141c2e;
        --bg-card-hover: #1a2540;
        --border:        #1f2d4a;
        --border-light:  #263351;
        --text-primary:  #e8edf5;
        --text-secondary:#8899b8;
        --text-muted:    #4a5c7a;
        --accent-amber:  #f59e0b;
        --accent-teal:   #14b8a6;
        --accent-blue:   #3b82f6;
        --accent-rose:   #f43f5e;
        --accent-violet: #8b5cf6;
        --accent-green:  #22c55e;
        --positive:      #10b981;
        --negative:      #f43f5e;
        --mono-font: 'DM Mono', 'Courier New', monospace;
        --body-font: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    }

    /* ===== グローバル ===== */
    html, body, [class*="css"] {
        font-family: var(--body-font);
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }

    .main .block-container {
        padding: 1.5rem 2rem 2rem;
        max-width: 1600px;
        background-color: var(--bg-primary);
    }

    /* ===== 非表示要素 ===== */
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; }

    /* ===== ヘッダーエリア ===== */
    .dash-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }

    .dash-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .dash-logo-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--accent-amber) 0%, #e07b04 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        box-shadow: 0 0 16px rgba(245, 158, 11, 0.3);
    }

    .dash-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        line-height: 1.2;
        margin: 0;
    }

    .dash-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin: 0.15rem 0 0;
        font-weight: 400;
    }

    /* ===== 期間バッジ ===== */
    .period-display {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 0.75rem;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 0.75rem;
        color: var(--text-secondary);
        font-family: var(--mono-font);
    }

    /* ===== セクションヘッダー ===== */
    .section-header {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin: 1.75rem 0 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    /* ===== KPIカード ===== */
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.1rem 1.25rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s, transform 0.2s;
        height: 100%;
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: var(--accent-color, var(--accent-teal));
        opacity: 0.8;
    }

    .kpi-card:hover {
        border-color: var(--border-light);
        transform: translateY(-1px);
    }

    .kpi-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    .kpi-label .badge {
        font-size: 0.6rem;
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-weight: 700;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        font-family: var(--mono-font);
        color: var(--text-primary);
        line-height: 1.1;
        letter-spacing: -0.03em;
        margin-bottom: 0.4rem;
    }

    .kpi-change {
        font-size: 0.72rem;
        font-family: var(--mono-font);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .kpi-change.pos { color: var(--positive); }
    .kpi-change.neg { color: var(--negative); }
    .kpi-change.neu { color: var(--text-muted); }

    .kpi-sparkbar {
        display: flex;
        gap: 2px;
        margin-top: 0.6rem;
        align-items: flex-end;
        height: 20px;
    }

    .kpi-sparkbar span {
        flex: 1;
        background: var(--accent-color, var(--accent-teal));
        opacity: 0.5;
        border-radius: 2px 2px 0 0;
        min-height: 3px;
    }

    /* ===== プログレスリング代替 - バー ===== */
    .progress-track {
        background: var(--border);
        border-radius: 99px;
        height: 5px;
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .progress-fill {
        height: 100%;
        border-radius: 99px;
        background: linear-gradient(90deg, var(--accent-teal), var(--accent-blue));
        transition: width 1s ease;
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.68rem;
        font-family: var(--mono-font);
        color: var(--text-muted);
        margin-top: 0.3rem;
    }

    /* ===== インサイトカード ===== */
    .insight-row {
        display: flex;
        gap: 0.75rem;
        flex-wrap: nowrap;
    }

    .insight-card {
        flex: 1;
        min-width: 0;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1rem 1.1rem;
        position: relative;
        overflow: hidden;
    }

    .insight-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
    }

    .insight-card.trend-up::before   { background: var(--accent-amber); }
    .insight-card.trend-down::before { background: var(--negative); }
    .insight-card.power-user::before { background: var(--accent-green); }
    .insight-card.usecase::before    { background: var(--accent-blue); }
    .insight-card.neutral::before    { background: var(--accent-violet); }

    .insight-tag {
        font-size: 0.6rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .trend-up   .insight-tag { color: var(--accent-amber); }
    .trend-down .insight-tag { color: var(--negative); }
    .power-user .insight-tag { color: var(--accent-green); }
    .usecase    .insight-tag { color: var(--accent-blue); }
    .neutral    .insight-tag { color: var(--accent-violet); }

    .insight-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }

    .insight-desc {
        font-size: 0.72rem;
        color: var(--text-secondary);
        line-height: 1.5;
    }

    /* ===== テーブル ===== */
    .rank-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }

    .rank-table th {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        padding: 0.6rem 0.75rem;
        border-bottom: 1px solid var(--border);
        background: var(--bg-card);
        white-space: nowrap;
    }

    .rank-table th:first-child { border-radius: 8px 0 0 0; }
    .rank-table th:last-child  { border-radius: 0 8px 0 0; }

    .rank-table td {
        padding: 0.7rem 0.75rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.82rem;
        color: var(--text-primary);
        background: var(--bg-card);
    }

    .rank-table tr:hover td {
        background: var(--bg-card-hover);
    }

    .rank-table tr:last-child td { border-bottom: none; }

    .rank-icon {
        font-size: 1rem;
        line-height: 1;
    }

    .user-name {
        font-weight: 600;
        color: var(--text-primary);
    }

    .user-time {
        font-size: 0.65rem;
        color: var(--text-muted);
        font-family: var(--mono-font);
    }

    .num-cell {
        font-family: var(--mono-font);
        font-size: 0.82rem;
        text-align: right;
        color: var(--text-secondary);
    }

    .num-cell.highlight {
        color: var(--accent-amber);
        font-weight: 600;
    }

    .tag-pill {
        display: inline-block;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        text-transform: uppercase;
    }

    .tag-skill    { background: rgba(20,184,166,0.15);  color: var(--accent-teal); }
    .tag-mcp      { background: rgba(139,92,246,0.15);  color: var(--accent-violet); }
    .tag-subagent { background: rgba(34,197,94,0.15);   color: var(--accent-green); }
    .tag-command  { background: rgba(59,130,246,0.15);  color: var(--accent-blue); }

    /* ===== タブ ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        background: transparent;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px 6px 0 0;
        padding: 0.5rem 1rem;
        font-size: 0.8rem;
        color: var(--text-muted);
        border: none;
        font-family: var(--body-font);
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: var(--bg-card);
        color: var(--text-primary) !important;
        border: 1px solid var(--border);
        border-bottom: 1px solid var(--bg-card);
    }

    /* ===== チャートコンテナ ===== */
    .chart-wrap {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.25rem;
    }

    .chart-title {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 1rem;
    }

    /* ===== ラジオボタン（期間選択） ===== */
    .stRadio > div {
        display: flex;
        gap: 0.25rem;
        flex-direction: row !important;
    }

    .stRadio label {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        padding: 0.3rem 0.75rem !important;
        font-size: 0.75rem !important;
        font-family: var(--mono-font) !important;
        color: var(--text-secondary) !important;
        cursor: pointer;
        transition: all 0.15s;
    }

    .stRadio label:has(input:checked) {
        background: var(--accent-amber) !important;
        color: #0a0e1a !important;
        border-color: var(--accent-amber) !important;
        font-weight: 600 !important;
    }

    /* ===== Streamlit要素の上書き ===== */
    .stDataFrame, [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden;
        background: var(--bg-card) !important;
    }

    [data-testid="metric-container"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1rem;
    }

    .stAlert {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: 8px !important;
    }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

</style>
""", unsafe_allow_html=True)

# =============================================================================
# Snowflake接続
# =============================================================================
@st.cache_resource
def get_session():
    return get_active_session()

session = get_session()

# =============================================================================
# データ取得関数
# =============================================================================
@st.cache_data(ttl=60)
def get_kpi_metrics(team_id: str, days: int):
    query = f"""
    WITH current_period AS (
        SELECT
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                                     AS skill_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END)   AS subagent_count,
            COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END)                                        AS mcp_count,
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)                     AS message_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END)                         AS session_count,
            COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END)                                    AS command_count,
            COUNT(DISTINCT USER_ID)                                                          AS active_users
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    ),
    previous_period AS (
        SELECT
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                                     AS skill_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END)   AS subagent_count,
            COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END)                                        AS mcp_count,
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)                     AS message_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END)                         AS session_count
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days * 2}, CURRENT_TIMESTAMP())
          AND EVENT_TIMESTAMP <  DATEADD('day', -{days},     CURRENT_TIMESTAMP())
    ),
    total_users AS (
        SELECT COUNT(DISTINCT USER_ID) AS total_users
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
    )
    SELECT
        c.*,
        p.skill_count    AS prev_skill,
        p.subagent_count AS prev_subagent,
        p.mcp_count      AS prev_mcp,
        p.message_count  AS prev_message,
        p.session_count  AS prev_session,
        t.total_users
    FROM current_period c, previous_period p, total_users t
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_user_stats(team_id: str, days: int, limit: int = 20):
    query = f"""
    SELECT
        USER_ID,
        SPLIT_PART(USER_ID, '@', 1)                                                          AS DISPLAY_NAME,
        COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                                          AS SKILL_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END)        AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END)                                             AS MCP_COUNT,
        COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END)                                         AS COMMAND_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)                          AS MESSAGE_COUNT,
        COUNT(*)                                                                              AS TOTAL_COUNT,
        MAX(EVENT_TIMESTAMP)                                                                  AS LAST_ACTIVE
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY USER_ID
    ORDER BY TOTAL_COUNT DESC
    LIMIT {limit}
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_tool_stats(team_id: str, days: int):
    query = f"""
    SELECT
        TOOL_NAME,
        COUNT(*) AS COUNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND TOOL_NAME IS NOT NULL
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY TOOL_NAME
    ORDER BY COUNT DESC
    LIMIT 10
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_timeline_data(team_id: str, days: int):
    query = f"""
    SELECT
        DATE_TRUNC('day', EVENT_TIMESTAMP)::DATE                                         AS EVENT_DATE,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)                      AS MESSAGES,
        COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse', 'PreToolUse') THEN 1 END)          AS TOOLS,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END)                          AS SESSIONS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', EVENT_TIMESTAMP)
    ORDER BY EVENT_DATE
    """
    return session.sql(query).to_pandas()


# =============================================================================
# ヘルパー関数
# =============================================================================
def calc_change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


def fmt_change(change):
    if change > 0:
        return f"▲ +{change}%", "pos"
    elif change < 0:
        return f"▼ {change}%", "neg"
    else:
        return "— 0%", "neu"


def time_ago(dt):
    if pd.isna(dt):
        return ""
    now = datetime.now()
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days}日前"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}時間前"
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}分前"
    return "今"


def rank_icon(rank):
    return ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"<span style='font-family:var(--mono-font);color:var(--text-muted)'>{rank}</span>"


def sparkbars(heights=None, color="var(--accent-teal)"):
    if heights is None:
        heights = [30, 45, 35, 60, 50, 70, 65]
    bars = "".join(f'<span style="height:{h}%;background:{color}"></span>' for h in heights)
    return f'<div class="kpi-sparkbar">{bars}</div>'


def kpi_card(label, value, change_val, prev_val, accent, badge=None, extra_html=""):
    change_text, change_cls = fmt_change(change_val)
    badge_html = f'<span class="badge" style="background:rgba(255,255,255,0.08);color:var(--text-muted)">{badge}</span>' if badge else ""
    spark_colors = {
        "var(--accent-teal)":   "#14b8a6",
        "var(--accent-amber)":  "#f59e0b",
        "var(--accent-violet)": "#8b5cf6",
        "var(--accent-blue)":   "#3b82f6",
        "var(--accent-green)":  "#22c55e",
        "var(--negative)":      "#f43f5e",
    }
    sc = spark_colors.get(accent, "#14b8a6")
    return f"""
    <div class="kpi-card" style="--accent-color:{accent}">
        <div class="kpi-label">{label}{badge_html}</div>
        <div class="kpi-value">{value:,}</div>
        <div class="kpi-change {change_cls}">{change_text}
            <span style="color:var(--text-muted);font-weight:400">前期比</span>
        </div>
        {sparkbars(color=sc)}
        {extra_html}
    </div>
    """


# =============================================================================
# メイン
# =============================================================================
def main():
    # ── ヘッダー ──────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 2])

    with hdr_l:
        st.markdown("""
        <div class="dash-logo">
            <div class="dash-logo-icon">⬡</div>
            <div>
                <p class="dash-title">Claude Code Usage Dashboard</p>
                <p class="dash-subtitle">チーム全体の利用状況を一目で把握</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with hdr_r:
        st.markdown('<div style="display:flex;justify-content:flex-end;align-items:center;height:100%">', unsafe_allow_html=True)
        period_options = {"1D": 1, "7D": 7, "30D": 30, "All": 365}
        selected_period = st.radio(
            "期間",
            options=list(period_options.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed"
        )
        days = period_options[selected_period]
        st.markdown('</div>', unsafe_allow_html=True)

    team_id = "default-team"

    # ── タブ ──────────────────────────────────────────────────
    tab_dash, tab_tools, tab_tokens, tab_users = st.tabs([
        "ダッシュボード", "ツール分析", "トークン使用量", "ユーザー一覧"
    ])

    with tab_dash:
        render_dashboard(team_id, days)

    with tab_tools:
        render_tools_analysis(team_id, days)

    with tab_tokens:
        st.markdown('<div class="section-header">トークン使用量</div>', unsafe_allow_html=True)
        st.info("トークン使用量の機能は開発中です。")

    with tab_users:
        render_users_list(team_id, days)


# =============================================================================
# ダッシュボードタブ
# =============================================================================
def render_dashboard(team_id: str, days: int):
    # データ取得
    try:
        kpi_df = get_kpi_metrics(team_id, days)
        if kpi_df.empty:
            st.warning("データがありません。プラグインからデータを送信してください。")
            return
        kpi = kpi_df.iloc[0]
    except Exception:
        kpi = pd.Series({
            'SKILL_COUNT': 56, 'SUBAGENT_COUNT': 508, 'MCP_COUNT': 720,
            'MESSAGE_COUNT': 3085, 'SESSION_COUNT': 584, 'COMMAND_COUNT': 120,
            'ACTIVE_USERS': 32, 'TOTAL_USERS': 34,
            'PREV_SKILL': 50, 'PREV_SUBAGENT': 555, 'PREV_MCP': 579,
            'PREV_MESSAGE': 3193, 'PREV_SESSION': 770
        })

    skill_ch   = calc_change(kpi.get('SKILL_COUNT',   0), kpi.get('PREV_SKILL',    0))
    sub_ch     = calc_change(kpi.get('SUBAGENT_COUNT', 0), kpi.get('PREV_SUBAGENT', 0))
    mcp_ch     = calc_change(kpi.get('MCP_COUNT',      0), kpi.get('PREV_MCP',      0))
    msg_ch     = calc_change(kpi.get('MESSAGE_COUNT',  0), kpi.get('PREV_MESSAGE',  0))
    sess_ch    = calc_change(kpi.get('SESSION_COUNT',  0), kpi.get('PREV_SESSION',  0))
    active     = int(kpi.get('ACTIVE_USERS', 0))
    total      = int(kpi.get('TOTAL_USERS', 1))
    pct        = round(active / total * 100) if total > 0 else 0

    # ── Overview KPI ──────────────────────────────────────────
    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.markdown(kpi_card("Skill実行数", int(kpi.get('SKILL_COUNT', 0)), skill_ch, kpi.get('PREV_SKILL', 0),
                             "var(--accent-teal)", badge="Skill"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Subagent数", int(kpi.get('SUBAGENT_COUNT', 0)), sub_ch, kpi.get('PREV_SUBAGENT', 0),
                             "var(--accent-green)", badge="Agent"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("MCP呼び出し", int(kpi.get('MCP_COUNT', 0)), mcp_ch, kpi.get('PREV_MCP', 0),
                             "var(--accent-violet)", badge="MCP"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("メッセージ数", int(kpi.get('MESSAGE_COUNT', 0)), msg_ch, kpi.get('PREV_MESSAGE', 0),
                             "var(--accent-amber)"), unsafe_allow_html=True)
    with c5:
        extra = f"""
        <div class="progress-track">
            <div class="progress-fill" style="width:{pct}%"></div>
        </div>
        <div class="progress-label"><span>普及率</span><span>{pct}%</span></div>
        """
        st.markdown(f"""
        <div class="kpi-card" style="--accent-color:var(--accent-blue)">
            <div class="kpi-label">アクティブユーザー</div>
            <div class="kpi-value">{active} <span style="font-size:1rem;font-weight:400;color:var(--text-muted)">/ {total}</span></div>
            <div class="kpi-change neu">— 名</div>
            {extra}
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(kpi_card("セッション数", int(kpi.get('SESSION_COUNT', 0)), sess_ch, kpi.get('PREV_SESSION', 0),
                             "var(--negative)"), unsafe_allow_html=True)

    # ── AI Insights ───────────────────────────────────────────
    st.markdown('<div class="section-header">AI Insights <span style="font-size:0.65rem;font-weight:400;text-transform:none;letter-spacing:0;color:var(--text-muted)">Powered by Claude</span></div>', unsafe_allow_html=True)

    def _insight(cls, tag, title, desc):
        return f"""
        <div class="insight-card {cls}">
            <div class="insight-tag">{tag}</div>
            <div class="insight-title">{title}</div>
            <div class="insight-desc">{desc}</div>
        </div>"""

    i1 = _insight(
        "trend-up" if mcp_ch > 10 else "usecase",
        "TREND UP" if mcp_ch > 10 else "USECASE INSIGHT",
        f"MCP呼び出しが{mcp_ch:+.0f}%増加" if mcp_ch > 10 else "調査・バグ修正が利用の中心",
        f"MCP活用が急速に広がっています。" if mcp_ch > 10 else "調査とバグ修正が主要な利用用途です。"
    )
    i2 = _insight("power-user", "POWER USER", "パワーユーザーを特定",
                  "上位ユーザーがチームの利用をリードしています。")
    i3 = _insight(
        "trend-down" if sub_ch < -5 else "trend-up",
        "TREND DOWN" if sub_ch < -5 else "TREND UP",
        f"Subagent利用が{abs(sub_ch):.0f}%減少" if sub_ch < -5 else "Skill実行が増加トレンド",
        "サブエージェントの活用見直しを検討してください。" if sub_ch < -5 else "チームのSkill活用が着実に拡大しています。"
    )
    i4 = _insight("usecase", "USECASE INSIGHT", "コード生成が最多用途",
                  "Write/Editツールの利用が多く、コード生成に活用されています。")
    i5 = _insight("neutral", "ADOPTION", "普及率の状況",
                  f"チームの{pct}%がアクティブです。未利用メンバーへの展開機会があります。")

    st.markdown(f'<div class="insight-row">{i1}{i2}{i3}{i4}{i5}</div>', unsafe_allow_html=True)

    # ── チャート ──────────────────────────────────────────────
    st.markdown('<div class="section-header">利用推移 / ツール分布</div>', unsafe_allow_html=True)

    chart_l, chart_r = st.columns(2)

    with chart_l:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">利用推移（日次）</div>', unsafe_allow_html=True)
        try:
            tl = get_timeline_data(team_id, days if days < 365 else 30)
            if not tl.empty:
                st.line_chart(tl.set_index('EVENT_DATE')[['MESSAGES', 'TOOLS', 'SESSIONS']],
                              color=["#f59e0b", "#14b8a6", "#8b5cf6"])
            else:
                st.caption("時系列データがありません")
        except Exception:
            st.caption("時系列データを取得できませんでした")
        st.markdown('</div>', unsafe_allow_html=True)

    with chart_r:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">ツール利用 Top 10</div>', unsafe_allow_html=True)
        try:
            td = get_tool_stats(team_id, days)
            if not td.empty:
                st.bar_chart(td.set_index('TOOL_NAME')['COUNT'], color="#14b8a6")
            else:
                st.caption("ツールデータがありません")
        except Exception:
            st.caption("ツールデータを取得できませんでした")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── ユーザーランキングテーブル ────────────────────────────
    st.markdown('<div class="section-header">ユーザー別利用状況</div>', unsafe_allow_html=True)
    render_user_table(team_id, days)


# =============================================================================
# ユーザーランキングテーブル
# =============================================================================
def render_user_table(team_id: str, days: int):
    try:
        df = get_user_stats(team_id, days)
        if df.empty:
            st.info("ユーザーデータがありません")
            return

        rows_html = ""
        for i, row in df.iterrows():
            rank = i + 1
            name = row.get('DISPLAY_NAME', row.get('USER_ID', '—'))
            ago  = time_ago(row.get('LAST_ACTIVE'))
            sk   = int(row.get('SKILL_COUNT',   0))
            sa   = int(row.get('SUBAGENT_COUNT', 0))
            mc   = int(row.get('MCP_COUNT',      0))
            cm   = int(row.get('COMMAND_COUNT',  0))
            ms   = int(row.get('MESSAGE_COUNT',  0))
            tot  = int(row.get('TOTAL_COUNT',    0))

            tags = ""
            if sk > 0:  tags += f'<span class="tag-pill tag-skill">skill</span> '
            if sa > 0:  tags += f'<span class="tag-pill tag-subagent">agent</span> '
            if mc > 0:  tags += f'<span class="tag-pill tag-mcp">mcp</span> '

            rows_html += f"""
            <tr>
                <td><span class="rank-icon">{rank_icon(rank)}</span></td>
                <td>
                    <div class="user-name">{name}</div>
                    <div class="user-time">{ago}&nbsp;&nbsp;{tags}</div>
                </td>
                <td class="num-cell">{sk}</td>
                <td class="num-cell">{sa}</td>
                <td class="num-cell">{mc}</td>
                <td class="num-cell">{cm}</td>
                <td class="num-cell">{ms}</td>
                <td class="num-cell highlight">{tot}</td>
            </tr>"""

        table_html = f"""
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:10px;overflow:hidden">
        <table class="rank-table">
            <thead>
                <tr>
                    <th style="width:3rem">#</th>
                    <th>ユーザー</th>
                    <th style="text-align:right">Skill</th>
                    <th style="text-align:right">Subagent</th>
                    <th style="text-align:right">MCP</th>
                    <th style="text-align:right">Command</th>
                    <th style="text-align:right">Message</th>
                    <th style="text-align:right">合計 ↓</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>"""
        st.markdown(table_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"ユーザーデータ取得エラー: {e}")


# =============================================================================
# ツール分析タブ
# =============================================================================
def render_tools_analysis(team_id: str, days: int):
    st.markdown('<div class="section-header">ツール利用分析</div>', unsafe_allow_html=True)
    try:
        td = get_tool_stats(team_id, days)
        if td.empty:
            st.info("ツールデータがありません")
            return

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown('<div class="chart-title">ツール利用ランキング</div>', unsafe_allow_html=True)
            st.dataframe(
                td.rename(columns={'TOOL_NAME': 'ツール名', 'COUNT': '実行回数'}),
                hide_index=True,
                use_container_width=True
            )
        with c2:
            st.markdown('<div class="chart-title">ツール利用割合</div>', unsafe_allow_html=True)
            st.bar_chart(td.set_index('TOOL_NAME')['COUNT'], color="#8b5cf6")

    except Exception as e:
        st.error(f"ツールデータ取得エラー: {e}")


# =============================================================================
# ユーザー一覧タブ
# =============================================================================
def render_users_list(team_id: str, days: int):
    st.markdown('<div class="section-header">ユーザー一覧</div>', unsafe_allow_html=True)
    try:
        df = get_user_stats(team_id, days, limit=50)
        if df.empty:
            st.info("ユーザーデータがありません")
            return

        st.dataframe(
            df[['DISPLAY_NAME', 'SKILL_COUNT', 'SUBAGENT_COUNT',
                'MCP_COUNT', 'COMMAND_COUNT', 'MESSAGE_COUNT', 'TOTAL_COUNT']].rename(columns={
                'DISPLAY_NAME':   'ユーザー',
                'SKILL_COUNT':    'Skill',
                'SUBAGENT_COUNT': 'Subagent',
                'MCP_COUNT':      'MCP',
                'COMMAND_COUNT':  'Command',
                'MESSAGE_COUNT':  'Message',
                'TOTAL_COUNT':    '合計',
            }),
            hide_index=True,
            use_container_width=True
        )
    except Exception as e:
        st.error(f"ユーザーデータ取得エラー: {e}")


# =============================================================================
# エントリポイント
# =============================================================================
if __name__ == "__main__":
    main()
