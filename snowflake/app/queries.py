# =============================================================================
# queries.py - Snowflake SQL クエリ関数
#
# データソース:
#   LAYER3 SUMMARY テーブル → 8 クエリ（高速・事前集計済み）
#   LAYER2 EVENTS          → 6 クエリ（時間帯・セッション詳細など粒度が必要なもの）
# =============================================================================

import streamlit as st
import pandas as pd
from helpers import get_session

_L2 = "CLAUDE_USAGE_DB.LAYER2"  # イベント詳細
_L3 = "CLAUDE_USAGE_DB.LAYER3"  # サマリーテーブル

# =============================================================================
# Tab1 概要
# =============================================================================

@st.cache_data(ttl=300)
def get_kpi_overview(team_id: str, days: int) -> pd.DataFrame:
    """概要KPI（DAILY_SUMMARY + USER_SUMMARY）"""
    query = f"""
    WITH cur_daily AS (
        SELECT
            SUM(MESSAGE_COUNT)    AS MSG_COUNT,
            SUM(SESSION_COUNT)    AS SESS_COUNT,
            SUM(SKILL_COUNT)      AS SKILL_COUNT,
            SUM(MCP_COUNT)        AS MCP_COUNT,
            SUM(LIMIT_HIT_COUNT)  AS LIMIT_HITS
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ),
    cur_users AS (
        SELECT COUNT(DISTINCT USER_ID) AS ACTIVE_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ),
    prev_daily AS (
        SELECT
            SUM(MESSAGE_COUNT)  AS MSG_COUNT,
            SUM(SESSION_COUNT)  AS SESS_COUNT,
            SUM(SKILL_COUNT)    AS SKILL_COUNT,
            SUM(MCP_COUNT)      AS MCP_COUNT
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
          AND SUMMARY_DATE <  DATEADD('day', -{days},     CURRENT_DATE())
    ),
    prev_users AS (
        SELECT COUNT(DISTINCT USER_ID) AS ACTIVE_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
          AND SUMMARY_DATE <  DATEADD('day', -{days},     CURRENT_DATE())
    ),
    tot AS (
        SELECT COUNT(DISTINCT USER_ID) AS TOTAL_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
    )
    SELECT
        cd.MSG_COUNT, cd.SESS_COUNT, cu.ACTIVE_USERS,
        cd.SKILL_COUNT, cd.MCP_COUNT, cd.LIMIT_HITS,
        pd.MSG_COUNT    AS PREV_MSG,
        pd.SESS_COUNT   AS PREV_SESS,
        pu.ACTIVE_USERS AS PREV_USERS,
        pd.SKILL_COUNT  AS PREV_SKILL,
        pd.MCP_COUNT    AS PREV_MCP,
        t.TOTAL_USERS
    FROM cur_daily cd, cur_users cu, prev_daily pd, prev_users pu, tot t
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_timeline_data(team_id: str, days: int) -> pd.DataFrame:
    """日次推移（DAILY_SUMMARY）"""
    query = f"""
    SELECT
        SUMMARY_DATE           AS EVENT_DATE,
        MESSAGE_COUNT          AS MESSAGES,
        TOOL_EXECUTION_COUNT   AS TOOLS,
        SESSION_COUNT          AS SESSIONS,
        LIMIT_HIT_COUNT        AS LIMIT_HITS
    FROM {_L3}.DAILY_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND SUMMARY_DATE >= DATEADD('day', -{min(days, 90)}, CURRENT_DATE())
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_heatmap_data(team_id: str, days: int) -> pd.DataFrame:
    """時間帯×曜日ヒートマップ（USAGE_EVENTS — 時間粒度が必要）"""
    query = f"""
    SELECT
        DAYOFWEEK(EVENT_TIMESTAMP) AS DOW,
        HOUR(EVENT_TIMESTAMP)      AS HOUR_OF_DAY,
        COUNT(*)                   AS EVENT_COUNT
    FROM {_L2}.EVENTS
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
    """ユーザーランキング（USER_SUMMARY）"""
    query = f"""
    SELECT
        USER_ID,
        SPLIT_PART(USER_ID, '@', 1)    AS DISPLAY_NAME,
        SUM(SKILL_COUNT)               AS SKILL_COUNT,
        SUM(SUBAGENT_COUNT)            AS SUBAGENT_COUNT,
        SUM(MCP_COUNT)                 AS MCP_COUNT,
        SUM(COMMAND_COUNT)             AS COMMAND_COUNT,
        SUM(MESSAGE_COUNT)             AS MESSAGE_COUNT,
        SUM(SESSION_COUNT)             AS SESSION_COUNT,
        SUM(LIMIT_HIT_COUNT)           AS LIMIT_HITS,
        SUM(TOTAL_EVENTS)              AS TOTAL_COUNT,
        MAX(LAST_ACTIVE_AT)            AS LAST_ACTIVE,
        MIN(SUMMARY_DATE)              AS FIRST_ACTIVE
    FROM {_L3}.USER_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
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
    """ユーザー日次推移（USER_SUMMARY）"""
    safe_uid = user_id.replace("'", "''")
    query = f"""
    SELECT
        SUMMARY_DATE        AS EVENT_DATE,
        MESSAGE_COUNT       AS MESSAGES,
        SESSION_COUNT       AS SESSIONS,
        LIMIT_HIT_COUNT     AS LIMIT_HITS
    FROM {_L3}.USER_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND USER_ID = '{safe_uid}'
      AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_top_tools(team_id: str, user_id: str, days: int) -> pd.DataFrame:
    """ユーザー別Topツール（USAGE_EVENTS — ユーザー×ツール粒度が必要）"""
    safe_uid = user_id.replace("'", "''")
    query = f"""
    SELECT TOOL_NAME, COUNT(*) AS CNT
    FROM {_L2}.EVENTS
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
    """ツールランキング（TOOL_SUMMARY）"""
    query = f"""
    SELECT
        TOOL_NAME,
        SUM(EXECUTION_COUNT) AS TOTAL_COUNT,
        SUM(SUCCESS_COUNT)   AS SUCCESS_COUNT,
        ROUND(
            SUM(SUCCESS_COUNT)
            / NULLIF(SUM(EXECUTION_COUNT), 0) * 100, 1
        ) AS SUCCESS_RATE
    FROM {_L3}.TOOL_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
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
    """上位 5 ツールの日次トレンド（TOOL_SUMMARY）"""
    query = f"""
    WITH top_tools AS (
        SELECT TOOL_NAME
        FROM {_L3}.TOOL_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        GROUP BY TOOL_NAME
        ORDER BY SUM(EXECUTION_COUNT) DESC
        LIMIT 5
    )
    SELECT
        s.SUMMARY_DATE  AS EVENT_DATE,
        s.TOOL_NAME,
        s.EXECUTION_COUNT AS CNT
    FROM {_L3}.TOOL_SUMMARY s
    JOIN top_tools t ON s.TOOL_NAME = t.TOOL_NAME
    WHERE s.TEAM_ID = '{team_id}'
      AND s.SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ORDER BY 1, 2
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab4 セッション（USAGE_EVENTS — SESSION_ID 単位の計算が必要）
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
            MAX(CASE WHEN STOP_REASON = 'usage_limit' THEN 1 ELSE 0 END) AS is_limit,
            COALESCE(MAX(STOP_REASON), 'unknown') AS stop_reason
        FROM {_L2}.EVENTS
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
        COALESCE(STOP_REASON, 'unknown') AS STOP_REASON,
        COUNT(DISTINCT SESSION_ID)       AS SESSION_COUNT
    FROM {_L2}.EVENTS
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
    """時間帯別制限ヒット（USAGE_EVENTS — 時間粒度が必要）"""
    query = f"""
    SELECT
        HOUR(EVENT_TIMESTAMP) AS HOUR_OF_DAY,
        COUNT(*)              AS LIMIT_HITS
    FROM {_L2}.EVENTS
    WHERE TEAM_ID = '{team_id}'
      AND IS_USAGE_LIMIT = TRUE
      AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()

# =============================================================================
# Tab5 プロジェクト（USAGE_EVENTS — PROJECT_NAME 粒度が必要）
# =============================================================================

@st.cache_data(ttl=300)
def get_project_ranking(team_id: str, days: int, limit: int = 15) -> pd.DataFrame:
    query = f"""
    SELECT
        COALESCE(PROJECT_NAME, '(no project)') AS PROJECT_NAME,
        COUNT(*)                               AS EVENT_COUNT,
        COUNT(DISTINCT USER_ID)               AS USER_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MSG_COUNT,
        COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END)                 AS SKILL_COUNT,
        COUNT(CASE WHEN IS_MCP   = TRUE THEN 1 END)                 AS MCP_COUNT
    FROM {_L2}.EVENTS
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
    """月次アクティブ（DAILY_SUMMARY + USER_SUMMARY）"""
    query = f"""
    WITH monthly_counts AS (
        SELECT
            DATE_TRUNC('month', SUMMARY_DATE)::DATE AS MONTH,
            SUM(MESSAGE_COUNT)                      AS MESSAGES,
            SUM(SESSION_COUNT)                      AS SESSIONS
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
        GROUP BY 1
    ),
    monthly_users AS (
        SELECT
            DATE_TRUNC('month', SUMMARY_DATE)::DATE AS MONTH,
            COUNT(DISTINCT USER_ID)                 AS ACTIVE_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
        GROUP BY 1
    )
    SELECT
        u.MONTH,
        u.ACTIVE_USERS,
        c.SESSIONS,
        c.MESSAGES
    FROM monthly_users u
    JOIN monthly_counts c ON u.MONTH = c.MONTH
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_feature_adoption(team_id: str, days: int) -> pd.DataFrame:
    """機能普及率（USER_SUMMARY）"""
    query = f"""
    SELECT
        COUNT(DISTINCT USER_ID)                                            AS TOTAL_USERS,
        COUNT(DISTINCT CASE WHEN SUM_SKILL    > 0 THEN USER_ID END)       AS SKILL_USERS,
        COUNT(DISTINCT CASE WHEN SUM_MCP      > 0 THEN USER_ID END)       AS MCP_USERS,
        COUNT(DISTINCT CASE WHEN SUM_SUBAGENT > 0 THEN USER_ID END)       AS SUBAGENT_USERS,
        COUNT(DISTINCT CASE WHEN SUM_COMMAND  > 0 THEN USER_ID END)       AS COMMAND_USERS
    FROM (
        SELECT
            USER_ID,
            SUM(SKILL_COUNT)    AS SUM_SKILL,
            SUM(MCP_COUNT)      AS SUM_MCP,
            SUM(SUBAGENT_COUNT) AS SUM_SUBAGENT,
            SUM(COMMAND_COUNT)  AS SUM_COMMAND
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        GROUP BY USER_ID
    )
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


