-- ============================================================================
-- Claude Code Usage Tracker - 分析用テーブル・ビュー構築
--
-- データソース: CLAUDE_USAGE_DB.RAWDATA.CLAUDE_LOG_DATA（既存）
-- 実行前提   : 01_create_tables.sql 実行済み（WH / LAYER3 schema が存在すること）
--
-- 作成オブジェクト:
--   FACT_EVENTS       クリーン・重複排除・正規化済みファクトテーブル
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


-- ============================================================================
-- STEP 1: FACT_EVENTS（クリーン・正規化・重複排除ファクトテーブル）
--
-- RAWDATA.CLAUDE_LOG_DATA との列名マッピング:
--   TIMESTAMP            → EVENT_TIMESTAMP
--   PROJECT              → PROJECT_NAME
--   IAM_USER / USER_ID   → USER_ID（IAM_USER 優先で人名に統一）
--   SUCCESS              → TOOL_SUCCESS
--   TOOL_RESPONSE_LENGTH → OUTPUT_LENGTH
--   CATEGORIES（VARIANT）→ IS_SKILL / IS_MCP / IS_COMMAND 等の BOOLEAN 列に展開
-- ============================================================================
CREATE OR REPLACE TABLE FACT_EVENTS AS
SELECT
    -- ── 基本フィールド ─────────────────────────────────────────────────
    EVENT_TYPE,
    TIMESTAMP::TIMESTAMP_NTZ                                         AS EVENT_TIMESTAMP,
    COALESCE(NULLIF(TRIM(IAM_USER), ''), USER_ID)                   AS USER_ID,
    TEAM_ID,
    COALESCE(NULLIF(TRIM(PROJECT), ''), 'unknown')                  AS PROJECT_NAME,
    SESSION_ID,
    PERMISSION_MODE,

    -- ── ツール情報 ────────────────────────────────────────────────────
    TOOL_NAME,
    TOOL_USE_ID,
    SUCCESS                                                          AS TOOL_SUCCESS,
    TOOL_RESPONSE_LENGTH                                             AS OUTPUT_LENGTH,
    PROMPT_LENGTH,
    TOOL_INPUT_LENGTH,
    STOP_HOOK_ACTIVE,

    -- ── カテゴリフラグ（CATEGORIES VARIANT から展開） ──────────────────
    COALESCE(CATEGORIES:skill::BOOLEAN,          FALSE)             AS IS_SKILL,
    COALESCE(CATEGORIES:subagent::BOOLEAN,       FALSE)             AS IS_SUBAGENT,
    COALESCE(CATEGORIES:mcp::BOOLEAN,            FALSE)             AS IS_MCP,
    COALESCE(CATEGORIES:command::BOOLEAN,        FALSE)             AS IS_COMMAND,
    COALESCE(CATEGORIES:file_operation::BOOLEAN, FALSE)             AS IS_FILE_OPERATION,
    COALESCE(CATEGORIES:web::BOOLEAN,            FALSE)             AS IS_WEB,
    COALESCE(CATEGORIES:code_execution::BOOLEAN, FALSE)             AS IS_CODE_EXECUTION,

    -- ── 利用制限（現データには含まれない。今後の拡張用に列を確保） ──────
    FALSE                                                           AS IS_USAGE_LIMIT,
    NULL::VARCHAR(50)                                               AS STOP_REASON,

    -- ── メタデータ ───────────────────────────────────────────────────
    METADATA,
    CREATED_DATE

FROM CLAUDE_USAGE_DB.RAWDATA.CLAUDE_LOG_DATA

-- 重複排除: 同一 (EVENT_TYPE / TIMESTAMP / SESSION_ID / TOOL_USE_ID) の重複行を除去
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY
        EVENT_TYPE,
        TIMESTAMP,
        COALESCE(SESSION_ID,  ''),
        COALESCE(TOOL_USE_ID, '')
    ORDER BY CREATED_DATE
) = 1;

-- クラスタリング（TEAM_ID + 日付でフィルタするクエリが大多数）
ALTER TABLE FACT_EVENTS
    CLUSTER BY (TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP));

-- 確認
SELECT
    COUNT(*)                                      AS FACT_ROWS,
    COUNT(DISTINCT USER_ID)                       AS USERS,
    COUNT(DISTINCT SESSION_ID)                    AS SESSIONS,
    MIN(EVENT_TIMESTAMP)::DATE                    AS EARLIEST_DATE,
    MAX(EVENT_TIMESTAMP)::DATE                    AS LATEST_DATE
FROM FACT_EVENTS;


-- ============================================================================
-- STEP 2: 分析ビュー（タブ別）
-- ============================================================================

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
    COUNT(CASE WHEN IS_WEB              = TRUE THEN 1 END)            AS WEB_COUNT,
    COUNT(CASE WHEN IS_CODE_EXECUTION   = TRUE THEN 1 END)            AS CODE_EXEC_COUNT,
    COUNT(CASE WHEN IS_FILE_OPERATION   = TRUE THEN 1 END)            AS FILE_OP_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT      = TRUE THEN 1 END)            AS LIMIT_HIT_COUNT,
    COUNT(DISTINCT USER_ID)                                            AS ACTIVE_USERS
FROM FACT_EVENTS
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
    COUNT(CASE WHEN IS_WEB            = TRUE THEN 1 END)              AS WEB_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT    = TRUE THEN 1 END)              AS LIMIT_HIT_COUNT,
    MAX(EVENT_TIMESTAMP)                                               AS LAST_ACTIVE_AT,
    MIN(DATE_TRUNC('DAY', EVENT_TIMESTAMP))::DATE                     AS FIRST_ACTIVE_DATE
FROM FACT_EVENTS
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
    AVG(OUTPUT_LENGTH)                                                 AS AVG_OUTPUT_LENGTH,
    AVG(TOOL_INPUT_LENGTH)                                             AS AVG_INPUT_LENGTH
FROM FACT_EVENTS
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
    COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END)       AS TOOL_COUNT,
    MAX(CASE WHEN STOP_HOOK_ACTIVE = TRUE THEN 1 ELSE 0 END)          AS HAD_STOP_HOOK
FROM FACT_EVENTS
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
FROM FACT_EVENTS
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
FROM FACT_EVENTS
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
    COUNT(DISTINCT CASE WHEN IS_COMMAND        = TRUE THEN USER_ID END)       AS COMMAND_USERS,
    COUNT(DISTINCT CASE WHEN IS_WEB            = TRUE THEN USER_ID END)       AS WEB_USERS,
    COUNT(DISTINCT CASE WHEN IS_CODE_EXECUTION = TRUE THEN USER_ID END)       AS CODE_EXEC_USERS
FROM FACT_EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP);


-- ============================================================================
-- 完了確認
-- ============================================================================
SELECT 'FACT_EVENTS',     COUNT(*) FROM FACT_EVENTS
UNION ALL
SELECT 'V_OVERVIEW_DAILY',  COUNT(*) FROM V_OVERVIEW_DAILY
UNION ALL
SELECT 'V_USER_STATS',      COUNT(*) FROM V_USER_STATS
UNION ALL
SELECT 'V_TOOL_STATS',      COUNT(*) FROM V_TOOL_STATS;

SELECT '完了！ SiS アプリのデータソースは FACT_EVENTS テーブルです。' AS STATUS;
