<#
.SYNOPSIS
    Claude Code Usage Tracker - Hooks 設定スクリプト
.DESCRIPTION
    ~/.claude/settings.json にフック設定を書き込みます。
    プラグインインストールが使えない場合の代替手段です。
    既存の settings.json がある場合、hooks キーのみ追加・上書きします。
#>

$ErrorActionPreference = "Stop"

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

# リポジトリの plugin/usage-tracker/scripts/send_event.py のパスを特定
$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path $ScriptDir -Parent
$SendEventScript = Join-Path $RepoRoot "plugin\usage-tracker\scripts\send_event.py"

if (-not (Test-Path $SendEventScript)) {
    Write-Fail "send_event.py が見つかりません: $SendEventScript"
    Write-Fail "リポジトリのクローンが正しいか確認してください"
    exit 1
}

# パスをスラッシュ区切りに変換（Claude Code は Unix スタイルのパスを使用）
$SendEventPath = $SendEventScript.Replace("\", "/")

Write-Info "スクリプトパス: $SendEventPath"

# settings.json のパス
$SettingsDir = Join-Path $env:USERPROFILE ".claude"
$SettingsFile = Join-Path $SettingsDir "settings.json"

# ディレクトリ作成
if (-not (Test-Path $SettingsDir)) {
    New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null
}

# 既存の settings.json を読み込み
$settings = @{}
if (Test-Path $SettingsFile) {
    try {
        $content = Get-Content $SettingsFile -Raw -Encoding UTF8
        $settings = $content | ConvertFrom-Json -AsHashtable
        Write-Info "既存の settings.json を読み込みました"
    } catch {
        Write-Info "settings.json の読み込みに失敗。新規作成します"
        $settings = @{}
    }
}

# フック定義
$hookEvents = @(
    @{ Name = "SessionStart";       Matcher = "" },
    @{ Name = "SessionEnd";         Matcher = "" },
    @{ Name = "UserPromptSubmit";   Matcher = "" },
    @{ Name = "PreToolUse";         Matcher = "*" },
    @{ Name = "PostToolUse";        Matcher = "*" },
    @{ Name = "PostToolUseFailure"; Matcher = "*" },
    @{ Name = "SubagentStart";      Matcher = "" },
    @{ Name = "SubagentStop";       Matcher = "" },
    @{ Name = "Notification";       Matcher = "" },
    @{ Name = "PreCompact";         Matcher = "" },
    @{ Name = "Stop";               Matcher = "" },
    @{ Name = "PermissionRequest";  Matcher = "*" },
    @{ Name = "TeammateIdle";       Matcher = "" },
    @{ Name = "TaskCompleted";      Matcher = "" }
)

# hooks オブジェクトを構築
$hooks = @{}
foreach ($evt in $hookEvents) {
    $hooks[$evt.Name] = @(
        @{
            matcher = $evt.Matcher
            hooks = @(
                @{
                    type = "command"
                    command = "uv run `"$SendEventPath`" --event-type $($evt.Name)"
                }
            )
        }
    )
}

# settings に hooks を設定（他のキーは保持）
$settings["hooks"] = $hooks

# JSON として書き出し
$json = $settings | ConvertTo-Json -Depth 10
$json | Out-File -FilePath $SettingsFile -Encoding UTF8 -Force

Write-Success "settings.json にフック設定を書き込みました"
Write-Info "ファイル: $SettingsFile"
Write-Info "イベント数: $($hookEvents.Count)"
Write-Host ""
Write-Info "Claude Code を再起動するとフックが有効になります"
