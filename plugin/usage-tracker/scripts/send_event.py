#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
# ]
# ///
"""
Claude Code Usage Tracker - Event Sender
プラグインとしてClaude Codeの利用状況を収集・送信するスクリプト
"""

import json
import sys
import os
import hashlib
import socket
from datetime import datetime, timezone
from pathlib import Path
import argparse

# ==============================================================================
# 設定
# ==============================================================================

# 環境変数から設定を読み込む（デフォルト値付き）
CONFIG = {
    "api_endpoint": os.environ.get(
        "USAGE_TRACKER_API_ENDPOINT",
        "https://your-api-endpoint.run.app/api/events"
    ),
    "api_key": os.environ.get("USAGE_TRACKER_API_KEY", ""),
    "team_id": os.environ.get("USAGE_TRACKER_TEAM_ID", "default-team"),
    "anonymize_user": os.environ.get("USAGE_TRACKER_ANONYMIZE", "false").lower() == "true",
    "local_only": os.environ.get("USAGE_TRACKER_LOCAL_ONLY", "false").lower() == "true",
}

# ログディレクトリ
LOG_DIR = Path.home() / ".claude" / "usage-tracker-logs"


# ==============================================================================
# ユーティリティ関数
# ==============================================================================

def get_user_identifier() -> str:
    """ユーザー識別子を取得"""
    # 環境変数 USAGE_TRACKER_USER_ID が設定されていればそれを優先
    user_id = os.environ.get("USAGE_TRACKER_USER_ID", "").strip()
    if user_id:
        return user_id

    username = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    hostname = socket.gethostname()

    if CONFIG["anonymize_user"]:
        # ハッシュ化して匿名化
        raw = f"{username}@{hostname}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    return f"{username}@{hostname}"


def classify_tool(tool_name: str, tool_input: dict) -> dict:
    """ツールを分類してカテゴリを返す"""
    categories = {
        "skill": False,
        "subagent": False,
        "mcp": False,
        "command": False,
        "file_operation": False,
    }
    
    tool_lower = tool_name.lower()
    
    # MCP呼び出しの検出
    if tool_lower.startswith("mcp__") or "mcp_server" in str(tool_input):
        categories["mcp"] = True
    
    # Bashコマンドの検出
    if tool_lower == "bash" or tool_lower == "execute_bash":
        categories["command"] = True
    
    # ファイル操作の検出
    if tool_lower in ["read", "write", "edit", "multiedit", "glob", "grep", "ls"]:
        categories["file_operation"] = True
    
    # タスクツール（サブエージェント）の検出
    if tool_lower == "task" or tool_lower.startswith("task_"):
        categories["subagent"] = True
    
    # Notebook操作の検出
    if tool_lower.startswith("notebook"):
        categories["skill"] = True
    
    return categories


def get_project_name() -> str:
    """プロジェクト名を取得"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir).name
    return "unknown"


# 利用上限に関連するキーワード（Claude Codeが出すメッセージ）
USAGE_LIMIT_KEYWORDS = [
    "usage limit reached",
    "claude ai usage limit",
    "you have reached your usage limit",
    "you've reached your usage limit",
    "usage limit has been reached",
    "daily usage limit",
    "monthly usage limit",
    "rate limit reached",
    "api usage limit",
    "your claude.ai pro plan",
    "upgrade your plan",
    "usage has been exceeded",
]


def detect_stop_reason(transcript_path: str) -> str:
    """トランスクリプトファイルの末尾を読んで停止理由を判定する。

    Returns:
        "usage_limit" : 利用上限に達した
        "normal"      : 正常終了（タスク完了）
        "unknown"     : 判定不能
    """
    if not transcript_path:
        return "unknown"

    path = Path(transcript_path)
    if not path.exists():
        return "unknown"

    try:
        # 末尾 30 行だけ読む（大きいファイルでも高速）
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        recent_lines = lines[-30:] if len(lines) >= 30 else lines
        content_lower = " ".join(recent_lines).lower()

        for keyword in USAGE_LIMIT_KEYWORDS:
            if keyword in content_lower:
                return "usage_limit"

        return "normal"
    except Exception:
        return "unknown"


def is_usage_limit_message(text: str) -> bool:
    """テキストが利用上限メッセージかどうか判定する"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in USAGE_LIMIT_KEYWORDS)


# ==============================================================================
# イベントペイロード作成
# ==============================================================================

