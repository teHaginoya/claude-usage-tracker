# Claude Code Usage Tracker - プロジェクトガイド

このリポジトリは、チームの Claude Code 利用状況を収集・可視化するためのツールセットです。

## 自動セットアップ（Claude が実行する手順）

ユーザーから「セットアップして」「usage tracker を設定して」等の依頼があった場合、
以下の手順を **Claude が自動で実行** してください。

### 前提条件の確認

- Windows PC であること
- このリポジトリがクローン済みであること（Claude Code が起動しているなら済み）

### Step 1: uv のインストール確認

```powershell
uv --version
```

未インストールの場合:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Hooks の設定（プラグインインストール相当）

`install_hooks.ps1` を実行して `~/.claude/settings.json` にフック設定を自動で書き込みます。
既存の `settings.json` がある場合は `hooks` キーのみ追加・上書きし、他の設定は保持されます。

```powershell
cd <リポジトリパス>/snowflake-upload
Unblock-File -Path .\install_hooks.ps1
.\install_hooks.ps1
```

#### スクリプトが失敗した場合の手動設定

`install_hooks.ps1` の実行に失敗した場合や、Claude Code が不安定になる場合は、
`~/.claude/settings.json` を直接編集してフック設定を追加してください。

1. `~/.claude/settings.json` を開く（なければ新規作成）
2. `hooks` キーに以下の設定を追加する（`<リポジトリパス>` は実際のパスに置換）

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type PreToolUse" }] }],
    "PostToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type PostToolUse" }] }],
    "Stop": [{ "matcher": "", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type Stop" }] }],
    "UserPromptSubmit": [{ "matcher": "", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type UserPromptSubmit" }] }],
    "SessionStart": [{ "matcher": "", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type SessionStart" }] }],
    "SessionEnd": [{ "matcher": "", "hooks": [{ "type": "command", "command": "uv run \"<リポジトリパス>/plugin/usage-tracker/scripts/send_event.py\" --event-type SessionEnd" }] }]
  }
}
```

> **Note**: 上記は主要な6イベントの例です。全14イベント（PostToolUseFailure, SubagentStart, SubagentStop, Notification, PreCompact, PermissionRequest, TeammateIdle, TaskCompleted）も同様に追加できます。
> Claude Code を再起動するとフックが有効になります。

### Step 3: Snowflake 環境変数の設定

ユーザーに Snowflake の LOGIN_NAME を聞いてください。
`IT.` 付きのメールアドレスです（例: `IT.YAMADA.TARO@IFTC.CO.JP`）。

```powershell
# アカウント識別子（全員共通）
[System.Environment]::SetEnvironmentVariable("SNOWFLAKE_ACCOUNT", "MYLMWWX-DPF002", "User")
# ユーザーの LOGIN_NAME
[System.Environment]::SetEnvironmentVariable("SNOWFLAKE_USER", "<ユーザーのLOGIN_NAME>", "User")
# 秘密鍵パス
[System.Environment]::SetEnvironmentVariable("SNOWFLAKE_PRIVATE_KEY_PATH", "$env:USERPROFILE\.snowflake\rsa_key.p8", "User")
# デフォルト値
[System.Environment]::SetEnvironmentVariable("SNOWFLAKE_WAREHOUSE", "CLAUDE_USAGE_WH", "User")
[System.Environment]::SetEnvironmentVariable("SNOWFLAKE_DATABASE", "CLAUDE_USAGE_DB", "User")
```

### Step 4: RSA キーペアの生成

```powershell
cd <リポジトリパス>/snowflake-upload
uv run upload_to_snowflake.py --action generate-key --no-input
```

### Step 5: 公開鍵の登録（ユーザーに手動操作を依頼）

生成された公開鍵ファイル (`~/.snowflake/rsa_key.pub`) を読み取り、
以下の SQL をユーザーに提示して Snowsight で実行してもらってください:

```sql
ALTER USER <ユーザー名> SET RSA_PUBLIC_KEY='<公開鍵の内容>';
```

ユーザーへの案内:
1. Snowsight (https://app.snowflake.com) にログイン
2. ワークシートを開く
3. 上記 SQL を貼り付けて実行

### Step 6: 接続テスト

ユーザーが公開鍵登録を完了したら:

```powershell
cd <リポジトリパス>/snowflake-upload
uv run upload_to_snowflake.py --action config
```

`[OK] 接続成功` と表示されれば成功です。
`USAGE_TRACKER_USER_ID` も自動設定されます。

### Step 7: タスクスケジューラ登録

```powershell
cd <リポジトリパス>/snowflake-upload
Unblock-File -Path .\setup_snowflake.ps1
.\setup_snowflake.ps1 -Action register-task
```

> **Note**: 旧 S3 タスク（`Claude Usage Log Upload`）が登録されている場合は、スクリプトが検出して削除するか確認します。

### Step 8: 完了確認

ユーザーに以下を伝えてください:
- セットアップ完了
- 今後は Claude Code を普通に使うだけでログが自動記録される
- 毎日午前3時に Snowflake に自動アップロードされる
- Claude Code を再起動すると hooks が有効になる

---

## 手動セットアップ

Claude を使わず手動でセットアップする場合は [セットアップガイド](docs/SETUP_GUIDE_FOR_TEAM.md) を参照してください。

## アーキテクチャ

```text
Claude Code → プラグイン(Hook) → JSONL ログ → Snowflake PUT → LAYER1 → LAYER2 → LAYER3
```

### データウェアハウス 3層構成

- **LAYER1 (Raw)**: Internal Stage + `RAW_EVENTS`（JSONL を VARIANT としてそのまま保持）
- **LAYER2 (Clean)**: `EVENTS`（カラム展開・SHA2 による重複排除・蓄積）
- **LAYER3 (Mart)**: `DAILY_SUMMARY`, `USER_SUMMARY`, `TOOL_SUMMARY` + 分析ビュー

### パイプライン

`upload_to_snowflake.py --action upload` が実行する処理:

1. `PUT` → `@LAYER1.CLAUDE_USAGE_INTERNAL_STAGE/{username}/`
2. `COPY INTO` → `LAYER1.RAW_EVENTS`
3. `MERGE INTO` → `LAYER2.EVENTS`（SHA2 ハッシュで重複排除）
4. `MERGE INTO` → `LAYER3.DAILY_SUMMARY`, `USER_SUMMARY`, `TOOL_SUMMARY`

## ディレクトリ構成

- `plugin/` - Claude Code プラグイン（Hook + スラッシュコマンド）
- `snowflake-upload/` - Snowflake アップロードスクリプト
  - `upload_to_snowflake.py` - メインパイプライン（uv run で実行）
  - `setup_snowflake.ps1` - セットアップ・タスク登録
- `snowflake/setup/` - Snowflake DDL / データロード SQL
- `snowflake/app/` - Streamlit in Snowflake ダッシュボード
- `docs/` - ドキュメント

## 認証方式

RSA キーペア認証を使用。パスワード認証は使用しません。

- 秘密鍵: `~/.snowflake/rsa_key.p8`
- 公開鍵: `~/.snowflake/rsa_key.pub`
- キーペア生成: `uv run upload_to_snowflake.py --action generate-key --no-input`

## 環境変数

| 変数名 | 必須 | デフォルト | 説明 |
| --- | --- | --- | --- |
| `SNOWFLAKE_ACCOUNT` | Yes | `MYLMWWX-DPF002` | Snowflake アカウント識別子（全員共通） |
| `SNOWFLAKE_USER` | Yes | - | Snowflake LOGIN_NAME |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | No | `~/.snowflake/rsa_key.p8` | 秘密鍵パス |
| `SNOWFLAKE_WAREHOUSE` | No | `CLAUDE_USAGE_WH` | ウェアハウス名 |
| `SNOWFLAKE_DATABASE` | No | `CLAUDE_USAGE_DB` | データベース名 |
| `USAGE_TRACKER_USER_ID` | Auto | - | 接続テスト時に自動設定 |

## Snowflake 管理者向け

運用管理については [管理者ガイド](docs/ADMIN_GUIDE.md) を参照してください。
