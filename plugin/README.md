# Usage Tracker Marketplace

Claude Code利用状況追跡プラグインのマーケットプレイスです。

## 🚀 インストール方法

### 1. マーケットプレイスを追加

```bash
# Claude Codeで実行
/plugin marketplace add your-org/usage-tracker-marketplace
```

または、ローカルでテストする場合:

```bash
git clone https://github.com/your-org/usage-tracker-marketplace.git
cd usage-tracker-marketplace
claude
/plugin marketplace add ./
```

### 2. プラグインをインストール

```bash
/plugin install usage-tracker@usage-tracker-marketplace
```

### 3. Claude Codeを再起動

プラグインを有効化するためにClaude Codeを再起動してください。

## 📦 含まれるプラグイン

### usage-tracker

チームのClaude Code利用状況を収集・可視化するプラグイン

**機能:**
- 自動イベント収集（Hook）
- 統計表示コマンド (`/usage-stats`)
- 設定管理コマンド (`/usage-config`)
- データエクスポート (`/usage-export`)

詳細は [usage-tracker/README.md](./usage-tracker/README.md) を参照してください。

## 🔧 チーム向け設定

チーム全体にプラグインを自動配布するには、リポジトリの `.claude/settings.json` に以下を追加:

```json
{
  "plugins": {
    "marketplaces": [
      {
        "source": "your-org/usage-tracker-marketplace",
        "plugins": ["usage-tracker"]
      }
    ]
  }
}
```

## 📊 バックエンドサーバー（オプション）

チーム全体のデータを集約するには、`usage-tracker/server/` のAPIをデプロイしてください。

### Cloud Runへのデプロイ

```bash
cd usage-tracker/server
gcloud run deploy usage-tracker-api \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 環境変数設定

デプロイ後、チームメンバーに以下の環境変数を設定してもらいます:

```bash
export USAGE_TRACKER_API_ENDPOINT="https://your-api.run.app/api/events"
export USAGE_TRACKER_TEAM_ID="your-team-id"
```