# =============================================================================
# Tab7 導入効果
# =============================================================================

@st.cache_data(ttl=300)
def get_roi_kpi(team_id: str, days: int) -> pd.DataFrame:
    """導入効果KPI（DAILY/USER/TOOL_SUMMARY 横断）"""
    query = f"""
    WITH cur AS (
        SELECT
            SUM(TOOL_EXECUTION_COUNT) AS TOOL_EXECS,
            SUM(MESSAGE_COUNT)        AS MSG_COUNT,
            SUM(SESSION_COUNT)        AS SESS_COUNT
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ),
    cur_users AS (
        SELECT
            COUNT(DISTINCT USER_ID) AS ACTIVE_USERS,
            SUM(TOTAL_EVENTS)       AS TOTAL_EVENTS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ),
    cur_feat AS (
        SELECT
            COUNT(DISTINCT USER_ID)                                  AS FEAT_TOTAL,
            COUNT(DISTINCT CASE WHEN SUM_SK  > 0 THEN USER_ID END)  AS SKILL_USERS,
            COUNT(DISTINCT CASE WHEN SUM_MCP > 0 THEN USER_ID END)  AS MCP_USERS,
            COUNT(DISTINCT CASE WHEN SUM_SA  > 0 THEN USER_ID END)  AS SA_USERS,
            COUNT(DISTINCT CASE WHEN SUM_CMD > 0 THEN USER_ID END)  AS CMD_USERS
        FROM (
            SELECT USER_ID,
                   SUM(SKILL_COUNT) AS SUM_SK, SUM(MCP_COUNT) AS SUM_MCP,
                   SUM(SUBAGENT_COUNT) AS SUM_SA, SUM(COMMAND_COUNT) AS SUM_CMD
            FROM {_L3}.USER_SUMMARY
            WHERE TEAM_ID = '{team_id}'
              AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
            GROUP BY USER_ID
        )
    ),
    cur_tools AS (
        SELECT
            SUM(SUCCESS_COUNT)   AS TOOL_SUCCESS,
            SUM(EXECUTION_COUNT) AS TOOL_TOTAL
        FROM {_L3}.TOOL_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    ),
    prev AS (
        SELECT SUM(TOOL_EXECUTION_COUNT) AS TOOL_EXECS
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
          AND SUMMARY_DATE <  DATEADD('day', -{days}, CURRENT_DATE())
    ),
    prev_users AS (
        SELECT
            COUNT(DISTINCT USER_ID) AS ACTIVE_USERS,
            SUM(TOTAL_EVENTS)       AS TOTAL_EVENTS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
          AND SUMMARY_DATE <  DATEADD('day', -{days}, CURRENT_DATE())
    ),
    prev_tools AS (
        SELECT
            SUM(SUCCESS_COUNT)   AS TOOL_SUCCESS,
            SUM(EXECUTION_COUNT) AS TOOL_TOTAL
        FROM {_L3}.TOOL_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
          AND SUMMARY_DATE <  DATEADD('day', -{days}, CURRENT_DATE())
    ),
    prev_feat AS (
        SELECT
            COUNT(DISTINCT USER_ID)                                  AS FEAT_TOTAL,
            COUNT(DISTINCT CASE WHEN SUM_SK  > 0 THEN USER_ID END)  AS SKILL_USERS,
            COUNT(DISTINCT CASE WHEN SUM_MCP > 0 THEN USER_ID END)  AS MCP_USERS,
            COUNT(DISTINCT CASE WHEN SUM_SA  > 0 THEN USER_ID END)  AS SA_USERS,
            COUNT(DISTINCT CASE WHEN SUM_CMD > 0 THEN USER_ID END)  AS CMD_USERS
        FROM (
            SELECT USER_ID,
                   SUM(SKILL_COUNT) AS SUM_SK, SUM(MCP_COUNT) AS SUM_MCP,
                   SUM(SUBAGENT_COUNT) AS SUM_SA, SUM(COMMAND_COUNT) AS SUM_CMD
            FROM {_L3}.USER_SUMMARY
            WHERE TEAM_ID = '{team_id}'
              AND SUMMARY_DATE >= DATEADD('day', -{days * 2}, CURRENT_DATE())
              AND SUMMARY_DATE <  DATEADD('day', -{days}, CURRENT_DATE())
            GROUP BY USER_ID
        )
    ),
    tot AS (
        SELECT COUNT(DISTINCT USER_ID) AS TOTAL_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
    )
    SELECT
        c.TOOL_EXECS, c.MSG_COUNT, c.SESS_COUNT,
        cu.ACTIVE_USERS, cu.TOTAL_EVENTS,
        cf.FEAT_TOTAL, cf.SKILL_USERS, cf.MCP_USERS, cf.SA_USERS, cf.CMD_USERS,
        ct.TOOL_SUCCESS, ct.TOOL_TOTAL,
        p.TOOL_EXECS      AS PREV_TOOL_EXECS,
        pu.ACTIVE_USERS   AS PREV_ACTIVE_USERS,
        pu.TOTAL_EVENTS   AS PREV_TOTAL_EVENTS,
        pt.TOOL_SUCCESS   AS PREV_TOOL_SUCCESS,
        pt.TOOL_TOTAL     AS PREV_TOOL_TOTAL,
        pf.FEAT_TOTAL     AS PREV_FEAT_TOTAL,
        pf.SKILL_USERS    AS PREV_SKILL_USERS,
        pf.MCP_USERS      AS PREV_MCP_USERS,
        pf.SA_USERS       AS PREV_SA_USERS,
        pf.CMD_USERS      AS PREV_CMD_USERS,
        tt.TOTAL_USERS
    FROM cur c, cur_users cu, cur_feat cf, cur_tools ct,
         prev p, prev_users pu, prev_tools pt, prev_feat pf, tot tt
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_productivity_trend(team_id: str, days: int) -> pd.DataFrame:
    """日次生産性トレンド（DAILY_SUMMARY + USER_SUMMARY）"""
    cap = min(days, 90)
    query = f"""
    WITH daily_tools AS (
        SELECT
            SUMMARY_DATE,
            SUM(TOOL_EXECUTION_COUNT) AS TOOL_EXECS,
            SUM(MESSAGE_COUNT)        AS MESSAGES,
            SUM(SESSION_COUNT)        AS SESSIONS
        FROM {_L3}.DAILY_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{cap}, CURRENT_DATE())
        GROUP BY SUMMARY_DATE
    ),
    daily_users AS (
        SELECT
            SUMMARY_DATE,
            COUNT(DISTINCT USER_ID) AS ACTIVE_USERS
        FROM {_L3}.USER_SUMMARY
        WHERE TEAM_ID = '{team_id}'
          AND SUMMARY_DATE >= DATEADD('day', -{cap}, CURRENT_DATE())
        GROUP BY SUMMARY_DATE
    )
    SELECT
        t.SUMMARY_DATE AS EVENT_DATE,
        t.TOOL_EXECS,
        t.MESSAGES,
        t.SESSIONS,
        u.ACTIVE_USERS,
        ROUND(t.TOOL_EXECS / NULLIF(u.ACTIVE_USERS, 0), 1) AS TOOLS_PER_USER,
        ROUND(t.MESSAGES  / NULLIF(u.ACTIVE_USERS, 0), 1)  AS MSGS_PER_USER
    FROM daily_tools t
    LEFT JOIN daily_users u ON t.SUMMARY_DATE = u.SUMMARY_DATE
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_efficiency(team_id: str, days: int) -> pd.DataFrame:
    """ユーザー効率マップ（USER_SUMMARY）"""
    query = f"""
    SELECT
        USER_ID,
        SPLIT_PART(USER_ID, '@', 1)  AS DISPLAY_NAME,
        SUM(MESSAGE_COUNT)            AS MESSAGES,
        SUM(SESSION_COUNT)            AS SESSIONS,
        SUM(TOTAL_EVENTS)             AS TOTAL_EVENTS,
        SUM(SKILL_COUNT)
          + SUM(MCP_COUNT)
          + SUM(SUBAGENT_COUNT)       AS ADVANCED_FEATURES
    FROM {_L3}.USER_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND SUMMARY_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
    GROUP BY USER_ID
    HAVING SUM(MESSAGE_COUNT) > 0
    ORDER BY TOTAL_EVENTS DESC
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_weekly_feature_mix(team_id: str, days: int) -> pd.DataFrame:
    """週次機能活用ミックス（DAILY_SUMMARY）"""
    cap = min(days, 90)
    query = f"""
    SELECT
        DATE_TRUNC('week', SUMMARY_DATE)::DATE AS WEEK_START,
        SUM(MESSAGE_COUNT)                      AS MESSAGES,
        SUM(SKILL_COUNT)                        AS SKILLS,
        SUM(MCP_COUNT)                          AS MCP,
        GREATEST(
            SUM(TOOL_EXECUTION_COUNT)
              - SUM(SKILL_COUNT)
              - SUM(MCP_COUNT), 0)              AS BASIC_TOOLS
    FROM {_L3}.DAILY_SUMMARY
    WHERE TEAM_ID = '{team_id}'
      AND SUMMARY_DATE >= DATEADD('day', -{cap}, CURRENT_DATE())
    GROUP BY 1
    ORDER BY 1
    """
    try:
        return get_session().sql(query).to_pandas()
    except Exception:
        return pd.DataFrame()
