-- ============================================================================
-- Claude Code Usage Tracker - データ取り込み用SQL
-- ============================================================================
-- このファイルは、S3やTROCCOからデータを取り込む際に使用します

USE DATABASE CLAUDE_USAGE_DB;
USE SCHEMA USAGE_TRACKING;

-- ============================================================================
-- パターン1: TROCCO経由でJSONデータを取り込む場合
-- ============================================================================
-- TROCCOでS3からSnowflakeに転送する際、以下のマッピングを設定してください
--
-- 【TROCCOの設定】
-- ソース: S3 (JSONLファイル)
-- デスティネーション: Snowflake (USAGE_EVENTS テーブル)
--
-- 【カラムマッピング】
-- event_type       → EVENT_TYPE
-- timestamp        → EVENT_TIMESTAMP
-- user_id          → USER_ID
-- team_id          → TEAM_ID
-- project          → PROJECT_NAME
-- session_id       → SESSION_ID
-- tool_name        → TOOL_NAME
-- success          → TOOL_SUCCESS
-- output_length    → OUTPUT_LENGTH
-- error            → ERROR_MESSAGE
-- categories.skill → IS_SKILL
-- categories.subagent → IS_SUBAGENT
-- categories.mcp   → IS_MCP
-- categories.command → IS_COMMAND
-- categories.file_operation → IS_FILE_OPERATION
-- prompt_length    → PROMPT_LENGTH
-- metadata         → METADATA (VARIANT型)

-- ============================================================================
-- パターン2: S3から直接取り込む場合（ステージ経由）
-- ============================================================================

-- ステージの作成（S3バケットを指定）
-- ※ 実際のバケット名と認証情報に置き換えてください
/*
CREATE OR REPLACE STAGE CLAUDE_USAGE_STAGE
    URL = 's3://your-bucket-name/claude-usage-logs/'
    CREDENTIALS = (
        AWS_KEY_ID = 'YOUR_AWS_ACCESS_KEY'
        AWS_SECRET_KEY = 'YOUR_AWS_SECRET_KEY'
    )
    FILE_FORMAT = (
        TYPE = 'JSON'
        STRIP_OUTER_ARRAY = TRUE
    );
*/

-- ステージからデータをコピー
/*
COPY INTO USAGE_EVENTS (
    EVENT_TYPE,
    EVENT_TIMESTAMP,
    USER_ID,
    TEAM_ID,
    PROJECT_NAME,
    SESSION_ID,
    TOOL_NAME,
    TOOL_SUCCESS,
    OUTPUT_LENGTH,
    ERROR_MESSAGE,
    IS_SKILL,
    IS_SUBAGENT,
    IS_MCP,
    IS_COMMAND,
    IS_FILE_OPERATION,
    PROMPT_LENGTH,
    METADATA
)
FROM (
    SELECT
        $1:event_type::VARCHAR,
        $1:timestamp::TIMESTAMP_NTZ,
        $1:user_id::VARCHAR,
        $1:team_id::VARCHAR,
        $1:project::VARCHAR,
        $1:session_id::VARCHAR,
        $1:tool_name::VARCHAR,
        $1:success::BOOLEAN,
        $1:output_length::INTEGER,
        $1:error::VARCHAR,
        $1:categories:skill::BOOLEAN,
        $1:categories:subagent::BOOLEAN,
        $1:categories:mcp::BOOLEAN,
        $1:categories:command::BOOLEAN,
        $1:categories:file_operation::BOOLEAN,
        $1:prompt_length::INTEGER,
        $1:metadata::VARIANT
    FROM @CLAUDE_USAGE_STAGE
)
FILE_FORMAT = (TYPE = 'JSON')
ON_ERROR = 'CONTINUE';
*/

-- ============================================================================
-- パターン3: 内部ステージ経由（ファイルをアップロードする場合）
-- ============================================================================

-- 内部ステージの作成
CREATE OR REPLACE STAGE CLAUDE_USAGE_INTERNAL_STAGE
    FILE_FORMAT = (
        TYPE = 'JSON'
        STRIP_OUTER_ARRAY = FALSE
    );

-- ファイルをアップロード（SnowSQLから実行）
-- PUT file://C:/Users/iftc/.claude/usage-tracker-logs/events-*.jsonl @CLAUDE_USAGE_INTERNAL_STAGE;

