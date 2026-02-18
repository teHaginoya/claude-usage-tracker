# =============================================================================
# queries.py - Snowflake SQL クエリ関数
# =============================================================================

import streamlit as st
import pandas as pd
from helpers import get_session

# =============================================================================
# Tab1 概要
# =============================================================================

@st.cache_data(ttl=300)
def get_kpi_overview(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_timeline_data(team_id: str, days: int) -> pd.DataFrame:
    query = f"""
    SELECT
        DATE_TRUNC('day', EVENT_TIMESTAMP)::DATE                                AS EVENT_DATE,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit'           THEN 1 END)   AS MESSAGES,
        COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse','PreToolUse') THEN 1 END)  AS TOOLS,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'               THEN 1 END)   AS SESSIONS,
        COUNT(CASE WHEN METADATA:is_usage_limit::BOOLEAN = TRUE   THEN 1 END)   AS LIMIT_HITS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND EVENT_TIMESTAMP >= DATEADD('day', -{min(days, 90)}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_heatmap_data(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab2 ユーザー
# =============================================================================

@st.cache_data(ttl=300)
def get_user_stats(team_id: str, days: int, limit: int = 30) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_detail_timeline(team_id: str, user_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_top_tools(team_id: str, user_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab3 ツール
# =============================================================================

@st.cache_data(ttl=300)
def get_tool_stats(team_id: str, days: int, limit: int = 15) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_tool_trend(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab4 セッション
# =============================================================================

@st.cache_data(ttl=300)
def get_session_kpi(team_id: str, days: int) -> pd.DataFrame:
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
        COUNT(*)                                                 AS TOTAL_SESSIONS,
        ROUND(AVG(DATEDIFF('minute', start_time, end_time)), 1) AS AVG_DURATION_MIN,
        SUM(is_limit)                                            AS LIMIT_STOPPED,
        COUNT(CASE WHEN stop_reason = 'normal' THEN 1 END)      AS NORMAL_STOPPED,
        COUNT(DISTINCT USER_ID)                                  AS ACTIVE_USERS_SESS
    FROM sessions
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_stop_reason_data(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_limit_hit_by_hour(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab5 プロジェクト
# =============================================================================

@st.cache_data(ttl=300)
def get_project_ranking(team_id: str, days: int, limit: int = 15) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab6 普及
# =============================================================================

@st.cache_data(ttl=300)
def get_monthly_active(team_id: str) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_feature_adoption(team_id: str, days: int) -> pd.DataFrame:
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
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()
