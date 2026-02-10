# Claude Code 利用状況トラッカー セットアップガイド

チームのClaude Code利用状況を収集・可視化するためのセットアップ手順です。
初心者の方でも順番通りに進めれば設定できます。

---

## 📋 全体の流れ

```
Step 1: 必要なツールのインストール（uv, AWS CLI）
Step 2: Claude Code プラグインのインストール
Step 3: S3アップロードツールのセットアップ
Step 4: AWS認証情報の設定
Step 5: 動作確認
Step 6: 自動アップロードの設定
```

所要時間: 約30分

---

## 📦 事前に用意するもの

- [ ] Windows PC
- [ ] Claude Code がインストール済み
- [ ] 管理者から受け取るもの:
  - AWS Access Key ID
  - AWS Secret Access Key
  - S3バケット名

---

## Step 1: 必要なツールのインストール

### 1-1. PowerShellを開く

1. Windowsキーを押す
2. 「PowerShell」と入力
3. 「Windows PowerShell」をクリックして開く

### 1-2. uv をインストール

以下のコマンドをコピーしてPowerShellに貼り付け、Enterを押します。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

「everything's installed!」と表示されたら成功です。

### 1-3. PowerShellを再起動

1. PowerShellを閉じる（×ボタン）
2. もう一度PowerShellを開く

### 1-4. uvがインストールされたか確認

```powershell
uv --version
```

「uv 0.x.x」のようにバージョンが表示されればOKです。

---

## Step 2: Claude Code プラグインのインストール

### 2-1. プラグインファイルを配置

1. 管理者から受け取った `usage-tracker-plugin.zip` をダウンロード
2. ZIPファイルを右クリック → 「すべて展開」
3. 展開先を `C:\Users\あなたのユーザー名\` に設定
4. 「展開」をクリック

結果: `C:\Users\あなたのユーザー名\usage-tracker-marketplace` フォルダができます

### 2-2. Claude Code を起動

```powershell
claude
```

### 2-3. マーケットプレイスを追加

Claude Codeの中で以下を入力:

```
/plugin marketplace add ./usage-tracker-marketplace
```

※ 先にホームフォルダに移動してください:
```powershell
cd $env:USERPROFILE
claude
```

### 2-4. プラグインをインストール

```
/plugin install usage-tracker@usage-tracker-marketplace
```

メニューが表示されたら:
- 「Install for you (user scope)」を選択
- Enterを押す

### 2-5. Claude Codeを再起動

```
exit
```

でClaude Codeを終了し、再度起動:

```powershell
claude
```

### 2-6. 動作確認

```
/usage-stats
```

「ログディレクトリが見つかりません」または統計が表示されればOKです。

---

## Step 3: S3アップロードツールのセットアップ

### 3-1. アップロードツールを配置

1. 管理者から受け取った `s3-upload-tools.zip` をダウンロード
2. ZIPファイルを右クリック → 「すべて展開」
3. 展開先を `C:\Users\あなたのユーザー名\` に設定
4. 「展開」をクリック

結果: `C:\Users\あなたのユーザー名\s3-upload` フォルダができます

### 3-2. 実行ポリシーを変更

PowerShellで以下を実行:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

「実行ポリシーを変更しますか?」と聞かれたら `Y` を入力してEnter

### 3-3. ファイルのブロックを解除

```powershell
Unblock-File -Path $env:USERPROFILE\s3-upload\setup_and_upload.ps1
```

---

## Step 4: AWS認証情報の設定

### 4-1. s3-uploadフォルダに移動

```powershell
cd $env:USERPROFILE\s3-upload
```

### 4-2. セットアップスクリプトを実行

```powershell
.\setup_and_upload.ps1 -Action setup-local
```

### 4-3. S3バケット名を入力

「Enter S3 bucket name」と表示されたら、管理者から受け取ったバケット名を入力:

```
Enter S3 bucket name: claude-activity-log-XXXXXXXXXXXX
```

（XXXXXXXXXXXXの部分は管理者から伝えられた値）

### 4-4. AWS認証情報を設定

PowerShellで以下を実行:

```powershell
aws configure
```

順番に入力:
```
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
cd $env:USERPROFILE\s3-upload
.\setup_and_upload.ps1 -Action upload
```

「[UP] events-XXXX-XX-XX.jsonl → s3://...」と表示され、
「OK」が出れば成功です！

### 5-3. アップロードされたか確認

```powershell
aws s3 ls s3://claude-activity-log-XXXXXXXXXXXX/claude-usage-logs/ --recursive
```

ファイルが表示されればOKです。

---

## Step 6: 自動アップロードの設定（オプション）

毎日自動でログをアップロードする設定です。

### 6-1. タスクスケジューラに登録

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File $env:USERPROFILE\s3-upload\setup_and_upload.ps1 -Action upload"
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

## ✅ セットアップ完了！

これで設定は完了です。

### 今後の使い方

- **普段使い**: いつも通りClaude Codeを使うだけでOK
  - ログは自動で記録されます
  - 毎日午前3時に自動でS3にアップロードされます

- **手動でアップロードしたい時**:
  ```powershell
  cd $env:USERPROFILE\s3-upload
  .\setup_and_upload.ps1 -Action upload
  ```

- **自分の統計を見たい時**:
  Claude Codeで `/usage-stats` を実行

---

## ❓ トラブルシューティング

### 「uv が認識されません」

→ PowerShellを再起動してください

### 「スクリプトの実行が無効です」

→ 以下を実行:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 「デジタル署名されていません」

→ 以下を実行:
```powershell
Unblock-File -Path $env:USERPROFILE\s3-upload\setup_and_upload.ps1
```

### 「Access Denied」

→ AWS認証情報が正しく設定されていません。管理者に確認してください。

### 「ログファイルが見つからない」

→ Claude Codeを少し使ってから再確認してください。
   プラグインが正しくインストールされているか確認:
   ```
   /plugin
   ```
   → 「Installed」タブに「usage-tracker」があればOK

### PCを再起動したらエラーが出る

→ 環境変数が読み込まれていない可能性があります。
   PowerShellを新しく開いて再度お試しください。

---

## 📞 サポート

問題が解決しない場合は、以下の情報を添えて管理者に連絡してください:

1. エラーメッセージのスクリーンショット
2. 実行したコマンド
3. どのステップで止まったか
