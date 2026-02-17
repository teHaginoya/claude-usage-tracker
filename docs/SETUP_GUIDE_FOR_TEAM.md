# Claude Code 利用状況トラッカー セットアップガイド

チームのClaude Code利用状況を収集・可視化するためのセットアップ手順です。
初心者の方でも順番通りに進めれば設定できます。

---

## 全体の流れ

```text
Step 1: 必要なツールのインストール（Git, uv, AWS CLI）
Step 2: リポジトリのクローン
Step 3: Claude Code プラグインのインストール
Step 4: AWS認証情報の設定
Step 5: 動作確認
Step 6: 自動アップロードの設定
```

---

## 事前に用意するもの

- Windows PC
- Claude Code がインストール済み
- 管理者から受け取るもの:
  - AWS Access Key ID
  - AWS Secret Access Key

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

`plugin/`, `s3-upload/`, `docs/` などのフォルダが表示されればOKです。

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

## Step 4: AWS CLIのインストールと認証情報の設定

### 4-1. s3-uploadフォルダに移動

```powershell
cd $env:USERPROFILE\claude-usage-tracker\s3-upload
```

### 4-2. スクリプトのブロックを解除

```powershell
Unblock-File -Path $env:USERPROFILE\claude-usage-tracker\s3-upload\setup_and_upload.ps1
```

### 4-3. AWS CLIをインストール

```powershell
.\setup_and_upload.ps1 -Action setup-aws
```

「AWS credentials already configured」と表示されたり、認証情報の入力を求められたりした場合は、スキップまたは後の手順で設定します。
AWS CLIが既にインストール済みの場合は自動でスキップされます。

### 4-4. 環境変数を設定

S3バケット名はリポジトリの `s3-upload/config.json` に設定済みなので、自動で読み込まれます。

```powershell
.\setup_and_upload.ps1 -Action setup-local
```

途中で以下のように聞かれます:

```text
Enter your user ID (e.g. yamada.taro): （自分の名前を入力、例: yamada.taro）
```

ここで入力した名前がS3のファイル名に使われます。
例: `yamada.taro-events-20260217.jsonl`

### 4-5. AWS認証情報を設定

PowerShellで以下を実行:

```powershell
aws configure
```

順番に入力:

```text
AWS Access Key ID [None]: （管理者から受け取ったアクセスキー）
AWS Secret Access Key [None]: （管理者から受け取ったシークレットキー）
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

---

## Step 5: 動作確認

### 5-1. ログファイルがあるか確認

```powershell
dir $env:USERPROFILE\.claude\usage-tracker-logs\
```

`events-2026-XX-XX.jsonl` のようなファイルがあればOKです。

※ ファイルがない場合は、Claude Codeを少し使ってから再確認してください。

### 5-2. S3にアップロードしてみる

```powershell
cd $env:USERPROFILE\claude-usage-tracker\s3-upload
.\setup_and_upload.ps1 -Action upload
```

「[UP] events-XXXX-XX-XX.jsonl → s3://...」と表示され、
「OK」が出れば成功です。

### 5-3. アップロードされたか確認

```powershell
aws s3 ls s3://claude-activity-log-632903090408/claude-usage-logs/ --recursive
```

ファイルが表示されればOKです。

---

## Step 6: 自動アップロードの設定（オプション）

毎日自動でログをアップロードする設定です。

### 6-1. タスクスケジューラに登録

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File $env:USERPROFILE\claude-usage-tracker\s3-upload\setup_and_upload.ps1 -Action upload"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "Claude Usage Log Upload" -Action $action -Trigger $trigger -Settings $settings -Description "Claude Codeの利用ログをS3にアップロード"
```

### 6-2. 登録されたか確認

```powershell
Get-ScheduledTask -TaskName "Claude Usage Log Upload"
```

「Ready」と表示されればOKです。

---

## セットアップ完了

これで設定は完了です。

### 今後の使い方

- **普段使い**: いつも通りClaude Codeを使うだけでOK
  - ログは自動で記録されます
  - 毎日午前3時に自動でS3にアップロードされます（Step 6を実施した場合）

- **手動でアップロードしたい時**:

  ```powershell
  cd $env:USERPROFILE\claude-usage-tracker\s3-upload
  .\setup_and_upload.ps1 -Action upload
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
Unblock-File -Path $env:USERPROFILE\claude-usage-tracker\s3-upload\setup_and_upload.ps1
```

### 「Access Denied」

→ AWS認証情報が正しく設定されていません。管理者に確認してください。

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

---

## サポート

問題が解決しない場合は、以下の情報を添えて管理者に連絡してください:

1. エラーメッセージのスクリーンショット
2. 実行したコマンド
3. どのステップで止まったか
