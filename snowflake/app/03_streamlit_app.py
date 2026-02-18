# =============================================================================
# Claude Code Usage Dashboard - Streamlit in Snowflake
# =============================================================================
# 6タブ完全実装: 概要 / ユーザー / ツール / セッション / プロジェクト / 普及
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session
from datetime import datetime, timedelta
import random

# =============================================================================
# ページ設定
# =============================================================================
st.set_page_config(
    page_title="Claude Code Usage Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
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

    /* ===== プログレスバー ===== */
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

    /* ===== 利用制限バッジ ===== */
    .limit-badge {
        display: inline-block;
        margin-top: 0.5rem;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: rgba(244, 63, 94, 0.15);
        color: var(--negative);
        border: 1px solid rgba(244, 63, 94, 0.3);
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

    .rank-table tr:hover td { background: var(--bg-card-hover); }
    .rank-table tr:last-child td { border-bottom: none; }

    .rank-icon { font-size: 1rem; line-height: 1; }

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

    /* ===== ユーザー詳細パネル ===== */
    .detail-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-left: 3px solid var(--accent-amber);
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
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

    /* ===== ラジオボタン ===== */
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

    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 6px !important;
    }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

</style>
""", unsafe_allow_html=True)

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

# =============================================================================
# Snowflake 接続
# =============================================================================
@st.cache_resource
def get_session():
    return get_active_session()

session = get_session()

# =============================================================================
# データ取得関数
# =============================================================================

@st.cache_data(ttl=300)
def get_kpi_overview(team_id: str, days: int):
    """概要KPI（利用制限ヒット数を含む）"""
    query = f"""
    WITH cur AS (
        SELECT
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)          AS MSG_COUNT,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END)          AS SESS_COUNT,
            COUNT(DISTINCT USER_ID)                                               AS ACTIVE_USERS,
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                          AS SKILL_COUNT,
            COUNT(CASE WHEN IS_MCP   = TRUE THEN 1 END)                          AS MCP_COUNT,
            COUNT(CASE WHEN METADATA:is_usage_limit::BOOLEAN = TRUE THEN 1 END)  AS LIMIT_HITS
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    ),
    prev AS (
        SELECT
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MSG_COUNT,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESS_COUNT,
            COUNT(DISTINCT USER_ID)                                      AS ACTIVE_USERS,
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                 AS SKILL_COUNT,
            COUNT(CASE WHEN IS_MCP   = TRUE THEN 1 END)                 AS MCP_COUNT
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days * 2}, CURRENT_TIMESTAMP())
          AND EVENT_TIMESTAMP <  DATEADD('day', -{days},     CURRENT_TIMESTAMP())
    ),
    tot AS (
        SELECT COUNT(DISTINCT USER_ID) AS TOTAL_USERS
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
    )
    SELECT
        c.*,
        p.MSG_COUNT    AS PREV_MSG,
        p.SESS_COUNT   AS PREV_SESS,
        p.ACTIVE_USERS AS PREV_USERS,
        p.SKILL_COUNT  AS PREV_SKILL,
        p.MCP_COUNT    AS PREV_MCP,
        t.TOTAL_USERS
    FROM cur c, prev p, tot t
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_timeline_data(team_id: str, days: int):
    query = f"""
    SELECT
        DATE_TRUNC('day', EVENT_TIMESTAMP)::DATE                                          AS EVENT_DATE,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit'          THEN 1 END)              AS MESSAGES,
        COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse','PreToolUse') THEN 1 END)            AS TOOLS,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'               THEN 1 END)             AS SESSIONS,
        COUNT(CASE WHEN METADATA:is_usage_limit::BOOLEAN = TRUE   THEN 1 END)             AS LIMIT_HITS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{min(days, 90)}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_heatmap_data(team_id: str, days: int):
    query = f"""
    SELECT
        DAYOFWEEK(EVENT_TIMESTAMP) AS DOW,
        HOUR(EVENT_TIMESTAMP)      AS HOUR_OF_DAY,
        COUNT(*)                   AS EVENT_COUNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_stats(team_id: str, days: int, limit: int = 30):
    query = f"""
    SELECT
        USER_ID,
        SPLIT_PART(USER_ID, '@', 1)                                              AS DISPLAY_NAME,
        COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)                           AS SKILL_COUNT,
        COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)                           AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)                           AS MCP_COUNT,
        COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)                           AS COMMAND_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)              AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END)              AS SESSION_COUNT,
        COUNT(CASE WHEN METADATA:is_usage_limit::BOOLEAN = TRUE THEN 1 END)      AS LIMIT_HITS,
        COUNT(*)                                                                  AS TOTAL_COUNT,
        MAX(EVENT_TIMESTAMP)                                                      AS LAST_ACTIVE,
        MIN(DATE_TRUNC('day', EVENT_TIMESTAMP))::DATE                            AS FIRST_ACTIVE
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY USER_ID
    ORDER BY TOTAL_COUNT DESC
    LIMIT {limit}
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_detail_timeline(team_id: str, user_id: str, days: int):
    safe_uid = user_id.replace("'", "''")
    query = f"""
    SELECT
        DATE_TRUNC('day', EVENT_TIMESTAMP)::DATE                               AS EVENT_DATE,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)            AS MESSAGES,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END)            AS SESSIONS,
        COUNT(CASE WHEN METADATA:is_usage_limit::BOOLEAN = TRUE THEN 1 END)    AS LIMIT_HITS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND USER_ID = '{safe_uid}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_top_tools(team_id: str, user_id: str, days: int):
    safe_uid = user_id.replace("'", "''")
    query = f"""
    SELECT TOOL_NAME, COUNT(*) AS CNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND USER_ID = '{safe_uid}'
      AND TOOL_NAME IS NOT NULL
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY TOOL_NAME
    ORDER BY CNT DESC
    LIMIT 10
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_tool_stats(team_id: str, days: int, limit: int = 15):
    query = f"""
    SELECT
        TOOL_NAME,
        COUNT(*) AS TOTAL_COUNT,
        SUM(CASE WHEN TOOL_SUCCESS = TRUE THEN 1 ELSE 0 END) AS SUCCESS_COUNT,
        ROUND(
            SUM(CASE WHEN TOOL_SUCCESS = TRUE THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0) * 100, 1
        ) AS SUCCESS_RATE
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND TOOL_NAME IS NOT NULL
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY TOOL_NAME
    ORDER BY TOTAL_COUNT DESC
    LIMIT {limit}
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_tool_trend(team_id: str, days: int):
    """上位 5 ツールの日次トレンド"""
    query = f"""
    WITH top_tools AS (
        SELECT TOOL_NAME
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND TOOL_NAME IS NOT NULL
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY TOOL_NAME
        ORDER BY COUNT(*) DESC
        LIMIT 5
    )
    SELECT
        DATE_TRUNC('day', e.EVENT_TIMESTAMP)::DATE AS EVENT_DATE,
        e.TOOL_NAME,
        COUNT(*) AS CNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS e
    JOIN top_tools t ON e.TOOL_NAME = t.TOOL_NAME
    WHERE e.TEAM_ID = '{team_id}'
      AND e.EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_session_kpi(team_id: str, days: int):
    query = f"""
    WITH sessions AS (
        SELECT
            SESSION_ID,
            USER_ID,
            MIN(EVENT_TIMESTAMP) AS start_time,
            MAX(EVENT_TIMESTAMP) AS end_time,
            MAX(CASE WHEN METADATA:stop_reason::STRING = 'usage_limit' THEN 1 ELSE 0 END) AS is_limit,
            COALESCE(MAX(METADATA:stop_reason::STRING), 'unknown') AS stop_reason
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
          AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY SESSION_ID, USER_ID
    )
    SELECT
        COUNT(*)                                                    AS TOTAL_SESSIONS,
        ROUND(AVG(DATEDIFF('minute', start_time, end_time)), 1)    AS AVG_DURATION_MIN,
        SUM(is_limit)                                               AS LIMIT_STOPPED,
        COUNT(CASE WHEN stop_reason = 'normal' THEN 1 END)         AS NORMAL_STOPPED,
        COUNT(DISTINCT USER_ID)                                     AS ACTIVE_USERS_SESS
    FROM sessions
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_stop_reason_data(team_id: str, days: int):
    query = f"""
    SELECT
        COALESCE(METADATA:stop_reason::STRING, 'unknown') AS STOP_REASON,
        COUNT(DISTINCT SESSION_ID)                         AS SESSION_COUNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TYPE = 'Stop'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 2 DESC
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_limit_hit_by_hour(team_id: str, days: int):
    query = f"""
    SELECT
        HOUR(EVENT_TIMESTAMP) AS HOUR_OF_DAY,
        COUNT(*)              AS LIMIT_HITS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND METADATA:is_usage_limit::BOOLEAN = TRUE
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_project_ranking(team_id: str, days: int, limit: int = 15):
    query = f"""
    SELECT
        COALESCE(PROJECT_PATH, '(no project)') AS PROJECT_NAME,
        COUNT(*)                               AS EVENT_COUNT,
        COUNT(DISTINCT USER_ID)               AS USER_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MSG_COUNT,
        COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                 AS SKILL_COUNT,
        COUNT(CASE WHEN IS_MCP   = TRUE THEN 1 END)                 AS MCP_COUNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY EVENT_COUNT DESC
    LIMIT {limit}
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_monthly_active(team_id: str):
    query = f"""
    SELECT
        DATE_TRUNC('month', EVENT_TIMESTAMP)::DATE AS MONTH,
        COUNT(DISTINCT USER_ID)                    AS ACTIVE_USERS,
        COUNT(DISTINCT SESSION_ID)                 AS SESSIONS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGES
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_feature_adoption(team_id: str, days: int):
    query = f"""
    SELECT
        COUNT(DISTINCT USER_ID)                                       AS TOTAL_USERS,
        COUNT(DISTINCT CASE WHEN IS_SKILL    = TRUE THEN USER_ID END) AS SKILL_USERS,
        COUNT(DISTINCT CASE WHEN IS_MCP      = TRUE THEN USER_ID END) AS MCP_USERS,
        COUNT(DISTINCT CASE WHEN IS_SUBAGENT = TRUE THEN USER_ID END) AS SUBAGENT_USERS,
        COUNT(DISTINCT CASE WHEN IS_COMMAND  = TRUE THEN USER_ID END) AS COMMAND_USERS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    """
    try:
        return session.sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


