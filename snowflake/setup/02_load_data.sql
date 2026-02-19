-- ============================================================================
-- Claude Code Usage Tracker - データ取り込み SQL
-- 前提: 01_create_tables.sql 実行済み
-- ============================================================================

USE WAREHOUSE CLAUDE_USAGE_WH;
USE DATABASE  CLAUDE_USAGE_DB;
USE SCHEMA    USAGE_TRACKING;

-- ============================================================================
-- パターン A: ローカル JSONL ファイルを内部ステージ経由で取り込む（推奨）
--
-- send_event.py が生成するファイル:
--   ~/.claude/usage-tracker-logs/events-YYYY-MM-DD.jsonl
--
-- 【手順】
--   1. SnowSQL または Snowflake CLI でアップロード:
--      PUT file://~/.claude/usage-tracker-logs/events-*.jsonl
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_USAGE_INTERNAL_STAGE
--          AUTO_COMPRESS=TRUE;
--   2. 以下の COPY INTO を実行
-- ============================================================================

COPY INTO USAGE_EVENTS (
    EVENT_TYPE,
    EVENT_TIMESTAMP,
    USER_ID,
    TEAM_ID,
    SESSION_ID,
    PROJECT_NAME,
    TOOL_NAME,
    TOOL_SUCCESS,
    OUTPUT_LENGTH,
    ERROR_MESSAGE,
    PROMPT_LENGTH,
    IS_SKILL,
    IS_SUBAGENT,
    IS_MCP,
    IS_COMMAND,
    IS_FILE_OPERATION,
    IS_USAGE_LIMIT,
    STOP_REASON,
    METADATA
)
FROM (
    SELECT
        -- 基本フィールド
        $1:event_type::VARCHAR,
        TRY_TO_TIMESTAMP_NTZ($1:timestamp::VARCHAR),
        $1:user_id::VARCHAR,
        COALESCE($1:team_id::VARCHAR, 'default-team'),
        $1:session_id::VARCHAR,
        $1:project::VARCHAR,                                    -- send_event.py の "project" キー

        -- ツール情報
        $1:tool_name::VARCHAR,
        $1:success::BOOLEAN,
        $1:output_length::INTEGER,
        $1:error::VARCHAR,
        $1:prompt_length::INTEGER,

        -- カテゴリフラグ（send_event.py の categories 配下）
        COALESCE($1:categories:skill::BOOLEAN,          FALSE),
        COALESCE($1:categories:subagent::BOOLEAN,       FALSE),
        COALESCE($1:categories:mcp::BOOLEAN,            FALSE),
        COALESCE($1:categories:command::BOOLEAN,        FALSE),
        COALESCE($1:categories:file_operation::BOOLEAN, FALSE),

        -- 利用上限・停止理由（root フィールド）
        COALESCE($1:is_usage_limit::BOOLEAN,            FALSE), -- Notification イベントで TRUE
        $1:stop_reason::VARCHAR,                                -- Stop イベント: normal/usage_limit/unknown

        -- 全ペイロードを VARIANT として保持
        $1::VARIANT

    FROM @CLAUDE_USAGE_INTERNAL_STAGE
)
ON_ERROR = 'CONTINUE';

-- ============================================================================
-- パターン B: S3 外部ステージ経由（サーバー → S3 → Snowflake の場合）
-- ============================================================================

