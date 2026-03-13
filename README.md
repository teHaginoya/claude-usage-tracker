# Claude Code Usage Tracker

チームのClaude Code利用状況を収集・可視化するためのツールセットです。

## 概要

Claude Codeの利用ログをローカルに記録し、Snowflake内部ステージに直接アップロードします。
3層データウェアハウス構成で分析・可視化を行います。

```
Claude Code → ローカルログ → Snowflake Internal Stage → Snowflake → Streamlit
 (プラグイン)   (自動記録)    (PUT / キーペア認証)        (分析DB)   (ダッシュボード)
```

### データウェアハウス構成

```
LAYER1 (Raw)   : Internal Stage + RAW_EVENTS（JSONL をそのまま VARIANT で保持）
LAYER2 (Clean) : EVENTS（カラム展開・SHA2 による重複排除・蓄積）
LAYER3 (Mart)  : DAILY/USER/TOOL_SUMMARY + 分析ビュー
```

## セットアップ

詳細な手順は [セットアップガイド](docs/SETUP_GUIDE_FOR_TEAM.md) を参照してください。

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
├── snowflake-upload/         # Snowflake アップロードツール
│   ├── upload_to_snowflake.py  # PUT + COPY + MERGE パイプライン
│   └── setup_snowflake.ps1     # セットアップ・タスク登録
├── snowflake/                # Snowflake + Streamlit
│   ├── app/                  # Streamlit in Snowflake アプリ
│   │   ├── streamlit_app.py
│   │   ├── queries.py
│   │   ├── tab_sessions.py
│   │   └── tab_roi.py
│   └── setup/                # テーブル作成・データロードSQL
│       ├── 01_create_tables.sql
│       ├── 02_load_data.sql
│       ├── 03_create_streamlit.sql
│       └── 04_create_analytical_tables.sql
├── s3-upload/                # (旧) S3アップロード ※廃止予定
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
| スキル利用数 | スキル（スラッシュコマンド）の利用回数 |
| ファイル操作数 | ファイル読み書き操作の回数 |

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
- ユーザーID（Snowflakeユーザー名）
- プロンプト/出力の長さのみ