# =============================================================================
# ヘルパー関数
# =============================================================================

def calc_change(cur, prev):
    cur = cur or 0
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
    return icons.get(r, f'<span style="font-family:var(--mono-font);color:var(--text-muted)">{r}</span>')


def sparkbars(heights=None, color="var(--accent-teal)"):
    if heights is None:
        heights = [30, 45, 35, 60, 50, 70, 65]
    bars = "".join(
        f'<span style="height:{h}%;background:{color}"></span>' for h in heights
    )
    return f'<div class="kpi-sparkbar">{bars}</div>'


def kpi_card(label, value, change_val, accent, badge=None, extra_html="", value_fmt=None):
    change_text, change_cls = fmt_change(change_val)
    badge_html = (
        f'<span class="badge" style="background:rgba(255,255,255,0.08);color:var(--text-muted)">{badge}</span>'
        if badge else ""
    )
    sc_map = {
        "var(--accent-teal)":   "#14b8a6",
        "var(--accent-amber)":  "#f59e0b",
        "var(--accent-violet)": "#8b5cf6",
        "var(--accent-blue)":   "#3b82f6",
        "var(--accent-green)":  "#22c55e",
        "var(--negative)":      "#f43f5e",
    }
    sc = sc_map.get(accent, "#14b8a6")
    if value_fmt:
        val_str = value_fmt
    elif isinstance(value, float):
        val_str = f"{value:,.1f}"
    else:
        val_str = f"{int(value or 0):,}"
    return f"""
    <div class="kpi-card" style="--accent-color:{accent}">
        <div class="kpi-label">{label}{badge_html}</div>
        <div class="kpi-value">{val_str}</div>
        <div class="kpi-change {change_cls}">{change_text}
            <span style="color:var(--text-muted);font-weight:400">前期比</span>
        </div>
        {sparkbars(color=sc)}
        {extra_html}
    </div>"""


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


