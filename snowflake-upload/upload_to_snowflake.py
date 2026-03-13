#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "snowflake-connector-python>=3.6.0",
#     "cryptography>=42.0.0",
# ]
# ///
"""
Claude Code Usage Tracker - Snowflake Upload
ローカルの JSONL ログを Snowflake 内部ステージに PUT し、
LAYER1 → LAYER2 → LAYER3 のパイプラインでテーブルを更新する。

パイプライン:
  PUT → @LAYER1.STAGE
  COPY INTO → LAYER1.RAW_EVENTS (VARIANT そのまま)
  MERGE INTO → LAYER2.EVENTS (カラム展開・重複排除)
  MERGE INTO → LAYER3.DAILY/USER/TOOL_SUMMARY

Usage:
    uv run upload_to_snowflake.py --action upload [--force]
    uv run upload_to_snowflake.py --action list
    uv run upload_to_snowflake.py --action config
    uv run upload_to_snowflake.py --action generate-key
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
LOG_DIR = Path.home() / ".claude" / "usage-tracker-logs"
UPLOADED_FILE = LOG_DIR / ".uploaded_files.json"
KEY_DIR = Path.home() / ".snowflake"

STAGE = "CLAUDE_USAGE_DB.LAYER1.CLAUDE_USAGE_INTERNAL_STAGE"

_L1 = "CLAUDE_USAGE_DB.LAYER1"
_L2 = "CLAUDE_USAGE_DB.LAYER2"
_L3 = "CLAUDE_USAGE_DB.LAYER3"

# ---------------------------------------------------------------------------
# SQL テンプレート (snowflake/setup/02_load_data.sql と同一)
# ---------------------------------------------------------------------------

# STEP 1: Stage → LAYER1.RAW_EVENTS
COPY_INTO_RAW_SQL = f"""
COPY INTO {_L1}.RAW_EVENTS (RAW_DATA, SOURCE_FILE)
FROM (
    SELECT
        $1,
        METADATA$FILENAME
    FROM @{STAGE}
)
ON_ERROR = 'CONTINUE';
""".strip()

# STEP 2: LAYER1.RAW_EVENTS → LAYER2.EVENTS (重複排除 MERGE)
MERGE_EVENTS_SQL = f"""
MERGE INTO {_L2}.EVENTS AS tgt
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
    FROM {_L1}.RAW_EVENTS
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
""".strip()

# STEP 3: LAYER2.EVENTS → LAYER3 サマリーテーブル
MERGE_DAILY_SQL = f"""
MERGE INTO {_L3}.DAILY_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE AS SUMMARY_DATE,
        TEAM_ID,
        COUNT(*)                                               AS TOTAL_EVENTS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESSION_COUNT,
        COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END) AS TOOL_EXECUTION_COUNT,
        COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)  AS MCP_COUNT,
        COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)  AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)  AS COMMAND_COUNT,
        COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)  AS SKILL_COUNT,
        COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END) AS LIMIT_HIT_COUNT,
        COUNT(DISTINCT USER_ID)                          AS ACTIVE_USERS,
        ROUND(AVG(CASE WHEN TOOL_SUCCESS IS NOT NULL
            THEN CASE WHEN TOOL_SUCCESS THEN 1.0 ELSE 0.0 END END) * 100, 1) AS SUCCESS_RATE
    FROM {_L2}.EVENTS
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
""".strip()

MERGE_USER_SQL = f"""
MERGE INTO {_L3}.USER_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE AS SUMMARY_DATE,
        USER_ID,
        TEAM_ID,
        COUNT(*)                                               AS TOTAL_EVENTS,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart'     THEN 1 END) AS SESSION_COUNT,
        COUNT(CASE WHEN TOOL_NAME IS NOT NULL           THEN 1 END) AS TOOL_EXECUTION_COUNT,
        COUNT(CASE WHEN IS_MCP      = TRUE THEN 1 END)  AS MCP_COUNT,
        COUNT(CASE WHEN IS_SUBAGENT = TRUE THEN 1 END)  AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_COMMAND  = TRUE THEN 1 END)  AS COMMAND_COUNT,
        COUNT(CASE WHEN IS_SKILL    = TRUE THEN 1 END)  AS SKILL_COUNT,
        COUNT(CASE WHEN IS_USAGE_LIMIT = TRUE THEN 1 END) AS LIMIT_HIT_COUNT,
        MAX(EVENT_TIMESTAMP)                             AS LAST_ACTIVE_AT
    FROM {_L2}.EVENTS
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
""".strip()

MERGE_TOOL_SQL = f"""
MERGE INTO {_L3}.TOOL_SUMMARY AS tgt
USING (
    SELECT
        DATE_TRUNC('DAY', EVENT_TIMESTAMP)::DATE AS SUMMARY_DATE,
        TEAM_ID,
        TOOL_NAME,
        COUNT(*)                                           AS EXECUTION_COUNT,
        COUNT(CASE WHEN TOOL_SUCCESS = TRUE  THEN 1 END)  AS SUCCESS_COUNT,
        COUNT(CASE WHEN TOOL_SUCCESS = FALSE THEN 1 END)  AS FAILURE_COUNT
    FROM {_L2}.EVENTS
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
""".strip()


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def write_ok(msg: str):
    print(f"[OK] {msg}")

def write_info(msg: str):
    print(f"[INFO] {msg}")

def write_fail(msg: str):
    print(f"[ERROR] {msg}", file=sys.stderr)


def get_env(name: str, default: str = "") -> str:
    """環境変数を取得。Windowsのユーザー環境変数も参照。"""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    # Windows: ユーザー環境変数から直接読む
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                val, _ = winreg.QueryValueEx(key, name)
                return val.strip()
        except (OSError, FileNotFoundError):
            pass
    return default


def get_username() -> str:
    """アップロード用のユーザー名を取得。"""
    uid = get_env("USAGE_TRACKER_USER_ID")
    if uid:
        return uid
    return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def _set_user_env(name: str, value: str):
    """環境変数をプロセスとWindowsユーザー環境変数の両方に設定。"""
    os.environ[name] = value
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment",
                0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        except OSError:
            pass


def load_uploaded() -> list[str]:
    """アップロード済みファイル一覧を読み込む。"""
    if not UPLOADED_FILE.exists():
        return []
    try:
        data = json.loads(UPLOADED_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return [data] if data else []
    except Exception:
        return []


def save_uploaded(files: list[str]):
    """アップロード済みファイル一覧を保存。"""
    UPLOADED_FILE.write_text(json.dumps(files, indent=2, ensure_ascii=False),
                             encoding="utf-8")


def create_connection():
    """RSA キーペアで Snowflake に接続。"""
    from cryptography.hazmat.primitives import serialization

    account = get_env("SNOWFLAKE_ACCOUNT")
    user = get_env("SNOWFLAKE_USER")
    key_path = get_env("SNOWFLAKE_PRIVATE_KEY_PATH",
                       str(KEY_DIR / "rsa_key.p8"))
    passphrase = get_env("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    warehouse = get_env("SNOWFLAKE_WAREHOUSE", "CLAUDE_USAGE_WH")
    database = get_env("SNOWFLAKE_DATABASE", "CLAUDE_USAGE_DB")

    if not account or not user:
        write_fail("SNOWFLAKE_ACCOUNT / SNOWFLAKE_USER が設定されていません")
        sys.exit(1)

    key_file = Path(key_path)
    if not key_file.exists():
        write_fail(f"秘密鍵が見つかりません: {key_file}")
        write_info("uv run upload_to_snowflake.py --action generate-key で生成してください")
        sys.exit(1)

    key_data = key_file.read_bytes()
    pwd = passphrase.encode() if passphrase else None
    private_key = serialization.load_pem_private_key(key_data, password=pwd)
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    import snowflake.connector
    conn = snowflake.connector.connect(
        account=account,
        user=user,
        private_key=private_key_bytes,
        warehouse=warehouse,
        database=database,
    )
    return conn


# ---------------------------------------------------------------------------
# アクション: generate-key
# ---------------------------------------------------------------------------
def action_generate_key(no_input: bool = False):
    """RSA キーペアを生成し公開鍵を表示する。"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    KEY_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = KEY_DIR / "rsa_key.p8"
    pub_path = KEY_DIR / "rsa_key.pub"

    if priv_path.exists():
        if no_input:
            # 非対話モード: 既存キーをそのまま使用
            write_info(f"既存のキーペアを使用: {priv_path}")
            if pub_path.exists():
                pub_text = pub_path.read_text(encoding="utf-8")
                _show_public_key(pub_text)
            return
        write_info(f"既存のキーペアが見つかりました: {priv_path}")
        resp = input("上書きしますか？ (y/N): ").strip().lower()
        if resp != "y":
            # 既存の公開鍵を表示
            if pub_path.exists():
                pub_text = pub_path.read_text(encoding="utf-8")
                _show_public_key(pub_text)
            return

    write_info("RSA 2048bit キーペアを生成中...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 秘密鍵 (パスフレーズなし)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(priv_pem)
    write_ok(f"秘密鍵: {priv_path}")

    # 公開鍵
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path.write_bytes(pub_pem)
    write_ok(f"公開鍵: {pub_path}")

    _show_public_key(pub_pem.decode("utf-8"))


def _show_public_key(pub_text: str):
    """公開鍵の表示と管理者への指示。"""
    # ヘッダ・フッタを除いた1行形式
    lines = [l for l in pub_text.strip().splitlines()
             if not l.startswith("-----")]
    key_body = "".join(lines)

    print()
    print("=" * 60)
    print(" Snowflake 管理者に以下の公開鍵を渡してください")
    print("=" * 60)
    print()
    print(f"  {key_body}")
    print()
    print("管理者が実行する SQL:")
    print(f"  ALTER USER <ユーザー名> SET RSA_PUBLIC_KEY='{key_body}';")
    print()
    print("=" * 60)


# ---------------------------------------------------------------------------
# アクション: config
# ---------------------------------------------------------------------------
def action_config():
    """現在の設定を表示し接続テスト。"""
    print()
    print("====== Snowflake Upload 設定 ======")
    print()
    items = [
        ("SNOWFLAKE_ACCOUNT", get_env("SNOWFLAKE_ACCOUNT", "(未設定)")),
        ("SNOWFLAKE_USER", get_env("SNOWFLAKE_USER", "(未設定)")),
        ("SNOWFLAKE_PRIVATE_KEY_PATH",
         get_env("SNOWFLAKE_PRIVATE_KEY_PATH",
                 str(KEY_DIR / "rsa_key.p8"))),
        ("SNOWFLAKE_WAREHOUSE",
         get_env("SNOWFLAKE_WAREHOUSE", "CLAUDE_USAGE_WH")),
        ("SNOWFLAKE_DATABASE",
         get_env("SNOWFLAKE_DATABASE", "CLAUDE_USAGE_DB")),
        ("USAGE_TRACKER_USER_ID", get_username()),
    ]
    for name, val in items:
        print(f"  {name}: {val}")
    print(f"  Log Dir: {LOG_DIR}")
    print(f"  Stage:   @{STAGE}")
    print()

    # 接続テスト
    write_info("接続テスト中...")
    try:
        conn = create_connection()
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        row = cur.fetchone()
        sf_user = row[0]
        write_ok(f"接続成功 - User: {sf_user}, Role: {row[1]}, WH: {row[2]}")

        # USAGE_TRACKER_USER_ID を Snowflake ユーザー名で自動設定
        current_uid = get_env("USAGE_TRACKER_USER_ID")
        if not current_uid or current_uid != sf_user:
            _set_user_env("USAGE_TRACKER_USER_ID", sf_user)
            write_ok(f"USAGE_TRACKER_USER_ID = {sf_user} (Snowflake ユーザー名で自動設定)")

        cur.close()
        conn.close()
    except Exception as e:
        write_fail(f"接続失敗: {e}")


# ---------------------------------------------------------------------------
# アクション: list
# ---------------------------------------------------------------------------
def action_list():
    """ローカルログファイルを一覧表示。"""
    print()
    print("====== ログファイル ======")
    print()

    if not LOG_DIR.exists():
        write_fail(f"ログディレクトリが見つかりません: {LOG_DIR}")
        write_info("Claude Code プラグインを使用するとログが生成されます")
        return

    files = sorted(LOG_DIR.glob("events-*.jsonl"))
    if not files:
        write_info("ログファイルがありません")
        return

    uploaded = load_uploaded()
    total_size = 0
    total_events = 0

    print(f"  ディレクトリ: {LOG_DIR}")
    print()

    for f in files:
        size = f.stat().st_size
        total_size += size
        with open(f, encoding="utf-8", errors="ignore") as fh:
            event_count = sum(1 for _ in fh)
        total_events += event_count
        size_kb = round(size / 1024, 1)
        status = "[済]" if f.name in uploaded else "[未]"
        print(f"  {status} {f.name} ({size_kb} KB, {event_count} events)")

    print()
    total_kb = round(total_size / 1024, 1)
    print(f"  合計: {len(files)} files, {total_kb} KB, {total_events} events")


# ---------------------------------------------------------------------------
# アクション: upload
# ---------------------------------------------------------------------------
def action_upload(force: bool = False):
    """PUT → LAYER1 → LAYER2 → LAYER3 のフルパイプライン。"""
    username = get_username()
    write_info(f"ユーザー: {username}")

    if force:
        write_info("--force: 全ファイルを再アップロードします")

    # ローカルファイルの検出
    if not LOG_DIR.exists():
        write_fail(f"ログディレクトリが見つかりません: {LOG_DIR}")
        return

    all_files = sorted(LOG_DIR.glob("events-*.jsonl"))
    if not all_files:
        write_info("アップロードするログファイルがありません")
        return

    # アップロード済みチェック
    uploaded = load_uploaded() if not force else []
    files_to_upload = [f for f in all_files if f.name not in uploaded]

    if not files_to_upload:
        write_info("新しいファイルはありません (--force で全ファイル再アップロード)")
        return

    write_info(f"対象ファイル: {len(files_to_upload)}/{len(all_files)}")
    print()

    # Snowflake 接続
    try:
        conn = create_connection()
    except Exception as e:
        write_fail(f"Snowflake 接続失敗: {e}")
        return

    cur = conn.cursor()
    newly_uploaded = []

    try:
        # --- PUT → @LAYER1.STAGE ---
        for f in files_to_upload:
            local_path = str(f).replace("\\", "/")
            stage_path = f"@{STAGE}/{username}/"
            put_sql = (
                f"PUT 'file://{local_path}' '{stage_path}' "
                f"AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            )
            try:
                print(f"  [PUT] {f.name} -> {stage_path}")
                cur.execute(put_sql)
                result = cur.fetchall()
                status = result[0][6] if result and len(result[0]) > 6 else "UNKNOWN"
                if status in ("UPLOADED", "SKIPPED"):
                    print(f"        {status}")
                    newly_uploaded.append(f.name)
                else:
                    write_fail(f"        PUT status: {status}")
            except Exception as e:
                write_fail(f"        PUT失敗: {e}")

        if not newly_uploaded:
            write_info("アップロードされたファイルがありません。")
            return

        # --- STEP 1: COPY INTO LAYER1.RAW_EVENTS ---
        print()
        write_info("STEP 1: COPY INTO LAYER1.RAW_EVENTS ...")
        try:
            copy_sql = COPY_INTO_RAW_SQL
            if force:
                copy_sql = copy_sql.replace(
                    "ON_ERROR = 'CONTINUE'",
                    "ON_ERROR = 'CONTINUE'\nFORCE = TRUE"
                )
            cur.execute(copy_sql)
            rows = cur.fetchall()
            loaded = 0
            for r in rows or []:
                if len(r) > 3:
                    loaded += r[3] if isinstance(r[3], int) else 0
            write_ok(f"LAYER1.RAW_EVENTS: {loaded} rows loaded")
        except Exception as e:
            write_fail(f"COPY INTO 失敗: {e}")
            return

        # --- STEP 2: MERGE INTO LAYER2.EVENTS ---
        print()
        write_info("STEP 2: MERGE INTO LAYER2.EVENTS (重複排除) ...")
        try:
            cur.execute(MERGE_EVENTS_SQL)
            row = cur.fetchone()
            inserted = row[0] if row else 0
            write_ok(f"LAYER2.EVENTS: {inserted} new rows inserted")
        except Exception as e:
            write_fail(f"MERGE INTO LAYER2.EVENTS 失敗: {e}")
            return

        # --- STEP 3: MERGE INTO LAYER3 サマリーテーブル ---
        print()
        write_info("STEP 3: LAYER3 サマリーテーブル更新 ...")
        for label, sql in [
            ("DAILY_SUMMARY", MERGE_DAILY_SQL),
            ("USER_SUMMARY", MERGE_USER_SQL),
            ("TOOL_SUMMARY", MERGE_TOOL_SQL),
        ]:
            try:
                write_info(f"  MERGE INTO {label} ...")
                cur.execute(sql)
                row = cur.fetchone()
                inserted = row[0] if row else 0
                updated = row[1] if row and len(row) > 1 else 0
                write_ok(f"  {label}: inserted={inserted}, updated={updated}")
            except Exception as e:
                write_fail(f"  {label} MERGE 失敗: {e}")

    finally:
        cur.close()
        conn.close()

    # アップロード済み記録を更新
    if newly_uploaded:
        all_uploaded = list(set(uploaded + newly_uploaded))
        save_uploaded(all_uploaded)

    print()
    write_ok(f"完了: {len(newly_uploaded)} ファイルアップロード済み")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Usage Tracker - Snowflake Upload")
    parser.add_argument(
        "--action",
        choices=["upload", "list", "config", "generate-key"],
        default="upload",
        help="実行するアクション",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="アップロード済みファイルも再アップロード",
    )
    parser.add_argument(
        "--no-input", action="store_true",
        help="非対話モード（自動セットアップ用）",
    )
    args = parser.parse_args()

    if args.action == "generate-key":
        action_generate_key(no_input=args.no_input)
    elif args.action == "config":
        action_config()
    elif args.action == "list":
        action_list()
    elif args.action == "upload":
        action_upload(force=args.force)


if __name__ == "__main__":
    main()
