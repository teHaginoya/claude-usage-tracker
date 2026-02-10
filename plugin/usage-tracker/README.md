# Claude Code Usage Tracker Plugin

チームのClaude Code利用状況を収集・可視化するプラグインです。

## 🎯 機能

- **自動イベント収集**: Hookを使ってClaude Codeの操作を自動記録
- **プライバシー保護**: プロンプト内容やコードは送信せず、メタデータのみを収集
- **ローカル保存**: すべてのデータはまずローカルに保存
- **オプションのサーバー送信**: チーム集約用のAPIに送信可能
- **統計コマンド**: `/usage-stats` で自分の利用状況を確認

## 📊 収集するメトリクス

| メトリクス | 説明 |
|-----------|------|
| メッセージ数 | ユーザーのプロンプト送信回数 |
| ツール実行数 | Read, Write, Bash, Edit等の利用回数 |
| MCP呼び出し | MCPツールの呼び出し回数 |
| Subagent数 | サブエージェントの利用回数 |
| セッション数 | 作業セッションの数 |

## 🚀 インストール

### 方法1: マーケットプレイスから（推奨）

```bash
# Claude Codeで実行
/plugin marketplace add your-org/usage-tracker-marketplace
/plugin install usage-tracker@your-org
```

### 方法2: ローカルディレクトリから

```bash
# リポジトリをクローン
git clone https://github.com/your-org/claude-usage-tracker.git

# Claude Codeで実行
/plugin marketplace add ./claude-usage-tracker
/plugin install usage-tracker@claude-usage-tracker
```

## ⚙️ 設定

環境変数で設定を行います。`~/.bashrc` または `~/.zshrc` に追加してください:

```bash
# Usage Tracker 設定
export USAGE_TRACKER_API_ENDPOINT="https://your-api.example.com/api/events"
export USAGE_TRACKER_API_KEY="your-api-key"
export USAGE_TRACKER_TEAM_ID="your-team-id"

# オプション
export USAGE_TRACKER_ANONYMIZE="false"    # ユーザー名をハッシュ化
export USAGE_TRACKER_LOCAL_ONLY="false"   # ローカル保存のみ
```

## 📝 使い方

### コマンド

| コマンド | 説明 |
|---------|------|
| `/usage-stats` | 自分の利用統計を表示 |
| `/usage-config` | 設定を表示・変更 |
| `/usage-export` | データをCSV/JSONでエクスポート |

### 例

```bash
# 過去7日間の統計を表示
/usage-stats

# CSV形式でエクスポート
/usage-export
```

## 📁 データ保存場所

ログは以下のディレクトリに保存されます:

```
~/.claude/usage-tracker-logs/
├── events-2024-01-01.jsonl
├── events-2024-01-02.jsonl
├── ...
└── errors.log
```

## 🔒 プライバシー

このプラグインは以下のデータを**送信しません**:

- ❌ プロンプトの内容
- ❌ コードの内容
- ❌ ファイルの内容
- ❌ ツール出力の詳細

送信するのは以下のメタデータのみです:

- ✅ イベントタイプ（SessionStart, PostToolUse等）
- ✅ タイムスタンプ
- ✅ ツール名（Read, Write, Bash等）
- ✅ ユーザーID（匿名化オプションあり）
- ✅ プロンプト/出力の**長さ**のみ

## 🛠️ バックエンドAPI（オプション）

チーム全体の利用状況を集約するには、バックエンドAPIをデプロイしてください。

詳細は `server/` ディレクトリを参照してください。

## 📄 ライセンス

MIT License
