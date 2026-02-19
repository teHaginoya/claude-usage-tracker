-- ============================================================================
-- Claude Code Usage Tracker - Snowflake テーブル定義
-- 実行順序: 01_create_tables.sql → 02_load_data.sql → 03_create_streamlit.sql
-- ============================================================================

-- ============================================================================
-- 0. ウェアハウス・データベース・スキーマ
--    ※ WAREHOUSE_SIZE / AUTO_SUSPEND は環境に合わせて変更してください
-- ============================================================================
CREATE WAREHOUSE IF NOT EXISTS CLAUDE_USAGE_WH
    WAREHOUSE_SIZE   = 'X-SMALL'
    AUTO_SUSPEND     = 60
    AUTO_RESUME      = TRUE
    COMMENT          = 'Claude Code Usage Dashboard 用ウェアハウス';

CREATE DATABASE IF NOT EXISTS CLAUDE_USAGE_DB
    COMMENT = 'Claude Code 利用状況トラッキング';

CREATE SCHEMA IF NOT EXISTS CLAUDE_USAGE_DB.LAYER3
    COMMENT = 'Claude Code イベントログ & 集計テーブル（加工済みレイヤー）';

USE WAREHOUSE CLAUDE_USAGE_WH;
USE DATABASE  CLAUDE_USAGE_DB;
USE SCHEMA    LAYER3;

-- ============================================================================
-- 1. メインイベントログテーブル
-- ============================================================================
CREATE TABLE IF NOT EXISTS USAGE_EVENTS (
    -- 主キー
    EVENT_ID         VARCHAR(36)   DEFAULT UUID_STRING(),

    -- イベント基本情報
    EVENT_TYPE       VARCHAR(50)   NOT NULL,           -- SessionStart / PostToolUse / UserPromptSubmit / Stop / Notification / etc.
    EVENT_TIMESTAMP  TIMESTAMP_NTZ NOT NULL,           -- イベント発生時刻（JST: Asia/Tokyo）
    RECEIVED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),  -- 取り込み時刻

    -- ユーザー・チーム・セッション
    USER_ID          VARCHAR(255)  NOT NULL,           -- user@hostname 形式
    TEAM_ID          VARCHAR(100)  DEFAULT 'default-team',
    SESSION_ID       VARCHAR(100),                     -- セッション識別子
    PROJECT_NAME     VARCHAR(255),                     -- プロジェクト名（作業ディレクトリ名）

    -- ツール情報（PreToolUse / PostToolUse 時のみ）
    TOOL_NAME        VARCHAR(100),                     -- Bash / Read / Write / Edit / mcp__* / etc.
    TOOL_SUCCESS     BOOLEAN,                          -- TRUE = 成功 / FALSE = 失敗
    OUTPUT_LENGTH    INTEGER,                          -- 出力文字数
    ERROR_MESSAGE    VARCHAR(500),                     -- エラーメッセージ（失敗時）
    PROMPT_LENGTH    INTEGER,                          -- プロンプト文字数（UserPromptSubmit 時）

    -- カテゴリフラグ
    IS_SKILL         BOOLEAN DEFAULT FALSE,
    IS_SUBAGENT      BOOLEAN DEFAULT FALSE,
    IS_MCP           BOOLEAN DEFAULT FALSE,
    IS_COMMAND       BOOLEAN DEFAULT FALSE,
    IS_FILE_OPERATION BOOLEAN DEFAULT FALSE,

    -- 利用制限・停止理由（send_event.py の root フィールドから取得）
    IS_USAGE_LIMIT   BOOLEAN DEFAULT FALSE,            -- Notification イベントで検出した利用上限
    STOP_REASON      VARCHAR(50),                      -- Stop イベントの停止理由: normal / usage_limit / unknown

    -- 拡張メタデータ（JSON）
    METADATA         VARIANT,                          -- 全ペイロードを保持（stop_reason / is_usage_limit 含む）

    PRIMARY KEY (EVENT_ID)
);

-- クラスタリング（TEAM_ID + EVENT_TIMESTAMP で絞り込むクエリが多いため）
ALTER TABLE USAGE_EVENTS
    CLUSTER BY (TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP));

-- ============================================================================
-- 2. 日別サマリーテーブル（高速集計用）
-- ============================================================================
CREATE TABLE IF NOT EXISTS DAILY_SUMMARY (
    SUMMARY_DATE          DATE         NOT NULL,
    TEAM_ID               VARCHAR(100) NOT NULL,
    TOTAL_EVENTS          INTEGER      DEFAULT 0,
    MESSAGE_COUNT         INTEGER      DEFAULT 0,
    SESSION_COUNT         INTEGER      DEFAULT 0,
    TOOL_EXECUTION_COUNT  INTEGER      DEFAULT 0,
    MCP_COUNT             INTEGER      DEFAULT 0,
    SUBAGENT_COUNT        INTEGER      DEFAULT 0,
    COMMAND_COUNT         INTEGER      DEFAULT 0,
    SKILL_COUNT           INTEGER      DEFAULT 0,
    LIMIT_HIT_COUNT       INTEGER      DEFAULT 0,
    ACTIVE_USERS          INTEGER      DEFAULT 0,
    SUCCESS_RATE          FLOAT,
    UPDATED_AT            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (SUMMARY_DATE, TEAM_ID)
);

