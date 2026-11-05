<#
.SYNOPSIS
    Prepares Windows 11 for iFix: WSL 2 + Ubuntu, the Linux device tooling and
    (optionally) usbipd-win so the iPhone can be shared into WSL.

.DESCRIPTION
    Run from an elevated PowerShell:
        powershell -ExecutionPolicy Bypass -File .\windows\install.ps1

    If WSL or Ubuntu is not installed yet, this script installs it, tells you to
    reboot, and exits. Run it again afterwards to finish the setup.

.PARAMETER SkipUsbipd
    Do not install usbipd-win.

.PARAMETER SkipTooling
    Only check WSL/Ubuntu, do not install the Linux packages.
#>
[CmdletBinding()]
param(
    [switch]$SkipUsbipd,
    [switch]$SkipTooling
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this from an elevated PowerShell (right-click > Run as administrator).'
    }
}

function Get-WslRepoPath([string]$Path) {
    $mapped = (& wsl -e wslpath -a $Path | Out-String).Trim()
    if (-not $mapped) { throw 'Could not map the repository path into WSL.' }
    return $mapped
}

Assert-Admin

$repo = Split-Path -Parent $PSCommandPath

Write-Host '==> Windows version'
$build = [Environment]::OSVersion.Version
Write-Host "    $($build.Major).$($build.Minor) build $($build.Build)"
if ($build.Build -lt 22000) {
    Write-Warning 'Windows 11 (build 22000+) is required for WSLg, so the iFix window can appear on your desktop.'
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Host '==> Installing WSL 2'
    wsl --install
    Write-Host ''
    Write-Host 'Reboot Windows, open Ubuntu once to create your Linux user, then run this script again.' -ForegroundColor Yellow
    exit 0
}

$distros = @(& wsl -l -q 2>$null | ForEach-Object { $_.Trim() -replace "`0", '' } | Where-Object { $_ })
if (-not ($distros | Where-Object { $_ -like 'Ubuntu*' })) {
    Write-Host '==> Installing Ubuntu'
    wsl --install -d Ubuntu
    Write-Host ''
    Write-Host 'Reboot Windows (if asked), open Ubuntu once to create your Linux user, then run this script again.' -ForegroundColor Yellow
    exit 0
}

Write-Host '==> Making sure WSL 2 is the default and up to date'
wsl --set-default-version 2 | Out-Null
wsl --update | Out-Null

if (-not $SkipTooling) {
    Write-Host '==> Installing the Linux tooling inside Ubuntu (sudo password may be requested)'
    $wslRepo = Get-WslRepoPath $repo
    & wsl -e bash -lc "cd '$wslRepo' && bash windows/setup-wsl.sh"
    if ($LASTEXITCODE -ne 0) { throw "windows/setup-wsl.sh failed with exit code $LASTEXITCODE." }
}

if (-not $SkipUsbipd) {
    if (Get-Command usbipd -ErrorAction SilentlyContinue) {
        Write-Host '==> usbipd-win already installed'
    } else {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host '==> Installing usbipd-win'
            winget install --id dorssel.usbipd-win --accept-source-agreements --accept-package-agreements
        } else {
            Write-Warning 'winget not found - install usbipd-win from https://github.com/dorssel/usbipd-win/releases'
        }
    }
}

Write-Host ''
Write-Host '==> Setup complete' -ForegroundColor Green
Write-Host '    Launch the GUI:  windows\run-ifix.cmd'
Write-Host '    Diagnostics:     wsl -e bash -lc "cd $(Get-WslRepoPath $repo) && python3 iFix.py --doctor"'
Write-Host ''
Write-Host '    To share the iPhone with WSL (run in an elevated terminal):'
Write-Host '      usbipd list'
Write-Host '      usbipd bind --busid <BUSID>'
Write-Host '      usbipd attach --wsl --busid <BUSID>'
