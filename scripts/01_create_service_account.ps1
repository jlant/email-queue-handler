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
$Description  = "Runs the Email Queue Handler scheduled task (least privilege)."

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
#   - "Log on as a batch job" (granted automatically when you register a task
#     to run whether-logged-on-or-not with this account, or grant explicitly
#     via secpol.msc -> Local Policies -> User Rights Assignment).
#   - Read access to the install directory and write access to the log directory
#     (handled in the deploy step).
# Deliberately NOT adding it to the Administrators group: least privilege.

Write-Host ""
Write-Host "Next: run 02_set_machine_env.ps1 to set the secret environment variables." -ForegroundColor Cyan
