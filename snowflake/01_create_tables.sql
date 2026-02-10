-- ============================================================================
-- Claude Code Usage Tracker - Snowflake テーブル定義
-- ============================================================================

-- 使用するデータベースとスキーマを作成（必要に応じて変更してください）
CREATE DATABASE IF NOT EXISTS CLAUDE_USAGE_DB;
CREATE SCHEMA IF NOT EXISTS CLAUDE_USAGE_DB.USAGE_TRACKING;

USE DATABASE CLAUDE_USAGE_DB;
USE SCHEMA USAGE_TRACKING;

-- ============================================================================
-- 1. イベントログテーブル（メインテーブル）
-- ============================================================================
CREATE TABLE IF NOT EXISTS USAGE_EVENTS (
    -- 主キー
    EVENT_ID VARCHAR(36) DEFAULT UUID_STRING(),
    
    -- イベント基本情報
    EVENT_TYPE VARCHAR(50) NOT NULL,          -- SessionStart, PostToolUse, UserPromptSubmit, etc.
    EVENT_TIMESTAMP TIMESTAMP_NTZ NOT NULL,   -- イベント発生時刻
    RECEIVED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),  -- データ取り込み時刻
    
    -- ユーザー・チーム情報
    USER_ID VARCHAR(255) NOT NULL,            -- ユーザー識別子（例: user@hostname）
    TEAM_ID VARCHAR(100) DEFAULT 'default-team',
    PROJECT_NAME VARCHAR(255),                -- プロジェクト名
    SESSION_ID VARCHAR(100),                  -- セッション識別子
    
    -- ツール情報
    TOOL_NAME VARCHAR(100),                   -- Read, Write, Bash, Edit, etc.
    TOOL_SUCCESS BOOLEAN,                     -- 成功/失敗
    OUTPUT_LENGTH INTEGER,                    -- 出力の長さ
    ERROR_MESSAGE VARCHAR(500),               -- エラーメッセージ（失敗時）
    
    -- カテゴリフラグ
    IS_SKILL BOOLEAN DEFAULT FALSE,
    IS_SUBAGENT BOOLEAN DEFAULT FALSE,
    IS_MCP BOOLEAN DEFAULT FALSE,
    IS_COMMAND BOOLEAN DEFAULT FALSE,
    IS_FILE_OPERATION BOOLEAN DEFAULT FALSE,
    
    -- プロンプト情報
    PROMPT_LENGTH INTEGER,                    -- プロンプトの長さ
    
    -- メタデータ（JSON形式で柔軟に格納）
    METADATA VARIANT,
    
    -- 制約
    PRIMARY KEY (EVENT_ID)
);

-- ============================================================================
-- 2. 日別サマリーテーブル（集計用）
-- ============================================================================
CREATE TABLE IF NOT EXISTS DAILY_SUMMARY (
    SUMMARY_DATE DATE NOT NULL,
    TEAM_ID VARCHAR(100) NOT NULL,
    
    -- カウント系
    TOTAL_EVENTS INTEGER DEFAULT 0,
    MESSAGE_COUNT INTEGER DEFAULT 0,
    SESSION_COUNT INTEGER DEFAULT 0,
    TOOL_EXECUTION_COUNT INTEGER DEFAULT 0,
    MCP_COUNT INTEGER DEFAULT 0,
    SUBAGENT_COUNT INTEGER DEFAULT 0,
    COMMAND_COUNT INTEGER DEFAULT 0,
    SKILL_COUNT INTEGER DEFAULT 0,
    
    -- ユーザー数
    ACTIVE_USERS INTEGER DEFAULT 0,
    
    -- 成功率
    SUCCESS_RATE FLOAT,
    
    -- 更新日時
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (SUMMARY_DATE, TEAM_ID)
);

-- ============================================================================
-- 3. ユーザー別サマリーテーブル
-- ============================================================================
CREATE TABLE IF NOT EXISTS USER_SUMMARY (
    SUMMARY_DATE DATE NOT NULL,
    USER_ID VARCHAR(255) NOT NULL,
    TEAM_ID VARCHAR(100) NOT NULL,
    
    -- カウント系
    TOTAL_EVENTS INTEGER DEFAULT 0,
    MESSAGE_COUNT INTEGER DEFAULT 0,
    SESSION_COUNT INTEGER DEFAULT 0,
    TOOL_EXECUTION_COUNT INTEGER DEFAULT 0,
    MCP_COUNT INTEGER DEFAULT 0,
    SUBAGENT_COUNT INTEGER DEFAULT 0,
    COMMAND_COUNT INTEGER DEFAULT 0,
    SKILL_COUNT INTEGER DEFAULT 0,
    
    -- 最終アクティブ
    LAST_ACTIVE_AT TIMESTAMP_NTZ,
    
    -- 更新日時
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (SUMMARY_DATE, USER_ID, TEAM_ID)
);