def apply_plotly(fig, height=280):
    fig.update_layout(**PLOTLY_BASE, height=height)
    fig.update_xaxes(showgrid=True, gridcolor="#1f2d4a", linecolor="#1f2d4a")
    fig.update_yaxes(showgrid=True, gridcolor="#1f2d4a", linecolor="#1f2d4a")
    return fig


# =============================================================================
# デモデータ生成（SQL失敗時のフォールバック）
# =============================================================================

def _seed():
    random.seed(42)


def demo_timeline(days):
    _seed()
    dates = pd.date_range(end=datetime.today(), periods=min(days, 30), freq="D")
    return pd.DataFrame({
        "EVENT_DATE":  dates,
        "MESSAGES":    [random.randint(60, 180) for _ in dates],
        "TOOLS":       [random.randint(200, 700) for _ in dates],
        "SESSIONS":    [random.randint(10, 40)  for _ in dates],
        "LIMIT_HITS":  [random.randint(0, 4)    for _ in dates],
    })


def demo_heatmap():
    _seed()
    rows = []
    for dow in range(7):
        for h in range(24):
            cnt = random.randint(0, 55) if 8 <= h <= 22 else random.randint(0, 8)
            rows.append({"DOW": dow, "HOUR_OF_DAY": h, "EVENT_COUNT": cnt})
    return pd.DataFrame(rows)


def demo_users():
    _seed()
    names = ["te.haginoya", "a.tanaka", "k.suzuki", "m.yamamoto", "r.kobayashi",
             "y.ito", "h.watanabe", "s.nakamura"]
    rows = []
    for u in names:
        tot = random.randint(200, 1200)
        rows.append({
            "USER_ID":        u + "@example.com",
            "DISPLAY_NAME":   u,
            "SKILL_COUNT":    random.randint(0, 30),
            "SUBAGENT_COUNT": random.randint(0, 60),
            "MCP_COUNT":      random.randint(0, 120),
            "COMMAND_COUNT":  random.randint(0, 25),
            "MESSAGE_COUNT":  random.randint(40, 280),
            "SESSION_COUNT":  random.randint(5, 50),
            "LIMIT_HITS":     random.randint(0, 6),
            "TOTAL_COUNT":    tot,
            "LAST_ACTIVE":    datetime.now() - timedelta(hours=random.randint(1, 96)),
            "FIRST_ACTIVE":   (datetime.now() - timedelta(days=random.randint(3, 60))).date(),
        })
    return pd.DataFrame(rows)


