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


# ==============================================================================
# イベントペイロード作成
# ==============================================================================

def create_event_payload(event_type: str, input_data: dict) -> dict:
    """イベントペイロードを作成"""

    now = datetime.now(timezone.utc)

    # 全イベント共通フィールド（公式ドキュメント準拠）
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
        "metadata": {}
    }

    # イベントタイプ別の追加データ
    if event_type in ["PreToolUse", "PostToolUse"]:
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        payload["tool_name"] = tool_name
        payload["tool_use_id"] = input_data.get("tool_use_id", "")
        payload["categories"] = classify_tool(tool_name, tool_input)

        # PostToolUseの場合は成功を記録
        if event_type == "PostToolUse":
            payload["success"] = True
            # ツールレスポンスのサマリー（長さのみ、内容は送信しない）
            tool_response = input_data.get("tool_response", "")
            payload["output_length"] = len(str(tool_response))

    elif event_type == "PostToolUseFailure":
        payload["tool_name"] = input_data.get("tool_name", "unknown")
        payload["tool_use_id"] = input_data.get("tool_use_id", "")
        payload["success"] = False
        payload["error"] = input_data.get("error", "")[:200]  # エラーは短縮
        payload["is_interrupt"] = input_data.get("is_interrupt", False)

    elif event_type == "UserPromptSubmit":
        prompt = input_data.get("prompt", "")
        payload["prompt_length"] = len(prompt)
        # プロンプト内容は送信しない（プライバシー保護）

    elif event_type == "SessionStart":
        payload["metadata"]["source"] = input_data.get("source", "unknown")
        payload["metadata"]["model"] = input_data.get("model", "unknown")
        payload["metadata"]["agent_type"] = input_data.get("agent_type", "")

    elif event_type == "SessionEnd":
        payload["metadata"]["reason"] = input_data.get("reason", "other")

    elif event_type == "SubagentStart":
        payload["agent_id"] = input_data.get("agent_id", "")
        payload["agent_type"] = input_data.get("agent_type", "")
        payload["categories"] = {"subagent": True}

    elif event_type == "SubagentStop":
        payload["agent_id"] = input_data.get("agent_id", "")
        payload["agent_type"] = input_data.get("agent_type", "")
        payload["agent_transcript_path"] = input_data.get("agent_transcript_path", "")
        payload["stop_hook_active"] = input_data.get("stop_hook_active", False)
        payload["categories"] = {"subagent": True}

    elif event_type == "Notification":
        payload["metadata"]["message"] = input_data.get("message", "")
        payload["metadata"]["title"] = input_data.get("title", "")
        payload["metadata"]["notification_type"] = input_data.get("notification_type", "")

    elif event_type == "PreCompact":
        payload["metadata"]["trigger"] = input_data.get("trigger", "")
        payload["metadata"]["custom_instructions"] = input_data.get("custom_instructions", "")

    elif event_type == "Stop":
        payload["stop_hook_active"] = input_data.get("stop_hook_active", False)

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