-- ============================================================================
-- 4. ツール別サマリーテーブル
-- ============================================================================
CREATE TABLE IF NOT EXISTS TOOL_SUMMARY (
    SUMMARY_DATE DATE NOT NULL,
    TEAM_ID VARCHAR(100) NOT NULL,
    TOOL_NAME VARCHAR(100) NOT NULL,
    
    -- カウント系
    EXECUTION_COUNT INTEGER DEFAULT 0,
    SUCCESS_COUNT INTEGER DEFAULT 0,
    FAILURE_COUNT INTEGER DEFAULT 0,
    
    -- 更新日時
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (SUMMARY_DATE, TEAM_ID, TOOL_NAME)
);

-- ============================================================================
-- 5. ビュー: ダッシュボード用の集計ビュー
-- ============================================================================

-- 期間別KPIビュー
CREATE OR REPLACE VIEW V_KPI_METRICS AS
SELECT 
    TEAM_ID,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP) AS EVENT_DATE,
    
    -- 基本カウント
    COUNT(*) AS TOTAL_EVENTS,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END) AS SESSION_COUNT,
    COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse', 'PreToolUse') THEN 1 END) AS TOOL_COUNT,
    COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS MCP_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END) AS COMMAND_COUNT,
    COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS SKILL_COUNT,
    
    -- ユニークユーザー数
    COUNT(DISTINCT USER_ID) AS ACTIVE_USERS
    
FROM USAGE_EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP);

-- ユーザーランキングビュー
CREATE OR REPLACE VIEW V_USER_RANKING AS
SELECT 
    USER_ID,
    TEAM_ID,
    SPLIT_PART(USER_ID, '@', 1) AS DISPLAY_NAME,
    
    COUNT(*) AS TOTAL_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
    COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS SKILL_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS MCP_COUNT,
    COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END) AS COMMAND_COUNT,
    
    MAX(EVENT_TIMESTAMP) AS LAST_ACTIVE_AT
    
FROM USAGE_EVENTS
GROUP BY USER_ID, TEAM_ID;

-- ツール利用ランキングビュー
CREATE OR REPLACE VIEW V_TOOL_RANKING AS
SELECT 
    TEAM_ID,
    TOOL_NAME,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP) AS EVENT_DATE,
    COUNT(*) AS EXECUTION_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = TRUE THEN 1 END) AS SUCCESS_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = FALSE THEN 1 END) AS FAILURE_COUNT
FROM USAGE_EVENTS
WHERE TOOL_NAME IS NOT NULL
GROUP BY TEAM_ID, TOOL_NAME, DATE_TRUNC('DAY', EVENT_TIMESTAMP);

-- ============================================================================
-- 6. S3からのデータ取り込み用ステージ（TROCCOを使う場合は不要）
-- ============================================================================
-- 直接S3から取り込む場合に使用
-- CREATE OR REPLACE STAGE USAGE_DATA_STAGE
--     URL = 's3://your-bucket/claude-usage-logs/'
--     CREDENTIALS = (AWS_KEY_ID = 'xxx' AWS_SECRET_KEY = 'xxx')
--     FILE_FORMAT = (TYPE = 'JSON');

-- ============================================================================
-- 7. サンプルデータ投入（テスト用）
-- ============================================================================
-- INSERT INTO USAGE_EVENTS (
--     EVENT_TYPE, EVENT_TIMESTAMP, USER_ID, TEAM_ID, PROJECT_NAME,
--     TOOL_NAME, TOOL_SUCCESS, IS_MCP, IS_COMMAND
-- ) VALUES
--     ('SessionStart', CURRENT_TIMESTAMP(), 'user1@host1', 'team-a', 'project-x', NULL, NULL, FALSE, FALSE),
--     ('UserPromptSubmit', CURRENT_TIMESTAMP(), 'user1@host1', 'team-a', 'project-x', NULL, NULL, FALSE, FALSE),
--     ('PostToolUse', CURRENT_TIMESTAMP(), 'user1@host1', 'team-a', 'project-x', 'Bash', TRUE, FALSE, TRUE),
--     ('PostToolUse', CURRENT_TIMESTAMP(), 'user2@host2', 'team-a', 'project-y', 'Read', TRUE, FALSE, FALSE);

-- ============================================================================
-- 完了メッセージ
-- ============================================================================
SELECT 'テーブル作成完了！' AS STATUS;