/*
-- S3 外部ステージの作成（認証情報は環境に合わせて設定）
CREATE OR REPLACE STAGE CLAUDE_USAGE_S3_STAGE
    URL         = 's3://your-bucket-name/claude-usage-logs/'
    CREDENTIALS = (
        AWS_KEY_ID     = 'YOUR_AWS_ACCESS_KEY'
        AWS_SECRET_KEY = 'YOUR_AWS_SECRET_KEY'
    )
    FILE_FORMAT = (
        TYPE              = 'JSON'
        STRIP_OUTER_ARRAY = FALSE
    );

-- S3 ステージからのロード（カラムマッピングは パターン A と同一）
COPY INTO USAGE_EVENTS (
    EVENT_TYPE, EVENT_TIMESTAMP, USER_ID, TEAM_ID, SESSION_ID,
    PROJECT_NAME, TOOL_NAME, TOOL_SUCCESS, OUTPUT_LENGTH, ERROR_MESSAGE,
    PROMPT_LENGTH, IS_SKILL, IS_SUBAGENT, IS_MCP, IS_COMMAND, IS_FILE_OPERATION,
    IS_USAGE_LIMIT, STOP_REASON, METADATA
)
FROM (
    SELECT
        $1:event_type::VARCHAR,
        TRY_TO_TIMESTAMP_NTZ($1:timestamp::VARCHAR),
        $1:user_id::VARCHAR,
        COALESCE($1:team_id::VARCHAR, 'default-team'),
        $1:session_id::VARCHAR,
        $1:project::VARCHAR,
        $1:tool_name::VARCHAR,
        $1:success::BOOLEAN,
        $1:output_length::INTEGER,
        $1:error::VARCHAR,
        $1:prompt_length::INTEGER,
        COALESCE($1:categories:skill::BOOLEAN,          FALSE),
        COALESCE($1:categories:subagent::BOOLEAN,       FALSE),
        COALESCE($1:categories:mcp::BOOLEAN,            FALSE),
        COALESCE($1:categories:command::BOOLEAN,        FALSE),
        COALESCE($1:categories:file_operation::BOOLEAN, FALSE),
        COALESCE($1:is_usage_limit::BOOLEAN,            FALSE),
        $1:stop_reason::VARCHAR,
        $1::VARIANT
    FROM @CLAUDE_USAGE_S3_STAGE
)
ON_ERROR = 'CONTINUE';
*/

-- ============================================================================
-- パターン C: TROCCO 経由（S3 → Snowflake の ETL ツール）
-- ============================================================================
-- TROCCO の設定：
-- ソース      : S3 (JSONL)
-- デスティネーション : Snowflake (CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS)
--
-- カラムマッピング:
--   event_type                    → EVENT_TYPE
--   timestamp                     → EVENT_TIMESTAMP
--   user_id                       → USER_ID
--   team_id                       → TEAM_ID
--   session_id                    → SESSION_ID
--   project                       → PROJECT_NAME
--   tool_name                     → TOOL_NAME
--   success                       → TOOL_SUCCESS
--   output_length                 → OUTPUT_LENGTH
--   error                         → ERROR_MESSAGE
--   prompt_length                 → PROMPT_LENGTH
--   categories.skill              → IS_SKILL
--   categories.subagent           → IS_SUBAGENT
--   categories.mcp                → IS_MCP
--   categories.command            → IS_COMMAND
--   categories.file_operation     → IS_FILE_OPERATION
--   is_usage_limit                → IS_USAGE_LIMIT
--   stop_reason                   → STOP_REASON
--   (全体を VARIANT に変換)       → METADATA

-- ============================================================================
-- サマリーテーブルの更新（日次バッチ or 手動実行）
-- ============================================================================

-- 日別サマリー（MERGE で重複なし更新）
MERGE INTO DAILY_SUMMARY AS tgt
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
    FROM USAGE_EVENTS
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

-- ============================================================================
-- 確認クエリ
-- ============================================================================
SELECT 'USAGE_EVENTS'  AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM USAGE_EVENTS  UNION ALL
SELECT 'DAILY_SUMMARY',                COUNT(*) FROM DAILY_SUMMARY             UNION ALL
SELECT 'USER_SUMMARY',                 COUNT(*) FROM USER_SUMMARY              UNION ALL
SELECT 'TOOL_SUMMARY',                 COUNT(*) FROM TOOL_SUMMARY;

SELECT * FROM USAGE_EVENTS ORDER BY EVENT_TIMESTAMP DESC LIMIT 10;
