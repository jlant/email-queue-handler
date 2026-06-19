#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Set the Email Queue Handler secret environment variables at MACHINE scope.

.DESCRIPTION
    The scheduled task runs non-interactively as svc_eqh, so secrets must be
    visible machine-wide, not tied to an interactive user profile. This script
    sets them at "Machine" scope via [Environment]::SetEnvironmentVariable.

    Only the two SECRETS go here (database + email passwords). Non-secret
    settings (host, database, smtp server, addresses) belong in config\app.toml,
    which is committed to source control. Secrets never touch the repo.

.NOTES
    Machine-scoped env vars are readable by any account that can read the
    registry's environment key. On a single-purpose server this is acceptable;
    if you need stronger isolation later, consider Windows Credential Manager
    or DPAPI. For now, machine env vars are the standard, simple choice.

    After running this, a NEW process must start to see the variables. The
    scheduled task will pick them up on its next run automatically; an already
    open shell will not - open a fresh one to verify.
#>

$ErrorActionPreference = "Stop"

function Set-MachineSecret {
    param([string]$Name)
    $secure = Read-Host -AsSecureString "Enter value for $Name"
    $bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        [Environment]::SetEnvironmentVariable($Name, $plain, "Machine")
        Write-Host "Set $Name (Machine scope)." -ForegroundColor Green
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

Set-MachineSecret -Name "EQH_SQLSERVER_PASSWORD"
Set-MachineSecret -Name "EQH_EMAIL_PASSWORD"

Write-Host ""
Write-Host "Secrets set. Verify (in a NEW elevated shell) with:" -ForegroundColor Cyan
Write-Host '  [Environment]::GetEnvironmentVariable("EQH_SQLSERVER_PASSWORD","Machine")' -ForegroundColor DarkGray
Write-Host ""
Write-Host "Next: deploy the code (step 7), then run 03_register_task.ps1." -ForegroundColor Cyan