def demo_tools():
    _seed()
    tools = ["Bash", "Read", "Write", "Edit", "Glob", "Grep",
             "WebFetch", "Task", "TodoWrite", "NotebookEdit", "WebSearch"]
    rows = []
    for t in tools:
        cnt = random.randint(40, 900)
        succ = random.randint(int(cnt * 0.65), cnt)
        rows.append({
            "TOOL_NAME":    t,
            "TOTAL_COUNT":  cnt,
            "SUCCESS_COUNT": succ,
            "SUCCESS_RATE": round(succ / cnt * 100, 1),
        })
    return pd.DataFrame(rows).sort_values("TOTAL_COUNT", ascending=False)


def demo_stop_reason():
    return pd.DataFrame({
        "STOP_REASON":   ["normal", "usage_limit", "unknown"],
        "SESSION_COUNT": [120, 23, 8],
    })


def demo_session_kpi():
    return pd.DataFrame({
        "TOTAL_SESSIONS":   [151],
        "AVG_DURATION_MIN": [18.5],
        "LIMIT_STOPPED":    [23],
        "NORMAL_STOPPED":   [120],
        "ACTIVE_USERS_SESS": [8],
    })


def demo_limit_by_hour():
    _seed()
    hours = list(range(24))
    hits = [random.randint(0, 9) if 9 <= h <= 22 else random.randint(0, 2) for h in hours]
    return pd.DataFrame({"HOUR_OF_DAY": hours, "LIMIT_HITS": hits})


def demo_projects():
    _seed()
    projs = ["claude-usage-tracker", "webapp-refactor", "data-pipeline",
             "api-service", "ml-experiment", "(no project)"]
    rows = []
    for p in projs:
        ec = random.randint(80, 2500)
        rows.append({
            "PROJECT_NAME": p,
            "EVENT_COUNT":  ec,
            "USER_COUNT":   random.randint(1, 6),
            "MSG_COUNT":    random.randint(20, 250),
            "SKILL_COUNT":  random.randint(0, 25),
            "MCP_COUNT":    random.randint(0, 60),
        })
    return pd.DataFrame(rows).sort_values("EVENT_COUNT", ascending=False)


def demo_monthly():
    _seed()
    months = pd.date_range(end=datetime.today().replace(day=1), periods=6, freq="MS")
    return pd.DataFrame({
        "MONTH":        months,
        "ACTIVE_USERS": [random.randint(2, 10) for _ in months],
        "SESSIONS":     [random.randint(40, 200) for _ in months],
        "MESSAGES":     [random.randint(400, 2000) for _ in months],
    })


def demo_feature_adoption():
    return pd.DataFrame({
        "TOTAL_USERS":   [10],
        "SKILL_USERS":   [4],
        "MCP_USERS":     [6],
        "SUBAGENT_USERS": [3],
        "COMMAND_USERS": [7],
    })


# =============================================================================
# Tab 1: 概要
# =============================================================================

