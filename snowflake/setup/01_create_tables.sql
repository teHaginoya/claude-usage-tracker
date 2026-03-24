-- ============================================================================
-- Claude Code Usage Tracker - Snowflake テーブル定義
-- 実行順序: 01_create_tables.sql → 02_load_data.sql → 03_create_streamlit.sql
--
-- レイヤー構成:
--   LAYER1 (Raw)   : ステージ + RAW_EVENTS（JSONL そのまま保持）
--   LAYER2 (Clean) : EVENTS（カラム展開・重複排除・蓄積）
--   LAYER3 (Mart)  : サマリーテーブル + SiS ステージ
-- ============================================================================

-- ============================================================================
-- 0. ウェアハウス・データベース・スキーマ
-- ============================================================================
CREATE WAREHOUSE IF NOT EXISTS CLAUDE_USAGE_WH
    WAREHOUSE_SIZE   = 'X-SMALL'
    AUTO_SUSPEND     = 60
    AUTO_RESUME      = TRUE
    COMMENT          = 'Claude Code Usage Dashboard 用ウェアハウス';

CREATE DATABASE IF NOT EXISTS CLAUDE_USAGE_DB
    COMMENT = 'Claude Code 利用状況トラッキング';

CREATE SCHEMA IF NOT EXISTS CLAUDE_USAGE_DB.LAYER1
    COMMENT = 'Raw: ステージ + 生ログ（VARIANT そのまま保持）';

CREATE SCHEMA IF NOT EXISTS CLAUDE_USAGE_DB.LAYER2
    COMMENT = 'Clean: カラム展開・重複排除・蓄積済みイベント';

CREATE SCHEMA IF NOT EXISTS CLAUDE_USAGE_DB.LAYER3
    COMMENT = 'Mart: サマリーテーブル + ダッシュボード用ビュー';

USE WAREHOUSE CLAUDE_USAGE_WH;

-- ============================================================================
-- 1. LAYER1: ステージ + RAW_EVENTS
-- ============================================================================
USE SCHEMA CLAUDE_USAGE_DB.LAYER1;

-- データ取り込み用内部ステージ
CREATE STAGE IF NOT EXISTS CLAUDE_USAGE_INTERNAL_STAGE
    FILE_FORMAT = (
        TYPE              = 'JSON'
        STRIP_OUTER_ARRAY = FALSE
    )
    COMMENT = 'JSONL イベントログのアップロード先';

-- 生ログテーブル（JSONL の各行を VARIANT としてそのまま保持）
CREATE TABLE IF NOT EXISTS RAW_EVENTS (
    RAW_DATA      VARIANT        NOT NULL,       -- JSONL 1行 = 1レコード
    SOURCE_FILE   VARCHAR(255),                   -- アップロード元ファイル名
    RECEIVED_AT   TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (RAW_DATA)                        -- VARIANT の完全一致で重複防止
);

-- ============================================================================
-- 2. LAYER2: EVENTS（カラム展開・重複排除・蓄積）
-- ============================================================================
USE SCHEMA CLAUDE_USAGE_DB.LAYER2;

CREATE TABLE IF NOT EXISTS EVENTS (
    -- 重複排除キー
    EVENT_HASH       VARCHAR(64)   NOT NULL,      -- SHA2(RAW_DATA) で生成

    -- イベント基本情報
    EVENT_TYPE       VARCHAR(50)   NOT NULL,
    EVENT_TIMESTAMP  TIMESTAMP_NTZ NOT NULL,       -- JST 変換済み
    RECEIVED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    -- ユーザー・チーム・セッション
    USER_ID          VARCHAR(255)  NOT NULL,
    TEAM_ID          VARCHAR(100)  DEFAULT 'default-team',
    SESSION_ID       VARCHAR(100),
    PROJECT_NAME     VARCHAR(255),

    -- ツール情報
    TOOL_NAME        VARCHAR(100),
    TOOL_SUCCESS     BOOLEAN,
    OUTPUT_LENGTH    INTEGER,
    ERROR_MESSAGE    VARCHAR(16777216),
    PROMPT_LENGTH    INTEGER,

    -- カテゴリフラグ
    IS_SKILL         BOOLEAN DEFAULT FALSE,
    IS_SUBAGENT      BOOLEAN DEFAULT FALSE,
    IS_MCP           BOOLEAN DEFAULT FALSE,
    IS_COMMAND       BOOLEAN DEFAULT FALSE,
    IS_FILE_OPERATION BOOLEAN DEFAULT FALSE,

    -- 利用制限・停止理由
    IS_USAGE_LIMIT   BOOLEAN DEFAULT FALSE,
    STOP_REASON      VARCHAR(50),

    -- 生データ参照
    RAW_DATA         VARIANT,

    PRIMARY KEY (EVENT_HASH)
);

-- クラスタリング
ALTER TABLE EVENTS
    CLUSTER BY (TEAM_ID, DATE_TRUNC('DAY', EVENT_TIMESTAMP));

-- ============================================================================
-- 3. LAYER3: サマリーテーブル + ビュー
-- ============================================================================
USE SCHEMA CLAUDE_USAGE_DB.LAYER3;

-- 日別サマリー
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

-- ユーザー別日次サマリー
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

-- ツール別日次サマリー
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
-- 4. LAYER3: SiS ステージ
-- ============================================================================

-- SiS アプリファイル用
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
    '③ 02_load_data.sql の COPY INTO / MERGE INTO でデータを取り込む'          AS STEP3;
