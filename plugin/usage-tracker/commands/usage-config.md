---
description: Usage Trackerの設定を表示・変更します。APIエンドポイント、チームID、匿名化設定などを管理できます。
allowed-tools: Bash
---

# Usage Config Command

Usage Trackerプラグインの設定を管理します。

## 設定項目

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `USAGE_TRACKER_API_ENDPOINT` | データ送信先のAPIエンドポイント | `https://your-api-endpoint.run.app/api/events` |
| `USAGE_TRACKER_API_KEY` | API認証キー | (空) |
| `USAGE_TRACKER_TEAM_ID` | チーム識別子 | `default-team` |
| `USAGE_TRACKER_ANONYMIZE` | ユーザー名をハッシュ化するか | `false` |
| `USAGE_TRACKER_LOCAL_ONLY` | ローカル保存のみ（送信しない） | `false` |

## 操作

### 現在の設定を表示

```bash
echo "📋 Usage Tracker 設定"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "API Endpoint: ${USAGE_TRACKER_API_ENDPOINT:-https://your-api-endpoint.run.app/api/events}"
echo "API Key: ${USAGE_TRACKER_API_KEY:-(未設定)}"
echo "Team ID: ${USAGE_TRACKER_TEAM_ID:-default-team}"
echo "Anonymize: ${USAGE_TRACKER_ANONYMIZE:-false}"
echo "Local Only: ${USAGE_TRACKER_LOCAL_ONLY:-false}"
echo ""
echo "📁 ログ保存先: ~/.claude/usage-tracker-logs/"
```

### 設定を変更するには

ユーザーに以下のガイダンスを表示:

```
設定を変更するには、シェルの設定ファイル（~/.bashrc または ~/.zshrc）に
以下の環境変数を追加してください:

# Usage Tracker 設定
export USAGE_TRACKER_API_ENDPOINT="https://your-api.example.com/api/events"
export USAGE_TRACKER_API_KEY="your-api-key"
export USAGE_TRACKER_TEAM_ID="your-team-id"
export USAGE_TRACKER_ANONYMIZE="false"
export USAGE_TRACKER_LOCAL_ONLY="false"

設定後、シェルを再起動するか `source ~/.bashrc` を実行してください。
```

## ユーザーの意図に応じた対応

- 「設定を見せて」→ 現在の設定を表示
- 「チームIDを変えたい」→ 環境変数の設定方法を案内
- 「ローカルだけで使いたい」→ `USAGE_TRACKER_LOCAL_ONLY=true` の設定を案内
- 「匿名化したい」→ `USAGE_TRACKER_ANONYMIZE=true` の設定を案内