def render_overview(team_id: str, days: int):
    # KPI データ
    kpi_raw = get_kpi_overview(team_id, days)
    if kpi_raw.empty:
        kpi = {
            "MSG_COUNT": 3085, "SESS_COUNT": 584, "ACTIVE_USERS": 8,
            "SKILL_COUNT": 56, "MCP_COUNT": 720, "LIMIT_HITS": 23,
            "PREV_MSG": 2900, "PREV_SESS": 550, "PREV_USERS": 7,
            "PREV_SKILL": 45, "PREV_MCP": 600, "TOTAL_USERS": 10,
        }
    else:
        r = kpi_raw.iloc[0]
        kpi = {k.upper(): (int(v) if pd.notna(v) else 0) for k, v in r.items()}

    # ── KPI カード ──────────────────────────────────────────────
    section("Overview")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        ch = calc_change(kpi.get("MSG_COUNT", 0), kpi.get("PREV_MSG", 0))
        st.markdown(kpi_card("メッセージ数", kpi.get("MSG_COUNT", 0), ch, "var(--accent-amber)"),
                    unsafe_allow_html=True)
    with c2:
        ch = calc_change(kpi.get("SESS_COUNT", 0), kpi.get("PREV_SESS", 0))
        st.markdown(kpi_card("セッション数", kpi.get("SESS_COUNT", 0), ch, "var(--accent-teal)"),
                    unsafe_allow_html=True)
    with c3:
        active = int(kpi.get("ACTIVE_USERS", 0))
        total  = int(kpi.get("TOTAL_USERS", 1)) or 1
        pct = round(active / total * 100)
        extra = (
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div>'
            f'<div class="progress-label"><span>普及率</span><span>{pct}%</span></div>'
        )
        ch = calc_change(active, kpi.get("PREV_USERS", 0))
        st.markdown(
            kpi_card("アクティブユーザー", active, ch, "var(--accent-blue)",
                     value_fmt=f"{active} <span style='font-size:1rem;font-weight:400;color:var(--text-muted)'>/ {total}</span>",
                     extra_html=extra),
            unsafe_allow_html=True,
        )
    with c4:
        ch = calc_change(kpi.get("SKILL_COUNT", 0), kpi.get("PREV_SKILL", 0))
        st.markdown(kpi_card("Skill実行", kpi.get("SKILL_COUNT", 0), ch,
                             "var(--accent-violet)", badge="Skill"),
                    unsafe_allow_html=True)
    with c5:
        ch = calc_change(kpi.get("MCP_COUNT", 0), kpi.get("PREV_MCP", 0))
        st.markdown(kpi_card("MCP呼び出し", kpi.get("MCP_COUNT", 0), ch,
                             "var(--accent-green)", badge="MCP"),
                    unsafe_allow_html=True)
    with c6:
        limit_hits = int(kpi.get("LIMIT_HITS", 0))
        extra_l = f'<div class="limit-badge">⚡ 利用制限ヒット</div>' if limit_hits > 0 else ""
        st.markdown(kpi_card("利用制限ヒット", limit_hits, 0.0, "var(--negative)",
                             extra_html=extra_l),
                    unsafe_allow_html=True)

    # ── 日次推移 + ヒートマップ ──────────────────────────────────
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
            fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
        ))
        fig.add_trace(go.Scatter(
            x=tl["EVENT_DATE"], y=tl["SESSIONS"],
            name="セッション", line=dict(color="#14b8a6", width=1.5, dash="dot"),
        ))
        if "LIMIT_HITS" in tl.columns:
            fig.add_trace(go.Bar(
                x=tl["EVENT_DATE"], y=tl["LIMIT_HITS"],
                name="制限ヒット", marker_color="rgba(244,63,94,0.55)",
                yaxis="y2",
            ))
            fig.update_layout(
                yaxis2=dict(overlaying="y", side="right", showgrid=False,
                            tickfont=dict(color="#f43f5e", size=9)),
            )
        fig.update_layout(title_text="日次利用推移", legend=dict(orientation="h", y=1.1, x=0))
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
            colorscale=[[0, "#141c2e"], [0.4, "#1f2d4a"], [0.7, "#8b5cf6"], [1, "#f59e0b"]],
            showscale=False,
            hoverongaps=False,
            hovertemplate="曜日: %{y}<br>時刻: %{x}<br>件数: %{z}<extra></extra>",
        ))
        fig2.update_layout(title_text="時間帯 × 曜日ヒートマップ")
        fig2 = apply_plotly(fig2, 280)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── AI Insights ─────────────────────────────────────────────
    section("AI Insights", "自動生成インサイト")

    msg_ch   = calc_change(kpi.get("MSG_COUNT",   0), kpi.get("PREV_MSG",   0))
    mcp_ch   = calc_change(kpi.get("MCP_COUNT",   0), kpi.get("PREV_MCP",   0))
    skill_ch = calc_change(kpi.get("SKILL_COUNT", 0), kpi.get("PREV_SKILL", 0))

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
        "TREND UP" if msg_ch >= 0 else "TREND DOWN",
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
        "power-user", "POWER USER",
        "上位ユーザーが利用を牽引",
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
        "neutral", "ADOPTION",
        f"普及率 {pct}%",
        f"チームの {pct}% がアクティブです。"
        + ("未利用メンバーへの展開機会があります。" if pct < 80
           else "高い普及率を維持しています。"),
    )
    st.markdown(
        f'<div class="insight-row">{i1}{i2}{i3}{i4}{i5}</div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# Tab 2: ユーザー
# =============================================================================

def render_users(team_id: str, days: int):
    section("ユーザー別利用状況")

    df = get_user_stats(team_id, days)
    if df.empty:
        df = demo_users()
    df.columns = [c.upper() for c in df.columns]

    # ランキングテーブル
    rows_html = ""
    for i, row in df.iterrows():
        rank  = i + 1
        uid   = str(row.get("USER_ID", "—"))
        name  = str(row.get("DISPLAY_NAME", uid))
        ago   = time_ago(row.get("LAST_ACTIVE"))
        sk    = int(row.get("SKILL_COUNT",    0))
        sa    = int(row.get("SUBAGENT_COUNT", 0))
        mc    = int(row.get("MCP_COUNT",      0))
        ms    = int(row.get("MESSAGE_COUNT",  0))
        se    = int(row.get("SESSION_COUNT",  0))
        lh    = int(row.get("LIMIT_HITS",     0))
        tot   = int(row.get("TOTAL_COUNT",    0))

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

    table_html = f"""
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:10px;overflow:hidden">
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
    </div>"""
    st.markdown(table_html, unsafe_allow_html=True)

    # ── ユーザー詳細 ────────────────────────────────────────────
    section("ユーザー詳細")
    user_options = ["(選択してください)"] + df["DISPLAY_NAME"].tolist()
    sel = st.selectbox("詳細を見るユーザーを選択", user_options, label_visibility="collapsed")

    if sel and sel != "(選択してください)":
        matched = df[df["DISPLAY_NAME"] == sel]
        if not matched.empty:
            user_row = matched.iloc[0]
            uid = str(user_row.get("USER_ID", sel))
            render_user_detail(team_id, uid, sel, days, user_row)


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
        st.markdown(kpi_card("メッセージ数", int(summary.get("MESSAGE_COUNT", 0)), 0.0, "var(--accent-amber)"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("セッション数", int(summary.get("SESSION_COUNT", 0)), 0.0, "var(--accent-teal)"),
                    unsafe_allow_html=True)
    with c3:
        lh = int(summary.get("LIMIT_HITS", 0))
        extra = f'<div class="limit-badge">⚡ 制限ヒット</div>' if lh > 0 else ""
        st.markdown(kpi_card("制限ヒット", lh, 0.0, "var(--negative)", extra_html=extra),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Skill実行", int(summary.get("SKILL_COUNT", 0)), 0.0,
                             "var(--accent-violet)", badge="Skill"),
                    unsafe_allow_html=True)

    # 日次推移 + ツール TOP
    tl = get_user_detail_timeline(team_id, user_id, days)
    if tl.empty:
        tl = demo_timeline(days)
    tl.columns = [c.upper() for c in tl.columns]

    top_tools = get_user_top_tools(team_id, user_id, days)
    if top_tools.empty:
        top_tools = demo_tools()[["TOOL_NAME", "TOTAL_COUNT"]].rename(
            columns={"TOTAL_COUNT": "CNT"}
        ).head(8)
    top_tools.columns = [c.upper() for c in top_tools.columns]
    tc1 = top_tools.columns[0]
    tc2 = top_tools.columns[1]

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
        fig.update_layout(title_text="日次利用推移", legend=dict(orientation="h", y=1.1, x=0))
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


# =============================================================================
# Tab 3: ツール
# =============================================================================

def render_tools(team_id: str, days: int):
    section("ツール利用分析")

    tool_df = get_tool_stats(team_id, days)
    if tool_df.empty:
        tool_df = demo_tools()
    tool_df.columns = [c.upper() for c in tool_df.columns]

    c1, c2 = st.columns([3, 2])

    with c1:
        fig = go.Figure(go.Bar(
            x=tool_df["TOTAL_COUNT"],
            y=tool_df["TOOL_NAME"],
            orientation="h",
            marker=dict(
                color=tool_df["TOTAL_COUNT"],
                colorscale=[[0, "#1f2d4a"], [0.5, "#3b82f6"], [1, "#14b8a6"]],
                showscale=False,
            ),
            text=tool_df["TOTAL_COUNT"],
            textposition="outside",
            textfont=dict(size=10, color="#8899b8"),
        ))
        fig.update_layout(
            title_text="ツール利用ランキング",
            yaxis={"categoryorder": "total ascending"},
        )
        fig = apply_plotly(fig, 400)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        section("成功率")
        rows_html = ""
        for _, row in tool_df.head(10).iterrows():
            name  = str(row.get("TOOL_NAME", "—"))
            tot   = int(row.get("TOTAL_COUNT", 0))
            rate  = row.get("SUCCESS_RATE", None)
            if rate is None or str(rate) == "nan":
                rate_html = '<span style="color:var(--text-muted)">—</span>'
                bar_pct = 0
                bar_color = "#4a5c7a"
            else:
                rate = float(rate)
                bar_pct = rate
                bar_color = "#22c55e" if rate >= 90 else "#f59e0b" if rate >= 70 else "#f43f5e"
                rate_html = f'<span style="color:{bar_color};font-family:var(--mono-font)">{rate:.1f}%</span>'

            rows_html += f"""
            <tr>
                <td class="user-name" style="font-size:0.78rem">{name}</td>
                <td class="num-cell">{tot:,}</td>
                <td style="min-width:80px">
                    {rate_html}
                    <div class="progress-track" style="margin-top:0.25rem">
                        <div class="progress-fill" style="width:{bar_pct}%;background:{bar_color}"></div>
                    </div>
                </td>
            </tr>"""

        tbl = (
            '<div style="background:var(--bg-card);border:1px solid var(--border);'
            'border-radius:10px;overflow:hidden">'
            '<table class="rank-table">'
            "<thead><tr>"
            "<th>ツール</th>"
            '<th style="text-align:right">実行数</th>'
            "<th>成功率</th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table></div>"
        )
        st.markdown(tbl, unsafe_allow_html=True)

    # ツール日次トレンド
    section("ツール利用トレンド（上位5）")
    trend = get_tool_trend(team_id, days)
    if not trend.empty:
        trend.columns = [c.upper() for c in trend.columns]
        fig3 = px.line(
            trend, x="EVENT_DATE", y="CNT", color="TOOL_NAME",
            color_discrete_sequence=["#f59e0b", "#14b8a6", "#8b5cf6", "#3b82f6", "#22c55e"],
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
    else:
        st.caption("トレンドデータがありません")


# =============================================================================
# Tab 4: セッション
# =============================================================================

def render_sessions(team_id: str, days: int):
    section("セッション分析")

    # KPI
    kpi_df = get_session_kpi(team_id, days)
    if kpi_df.empty:
        kpi_df = demo_session_kpi()
    kpi_df.columns = [c.upper() for c in kpi_df.columns]
    kpi = kpi_df.iloc[0]

    total_sess  = int(kpi.get("TOTAL_SESSIONS",   0))
    avg_dur     = float(kpi.get("AVG_DURATION_MIN", 0) or 0)
    lim_stopped = int(kpi.get("LIMIT_STOPPED",    0))
    nrm_stopped = int(kpi.get("NORMAL_STOPPED",   0))
    lim_pct     = round(lim_stopped / total_sess * 100, 1) if total_sess > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("総セッション数", total_sess, 0.0, "var(--accent-teal)"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(
            kpi_card("平均セッション長", avg_dur, 0.0, "var(--accent-blue)",
                     value_fmt=f"{avg_dur:.1f}<span style='font-size:0.9rem;color:var(--text-muted)'> 分</span>"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(kpi_card("正常終了", nrm_stopped, 0.0, "var(--accent-green)"),
                    unsafe_allow_html=True)
    with c4:
        extra = (
            f'<div class="limit-badge">利用制限率 {lim_pct}%</div>'
            if lim_stopped > 0 else ""
        )
        st.markdown(kpi_card("制限終了", lim_stopped, 0.0, "var(--negative)", extra_html=extra),
                    unsafe_allow_html=True)

    # チャート
    c1, c2 = st.columns(2)

    with c1:
        stop_df = get_stop_reason_data(team_id, days)
        if stop_df.empty:
            stop_df = demo_stop_reason()
        stop_df.columns = [c.upper() for c in stop_df.columns]

        label_map = {"normal": "正常終了", "usage_limit": "利用制限", "unknown": "不明"}
        color_map = {"正常終了": "#22c55e", "利用制限": "#f43f5e", "不明": "#4a5c7a"}
        labels = [label_map.get(str(x), str(x)) for x in stop_df["STOP_REASON"]]
        colors = [color_map.get(l, "#8b5cf6") for l in labels]

        fig = go.Figure(go.Pie(
            labels=labels, values=stop_df["SESSION_COUNT"],
            hole=0.6,
            marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
            textinfo="label+percent",
            textfont=dict(size=11),
        ))
        fig.update_layout(
            title_text="停止理由の内訳",
            annotations=[dict(
                text=f"{total_sess}<br>Sessions",
                x=0.5, y=0.5, font_size=14, showarrow=False,
                font=dict(color="#e8edf5"),
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

        fig2 = go.Figure(go.Bar(
            x=lim_hr["HOUR_OF_DAY"],
            y=lim_hr["LIMIT_HITS"],
            marker=dict(
                color=lim_hr["LIMIT_HITS"],
                colorscale=[[0, "#1f2d4a"], [0.5, "#8b5cf6"], [1, "#f43f5e"]],
                showscale=False,
            ),
            hovertemplate="%{x}時: %{y}件<extra></extra>",
        ))
        fig2.update_layout(
            title_text="制限ヒット 時間帯別",
            xaxis=dict(tickmode="linear", tick0=0, dtick=2, title="時刻"),
            yaxis=dict(title="ヒット数"),
        )
        fig2 = apply_plotly(fig2, 300)
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# Tab 5: プロジェクト
# =============================================================================

def render_projects(team_id: str, days: int):
    section("プロジェクト別分析")

    proj_df = get_project_ranking(team_id, days)
    if proj_df.empty:
        proj_df = demo_projects()
    proj_df.columns = [c.upper() for c in proj_df.columns]
    col_name = "PROJECT_NAME" if "PROJECT_NAME" in proj_df.columns else proj_df.columns[0]

    # 水平棒グラフ
    fig = go.Figure(go.Bar(
        x=proj_df["EVENT_COUNT"],
        y=proj_df[col_name],
        orientation="h",
        marker=dict(
            color=proj_df["EVENT_COUNT"],
            colorscale=[[0, "#1f2d4a"], [0.5, "#3b82f6"], [1, "#14b8a6"]],
            showscale=False,
        ),
        text=proj_df["EVENT_COUNT"],
        textposition="outside",
        textfont=dict(size=10, color="#8899b8"),
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

    # プロジェクト統計テーブル
    section("プロジェクト統計")
    rows_html = ""
    for _, row in proj_df.iterrows():
        full_name = str(row.get(col_name, "—"))
        short = full_name.split("/")[-1] if "/" in full_name else full_name
        ec  = int(row.get("EVENT_COUNT", 0))
        uc  = int(row.get("USER_COUNT",  0))
        mc  = int(row.get("MSG_COUNT",   0))
        sk  = int(row.get("SKILL_COUNT", 0))
        mcp = int(row.get("MCP_COUNT",   0))
        rows_html += f"""
        <tr>
            <td class="user-name" style="font-size:0.78rem" title="{full_name}">{short}</td>
            <td class="num-cell highlight">{ec:,}</td>
            <td class="num-cell">{uc}</td>
            <td class="num-cell">{mc:,}</td>
            <td class="num-cell">{sk}</td>
            <td class="num-cell">{mcp}</td>
        </tr>"""

    tbl = (
        '<div style="background:var(--bg-card);border:1px solid var(--border);'
        'border-radius:10px;overflow:hidden">'
        '<table class="rank-table">'
        "<thead><tr>"
        "<th>プロジェクト</th>"
        '<th style="text-align:right">イベント ↓</th>'
        '<th style="text-align:right">ユーザー</th>'
        '<th style="text-align:right">メッセージ</th>'
        '<th style="text-align:right">Skill</th>'
        '<th style="text-align:right">MCP</th>'
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )
    st.markdown(tbl, unsafe_allow_html=True)


# =============================================================================
# Tab 6: 普及
# =============================================================================

def render_adoption(team_id: str, days: int):
    section("普及・定着分析")

    # 月次アクティブユーザー
    monthly = get_monthly_active(team_id)
    if monthly.empty:
        monthly = demo_monthly()
    monthly.columns = [c.upper() for c in monthly.columns]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["MONTH"], y=monthly["ACTIVE_USERS"],
        name="月次アクティブユーザー",
        line=dict(color="#f59e0b", width=2.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
        marker=dict(size=6, color="#f59e0b"),
    ))
    fig.add_trace(go.Bar(
        x=monthly["MONTH"], y=monthly["SESSIONS"],
        name="セッション数",
        marker_color="rgba(20,184,166,0.25)",
        yaxis="y2",
    ))
    fig.update_layout(
        title_text="月次アクティブユーザー推移",
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(color="#14b8a6", size=9)),
        legend=dict(orientation="h", y=1.1, x=0),
    )
    fig = apply_plotly(fig, 280)
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # 機能普及率
    section("機能普及率")
    fa_df = get_feature_adoption(team_id, days)
    if fa_df.empty:
        fa_df = demo_feature_adoption()
    fa_df.columns = [c.upper() for c in fa_df.columns]
    fa = fa_df.iloc[0]

    total = int(fa.get("TOTAL_USERS", 1)) or 1
    features = [
        ("Skill",    int(fa.get("SKILL_USERS",    0)), "#14b8a6", "var(--accent-teal)"),
        ("MCP",      int(fa.get("MCP_USERS",      0)), "#8b5cf6", "var(--accent-violet)"),
        ("Subagent", int(fa.get("SUBAGENT_USERS", 0)), "#22c55e", "var(--accent-green)"),
        ("Command",  int(fa.get("COMMAND_USERS",  0)), "#3b82f6", "var(--accent-blue)"),
    ]

    ca, cb = st.columns([2, 3])

    with ca:
        bars_html = ""
        for fname, count, hex_color, _ in features:
            pct = round(count / total * 100)
            bars_html += (
                f'<div style="margin-bottom:1rem">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:0.3rem">'
                f'<span style="font-size:0.78rem;font-weight:600;color:var(--text-primary)">{fname}</span>'
                f'<span style="font-family:var(--mono-font);font-size:0.78rem;color:{hex_color}">'
                f"{count}/{total} ({pct}%)</span></div>"
                f'<div class="progress-track" style="height:8px">'
                f'<div class="progress-fill" style="width:{pct}%;background:{hex_color}"></div>'
                f"</div></div>"
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
            textfont=dict(size=11, color="#8899b8"),
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

    # 未使用者サマリー
    section("未使用者サマリー")
    cols = st.columns(4)
    for (fname, count, hex_color, accent), col in zip(features, cols):
        non = total - count
        with col:
            st.markdown(
                f'<div class="kpi-card" style="--accent-color:{accent}">'
                f'<div class="kpi-label">{fname} 未使用者</div>'
                f'<div class="kpi-value" style="font-size:1.5rem">{non}</div>'
                f'<div class="kpi-change neu" style="font-size:0.7rem">/ {total} 名中</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


# =============================================================================
# メイン
# =============================================================================

def main():
    # セッション状態初期化
    if "selected_user" not in st.session_state:
        st.session_state.selected_user = None

    # ── ヘッダー ────────────────────────────────────────────────
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
        period_options = {"1D": 1, "7D": 7, "30D": 30, "90D": 90, "All": 365}
        selected_period = st.radio(
            "期間",
            options=list(period_options.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )
        days = period_options[selected_period]

    team_id = "default-team"

    # ── 6タブ ───────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "概要", "ユーザー", "ツール", "セッション", "プロジェクト", "普及",
    ])

    with tab1:
        render_overview(team_id, days)
    with tab2:
        render_users(team_id, days)
    with tab3:
        render_tools(team_id, days)
    with tab4:
        render_sessions(team_id, days)
    with tab5:
        render_projects(team_id, days)
    with tab6:
        render_adoption(team_id, days)


# =============================================================================
# エントリポイント
# =============================================================================
if __name__ == "__main__":
    main()
