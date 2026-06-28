param(
    [int]$Count = 10,
    [int]$Interval = 10,
    [int]$DelaySeconds = 20,
    [switch]$ClearRuntime
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runner = Join-Path $Root "scripts\live_collector.ps1"

if (-not (Test-Path $Runner)) {
    throw "Runner not found: $Runner"
}

$argsList = @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$Runner`"",
    "-Count", "$Count",
    "-Interval", "$Interval",
    "-DelaySeconds", "$DelaySeconds"
)

if ($ClearRuntime) {
    $argsList += "-ClearRuntime"
}

Start-Process -FilePath "powershell.exe" -WindowStyle Minimized -WorkingDirectory $Root -ArgumentList $argsList

Write-Host "External collector window started."
Write-Host "Count=$Count Interval=$Interval DelaySeconds=$DelaySeconds ClearRuntime=$ClearRuntime"
Write-Host "You can now keep VS Code open or closed. The collector is running in a separate PowerShell window."
