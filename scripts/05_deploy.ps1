#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Deploy or update the Email Queue Handler on this server: pull the latest
    code, build the locked virtual environment, and verify before handing off
    to the scheduled task.

.DESCRIPTION
    Works for both first install (after git clone) and ongoing updates. Every
    step is built on the committed uv.lock, so the dependency set is identical
    and reproducible on every run. Safe to re-run.

    Sequence:
      1. git pull            - fetch latest code AND lockfile (skipped if -NoPull)
      2. uv sync --frozen    - build .venv to match the lockfile EXACTLY
      3. uv run pytest       - gate: do not consider a deploy good if tests fail
      4. ensure log dir + permissions for svc_eqh
      5. print next steps

.PARAMETER InstallDir
    The cloned project directory (contains pyproject.toml).

.PARAMETER UvPath
    Absolute path to the machine-wide uv (from 00_install_uv_machine_wide.ps1).

.PARAMETER ServiceAccount
    The account the scheduled task runs as; granted write to the log dir.

.PARAMETER NoPull
    Skip git pull (use the code already on disk). Useful for the very first
    deploy right after a manual clone, or to redeploy without changing code.

.PARAMETER SkipTests
    Skip the pytest gate. NOT recommended; use only if the test deps are
    intentionally not installed on this box.
#>

param(
    [string]$InstallDir     = "C:\Apps\email-queue-handler",
    [string]$UvPath         = "C:\ProgramData\uv\bin\uv.exe",
    [string]$ServiceAccount = "svc_eqh",
    [switch]$NoPull,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $InstallDir "pyproject.toml"))) {
    throw "No pyproject.toml in $InstallDir - is the repo cloned there? " +
          "Expected e.g. 'git clone <url> $InstallDir'."
}

Set-Location $InstallDir

Write-Host "=== 1. Get latest code ===" -ForegroundColor Cyan
if ($NoPull) {
    Write-Host "  -NoPull set; using code already on disk." -ForegroundColor Yellow
} else {
    git pull
}
$commit = (git rev-parse --short HEAD).Trim()
Write-Host "  at commit $commit" -ForegroundColor Green

Write-Host ""
Write-Host "=== 2. Build the locked virtual environment ===" -ForegroundColor Cyan
# --frozen: install EXACTLY what uv.lock specifies; fail if lock is out of date.
# This is also the step that downloads the managed Python on first run.
& $UvPath sync --frozen
Write-Host "  .venv synced to uv.lock" -ForegroundColor Green

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "=== 3. Run the test gate ===" -ForegroundColor Cyan
    & $UvPath run pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed - deploy aborted. The previous deployment (if any) " +
              "is untouched on disk; the scheduled task keeps running the prior code."
    }
    Write-Host "  tests passed" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "=== 3. Tests SKIPPED (-SkipTests) ===" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 4. Ensure log directory exists and is writable by $ServiceAccount ===" -ForegroundColor Cyan
$logDir = Join-Path $InstallDir "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
# svc_eqh must be able to write the rotating log file.
icacls $logDir /grant "${ServiceAccount}:(OI)(CI)M" /T | Out-Null
Write-Host "  $logDir writable by $ServiceAccount" -ForegroundColor Green

Write-Host ""
Write-Host "Deploy complete at commit $commit." -ForegroundColor Green
Write-Host ""
Write-Host "First-time setup still needed (run once, in order):" -ForegroundColor Cyan
Write-Host "  01_create_service_account.ps1   (create svc_eqh)" -ForegroundColor DarkGray
Write-Host "  02_set_machine_env.ps1          (set EQH_*_PASSWORD secrets)" -ForegroundColor DarkGray
Write-Host "  03_register_task.ps1            (register the every-minute task)" -ForegroundColor DarkGray
Write-Host "  04_smoke_test.ps1               (verify it actually runs)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "For an UPDATE (account/task already exist), this script is all you need," -ForegroundColor Cyan
Write-Host "followed by 04_smoke_test.ps1 to confirm the new code runs." -ForegroundColor Cyan
