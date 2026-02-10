<# 
.SYNOPSIS
    Claude Code Usage Tracker - Setup and Upload Script
.DESCRIPTION
    AWS CLI install, configure, S3 bucket creation, and log upload
.PARAMETER BucketName
    S3 bucket name prefix
.PARAMETER Region
    AWS region
.PARAMETER Action
    Action to perform: setup-aws, setup-local, upload, list, config, all
.PARAMETER Force
    Force upload even if already uploaded
#>

param(
    [string]$BucketName = "claude-activity-log",
    [string]$Region = "ap-northeast-1",
    [ValidateSet("setup-aws", "setup-local", "upload", "list", "config", "all")]
    [string]$Action = "all",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$LogDir = Join-Path $env:USERPROFILE ".claude\usage-tracker-logs"
$UploadedFile = Join-Path $LogDir ".uploaded_files.json"

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

function Install-AWSCLIIfNeeded {
    if (Test-CommandExists "aws") {
        Write-Success "AWS CLI is already installed"
        aws --version
        return
    }
    
    Write-Info "Installing AWS CLI..."
    
    $installerUrl = "https://awscli.amazonaws.com/AWSCLIV2.msi"
    $installerPath = Join-Path $env:TEMP "AWSCLIV2.msi"
    
    Write-Info "Downloading AWS CLI..."
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    
    Write-Info "Running installer..."
    Start-Process msiexec.exe -Wait -ArgumentList "/i `"$installerPath`" /quiet"
    
    # Refresh PATH
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
    
    Write-Success "AWS CLI installed"
}

function Setup-AWSCredentials {
    Write-Step "AWS Credentials Setup"
    
    $hasCredentials = $false
    try {
        $result = aws sts get-caller-identity 2>$null
        if ($result) {
            $identity = $result | ConvertFrom-Json
            Write-Success "AWS credentials already configured"
            Write-Host "  Account: $($identity.Account)"
            Write-Host "  User: $($identity.Arn)"
            
            $continue = Read-Host "Configure new credentials? (y/N)"
            if ($continue -ne "y") {
                return
            }
        }
    } catch {
        # No credentials
    }
    
    Write-Host ""
    Write-Host "Enter AWS credentials:"
    $accessKey = Read-Host "AWS Access Key ID"
    $secretKey = Read-Host "AWS Secret Access Key"
    
    aws configure set aws_access_key_id $accessKey
    aws configure set aws_secret_access_key $secretKey
    aws configure set region $Region
    aws configure set output json
    
    Write-Success "AWS credentials configured"
}

function Setup-S3Bucket {
    param([string]$BucketName)
    
    Write-Step "S3 Bucket Setup"
    
    $accountId = aws sts get-caller-identity --query Account --output text
    $fullBucketName = "$BucketName-$accountId"
    
    Write-Info "Bucket name: $fullBucketName"
    
    $bucketExists = $false
    try {
        aws s3api head-bucket --bucket $fullBucketName 2>$null
        $bucketExists = $true
        Write-Success "Bucket already exists: $fullBucketName"
    } catch {
        # Bucket does not exist
    }
    
    if (-not $bucketExists) {
        Write-Info "Creating bucket..."
        
        if ($Region -eq "us-east-1") {
            aws s3api create-bucket --bucket $fullBucketName
        } else {
            aws s3api create-bucket --bucket $fullBucketName --region $Region --create-bucket-configuration LocationConstraint=$Region
        }
        
        Write-Success "Bucket created: $fullBucketName"
    }
    
    Write-Info "Enabling versioning..."
    aws s3api put-bucket-versioning --bucket $fullBucketName --versioning-configuration Status=Enabled
    
    Write-Info "Blocking public access..."
    aws s3api put-public-access-block --bucket $fullBucketName --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    Write-Success "S3 bucket setup complete"
    
    [System.Environment]::SetEnvironmentVariable("USAGE_TRACKER_S3_BUCKET", $fullBucketName, "User")
    $env:USAGE_TRACKER_S3_BUCKET = $fullBucketName
    
    Write-Info "Environment variable set: USAGE_TRACKER_S3_BUCKET = $fullBucketName"
    
    return $fullBucketName
}

function Setup-LocalEnvironment {
    Write-Step "Local Environment Setup"
    
    $currentBucket = [System.Environment]::GetEnvironmentVariable("USAGE_TRACKER_S3_BUCKET", "User")
    
    if ($currentBucket) {
        Write-Info "Current setting: USAGE_TRACKER_S3_BUCKET = $currentBucket"
        $change = Read-Host "Change? (y/N)"
        if ($change -ne "y") {
            return
        }
    }
    
    $bucket = Read-Host "Enter S3 bucket name"
    
    [System.Environment]::SetEnvironmentVariable("USAGE_TRACKER_S3_BUCKET", $bucket, "User")
    [System.Environment]::SetEnvironmentVariable("USAGE_TRACKER_S3_PREFIX", "claude-usage-logs", "User")
    [System.Environment]::SetEnvironmentVariable("AWS_REGION", $Region, "User")
    
    $env:USAGE_TRACKER_S3_BUCKET = $bucket
    $env:USAGE_TRACKER_S3_PREFIX = "claude-usage-logs"
    $env:AWS_REGION = $Region
    
    Write-Success "Environment variables set"
}

function Show-LogFiles {
    Write-Step "Log Files"
    
    if (-not (Test-Path $LogDir)) {
        Write-Fail "Log directory not found: $LogDir"
        Write-Info "Logs will be saved here when using the Claude Code plugin"
        return
    }
    
    $logFiles = Get-ChildItem -Path $LogDir -Filter "events-*.jsonl" | Sort-Object Name
    
    if ($logFiles.Count -eq 0) {
        Write-Info "No log files found"
        return
    }
    
    Write-Host ""
    Write-Host "Log directory: $LogDir"
    Write-Host ""
    
    $totalSize = 0
    $totalEvents = 0
    
    foreach ($file in $logFiles) {
        $size = $file.Length
        $totalSize += $size
        
        $eventCount = (Get-Content $file.FullName | Measure-Object -Line).Lines
        $totalEvents += $eventCount
        
        $sizeKB = [math]::Round($size / 1024, 1)
        Write-Host "  $($file.Name) ($sizeKB KB, $eventCount events)"
    }
    
    Write-Host ""
    $totalSizeKB = [math]::Round($totalSize / 1024, 1)
    Write-Host "Total: $($logFiles.Count) files, $totalSizeKB KB, $totalEvents events"
}

function Show-Config {
    Write-Step "Current Configuration"
    
    $bucket = $env:USAGE_TRACKER_S3_BUCKET
    if (-not $bucket) {
        $bucket = [System.Environment]::GetEnvironmentVariable("USAGE_TRACKER_S3_BUCKET", "User")
    }
    
    $prefix = $env:USAGE_TRACKER_S3_PREFIX
    if (-not $prefix) {
        $prefix = [System.Environment]::GetEnvironmentVariable("USAGE_TRACKER_S3_PREFIX", "User")
    }
    if (-not $prefix) {
        $prefix = "claude-usage-logs"
    }
    
    $awsRegion = $env:AWS_REGION
    if (-not $awsRegion) {
        $awsRegion = [System.Environment]::GetEnvironmentVariable("AWS_REGION", "User")
    }
    if (-not $awsRegion) {
        $awsRegion = "ap-northeast-1"
    }
    
    Write-Host ""
    Write-Host "S3 Bucket:  $bucket"
    Write-Host "S3 Prefix:  $prefix"
    Write-Host "AWS Region: $awsRegion"
    Write-Host "Log Dir:    $LogDir"
    Write-Host ""
    
    Write-Host "AWS Credentials:"
    try {
        $result = aws sts get-caller-identity 2>$null
        if ($result) {
            $identity = $result | ConvertFrom-Json
            Write-Host "  Account: $($identity.Account)"
            Write-Host "  User: $($identity.Arn)"
        }
    } catch {
        Write-Host "  (Not configured or invalid)"
    }
}

function Get-IAMUserName {
    try {
        $arn = aws sts get-caller-identity --query Arn --output text 2>$null
        if ($arn -match "user/(.+)$") {
            return $matches[1]
        }
        return "unknown"
    } catch {
        return "unknown"
    }
}

function Upload-ToS3 {
    param(
        [switch]$DryRun,
        [switch]$ForceUpload
    )
    
    Write-Step "Upload to S3"
    
    $bucket = $env:USAGE_TRACKER_S3_BUCKET
    if (-not $bucket) {
        $bucket = [System.Environment]::GetEnvironmentVariable("USAGE_TRACKER_S3_BUCKET", "User")
    }
    
    if (-not $bucket -or $bucket -eq "your-bucket-name") {
        Write-Fail "S3 bucket not configured"
        Write-Info "Run setup-aws or setup-local first"
        return
    }
    
    $prefix = $env:USAGE_TRACKER_S3_PREFIX
    if (-not $prefix) {
        $prefix = "claude-usage-logs"
    }
    
    if (-not (Test-Path $LogDir)) {
        Write-Fail "Log directory not found: $LogDir"
        return
    }
    
    $logFiles = Get-ChildItem -Path $LogDir -Filter "events-*.jsonl" | Sort-Object Name
    
    if ($logFiles.Count -eq 0) {
        Write-Info "No log files to upload"
        return
    }
    
    # Get IAM user name
    $iamUser = Get-IAMUserName
    Write-Info "IAM User: $iamUser"
    
    Write-Host ""
    Write-Host "S3 Bucket: s3://$bucket/$prefix/$iamUser/"
    Write-Host "Files: $($logFiles.Count)"
    Write-Host ""
    
    if (-not $DryRun) {
        try {
            aws s3api head-bucket --bucket $bucket 2>$null
        } catch {
            Write-Fail "Cannot access S3 bucket: $bucket"
            Write-Info "Check bucket name and AWS credentials"
            return
        }
    }
    
    $uploadedFiles = @()
    if ((Test-Path $UploadedFile) -and -not $ForceUpload) {
        try {
            $content = Get-Content $UploadedFile -Raw
            if ($content) {
                $uploadedFiles = $content | ConvertFrom-Json
                if ($uploadedFiles -isnot [array]) {
                    $uploadedFiles = @($uploadedFiles)
                }
            }
        } catch {
            $uploadedFiles = @()
        }
    }
    
    $uploadedCount = 0
    $skippedCount = 0
    $newlyUploaded = @()
    
    foreach ($file in $logFiles) {
        $fileName = $file.Name
        
        # Extract date from filename: events-2026-02-10.jsonl -> 2026/02/10
        $datePart = $fileName -replace "events-", "" -replace ".jsonl", ""
        $datePath = $datePart -replace "-", "/"
        
        # S3 key: claude-usage-logs/te.haginoya/2026/02/10/events-2026-02-10.jsonl
        $s3Key = "$prefix/$iamUser/$datePath/$fileName"
        
        if ($uploadedFiles -contains $fileName -and -not $ForceUpload) {
            Write-Host "  [SKIP] $fileName" -ForegroundColor Gray
            $skippedCount++
            continue
        }
        
        if ($DryRun) {
            Write-Host "  [DRY] $fileName -> s3://$bucket/$s3Key" -ForegroundColor Yellow
            $uploadedCount++
        } else {
            Write-Host "  [UP]  $fileName -> s3://$bucket/$s3Key"
            
            try {
                aws s3 cp $file.FullName "s3://$bucket/$s3Key" --quiet
                Write-Host "        OK" -ForegroundColor Green
                $newlyUploaded += $fileName
                $uploadedCount++
            } catch {
                Write-Host "        FAILED: $_" -ForegroundColor Red
            }
        }
    }
    
    if (-not $DryRun -and $newlyUploaded.Count -gt 0) {
        $allUploaded = $uploadedFiles + $newlyUploaded | Select-Object -Unique
        $allUploaded | ConvertTo-Json | Set-Content $UploadedFile
    }
    
    Write-Host ""
    Write-Success "Result: $uploadedCount uploaded, $skippedCount skipped"
}

# Main
Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host " Claude Code Usage Tracker - Setup and Upload" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

switch ($Action) {
    "setup-aws" {
        Install-AWSCLIIfNeeded
        Setup-AWSCredentials
        Setup-S3Bucket -BucketName $BucketName
    }
    "setup-local" {
        Setup-LocalEnvironment
    }
    "upload" {
        Upload-ToS3 -ForceUpload:$Force
    }
    "list" {
        Show-LogFiles
    }
    "config" {
        Show-Config
    }
    "all" {
        Install-AWSCLIIfNeeded
        Setup-AWSCredentials
        Setup-S3Bucket -BucketName $BucketName
        Show-LogFiles
        Upload-ToS3 -ForceUpload:$Force
    }
}

Write-Host ""
