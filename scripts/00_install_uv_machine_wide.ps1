#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Install uv machine-wide under C:\ProgramData\uv so every account - including
    the non-interactive svc_eqh service account - shares one binary, one set of
    managed Pythons, and one package cache.

.DESCRIPTION
    A per-user uv install (under C:\Users\<you>\.local) is invisible to the
    scheduled-task service account. This script relocates uv to a shared,
    machine-readable root and sets machine-scoped environment variables so uv
    keeps ALL of its state there rather than in any user profile:

        C:\ProgramData\uv\bin      UV_INSTALL_DIR          (the uv.exe binary)
        C:\ProgramData\uv\python   UV_PYTHON_INSTALL_DIR   (managed Pythons)
        C:\ProgramData\uv\cache    UV_CACHE_DIR            (download/wheel cache)

    Run once, elevated. Safe to re-run (idempotent).

.NOTES
    After running, OPEN A NEW SHELL (env vars only apply to new processes), then
    verify with the checks printed at the end. The svc_eqh account will pick up
    the machine env vars automatically on the task's next run.
#>

param(
    [string]$Root          = "C:\ProgramData\uv",
    [string]$UvDownloadUrl = "https://astral.sh/uv/install.ps1"
)

$ErrorActionPreference = "Stop"

$BinDir    = Join-Path $Root "bin"
$PythonDir = Join-Path $Root "python"
$CacheDir  = Join-Path $Root "cache"

Write-Host "=== 1. Create the shared uv directory tree ===" -ForegroundColor Cyan
foreach ($d in @($Root, $BinDir, $PythonDir, $CacheDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    Write-Host "  $d"
}

Write-Host ""
Write-Host "=== 2. Set machine-scoped uv environment variables ===" -ForegroundColor Cyan
# These tell uv where to put its binary, Pythons, and cache - all under the
# shared root, none in a user profile. Machine scope = visible to svc_eqh.
[Environment]::SetEnvironmentVariable("UV_INSTALL_DIR",        $BinDir,    "Machine")
[Environment]::SetEnvironmentVariable("UV_PYTHON_INSTALL_DIR", $PythonDir, "Machine")
[Environment]::SetEnvironmentVariable("UV_CACHE_DIR",          $CacheDir,  "Machine")
# Make uv install Pythons in the managed dir and prefer them (no system Python).
[Environment]::SetEnvironmentVariable("UV_PYTHON_PREFERENCE",  "only-managed", "Machine")
Write-Host "  UV_INSTALL_DIR        = $BinDir"
Write-Host "  UV_PYTHON_INSTALL_DIR = $PythonDir"
Write-Host "  UV_CACHE_DIR          = $CacheDir"
Write-Host "  UV_PYTHON_PREFERENCE  = only-managed"

Write-Host ""
Write-Host "=== 3. Add the uv bin dir to the MACHINE PATH (once) ===" -ForegroundColor Cyan
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($machinePath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$machinePath;$BinDir", "Machine")
    Write-Host "  Added $BinDir to machine PATH."
} else {
    Write-Host "  $BinDir already on machine PATH - skipping."
}

Write-Host ""
Write-Host "=== 4. Install uv into the shared bin dir ===" -ForegroundColor Cyan
# The official installer respects UV_INSTALL_DIR, which we set above for THIS
# process so the binary lands in the shared location.
$env:UV_INSTALL_DIR = $BinDir
Invoke-RestMethod -Uri $UvDownloadUrl | Invoke-Expression

Write-Host ""
Write-Host "=== 5. Lock down permissions (least privilege) ===" -ForegroundColor Cyan
# Pythons + cache must be WRITABLE by service accounts (uv writes there on first
# run). The binary dir stays read/execute only for non-admins - a service
# account should not be able to overwrite the uv binary.
foreach ($writable in @($PythonDir, $CacheDir)) {
    icacls $writable /grant "Users:(OI)(CI)M" /T | Out-Null
    Write-Host "  granted Users modify on $writable"
}
icacls $BinDir /grant "Users:(OI)(CI)RX" /T | Out-Null
Write-Host "  granted Users read/execute on $BinDir"

Write-Host ""
Write-Host "Done. OPEN A NEW ELEVATED SHELL, then verify:" -ForegroundColor Green
Write-Host '  & "C:\ProgramData\uv\bin\uv.exe" --version' -ForegroundColor DarkGray
Write-Host '  [Environment]::GetEnvironmentVariable("UV_PYTHON_INSTALL_DIR","Machine")' -ForegroundColor DarkGray
Write-Host ""
Write-Host "Then confirm svc_eqh can use it (step 04 smoke test, check 1)." -ForegroundColor Cyan
Write-Host "You may also want to UNINSTALL the old per-user uv to avoid confusion:" -ForegroundColor Yellow
Write-Host '  Remove-Item "$env:USERPROFILE\.local\bin\uv.exe" -ErrorAction SilentlyContinue' -ForegroundColor DarkGray
