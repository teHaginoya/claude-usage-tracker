---
description: 自分のClaude Code利用統計を表示します。日数を指定して過去の利用状況を確認できます。
allowed-tools: Bash
---

# Usage Stats Command

ユーザーのローカルに保存されたClaude Code利用統計を分析して表示します。

## 実行手順

1. `~/.claude/usage-tracker-logs/` ディレクトリにあるJSONLログファイルを読み込む
2. 指定された期間（デフォルト7日）のデータを集計
3. 以下の統計を計算して表示:
   - 総メッセージ数
   - ツール実行回数（種類別）
   - MCP呼び出し回数
   - セッション数
   - 最もよく使うツールTop 5
   - 日別の利用推移

## 出力フォーマット

```
📊 Claude Code 利用統計 (過去 N 日間)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 メッセージ数: XXX
🔧 ツール実行数: XXX
  - Bash: XX
  - Read: XX
  - Write: XX
  - Edit: XX
  ...
🔌 MCP呼び出し: XX
📦 Subagent: XX
💻 セッション数: XX

📈 日別推移:
  2024-01-01: ████████ 45
  2024-01-02: ██████████████ 78
  ...

🏆 よく使うツール Top 5:
  1. Bash (120回)
  2. Read (89回)
  ...
```

## 実装

以下のPythonスクリプトを実行してください:

```python
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

log_dir = Path.home() / ".claude" / "usage-tracker-logs"
days = 7  # デフォルト7日間

# 期間を計算
end_date = datetime.now()
start_date = end_date - timedelta(days=days)

# 統計用の変数
stats = {
    "messages": 0,
    "tools": defaultdict(int),
    "mcp": 0,
    "subagent": 0,
    "sessions": 0,
    "daily": defaultdict(int),
}

# ログファイルを読み込む
for log_file in log_dir.glob("events-*.jsonl"):
    with open(log_file, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                
                if ts.replace(tzinfo=None) < start_date:
                    continue
                
                event_type = event.get("event_type", "")
                date_str = ts.strftime("%Y-%m-%d")
                stats["daily"][date_str] += 1
                
                if event_type == "UserPromptSubmit":
                    stats["messages"] += 1
                elif event_type == "SessionStart":
                    stats["sessions"] += 1
                elif event_type in ["PostToolUse", "PreToolUse"]:
                    tool = event.get("tool_name", "unknown")
                    stats["tools"][tool] += 1
                    
                    categories = event.get("categories", {})
                    if categories.get("mcp"):
                        stats["mcp"] += 1
                    if categories.get("subagent"):
                        stats["subagent"] += 1
            except:
                pass

# 結果を表示
print(f"\n📊 Claude Code 利用統計 (過去 {days} 日間)")
print("━" * 40)
print(f"\n📝 メッセージ数: {stats['messages']}")
print(f"🔧 ツール実行数: {sum(stats['tools'].values())}")

for tool, count in sorted(stats["tools"].items(), key=lambda x: -x[1])[:10]:
    print(f"   - {tool}: {count}")

print(f"🔌 MCP呼び出し: {stats['mcp']}")
print(f"📦 Subagent: {stats['subagent']}")
print(f"💻 セッション数: {stats['sessions']}")

print("\n📈 日別推移:")
max_count = max(stats["daily"].values()) if stats["daily"] else 1
for date, count in sorted(stats["daily"].items()):
    bar = "█" * int(count / max_count * 20)
    print(f"   {date}: {bar} {count}")

print("\n🏆 よく使うツール Top 5:")
for i, (tool, count) in enumerate(sorted(stats["tools"].items(), key=lambda x: -x[1])[:5], 1):
    print(f"   {i}. {tool} ({count}回)")
```

ユーザーが日数を指定した場合は `days` 変数を調整してください。
