# Claude Code 利用状況トラッカー セットアップガイド

チームのClaude Code利用状況を収集・可視化するためのセットアップ手順です。
初心者の方でも順番通りに進めれば設定できます。

---

## 全体の流れ

```text
Step 1: 必要なツールのインストール（Git, uv）
Step 2: リポジトリのクローン
Step 3: Claude Code プラグインのインストール
Step 4: Snowflake キーペア認証の設定
Step 5: 動作確認
Step 6: 自動アップロードの設定
```

---

## 事前に用意するもの

- Windows PC
- Claude Code がインストール済み
- 自分の Snowflake ユーザー名（LOGIN_NAME）を把握していること

---

## Step 1: 必要なツールのインストール

### 1-1. PowerShellを開く

1. Windowsキーを押す
2. 「PowerShell」と入力
3. 「Windows PowerShell」をクリックして開く

### 1-2. Git をインストール（未インストールの場合）

インストール済みか確認:

```powershell
git --version
```

「git version x.x.x」と表示されれば既にインストール済みです。
表示されない場合は [https://git-scm.com/download/win](https://git-scm.com/download/win) からインストールしてください。

### 1-3. uv をインストール

以下のコマンドをコピーしてPowerShellに貼り付け、Enterを押します。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

「everything's installed!」と表示されたら成功です。

### 1-4. PowerShellを再起動

1. PowerShellを閉じる（×ボタン）
2. もう一度PowerShellを開く

### 1-5. インストール確認

```powershell
uv --version
git --version
```

それぞれバージョンが表示されればOKです。

---

## Step 2: リポジトリのクローン

### 2-1. ホームフォルダに移動

```powershell
cd $env:USERPROFILE
```

### 2-2. リポジトリをクローン

```powershell
git clone https://github.com/teHaginoya/claude-usage-tracker.git
```

完了すると `claude-usage-tracker` フォルダが作成されます。

### 2-3. クローンできたか確認

```powershell
dir $env:USERPROFILE\claude-usage-tracker
```

`plugin/`, `snowflake-upload/`, `docs/` などのフォルダが表示されればOKです。

---

## Step 3: Claude Code プラグインのインストール

### 3-1. PowerShell実行ポリシーを変更

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

「実行ポリシーを変更しますか?」と聞かれたら `Y` を入力してEnter。

### 3-2. ホームフォルダでClaude Codeを起動

```powershell
cd $env:USERPROFILE
claude
```

### 3-3. マーケットプレイスを追加

Claude Codeの中で以下を入力:

```text
/plugin marketplace add ./claude-usage-tracker/plugin
```

### 3-4. プラグインをインストール

```text
/plugin install usage-tracker@usage-tracker-marketplace
```

メニューが表示されたら:

- 「Install for you (user scope)」を選択
- Enterを押す

### 3-5. Claude Codeを再起動

```text
exit
```

でClaude Codeを終了し、再度起動:

```powershell
claude
```

### 3-6. 動作確認

```text
/usage-stats
```

「ログディレクトリが見つかりません」または統計が表示されればOKです。

---

## Step 4: Snowflake キーペア認証の設定

### 4-1. snowflake-uploadフォルダに移動

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
```

### 4-2. スクリプトのブロックを解除

```powershell
Unblock-File -Path $env:USERPROFILE\claude-usage-tracker\snowflake-upload\setup_snowflake.ps1
```

### 4-3. セットアップを実行

```powershell
.\setup_snowflake.ps1 -Action setup
```

対話形式で以下を入力します:

```text
Snowflake アカウント識別子: MYLMWWX-DPF002（全員共通、そのままEnterでOK）
Snowflake ユーザー名: （自分の LOGIN_NAME、例: IT.YAMADA.TARO@IFTC.CO.JP）
```

セットアップ中に RSA キーペアが自動生成され、公開鍵が表示されます。

> **Note**: ユーザーIDは Snowflake の `CURRENT_USER()` から自動取得されるため、手動入力は不要です。
> 接続テスト成功後に `USAGE_TRACKER_USER_ID` が自動設定されます。

### 4-4. 公開鍵を Snowflake に登録する

セットアップ中に表示された公開鍵（1行の長い文字列）を Snowflake に登録します。
Snowflake の Web UI（Snowsight）にログインし、ワークシートで以下の SQL を実行してください:

```sql
ALTER USER <自分のユーザー名> SET RSA_PUBLIC_KEY='ここに表示された公開鍵を貼り付け';
```

> **Tip**: 公開鍵は `~/.snowflake/rsa_key.pub` にも保存されています。後から確認できます。

### 4-5. 接続テスト

公開鍵の登録が完了したら、接続テストを実行:

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
.\setup_snowflake.ps1 -Action upload
```

「[OK] 接続成功」「[OK] COPY INTO 完了」と表示されれば成功です。

---

## Step 5: 動作確認

### 5-1. ログファイルがあるか確認

```powershell
dir $env:USERPROFILE\.claude\usage-tracker-logs\
```

`events-2026-XX-XX.jsonl` のようなファイルがあればOKです。

※ ファイルがない場合は、Claude Codeを少し使ってから再確認してください。

### 5-2. Snowflakeにアップロードしてみる

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
.\setup_snowflake.ps1 -Action upload
```

「[UP] events-XXXX-XX-XX.jsonl -> @CLAUDE_USAGE_INTERNAL_STAGE/...」と表示され、
「[OK] 完了」が出れば成功です。

### 5-3. ログファイルの一覧を確認

```powershell
uv run upload_to_snowflake.py --action list
```

各ファイルの横に `[済]` / `[未]` が表示されます。

---

## Step 6: 自動アップロードの設定（オプション）

毎日自動でログをSnowflakeにアップロードする設定です。

### 6-1. タスクスケジューラに登録

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
.\setup_snowflake.ps1 -Action register-task
```

旧S3アップロードタスクがある場合は削除するか聞かれます。

### 6-2. 登録されたか確認

```powershell
Get-ScheduledTask -TaskName "Claude Usage Snowflake Upload"
```

「Ready」と表示されればOKです。

---

## セットアップ完了

これで設定は完了です。

### 今後の使い方

- **普段使い**: いつも通りClaude Codeを使うだけでOK
  - ログは自動で記録されます
  - 毎日午前3時に自動でSnowflakeにアップロードされます（Step 6を実施した場合）

- **手動でアップロードしたい時**:

  ```powershell
  cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
  .\setup_snowflake.ps1 -Action upload
  ```

- **自分の統計を見たい時**:
  Claude Codeで `/usage-stats` を実行

---

## トラブルシューティング

### 「git が認識されません」

→ Gitをインストール後、PowerShellを再起動してください。

### 「uv が認識されません」

→ PowerShellを再起動してください。

### 「スクリプトの実行が無効です」

→ 以下を実行:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 「デジタル署名されていません」

→ 以下を実行:

```powershell
Unblock-File -Path $env:USERPROFILE\claude-usage-tracker\snowflake-upload\setup_snowflake.ps1
```

### Snowflake 接続エラー

→ 以下を確認してください:

1. Snowsight で `ALTER USER SET RSA_PUBLIC_KEY` を実行済みか
2. `SNOWFLAKE_ACCOUNT` / `SNOWFLAKE_USER` が正しく設定されているか
3. 秘密鍵ファイルが `~/.snowflake/rsa_key.p8` に存在するか

設定確認:

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
uv run upload_to_snowflake.py --action config
```

### 「秘密鍵が見つかりません」

→ キーペアを再生成してください:

```powershell
cd $env:USERPROFILE\claude-usage-tracker\snowflake-upload
uv run upload_to_snowflake.py --action generate-key
```

生成後、新しい公開鍵を管理者に渡して再登録してもらってください。

### 「ログファイルが見つからない」

→ Claude Codeを少し使ってから再確認してください。
プラグインが正しくインストールされているか確認:

```text
/plugin
```

→ 「Installed」タブに「usage-tracker」があればOK

### PCを再起動したらエラーが出る

→ 環境変数が読み込まれていない可能性があります。
PowerShellを新しく開いて再度お試しください。

### errors.log にSSL接続エラーが大量に記録される

→ 古いバージョンのプラグインを使っている可能性があります。
最新版では `USAGE_TRACKER_LOCAL_ONLY` のデフォルトが `true` に変更されています。
`git pull` でリポジトリを更新し、プラグインを再インストールしてください。

### Stopフックで UnicodeEncodeError が出る

→ Windows日本語環境でパス文字列にサロゲート文字が含まれる場合に発生します。
最新版では `errors="replace"` で対処済みです。
`git pull` でリポジトリを更新し、プラグインを再インストールしてください。

### COPY INTO で 0 rows loaded と表示される

→ ファイルが既にロード済みの可能性があります。
強制再アップロードする場合:

```powershell
uv run upload_to_snowflake.py --action upload --force
```

---

## サポート

問題が解決しない場合は、以下の情報を添えて管理者に連絡してください:

1. エラーメッセージのスクリーンショット
2. 実行したコマンド
3. どのステップで止まったか
