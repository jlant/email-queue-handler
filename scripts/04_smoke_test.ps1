#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Verify the Email Queue Handler is correctly installed and the scheduled
    task actually runs. Catches the "registered but silently broken" failure.

.DESCRIPTION
    Walks the things that commonly break a non-interactive scheduled task, in
    order, so you find the problem before relying on it in production.
#>

param(
    [string]$InstallDir = "C:\Apps\email-queue-handler",
    [string]$UvPath     = "C:\ProgramData\uv\uv.exe",
    [string]$TaskName   = "EmailQueueHandler"
)

$ErrorActionPreference = "Stop"

Write-Host "=== 1. uv is reachable at the path the task uses ===" -ForegroundColor Cyan
if (Test-Path $UvPath) {
    & $UvPath --version
    Write-Host "OK: uv found at $UvPath" -ForegroundColor Green
} else {
    Write-Host "FAIL: uv not at $UvPath. A per-user uv install is NOT visible to" -ForegroundColor Red
    Write-Host "      svc_eqh. Install uv machine-wide, or copy uv.exe to this path." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 2. Config and machine secrets resolve (no real send) ===" -ForegroundColor Cyan
# read-config prints resolved settings with passwords MASKED, so it is safe to
# run and confirms app.toml + machine env vars are being picked up.
Push-Location $InstallDir
try {
    & $UvPath run eqh read-config --config "$InstallDir\config\app.toml"
} finally {
    Pop-Location
}
Write-Host "Check above: passwords should show *** (set), host/db/smtp populated." -ForegroundColor Yellow

Write-Host ""
Write-Host "=== 3. Force one immediate task run, then inspect result ===" -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5
$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
Write-Host "LastRunTime : $($info.LastRunTime)"
Write-Host "LastTaskResult (0x0 = success): 0x{0:X}" -f $info.LastTaskResult
if ($info.LastTaskResult -eq 0) {
    Write-Host "OK: task ran and exited 0." -ForegroundColor Green
} else {
    Write-Host "Task exited non-zero. Common codes:" -ForegroundColor Yellow
    Write-Host "  0x1  - app raised / run-level failure (check the app log)" -ForegroundColor DarkGray
    Write-Host "  0x41301 - still running (increase sleep, or run is slow)" -ForegroundColor DarkGray
    Write-Host "  0x2  - file not found (uv path or install dir wrong)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== 4. Tail the application log ===" -ForegroundColor Cyan
$log = Join-Path $InstallDir "logs\email_queue_handler.log"
if (Test-Path $log) {
    Get-Content $log -Tail 15
} else {
    Write-Host "No log at $log yet. If the task ran as svc_eqh, confirm that" -ForegroundColor Yellow
    Write-Host "account can WRITE to the logs directory." -ForegroundColor Yellow
}
