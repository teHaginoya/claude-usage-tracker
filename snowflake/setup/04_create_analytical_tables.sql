-- ============================================================================
-- Claude Code Usage Tracker - 分析用ビュー構築
--
-- データソース: CLAUDE_USAGE_DB.LAYER2.EVENTS（02_load_data.sql で蓄積済み）
-- 実行前提   : 01_create_tables.sql, 02_load_data.sql 実行済み
--
-- 作成オブジェクト (LAYER3):
--   V_OVERVIEW_DAILY  Tab1 日次KPI
--   V_USER_STATS      Tab2 ユーザー別統計
--   V_TOOL_STATS      Tab3 ツール別統計
--   V_SESSION_STATS   Tab4 セッション別統計
--   V_PROJECT_STATS   Tab5 プロジェクト別統計
--   V_MONTHLY_ACTIVE  Tab6 月次普及状況
--   V_FEATURE_ADOPTION Tab6 機能別採用率
-- ============================================================================

USE WAREHOUSE CLAUDE_USAGE_WH;
USE DATABASE  CLAUDE_USAGE_DB;
USE SCHEMA    LAYER3;


-- ── Tab 1: 概要 ─────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_OVERVIEW_DAILY AS
SELECT
    TEAM_ID,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE                          AS EVENT_DATE,
    COUNT(*)                                                           AS TOTAL_EVENTS,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit'  THEN 1 END)      AS MESSAGE_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'      THEN 1 END)      AS SESSION_COUNT,
    COUNT(CASE WHEN TOOL_NAME IS NOT NULL            THEN 1 END)      AS TOOL_COUNT,
    COUNT(CASE WHEN IS_MCP              = TRUE THEN 1 END)            AS MCP_COUNT,
    COUNT(CASE WHEN IS_SUBAGENT         = TRUE THEN 1 END)            AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_COMMAND          = TRUE THEN 1 END)            AS COMMAND_COUNT,
    COUNT(CASE WHEN IS_SKILL            = TRUE THEN 1 END)            AS SKILL_COUNT,
    COUNT(CASE WHEN IS_FILE_OPERATION   = TRUE THEN 1 END)            AS FILE_OP_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT      = TRUE THEN 1 END)            AS LIMIT_HIT_COUNT,
    COUNT(DISTINCT USER_ID)                                            AS ACTIVE_USERS
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP);


-- ── Tab 2: ユーザー ──────────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_USER_STATS AS
SELECT
    USER_ID,
    TEAM_ID,
    COUNT(*)                                                           AS TOTAL_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit'  THEN 1 END)      AS MESSAGE_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'      THEN 1 END)      AS SESSION_COUNT,
    COUNT(CASE WHEN IS_SKILL          = TRUE THEN 1 END)              AS SKILL_COUNT,
    COUNT(CASE WHEN IS_SUBAGENT       = TRUE THEN 1 END)              AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_MCP            = TRUE THEN 1 END)              AS MCP_COUNT,
    COUNT(CASE WHEN IS_COMMAND        = TRUE THEN 1 END)              AS COMMAND_COUNT,
    COUNT(CASE WHEN IS_FILE_OPERATION = TRUE THEN 1 END)              AS FILE_OP_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT    = TRUE THEN 1 END)              AS LIMIT_HIT_COUNT,
    MAX(EVENT_TIMESTAMP)                                               AS LAST_ACTIVE_AT,
    MIN(DATE_TRUNC('DAY', EVENT_TIMESTAMP))::DATE                     AS FIRST_ACTIVE_DATE
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY USER_ID, TEAM_ID;


