-- ============================================================================
-- Claude Code Usage Tracker - Streamlit in Snowflake (SiS) アプリ作成
-- 前提: 01_create_tables.sql → 02_load_data.sql 実行済み
-- ============================================================================

USE WAREHOUSE CLAUDE_USAGE_WH;
USE DATABASE  CLAUDE_USAGE_DB;
USE SCHEMA    USAGE_TRACKING;

-- ============================================================================
-- 1. SiS アプリ用ステージの確認
--    01_create_tables.sql で作成済み。まだ作成していない場合のみ実行してください。
-- ============================================================================
CREATE STAGE IF NOT EXISTS CLAUDE_DASHBOARD_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT   = 'Streamlit in Snowflake アプリファイル置き場';

-- ============================================================================
-- 2. アプリファイルのアップロード
--    SnowSQL または Snowflake CLI から以下のコマンドを実行してください。
--
--  【Windows の場合】
--    snowsql -a <your-account> -u <your-user> -q "
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/streamlit_app.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/helpers.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/queries.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/demo_data.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_overview.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_users.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_tools.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_sessions.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_projects.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--      PUT file://C:/path/to/claude-usage-tracker-repo/snowflake/app/tab_adoption.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--    "
--
--  【Mac / Linux の場合】
--    snowsql -a <your-account> -u <your-user> -q "
--      PUT file:///path/to/claude-usage-tracker-repo/snowflake/app/*.py
--          @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE
--          AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--    "
--
--  アップロード確認:
--    LIST @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE;
-- ============================================================================

-- ============================================================================
-- 3. Streamlit in Snowflake アプリの作成
--    ※ アップロード完了後に実行してください
-- ============================================================================
CREATE OR REPLACE STREAMLIT CLAUDE_CODE_USAGE_DASHBOARD
    ROOT_LOCATION = '@CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE'
    MAIN_FILE     = '/streamlit_app.py'
    QUERY_WAREHOUSE = 'CLAUDE_USAGE_WH'
    COMMENT       = 'Claude Code チーム利用状況ダッシュボード';

-- ============================================================================
-- 4. アクセス権限の設定
--    ダッシュボードを閲覧するロールに付与してください
--    ※ SYSADMIN や ACCOUNTADMIN で実行している場合は不要なこともあります
-- ============================================================================

-- -- データベース・スキーマへのアクセス
-- GRANT USAGE ON DATABASE CLAUDE_USAGE_DB              TO ROLE <your_role>;
-- GRANT USAGE ON SCHEMA   CLAUDE_USAGE_DB.USAGE_TRACKING TO ROLE <your_role>;
--
-- -- テーブル・ビューの読み取り
-- GRANT SELECT ON ALL TABLES IN SCHEMA CLAUDE_USAGE_DB.USAGE_TRACKING TO ROLE <your_role>;
-- GRANT SELECT ON ALL VIEWS  IN SCHEMA CLAUDE_USAGE_DB.USAGE_TRACKING TO ROLE <your_role>;
--
-- -- ステージへのアクセス（SiS がファイルを読むために必要）
-- GRANT READ ON STAGE CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE TO ROLE <your_role>;
--
-- -- ウェアハウスの使用
-- GRANT USAGE ON WAREHOUSE CLAUDE_USAGE_WH TO ROLE <your_role>;
--
-- -- Streamlit アプリの使用
-- GRANT USAGE ON STREAMLIT CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_CODE_USAGE_DASHBOARD TO ROLE <your_role>;

-- ============================================================================
-- 5. アップロード済みファイルの確認
-- ============================================================================
LIST @CLAUDE_USAGE_DB.USAGE_TRACKING.CLAUDE_DASHBOARD_STAGE;

-- ============================================================================
-- 6. SiS アプリの確認
-- ============================================================================
SHOW STREAMLITS IN SCHEMA CLAUDE_USAGE_DB.USAGE_TRACKING;

-- ============================================================================
-- 完了メッセージ
-- ============================================================================
SELECT 'SiS アプリ作成完了！Snowflake の Streamlit メニューから開いてください。' AS STATUS;
