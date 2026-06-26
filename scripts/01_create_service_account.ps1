#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Create the local service account that the Email Queue Handler scheduled
    task runs as.

.DESCRIPTION
    Creates a dedicated, least-privilege LOCAL account 'svc_eqh' whose only job
    is to run the email handler. Run this once, as Administrator, on a
    STANDALONE (workgroup) server.

    On a DOMAIN-JOINED server, do NOT use this script. Instead ask your AD
    administrator for a domain service account (ideally a gMSA), and use
    DOMAIN\svc_eqh (or the gMSA) in the task-registration step.

.NOTES
    The password you set here is also entered when registering the scheduled
    task. Choose a strong one and store it in your password manager - you will
    need it exactly once more.
#>

$ErrorActionPreference = "Stop"

$AccountName = "svc_eqh"
$FullName    = "Email Queue Handler Service Account"
$Description  = "Runs the Email Queue Handler scheduled task."

# Prompt for the password rather than hard-coding it in the script.
$Password = Read-Host -AsSecureString "Enter a strong password for $AccountName"

if (Get-LocalUser -Name $AccountName -ErrorAction SilentlyContinue) {
    Write-Host "Account '$AccountName' already exists - skipping creation." -ForegroundColor Yellow
} else {
    New-LocalUser -Name $AccountName `
        -Password $Password `
        -FullName $FullName `
        -Description $Description `
        -PasswordNeverExpires `
        -UserMayNotChangePassword
    Write-Host "Created local account '$AccountName'." -ForegroundColor Green
}

# The account does NOT need to be an administrator. It needs only:
#   - "Log on as a batch job" (granted below; required for a scheduled task to
#     launch non-interactively - without it the task fails to run with 0x41303).
#   - Read access to the install directory and write access to the log directory
#     (handled in the deploy step).
# Deliberately NOT adding it to the Administrators group: least privilege.

# --- Grant "Log on as a batch job" (SeBatchLogonRight) ---
# There is no native cmdlet for user-rights assignment, so we use secedit:
# export the current policy, ensure the account's SID is on the batch-logon
# line, and re-import. Idempotent - safe to run when the right is already held.
Write-Host ""
Write-Host "Granting 'Log on as a batch job' to $AccountName ..." -ForegroundColor Cyan

$sid = (Get-LocalUser -Name $AccountName).SID.Value
$tmpDir = [System.IO.Path]::GetTempPath()
$infPath = Join-Path $tmpDir "eqh_secpol.inf"
$dbPath  = Join-Path $tmpDir "eqh_secpol.sdb"

secedit /export /cfg $infPath /areas USER_RIGHTS | Out-Null
$content = Get-Content $infPath
$line = $content | Where-Object { $_ -match "^SeBatchLogonRight" }

if (-not $line) {
    # No batch-logon line at all: add one granting only this SID.
    $content += "SeBatchLogonRight = *$sid"
} elseif ($line -notmatch [regex]::Escape($sid)) {
    # Line exists but our SID is missing: append it.
    $content = $content -replace "^(SeBatchLogonRight\s*=\s*.*)$", "`$1,*$sid"
} else {
    Write-Host "  $AccountName already has the batch-logon right - skipping." -ForegroundColor Yellow
}

if ($line -notmatch [regex]::Escape($sid)) {
    Set-Content -Path $infPath -Value $content -Encoding Unicode
    secedit /configure /db $dbPath /cfg $infPath /areas USER_RIGHTS | Out-Null
    Write-Host "  granted." -ForegroundColor Green
}

Remove-Item $infPath, $dbPath -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Next: run 02_set_machine_env.ps1 to set the secret environment variables." -ForegroundColor Cyan
