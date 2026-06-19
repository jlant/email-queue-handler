#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Register the Email Queue Handler scheduled task: run once per minute,
    every day, whether or not a user is logged on, with no overlapping runs.

.DESCRIPTION
    Encodes the three production-safety properties for a once-a-minute job:
      1. No overlap  - if a run exceeds 60s, the next trigger is skipped rather
                       than starting a second instance against the same queue.
      2. Run hidden, whether-logged-on-or-not - survives reboots and logoffs.
      3. Least-privilege identity - runs as svc_eqh, not SYSTEM/admin.

    The task invokes `uv run eqh run` in the install directory, so it uses the
    project's locked virtual environment. Output/errors are captured by the
    app's own rotating log file (configured in app.toml); the task itself does
    not need to redirect stdout.

.PARAMETER InstallDir
    The directory the code is deployed to (contains pyproject.toml, config\).

.PARAMETER UvPath
    Full path to uv.exe. Service accounts often lack a PATH entry for uv, so we
    pass the absolute path. Find yours with `(Get-Command uv).Source` while
    logged in as yourself, or it is typically:
      C:\Users\<you>\.local\bin\uv.exe   (per-user install) - NOT visible to svc_eqh
      C:\ProgramData\uv\uv.exe           (if installed machine-wide)
    Prefer a machine-wide uv install so the service account can see it. See
    notes in 04_smoke_test.ps1.

.PARAMETER Account
    The account to run as. Local: ".\svc_eqh". Domain: "DOMAIN\svc_eqh".
#>

param(
    [string]$InstallDir = "C:\Apps\email-queue-handler",
    [string]$UvPath     = "C:\ProgramData\uv\uv.exe",
    [string]$Account    = ".\svc_eqh",
    [string]$TaskName   = "EmailQueueHandler"
)

$ErrorActionPreference = "Stop"

# NOTE: this script uses "splatting" (passing a hashtable of parameters with @)
# rather than backtick line-continuation. Backtick continuations with inline
# comments are fragile in PowerShell - a comment between the backtick and the
# newline breaks the continuation. Splatting avoids that entirely and lets each
# parameter carry a normal comment.

# --- Action: run one pass of the handler in the install directory ---
# We call uv with an explicit --config so the working directory does not matter.
# "run eqh run" executes the console script in the locked venv.
$actionArgs = @{
    Execute          = $UvPath
    Argument         = "run eqh run --config `"$InstallDir\config\app.toml`""
    WorkingDirectory = $InstallDir
}
$action = New-ScheduledTaskAction @actionArgs

# --- Trigger: every 1 minute, indefinitely, starting now ---
# Task Scheduler builds repetition on top of a base trigger: a one-time trigger
# with a 1-minute repetition for an effectively endless duration.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
$repeatSource = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration ([TimeSpan]::MaxValue)
$trigger.Repetition = $repeatSource.Repetition

# --- Settings: the production-safety knobs ---
$settingsArgs = @{
    MultipleInstances  = "IgnoreNew"                    # NO OVERLAP: skip a trigger if still running
    StartWhenAvailable = $true                          # catch up if the server was briefly off
    DontStopOnIdleEnd  = $true                          # keep running regardless of idle state
    ExecutionTimeLimit = (New-TimeSpan -Minutes 5)      # kill a hung run; next minute is fresh
    RestartCount       = 0                              # do not auto-retry a failed run
}
$settings = New-ScheduledTaskSettingsSet @settingsArgs

# --- Principal: who it runs as, and how ---
# LogonType Password = run whether or not the user is logged on.
# RunLevel Limited = least privilege (do NOT use Highest without a specific need).
$principalArgs = @{
    UserId    = $Account
    LogonType = "Password"
    RunLevel  = "Limited"
}
$principal = New-ScheduledTaskPrincipal @principalArgs

# --- Build the task object ---
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal

# --- Register it. The password is prompted, never written in the script. ---
$cred = Get-Credential -UserName $Account -Message "Enter the password for $Account"

$registerArgs = @{
    TaskName   = $TaskName
    InputObject = $task
    User       = $cred.UserName
    Password   = $cred.GetNetworkCredential().Password
    Force      = $true
}
Register-ScheduledTask @registerArgs

Write-Host ""
Write-Host "Registered scheduled task '$TaskName'." -ForegroundColor Green
Write-Host "It will run 'uv run eqh run' every minute as $Account." -ForegroundColor Green
Write-Host ""
Write-Host "Verify with:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo" -ForegroundColor DarkGray
Write-Host "  Start-ScheduledTask -TaskName $TaskName   # force an immediate run" -ForegroundColor DarkGray