-- ── Tab 3: ツール ────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_TOOL_STATS AS
SELECT
    TEAM_ID,
    TOOL_NAME,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE                          AS EVENT_DATE,
    COUNT(*)                                                           AS EXECUTION_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = TRUE  THEN 1 END)                  AS SUCCESS_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = FALSE THEN 1 END)                  AS FAILURE_COUNT,
    ROUND(
        COUNT(CASE WHEN TOOL_SUCCESS = TRUE THEN 1 END)
        / NULLIF(COUNT(*), 0) * 100, 1
    )                                                                  AS SUCCESS_RATE,
    AVG(OUTPUT_LENGTH)                                                 AS AVG_OUTPUT_LENGTH
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
WHERE TOOL_NAME IS NOT NULL
GROUP BY TEAM_ID, TOOL_NAME, DATE_TRUNC('DAY', EVENT_TIMESTAMP);


-- ── Tab 4: セッション ────────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_SESSION_STATS AS
SELECT
    SESSION_ID,
    USER_ID,
    TEAM_ID,
    MIN(EVENT_TIMESTAMP)                                               AS SESSION_START,
    MAX(EVENT_TIMESTAMP)                                               AS SESSION_END,
    DATEDIFF('minute',
        MIN(EVENT_TIMESTAMP),
        MAX(EVENT_TIMESTAMP))                                          AS DURATION_MIN,
    COUNT(*)                                                           AS EVENT_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)       AS MESSAGE_COUNT,
    COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END)       AS TOOL_COUNT
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY SESSION_ID, USER_ID, TEAM_ID;


-- ── Tab 5: プロジェクト ──────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_PROJECT_STATS AS
SELECT
    TEAM_ID,
    COALESCE(NULLIF(PROJECT_NAME, ''), '(no project)')                AS PROJECT_NAME,
    COUNT(*)                                                           AS EVENT_COUNT,
    COUNT(DISTINCT USER_ID)                                            AS USER_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit'  THEN 1 END)      AS MSG_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'      THEN 1 END)      AS SESSION_COUNT,
    COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)                    AS SKILL_COUNT,
    COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)                    AS MCP_COUNT,
    COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)                    AS COMMAND_COUNT,
    MAX(EVENT_TIMESTAMP)                                               AS LAST_ACTIVE_AT
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY TEAM_ID, COALESCE(NULLIF(PROJECT_NAME, ''), '(no project)');


-- ── Tab 6: 普及（月次） ──────────────────────────────────────────────────
CREATE OR REPLACE VIEW V_MONTHLY_ACTIVE AS
SELECT
    TEAM_ID,
    DATE_TRUNC('MONTH', EVENT_TIMESTAMP)::DATE                        AS MONTH,
    COUNT(DISTINCT USER_ID)                                            AS ACTIVE_USERS,
    COUNT(DISTINCT SESSION_ID)                                         AS SESSIONS,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END)       AS MESSAGES,
    COUNT(*)                                                           AS TOTAL_EVENTS
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('MONTH', EVENT_TIMESTAMP);


-- ── Tab 6: 普及（機能別採用率） ──────────────────────────────────────────
CREATE OR REPLACE VIEW V_FEATURE_ADOPTION AS
SELECT
    TEAM_ID,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE                                  AS EVENT_DATE,
    COUNT(DISTINCT USER_ID)                                                    AS TOTAL_USERS,
    COUNT(DISTINCT CASE WHEN IS_SKILL          = TRUE THEN USER_ID END)       AS SKILL_USERS,
    COUNT(DISTINCT CASE WHEN IS_MCP            = TRUE THEN USER_ID END)       AS MCP_USERS,
    COUNT(DISTINCT CASE WHEN IS_SUBAGENT       = TRUE THEN USER_ID END)       AS SUBAGENT_USERS,
    COUNT(DISTINCT CASE WHEN IS_COMMAND        = TRUE THEN USER_ID END)       AS COMMAND_USERS
FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP);


-- ============================================================================
-- 完了確認
-- ============================================================================
SELECT 'LAYER2.EVENTS',     COUNT(*) FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
UNION ALL
SELECT 'V_OVERVIEW_DAILY',  COUNT(*) FROM V_OVERVIEW_DAILY
UNION ALL
SELECT 'V_USER_STATS',      COUNT(*) FROM V_USER_STATS
UNION ALL
SELECT 'V_TOOL_STATS',      COUNT(*) FROM V_TOOL_STATS;
