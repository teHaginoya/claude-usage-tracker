-- ============================================================================
-- Claude Code Usage Tracker - データ取り込み SQL
--
-- パイプライン: Stage → LAYER1.RAW_EVENTS → LAYER2.EVENTS → LAYER3.*_SUMMARY
-- 前提: 01_create_tables.sql 実行済み
-- ============================================================================

USE WAREHOUSE CLAUDE_USAGE_WH;

-- ============================================================================
-- STEP 1: Stage → LAYER1.RAW_EVENTS
--
-- JSONL の各行を VARIANT としてそのまま保持。
-- ファイル名をメタデータとして記録。
--
-- 【手順】
--   1. PUT でローカルファイルをステージにアップロード:
--      PUT file://~/.claude/usage-tracker-logs/events-*.jsonl
--          @CLAUDE_USAGE_DB.LAYER1.CLAUDE_USAGE_INTERNAL_STAGE
--          AUTO_COMPRESS=TRUE;
--   2. 以下の COPY INTO を実行
-- ============================================================================

COPY INTO CLAUDE_USAGE_DB.LAYER1.RAW_EVENTS (RAW_DATA, SOURCE_FILE)
FROM (
    SELECT
        $1,
        METADATA$FILENAME
    FROM @CLAUDE_USAGE_DB.LAYER1.CLAUDE_USAGE_INTERNAL_STAGE
)
ON_ERROR = 'CONTINUE';


-- ============================================================================
-- STEP 2: LAYER1.RAW_EVENTS → LAYER2.EVENTS
--
-- カラム展開・型変換・重複排除して蓄積。
-- EVENT_HASH (SHA2) で MERGE するため、同一データの重複ロードを防止。
-- ============================================================================

MERGE INTO CLAUDE_USAGE_DB.LAYER2.EVENTS AS tgt
USING (
    SELECT
        SHA2(RAW_DATA::VARCHAR)                                       AS EVENT_HASH,
        RAW_DATA:event_type::VARCHAR                                  AS EVENT_TYPE,
        CONVERT_TIMEZONE('UTC', 'Asia/Tokyo',
            TRY_TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR))        AS EVENT_TIMESTAMP,
        RAW_DATA:user_id::VARCHAR                                     AS USER_ID,
        COALESCE(RAW_DATA:team_id::VARCHAR, 'default-team')           AS TEAM_ID,
        RAW_DATA:session_id::VARCHAR                                  AS SESSION_ID,
        RAW_DATA:project::VARCHAR                                     AS PROJECT_NAME,
        RAW_DATA:tool_name::VARCHAR                                   AS TOOL_NAME,
        RAW_DATA:success::BOOLEAN                                     AS TOOL_SUCCESS,
        RAW_DATA:output_length::INTEGER                               AS OUTPUT_LENGTH,
        RAW_DATA:error::VARCHAR                                       AS ERROR_MESSAGE,
        RAW_DATA:prompt_length::INTEGER                               AS PROMPT_LENGTH,
        COALESCE(RAW_DATA:categories:skill::BOOLEAN,          FALSE)  AS IS_SKILL,
        COALESCE(RAW_DATA:categories:subagent::BOOLEAN,       FALSE)  AS IS_SUBAGENT,
        COALESCE(RAW_DATA:categories:mcp::BOOLEAN,            FALSE)  AS IS_MCP,
        COALESCE(RAW_DATA:categories:command::BOOLEAN,        FALSE)  AS IS_COMMAND,
        COALESCE(RAW_DATA:categories:file_operation::BOOLEAN, FALSE)  AS IS_FILE_OPERATION,
        COALESCE(RAW_DATA:is_usage_limit::BOOLEAN,            FALSE)  AS IS_USAGE_LIMIT,
        RAW_DATA:stop_reason::VARCHAR                                 AS STOP_REASON,
        RAW_DATA                                                      AS RAW_DATA
    FROM CLAUDE_USAGE_DB.LAYER1.RAW_EVENTS
    WHERE RAW_DATA:event_type IS NOT NULL
) AS src
ON tgt.EVENT_HASH = src.EVENT_HASH
WHEN NOT MATCHED THEN INSERT (
    EVENT_HASH, EVENT_TYPE, EVENT_TIMESTAMP, USER_ID, TEAM_ID,
    SESSION_ID, PROJECT_NAME, TOOL_NAME, TOOL_SUCCESS, OUTPUT_LENGTH,
    ERROR_MESSAGE, PROMPT_LENGTH, IS_SKILL, IS_SUBAGENT, IS_MCP,
    IS_COMMAND, IS_FILE_OPERATION, IS_USAGE_LIMIT, STOP_REASON, RAW_DATA
) VALUES (
    src.EVENT_HASH, src.EVENT_TYPE, src.EVENT_TIMESTAMP, src.USER_ID, src.TEAM_ID,
    src.SESSION_ID, src.PROJECT_NAME, src.TOOL_NAME, src.TOOL_SUCCESS, src.OUTPUT_LENGTH,
    src.ERROR_MESSAGE, src.PROMPT_LENGTH, src.IS_SKILL, src.IS_SUBAGENT, src.IS_MCP,
    src.IS_COMMAND, src.IS_FILE_OPERATION, src.IS_USAGE_LIMIT, src.STOP_REASON, src.RAW_DATA
);