-- ============================================================================
-- 3. ユーザー別日次サマリーテーブル
-- ============================================================================
CREATE TABLE IF NOT EXISTS USER_SUMMARY (
    SUMMARY_DATE          DATE         NOT NULL,
    USER_ID               VARCHAR(255) NOT NULL,
    TEAM_ID               VARCHAR(100) NOT NULL,
    TOTAL_EVENTS          INTEGER      DEFAULT 0,
    MESSAGE_COUNT         INTEGER      DEFAULT 0,
    SESSION_COUNT         INTEGER      DEFAULT 0,
    TOOL_EXECUTION_COUNT  INTEGER      DEFAULT 0,
    MCP_COUNT             INTEGER      DEFAULT 0,
    SUBAGENT_COUNT        INTEGER      DEFAULT 0,
    COMMAND_COUNT         INTEGER      DEFAULT 0,
    SKILL_COUNT           INTEGER      DEFAULT 0,
    LIMIT_HIT_COUNT       INTEGER      DEFAULT 0,
    LAST_ACTIVE_AT        TIMESTAMP_NTZ,
    UPDATED_AT            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (SUMMARY_DATE, USER_ID, TEAM_ID)
);

-- ============================================================================
-- 4. ツール別日次サマリーテーブル
-- ============================================================================
CREATE TABLE IF NOT EXISTS TOOL_SUMMARY (
    SUMMARY_DATE     DATE         NOT NULL,
    TEAM_ID          VARCHAR(100) NOT NULL,
    TOOL_NAME        VARCHAR(100) NOT NULL,
    EXECUTION_COUNT  INTEGER      DEFAULT 0,
    SUCCESS_COUNT    INTEGER      DEFAULT 0,
    FAILURE_COUNT    INTEGER      DEFAULT 0,
    UPDATED_AT       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (SUMMARY_DATE, TEAM_ID, TOOL_NAME)
);

-- ============================================================================
-- 5. ビュー（ダッシュボードのクエリをサポート）
-- ============================================================================

-- 日次 KPI ビュー
CREATE OR REPLACE VIEW V_KPI_METRICS AS
SELECT
    TEAM_ID,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE          AS EVENT_DATE,
    COUNT(*)                                           AS TOTAL_EVENTS,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESSION_COUNT,
    COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END) AS TOOL_COUNT,
    COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)   AS MCP_COUNT,
    COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)   AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)   AS COMMAND_COUNT,
    COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)   AS SKILL_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END) AS LIMIT_HIT_COUNT,
    COUNT(DISTINCT USER_ID)                            AS ACTIVE_USERS
FROM USAGE_EVENTS
GROUP BY TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP);

-- ユーザーランキングビュー
CREATE OR REPLACE VIEW V_USER_RANKING AS
SELECT
    USER_ID,
    TEAM_ID,
    SPLIT_PART(USER_ID, '@', 1)                        AS DISPLAY_NAME,
    COUNT(*)                                            AS TOTAL_COUNT,
    COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
    COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)     AS SKILL_COUNT,
    COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)     AS SUBAGENT_COUNT,
    COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)     AS MCP_COUNT,
    COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)     AS COMMAND_COUNT,
    COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END)  AS LIMIT_HIT_COUNT,
    MAX(EVENT_TIMESTAMP)                                AS LAST_ACTIVE_AT
FROM USAGE_EVENTS
GROUP BY USER_ID, TEAM_ID;

-- ツール利用ビュー
CREATE OR REPLACE VIEW V_TOOL_RANKING AS
SELECT
    TEAM_ID,
    TOOL_NAME,
    DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE AS EVENT_DATE,
    COUNT(*)                                 AS EXECUTION_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = TRUE  THEN 1 END) AS SUCCESS_COUNT,
    COUNT(CASE WHEN TOOL_SUCCESS = FALSE THEN 1 END) AS FAILURE_COUNT,
    ROUND(
        COUNT(CASE WHEN TOOL_SUCCESS = TRUE THEN 1 END)
        / NULLIF(COUNT(*), 0) * 100, 1
    ) AS SUCCESS_RATE
FROM USAGE_EVENTS
WHERE TOOL_NAME IS NOT NULL
GROUP BY TEAM_ID, TOOL_NAME, DATE_TRUNC('DAY', EVENT_TIMESTAMP);

-- ============================================================================
-- 6. ステージ
-- ============================================================================

-- データ取り込み用（send_event.py が生成する JSONL ファイルのアップロード先）
CREATE OR REPLACE STAGE CLAUDE_USAGE_DB.LAYER3.CLAUDE_USAGE_INTERNAL_STAGE
    FILE_FORMAT = (
        TYPE              = 'JSON'
        STRIP_OUTER_ARRAY = FALSE
    )
    COMMENT = 'JSONL イベントログのアップロード先';

-- SiS アプリファイル用（Streamlit in Snowflake のソースコード置き場）
CREATE OR REPLACE STAGE CLAUDE_DASHBOARD_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT   = 'Streamlit in Snowflake アプリファイル置き場';

-- ============================================================================
-- 完了メッセージ
-- ============================================================================
SELECT
    'テーブル作成完了！次のステップ:'                                          AS STATUS,
    '① app/*.py を CLAUDE_DASHBOARD_STAGE にアップロード'                      AS STEP1,
    '② 03_create_streamlit.sql を実行して SiS アプリを作成'                    AS STEP2,
    '③ 02_load_data.sql の COPY INTO でイベントデータを取り込む'                AS STEP3;
