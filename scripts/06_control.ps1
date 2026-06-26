#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Control the Email Queue Handler scheduled task: check status, pause
    (disable), resume (enable), stop an in-flight run, or trigger a run now.

.DESCRIPTION
    A single documented entry point for the common operational actions, so you
    do not have to remember the individual ScheduledTasks cmdlets. The default
    action (no switch) is -Status, which only reads state and changes nothing.

    Stopping is safe and lossless: the handler is queue-driven, so while the
    task is disabled, rows simply accumulate in tblEmailMessage with
    EmailSent = 0. Re-enabling causes the next run to pick up everything that
    piled up. Nothing is lost by pausing.

.PARAMETER Status
    Show the task's current state and last run result. This is the default.

.PARAMETER Disable
    Pause the service: stop the task from firing. Reversible with -Enable.
    Does not affect a run already in progress (add -StopRunning for that).

.PARAMETER Enable
    Resume the service: allow the task to fire on its schedule again.

.PARAMETER StopRunning
    End an in-flight run right now. Each run normally finishes in a second or
    two; use this only if a run is hung. Can be combined with -Disable.

.PARAMETER RunNow
    Trigger one run immediately (does not change enabled/disabled state).

.EXAMPLE
    .\06_control.ps1
    Shows current status (default, read-only).

.EXAMPLE
    .\06_control.ps1 -Disable -StopRunning
    Stops any in-flight run and pauses the task. The belt-and-suspenders stop.

.EXAMPLE
    .\06_control.ps1 -Enable
    Resumes the task.
#>

param(
    [string]$TaskName = "EmailQueueHandler",
    [switch]$Status,
    [switch]$Disable,
    [switch]$Enable,
    [switch]$StopRunning,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

# Guard: -Disable and -Enable are contradictory.
if ($Disable -and $Enable) {
    throw "Specify only one of -Disable or -Enable, not both."
}

# Confirm the task exists before doing anything.
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "Scheduled task '$TaskName' not found. Has it been registered " +
          "(03_register_task.ps1)?"
}

function Show-Status {
    $t = Get-ScheduledTask -TaskName $TaskName
    $info = $t | Get-ScheduledTaskInfo
    $resultHex = "0x{0:X}" -f $info.LastTaskResult
    Write-Host ""
    Write-Host "Task           : $TaskName" -ForegroundColor Cyan
    Write-Host "State          : $($t.State)"
    Write-Host "Last run time  : $($info.LastRunTime)"
    Write-Host "Last result    : $resultHex   (0x0 = success)"
    Write-Host "Next run time  : $($info.NextRunTime)"
    Write-Host ""
}

# --- Actions (order matters: stop a run, then change enabled state) ---

if ($StopRunning) {
    Write-Host "Stopping any in-flight run of '$TaskName' ..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName
    Write-Host "  done." -ForegroundColor Green
}

if ($Disable) {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
    Write-Host "Task '$TaskName' DISABLED - it will not fire until re-enabled." -ForegroundColor Yellow
    Write-Host "Queued emails will accumulate and send when you re-enable." -ForegroundColor DarkGray
}

if ($Enable) {
    Enable-ScheduledTask -TaskName $TaskName | Out-Null
    Write-Host "Task '$TaskName' ENABLED - it will fire on schedule again." -ForegroundColor Green
}

if ($RunNow) {
    Write-Host "Triggering one run of '$TaskName' now ..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "  triggered (check status or the log for the result)." -ForegroundColor Green
}

# Always show status at the end (and it's the default when no action is given).
if ($Status -or -not ($Disable -or $Enable -or $StopRunning -or $RunNow)) {
    Show-Status
} else {
    # After an action, show the resulting state too.
    Show-Status
}
