---
description: 利用統計データをCSVまたはJSON形式でエクスポートします。チーム全体の分析やダッシュボード連携に使用できます。
allowed-tools: Bash, Write
---

# Usage Export Command

ローカルに保存された利用統計データをエクスポートします。

## エクスポート形式

- **CSV**: スプレッドシートでの分析用
- **JSON**: ダッシュボードやAPIとの連携用

## 実行手順

1. ユーザーに形式（CSV/JSON）と出力先を確認
2. ログファイルを読み込んでデータを整形
3. 指定された形式でファイルを出力

## 実装

### JSON形式でエクスポート

```python
import json
from pathlib import Path
from datetime import datetime

log_dir = Path.home() / ".claude" / "usage-tracker-logs"
output_file = Path.cwd() / f"claude-usage-export-{datetime.now().strftime('%Y%m%d')}.json"

events = []
for log_file in sorted(log_dir.glob("events-*.jsonl")):
    with open(log_file, "r") as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except:
                pass

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)

print(f"✅ エクスポート完了: {output_file}")
print(f"   イベント数: {len(events)}")
```

### CSV形式でエクスポート

```python
import json
import csv
from pathlib import Path
from datetime import datetime

log_dir = Path.home() / ".claude" / "usage-tracker-logs"
output_file = Path.cwd() / f"claude-usage-export-{datetime.now().strftime('%Y%m%d')}.csv"

events = []
for log_file in sorted(log_dir.glob("events-*.jsonl")):
    with open(log_file, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                flat_event = {
                    "timestamp": event.get("timestamp", ""),
                    "event_type": event.get("event_type", ""),
                    "user_id": event.get("user_id", ""),
                    "team_id": event.get("team_id", ""),
                    "project": event.get("project", ""),
                    "session_id": event.get("session_id", ""),
                    "tool_name": event.get("tool_name", ""),
                    "success": event.get("success", ""),
                    "is_mcp": event.get("categories", {}).get("mcp", False),
                    "is_subagent": event.get("categories", {}).get("subagent", False),
                    "is_command": event.get("categories", {}).get("command", False),
                }
                events.append(flat_event)
            except:
                pass

if events:
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)

print(f"✅ エクスポート完了: {output_file}")
print(f"   イベント数: {len(events)}")
```

## ユーザーの意図に応じた対応

- 「CSVで出力して」→ CSV形式でエクスポート
- 「JSONで出力して」→ JSON形式でエクスポート
- 「スプレッドシートで分析したい」→ CSV形式を推奨
- 「ダッシュボードに送りたい」→ JSON形式を推奨
- 特に指定がない場合 → 両方の選択肢を提示
