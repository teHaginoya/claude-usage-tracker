# Claude Code Usage Tracker

チームのClaude Code利用状況を収集・可視化するためのツールセットです。

## 概要

Claude Codeの利用ログをローカルに記録し、Amazon S3にアップロードします。
収集したデータはSnowflakeとStreamlitで可視化できます。

```
Claude Code → ローカルログ → Amazon S3 → TROCCO → Snowflake → Streamlit
 (プラグイン)   (自動記録)    (アップロード)  (連携)     (分析DB)   (ダッシュボード)
```

## セットアップ

詳細な手順は [セットアップガイド](docs/SETUP_GUIDE_FOR_TEAM.md) を参照してください。

リポジトリをクローンするだけで全ての資材が揃います:

```powershell
git clone https://github.com/teHaginoya/claude-usage-tracker.git
```

## ディレクトリ構成

```text
claude-usage-tracker/
├── plugin/                   # Claude Code プラグイン
│   ├── .claude-plugin/
│   │   └── marketplace.json  # マーケットプレイス定義
│   └── usage-tracker/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/         # スラッシュコマンド
│       ├── hooks/            # イベント収集Hook
│       └── scripts/          # イベント送信スクリプト
├── s3-upload/                # S3アップロードツール
│   └── setup_and_upload.ps1
├── snowflake/                # Snowflake + Streamlit
│   ├── docs/                 # 参考図・設計資料
│   ├── app/                  # Streamlitアプリのコード
│   │   └── 03_streamlit_app.py
│   ├── setup/                # テーブル作成・データロードSQL
│   │   ├── 01_create_tables.sql
│   │   └── 02_load_data.sql
│   └── skills/               # Claude Code スキルファイル
└── docs/                     # ドキュメント
    └── SETUP_GUIDE_FOR_TEAM.md
```

## 収集するメトリクス

| メトリクス | 説明 |
|---|---|
| メッセージ数 | ユーザーのプロンプト送信回数 |
| ツール実行数 | Read, Write, Bash, Edit 等の利用回数 |
| MCP呼び出し数 | MCPツールの呼び出し回数 |
| Subagent数 | サブエージェントの利用回数 |
| セッション数 | 作業セッションの数 |

## プライバシーについて

以下のデータは**収集・送信しません**:

- プロンプトの内容
- コードの内容
- ファイルの内容
- ツール出力の詳細

収集するのは以下のメタデータのみです:

- イベントタイプ（SessionStart, PostToolUse 等）
- タイムスタンプ
- ツール名（Read, Write, Bash 等）
- ユーザーID
- プロンプト/出力の長さのみ

## S3フォルダ構成

```text
s3://claude-activity-log-632903090408/
└── claude-usage-logs/
    └── {yyyyMMdd}/
        └── {IAMユーザー名}-events-{yyyyMMdd}.jsonl
```
