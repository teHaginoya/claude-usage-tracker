<#
.SYNOPSIS
    Claude Code Usage Tracker - Snowflake Setup and Upload
.DESCRIPTION
    Snowflake キーペア認証の設定、ログアップロード、タスクスケジューラ登録を行う。
.PARAMETER Action
    Action to perform: setup, upload, register-task, unregister-task
.PARAMETER Force
    Force upload even if already uploaded
#>

param(
    [ValidateSet("setup", "upload", "register-task", "unregister-task")]
    [string]$Action = "setup",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# タスクスケジューラ実行時にユーザー環境変数を確実に読み込む
foreach ($varName in @(
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH",
    "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "USAGE_TRACKER_USER_ID"
)) {
    if (-not [Environment]::GetEnvironmentVariable($varName, "Process")) {
        $userVal = [Environment]::GetEnvironmentVariable($varName, "User")
        if ($userVal) { [Environment]::SetEnvironmentVariable($varName, $userVal, "Process") }
    }
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Command)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Stop"
    try {
        if (Get-Command $Command) { return $true }
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

function Get-UvPath {
    try {
        $cmd = Get-Command uv -ErrorAction Stop
        return $cmd.Source
    } catch {
        # よくあるインストール先を探す
        $candidates = @(
            "$env:USERPROFILE\.local\bin\uv.exe",
            "$env:USERPROFILE\.cargo\bin\uv.exe"
        )
        foreach ($c in $candidates) {
            if (Test-Path $c) { return $c }
        }
        return $null
    }
}

$ScriptDir = $PSScriptRoot
$PythonScript = Join-Path $ScriptDir "upload_to_snowflake.py"

# =====================================================================
# Action: setup
# =====================================================================
function Invoke-Setup {
    Write-Step "Snowflake 接続設定"

    # uv チェック
    if (-not (Test-CommandExists "uv")) {
        Write-Fail "uv がインストールされていません"
        Write-Info "インストール: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
        return
    }
    Write-Success "uv が見つかりました"

    # 環境変数の設定
    Write-Host ""
    Write-Host "Snowflake の接続情報を設定します。"
    Write-Host ""

    # SNOWFLAKE_ACCOUNT (チーム共通)
    $defaultAccount = "MYLMWWX-DPF002"
    $current = [Environment]::GetEnvironmentVariable("SNOWFLAKE_ACCOUNT", "User")
    if ($current) {
        Write-Info "現在の設定: SNOWFLAKE_ACCOUNT = $current"
        $change = Read-Host "変更しますか？ (y/N)"
        if ($change -eq "y") { $current = $null }
    }
    if (-not $current) {
        $val = Read-Host "Snowflake アカウント識別子 (Enter でデフォルト: $defaultAccount)"
        if (-not $val) { $val = $defaultAccount }
        [System.Environment]::SetEnvironmentVariable("SNOWFLAKE_ACCOUNT", $val, "User")
        $env:SNOWFLAKE_ACCOUNT = $val
        Write-Success "SNOWFLAKE_ACCOUNT = $val"
    }

    # SNOWFLAKE_USER
    $current = [Environment]::GetEnvironmentVariable("SNOWFLAKE_USER", "User")
    if ($current) {
        Write-Info "現在の設定: SNOWFLAKE_USER = $current"
        $change = Read-Host "変更しますか？ (y/N)"
        if ($change -eq "y") { $current = $null }
    }
    if (-not $current) {
        $val = Read-Host "Snowflake ユーザー名"
        if ($val) {
            [System.Environment]::SetEnvironmentVariable("SNOWFLAKE_USER", $val, "User")
            $env:SNOWFLAKE_USER = $val
            Write-Success "SNOWFLAKE_USER = $val"
        }
    }

    # USAGE_TRACKER_USER_ID は接続テスト後に Snowflake の CURRENT_USER() から自動設定
    $current = [Environment]::GetEnvironmentVariable("USAGE_TRACKER_USER_ID", "User")
    if ($current) {
        Write-Success "USAGE_TRACKER_USER_ID = $current (設定済み)"
    } else {
        Write-Info "USAGE_TRACKER_USER_ID は接続テスト成功後に自動設定されます"
    }

    # オプション: ウェアハウス・DB・スキーマ (デフォルトあり)
    foreach ($item in @(
        @{ Name="SNOWFLAKE_WAREHOUSE"; Default="CLAUDE_USAGE_WH"; Label="ウェアハウス名" },
        @{ Name="SNOWFLAKE_DATABASE";  Default="CLAUDE_USAGE_DB"; Label="データベース名" },
        @{ Name="SNOWFLAKE_SCHEMA";    Default="LAYER3";          Label="スキーマ名" }
    )) {
        $current = [Environment]::GetEnvironmentVariable($item.Name, "User")
        if (-not $current) {
            [System.Environment]::SetEnvironmentVariable($item.Name, $item.Default, "User")
            [Environment]::SetEnvironmentVariable($item.Name, $item.Default, "Process")
            Write-Success "$($item.Name) = $($item.Default) (デフォルト)"
        } else {
            Write-Success "$($item.Name) = $current (設定済み)"
        }
    }

    # キーペア生成
    Write-Step "RSA キーペア生成"

    $keyPath = [Environment]::GetEnvironmentVariable("SNOWFLAKE_PRIVATE_KEY_PATH", "User")
    if (-not $keyPath) {
        $keyPath = Join-Path $env:USERPROFILE ".snowflake\rsa_key.p8"
        [System.Environment]::SetEnvironmentVariable("SNOWFLAKE_PRIVATE_KEY_PATH", $keyPath, "User")
        $env:SNOWFLAKE_PRIVATE_KEY_PATH = $keyPath
    }

    Write-Info "キーペア生成には Python の cryptography ライブラリを使用します"
    & uv run $PythonScript --action generate-key

    # 接続テスト（キー未登録の場合は失敗する）
    Write-Step "接続テスト"
    Write-Info "Snowsight で公開鍵を登録していない場合、接続テストは失敗します"
    Write-Info "その場合は、キー登録完了後に再テストしてください"
    Write-Host ""
    & uv run $PythonScript --action config

    Write-Host ""
    Write-Success "セットアップ完了"
    Write-Info "Snowsight で ALTER USER <ユーザー名> SET RSA_PUBLIC_KEY='公開鍵' を実行してください"
    Write-Info "登録後の接続テスト: .\setup_snowflake.ps1 -Action upload"
}

# =====================================================================
# Action: upload
# =====================================================================
function Invoke-Upload {
    Write-Step "Snowflake アップロード"

    $uvPath = Get-UvPath
    if (-not $uvPath) {
        Write-Fail "uv が見つかりません"
        return
    }

    $args_list = @("run", $PythonScript, "--action", "upload")
    if ($Force) { $args_list += "--force" }

    & $uvPath @args_list
}

# =====================================================================
# Action: register-task
# =====================================================================
function Invoke-RegisterTask {
    Write-Step "タスクスケジューラ登録"

    $taskName = "Claude Usage Snowflake Upload"

    # 既存の古いS3タスクがあれば通知
    try {
        $oldTask = Get-ScheduledTask -TaskName "Claude Usage Log Upload" -ErrorAction SilentlyContinue
        if ($oldTask) {
            Write-Info "旧S3アップロードタスク 'Claude Usage Log Upload' が登録されています"
            $remove = Read-Host "削除しますか？ (y/N)"
            if ($remove -eq "y") {
                Unregister-ScheduledTask -TaskName "Claude Usage Log Upload" -Confirm:$false
                Write-Success "旧タスクを削除しました"
            }
        }
    } catch {}

    # 既存タスクチェック
    try {
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Info "タスク '$taskName' は既に登録されています"
            $overwrite = Read-Host "上書きしますか？ (y/N)"
            if ($overwrite -ne "y") { return }
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        }
    } catch {}

    $uvPath = Get-UvPath
    if (-not $uvPath) {
        Write-Fail "uv が見つかりません"
        return
    }

    # setup_snowflake.ps1 経由で実行（環境変数ロードのため）
    $wrapperPath = Join-Path $ScriptDir "setup_snowflake.ps1"

    $taskAction = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wrapperPath`" -Action upload"
    $trigger = New-ScheduledTaskTrigger -Daily -At 3am
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $taskAction `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Claude Code の利用ログを Snowflake にアップロード"

    Write-Success "タスク '$taskName' を登録しました (毎日 3:00 AM)"
    Write-Info "確認: Get-ScheduledTask -TaskName '$taskName'"
}

# =====================================================================
# Action: unregister-task
# =====================================================================
function Invoke-UnregisterTask {
    $taskName = "Claude Usage Snowflake Upload"
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Success "タスク '$taskName' を削除しました"
    } catch {
        Write-Fail "タスクが見つかりません: $taskName"
    }
}

# =====================================================================
# Main
# =====================================================================
Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host " Claude Code Usage Tracker - Snowflake Upload" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

switch ($Action) {
    "setup"           { Invoke-Setup }
    "upload"          { Invoke-Upload }
    "register-task"   { Invoke-RegisterTask }
    "unregister-task" { Invoke-UnregisterTask }
}

Write-Host ""