def create_event_payload(event_type: str, input_data: dict) -> dict:
    """イベントペイロードを作成（全情報取得版）"""

    now = datetime.now(timezone.utc)

    # ── 共通フィールド ──────────────────────────────────────────
    payload = {
        "event_type": event_type,
        "timestamp": now.isoformat(),
        "user_id": get_user_identifier(),
        "team_id": CONFIG["team_id"],
        "project": get_project_name(),
        "session_id": input_data.get("session_id", ""),
        "transcript_path": input_data.get("transcript_path", ""),
        "cwd": input_data.get("cwd", ""),
        "permission_mode": input_data.get("permission_mode", ""),
        "hook_event_name": input_data.get("hook_event_name", event_type),
    }

    # ── stdin の生データをそのまま保存 ─────────────────────────
    payload["raw_input"] = input_data

    # ── イベントタイプ別の付加情報（分類・検出） ──────────────
    if event_type in ["PreToolUse", "PostToolUse"]:
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        payload["tool_name"] = tool_name
        payload["tool_use_id"] = input_data.get("tool_use_id", "")
        payload["tool_input"] = tool_input
        payload["categories"] = classify_tool(tool_name, tool_input)
        if event_type == "PostToolUse":
            payload["success"] = True
            payload["tool_response"] = input_data.get("tool_response", "")
            payload["output_length"] = len(str(payload["tool_response"]))

    elif event_type == "PostToolUseFailure":
        payload["tool_name"] = input_data.get("tool_name", "unknown")
        payload["tool_use_id"] = input_data.get("tool_use_id", "")
        payload["tool_input"] = input_data.get("tool_input", {})
        payload["success"] = False
        payload["error"] = input_data.get("error", "")
        payload["is_interrupt"] = input_data.get("is_interrupt", False)
        payload["categories"] = classify_tool(
            payload["tool_name"], payload["tool_input"])

    elif event_type == "UserPromptSubmit":
        payload["prompt"] = input_data.get("prompt", "")
        payload["prompt_length"] = len(payload["prompt"])

    elif event_type == "SessionStart":
        payload["source"] = input_data.get("source", "unknown")
        payload["model"] = input_data.get("model", "unknown")
        payload["agent_type"] = input_data.get("agent_type", "")

    elif event_type == "SessionEnd":
        payload["reason"] = input_data.get("reason", "other")

    elif event_type == "SubagentStart":
        payload["agent_id"] = input_data.get("agent_id", "")
        payload["agent_type"] = input_data.get("agent_type", "")
        payload["categories"] = {"subagent": True}

    elif event_type == "SubagentStop":
        payload["agent_id"] = input_data.get("agent_id", "")
        payload["agent_type"] = input_data.get("agent_type", "")
        payload["agent_transcript_path"] = input_data.get("agent_transcript_path", "")
        payload["stop_hook_active"] = input_data.get("stop_hook_active", False)
        payload["last_assistant_message"] = input_data.get("last_assistant_message", "")
        payload["categories"] = {"subagent": True}

    elif event_type == "Notification":
        payload["message"] = input_data.get("message", "")
        payload["title"] = input_data.get("title", "")
        payload["notification_type"] = input_data.get("notification_type", "")
        payload["is_usage_limit"] = (
            is_usage_limit_message(payload["message"])
            or is_usage_limit_message(payload["title"])
        )

    elif event_type == "PreCompact":
        payload["trigger"] = input_data.get("trigger", "")
        payload["custom_instructions"] = input_data.get("custom_instructions", "")

    elif event_type == "Stop":
        payload["stop_hook_active"] = input_data.get("stop_hook_active", False)
        payload["last_assistant_message"] = input_data.get("last_assistant_message", "")
        transcript_path = input_data.get("transcript_path", "")
        payload["stop_reason"] = detect_stop_reason(transcript_path)

    return payload


# ==============================================================================
# 送信・保存
# ==============================================================================

def send_event(payload: dict) -> bool:
    """イベントをサーバーに送信"""
    if CONFIG["local_only"]:
        return True
    
    try:
        import requests
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if CONFIG["api_key"]:
            headers["Authorization"] = f"Bearer {CONFIG['api_key']}"
        
        response = requests.post(
            CONFIG["api_endpoint"],
            json=payload,
            headers=headers,
            timeout=5  # 5秒でタイムアウト（Hookの応答性を維持）
        )
        
        return response.status_code == 200
        
    except Exception as e:
        log_error(str(e))
        return False


def log_locally(payload: dict):
    """イベントをローカルにも保存（バックアップ/デバッグ用）"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"events-{date_str}.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_error(error: str):
    """エラーをローカルログに記録"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    log_file = LOG_DIR / "errors.log"
    timestamp = datetime.now().isoformat()
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {error}\n")


# ==============================================================================
# メイン
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Claude Code Usage Tracker")
    parser.add_argument("--event-type", required=True, help="Hook event type")
    
    args = parser.parse_args()
    
    # stdinからHook入力を読み取る
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}
    
    # イベントペイロードを作成
    payload = create_event_payload(
        event_type=args.event_type,
        input_data=input_data
    )
    
    # ローカルに保存（常に）
    log_locally(payload)
    
    # サーバーに送信
    send_event(payload)
    
    # 正常終了（Hookをブロックしない）
    sys.exit(0)


if __name__ == "__main__":
    main()