-- アップロードしたファイルからデータをコピー
/*
COPY INTO USAGE_EVENTS (
    EVENT_TYPE,
    EVENT_TIMESTAMP,
    USER_ID,
    TEAM_ID,
    PROJECT_NAME,
    SESSION_ID,
    TOOL_NAME,
    TOOL_SUCCESS,
    OUTPUT_LENGTH,
    ERROR_MESSAGE,
    IS_SKILL,
    IS_SUBAGENT,
    IS_MCP,
    IS_COMMAND,
    IS_FILE_OPERATION,
    PROMPT_LENGTH,
    METADATA
)
FROM (
    SELECT
        $1:event_type::VARCHAR,
        TRY_TO_TIMESTAMP_NTZ($1:timestamp::VARCHAR),
        $1:user_id::VARCHAR,
        $1:team_id::VARCHAR,
        $1:project::VARCHAR,
        $1:session_id::VARCHAR,
        $1:tool_name::VARCHAR,
        $1:success::BOOLEAN,
        $1:output_length::INTEGER,
        $1:error::VARCHAR,
        COALESCE($1:categories:skill::BOOLEAN, FALSE),
        COALESCE($1:categories:subagent::BOOLEAN, FALSE),
        COALESCE($1:categories:mcp::BOOLEAN, FALSE),
        COALESCE($1:categories:command::BOOLEAN, FALSE),
        COALESCE($1:categories:file_operation::BOOLEAN, FALSE),
        $1:prompt_length::INTEGER,
        $1:metadata::VARIANT
    FROM @CLAUDE_USAGE_INTERNAL_STAGE
)
ON_ERROR = 'CONTINUE';
*/

-- ============================================================================
-- サマリーテーブルの更新（日次バッチ用）
-- ============================================================================

-- 日別サマリーの更新
MERGE INTO DAILY_SUMMARY AS target
USING (
    SELECT 
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE AS SUMMARY_DATE,
        TEAM_ID,
        COUNT(*) AS TOTAL_EVENTS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END) AS SESSION_COUNT,
        COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse', 'PreToolUse') THEN 1 END) AS TOOL_EXECUTION_COUNT,
        COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS MCP_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END) AS COMMAND_COUNT,
        COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS SKILL_COUNT,
        COUNT(DISTINCT USER_ID) AS ACTIVE_USERS,
        AVG(CASE WHEN TOOL_SUCCESS IS NOT NULL THEN CASE WHEN TOOL_SUCCESS THEN 1.0 ELSE 0.0 END END) AS SUCCESS_RATE
    FROM USAGE_EVENTS
    GROUP BY DATE_TRUNC('DAY', EVENT_TIMESTAMP), TEAM_ID
) AS source
ON target.SUMMARY_DATE = source.SUMMARY_DATE AND target.TEAM_ID = source.TEAM_ID
WHEN MATCHED THEN UPDATE SET
    TOTAL_EVENTS = source.TOTAL_EVENTS,
    MESSAGE_COUNT = source.MESSAGE_COUNT,
    SESSION_COUNT = source.SESSION_COUNT,
    TOOL_EXECUTION_COUNT = source.TOOL_EXECUTION_COUNT,
    MCP_COUNT = source.MCP_COUNT,
    SUBAGENT_COUNT = source.SUBAGENT_COUNT,
    COMMAND_COUNT = source.COMMAND_COUNT,
    SKILL_COUNT = source.SKILL_COUNT,
    ACTIVE_USERS = source.ACTIVE_USERS,
    SUCCESS_RATE = source.SUCCESS_RATE,
    UPDATED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
    SUMMARY_DATE, TEAM_ID, TOTAL_EVENTS, MESSAGE_COUNT, SESSION_COUNT,
    TOOL_EXECUTION_COUNT, MCP_COUNT, SUBAGENT_COUNT, COMMAND_COUNT, SKILL_COUNT,
    ACTIVE_USERS, SUCCESS_RATE
) VALUES (
    source.SUMMARY_DATE, source.TEAM_ID, source.TOTAL_EVENTS, source.MESSAGE_COUNT, source.SESSION_COUNT,
    source.TOOL_EXECUTION_COUNT, source.MCP_COUNT, source.SUBAGENT_COUNT, source.COMMAND_COUNT, source.SKILL_COUNT,
    source.ACTIVE_USERS, source.SUCCESS_RATE
);

-- ============================================================================
-- 確認クエリ
-- ============================================================================

-- データ件数確認
SELECT 'USAGE_EVENTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM USAGE_EVENTS
UNION ALL
SELECT 'DAILY_SUMMARY', COUNT(*) FROM DAILY_SUMMARY
UNION ALL
SELECT 'USER_SUMMARY', COUNT(*) FROM USER_SUMMARY
UNION ALL
SELECT 'TOOL_SUMMARY', COUNT(*) FROM TOOL_SUMMARY;

-- 最新データ確認
SELECT * FROM USAGE_EVENTS ORDER BY EVENT_TIMESTAMP DESC LIMIT 10;