-- ============================================================================
-- STEP 3: LAYER2.EVENTS → LAYER3 サマリーテーブル
-- ============================================================================

-- 3-1. 日別サマリー
MERGE INTO CLAUDE_USAGE_DB.LAYER3.DAILY_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE              AS SUMMARY_DATE,
        TEAM_ID,
        COUNT(*)                                               AS TOTAL_EVENTS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESSION_COUNT,
        COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END) AS TOOL_EXECUTION_COUNT,
        COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)        AS MCP_COUNT,
        COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)        AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)        AS COMMAND_COUNT,
        COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)        AS SKILL_COUNT,
        COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END)     AS LIMIT_HIT_COUNT,
        COUNT(DISTINCT USER_ID)                                AS ACTIVE_USERS,
        ROUND(AVG(CASE WHEN TOOL_SUCCESS IS NOT NULL
            THEN CASE WHEN TOOL_SUCCESS THEN 1.0 ELSE 0.0 END END) * 100, 1) AS SUCCESS_RATE
    FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
    GROUP BY DATE_TRUNC('DAY', EVENT_TIMESTAMP), TEAM_ID
) AS src
ON tgt.SUMMARY_DATE = src.SUMMARY_DATE AND tgt.TEAM_ID = src.TEAM_ID
WHEN MATCHED THEN UPDATE SET
    TOTAL_EVENTS         = src.TOTAL_EVENTS,
    MESSAGE_COUNT        = src.MESSAGE_COUNT,
    SESSION_COUNT        = src.SESSION_COUNT,
    TOOL_EXECUTION_COUNT = src.TOOL_EXECUTION_COUNT,
    MCP_COUNT            = src.MCP_COUNT,
    SUBAGENT_COUNT       = src.SUBAGENT_COUNT,
    COMMAND_COUNT        = src.COMMAND_COUNT,
    SKILL_COUNT          = src.SKILL_COUNT,
    LIMIT_HIT_COUNT      = src.LIMIT_HIT_COUNT,
    ACTIVE_USERS         = src.ACTIVE_USERS,
    SUCCESS_RATE         = src.SUCCESS_RATE,
    UPDATED_AT           = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
    SUMMARY_DATE, TEAM_ID, TOTAL_EVENTS, MESSAGE_COUNT, SESSION_COUNT,
    TOOL_EXECUTION_COUNT, MCP_COUNT, SUBAGENT_COUNT, COMMAND_COUNT, SKILL_COUNT,
    LIMIT_HIT_COUNT, ACTIVE_USERS, SUCCESS_RATE
) VALUES (
    src.SUMMARY_DATE, src.TEAM_ID, src.TOTAL_EVENTS, src.MESSAGE_COUNT, src.SESSION_COUNT,
    src.TOOL_EXECUTION_COUNT, src.MCP_COUNT, src.SUBAGENT_COUNT, src.COMMAND_COUNT, src.SKILL_COUNT,
    src.LIMIT_HIT_COUNT, src.ACTIVE_USERS, src.SUCCESS_RATE
);

