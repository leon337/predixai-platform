param(
    [int]$Count = 10,
    [int]$Interval = 10,
    [int]$DelaySeconds = 20,
    [switch]$ClearRuntime
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

New-Item -ItemType Directory -Force "logs" | Out-Null
New-Item -ItemType Directory -Force "data\runtime" | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $Root "logs\live_collector_$Stamp.log"

function Write-CollectorLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Write-Host $line
    $line | Out-File $LogPath -Append -Encoding utf8
}

Write-CollectorLog "PredixAI External Live Collector started."
Write-CollectorLog "Root: $Root"
Write-CollectorLog "Count: $Count"
Write-CollectorLog "Interval: $Interval"
Write-CollectorLog "DelaySeconds: $DelaySeconds"
Write-CollectorLog "ClearRuntime: $ClearRuntime"

$PythonPath = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-CollectorLog "ERROR: venv python not found at $PythonPath"
    exit 1
}

if ($ClearRuntime) {
    Write-CollectorLog "Clearing runtime files."
    Remove-Item -Force "data\runtime\live_price_history.json" -ErrorAction SilentlyContinue
    Remove-Item -Force "data\runtime\last_live_reading.json" -ErrorAction SilentlyContinue
}

if ($DelaySeconds -gt 0) {
    Write-CollectorLog "Waiting $DelaySeconds seconds. Put Olymp Trade in front now."
    Start-Sleep -Seconds $DelaySeconds
}

Write-CollectorLog "Collector command starting."

& $PythonPath -m predixai.main --live-loop --loop-count $Count --loop-interval $Interval 2>&1 |
    Tee-Object -FilePath $LogPath -Append

$ExitCode = $LASTEXITCODE
Write-CollectorLog "Collector finished with exit code $ExitCode."

exit $ExitCode