-- 3-2. ユーザー別日次サマリー
MERGE INTO CLAUDE_USAGE_DB.LAYER3.USER_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE              AS SUMMARY_DATE,
        USER_ID,
        TEAM_ID,
        COUNT(*)                                               AS TOTAL_EVENTS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESSION_COUNT,
        COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END) AS TOOL_EXECUTION_COUNT,
        COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)        AS MCP_COUNT,
        COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)        AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)        AS COMMAND_COUNT,
        COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)        AS SKILL_COUNT,
        COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END)     AS LIMIT_HIT_COUNT,
        MAX(EVENT_TIMESTAMP)                                   AS LAST_ACTIVE_AT
    FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
    GROUP BY DATE_TRUNC('DAY', EVENT_TIMESTAMP), USER_ID, TEAM_ID
) AS src
ON  tgt.SUMMARY_DATE = src.SUMMARY_DATE
AND tgt.USER_ID      = src.USER_ID
AND tgt.TEAM_ID      = src.TEAM_ID
WHEN MATCHED THEN UPDATE SET
    TOTAL_EVENTS         = src.TOTAL_EVENTS,
    MESSAGE_COUNT        = src.MESSAGE_COUNT,
    SESSION_COUNT        = src.SESSION_COUNT,
    TOOL_EXECUTION_COUNT = src.TOOL_EXECUTION_COUNT,
    MCP_COUNT            = src.MCP_COUNT,
    SUBAGENT_COUNT       = src.SUBAGENT_COUNT,
    COMMAND_COUNT        = src.COMMAND_COUNT,
    SKILL_COUNT          = src.SKILL_COUNT,
    LIMIT_HIT_COUNT      = src.LIMIT_HIT_COUNT,
    LAST_ACTIVE_AT       = src.LAST_ACTIVE_AT,
    UPDATED_AT           = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
    SUMMARY_DATE, USER_ID, TEAM_ID, TOTAL_EVENTS, MESSAGE_COUNT,
    SESSION_COUNT, TOOL_EXECUTION_COUNT, MCP_COUNT, SUBAGENT_COUNT,
    COMMAND_COUNT, SKILL_COUNT, LIMIT_HIT_COUNT, LAST_ACTIVE_AT
) VALUES (
    src.SUMMARY_DATE, src.USER_ID, src.TEAM_ID, src.TOTAL_EVENTS, src.MESSAGE_COUNT,
    src.SESSION_COUNT, src.TOOL_EXECUTION_COUNT, src.MCP_COUNT, src.SUBAGENT_COUNT,
    src.COMMAND_COUNT, src.SKILL_COUNT, src.LIMIT_HIT_COUNT, src.LAST_ACTIVE_AT
);

-- 3-3. ツール別日次サマリー
MERGE INTO CLAUDE_USAGE_DB.LAYER3.TOOL_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE  AS SUMMARY_DATE,
        TEAM_ID,
        TOOL_NAME,
        COUNT(*)                                           AS EXECUTION_COUNT,
        COUNT(CASE WHEN TOOL_SUCCESS = TRUE  THEN 1 END)  AS SUCCESS_COUNT,
        COUNT(CASE WHEN TOOL_SUCCESS = FALSE THEN 1 END)  AS FAILURE_COUNT
    FROM CLAUDE_USAGE_DB.LAYER2.EVENTS
    WHERE TOOL_NAME IS NOT NULL
    GROUP BY DATE_TRUNC('DAY', EVENT_TIMESTAMP), TEAM_ID, TOOL_NAME
) AS src
ON  tgt.SUMMARY_DATE = src.SUMMARY_DATE
AND tgt.TEAM_ID      = src.TEAM_ID
AND tgt.TOOL_NAME    = src.TOOL_NAME
WHEN MATCHED THEN UPDATE SET
    EXECUTION_COUNT = src.EXECUTION_COUNT,
    SUCCESS_COUNT   = src.SUCCESS_COUNT,
    FAILURE_COUNT   = src.FAILURE_COUNT,
    UPDATED_AT      = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
    SUMMARY_DATE, TEAM_ID, TOOL_NAME, EXECUTION_COUNT, SUCCESS_COUNT, FAILURE_COUNT
) VALUES (
    src.SUMMARY_DATE, src.TEAM_ID, src.TOOL_NAME,
    src.EXECUTION_COUNT, src.SUCCESS_COUNT, src.FAILURE_COUNT
);

-- ============================================================================
-- 確認クエリ
-- ============================================================================
SELECT 'LAYER1.RAW_EVENTS'    AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM CLAUDE_USAGE_DB.LAYER1.RAW_EVENTS  UNION ALL
SELECT 'LAYER2.EVENTS',                      COUNT(*) FROM CLAUDE_USAGE_DB.LAYER2.EVENTS                  UNION ALL
SELECT 'LAYER3.DAILY_SUMMARY',               COUNT(*) FROM CLAUDE_USAGE_DB.LAYER3.DAILY_SUMMARY           UNION ALL
SELECT 'LAYER3.USER_SUMMARY',                COUNT(*) FROM CLAUDE_USAGE_DB.LAYER3.USER_SUMMARY            UNION ALL
SELECT 'LAYER3.TOOL_SUMMARY',                COUNT(*) FROM CLAUDE_USAGE_DB.LAYER3.TOOL_SUMMARY;
