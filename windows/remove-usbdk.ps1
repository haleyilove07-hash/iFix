# Removes the UsbDk filter driver, which blocks usbipd-win from passing USB
# devices (including an iPad in DFU mode) through to WSL. UsbDk registers itself
# in the USB device class UpperFilters, so it intercepts every USB device before
# usbipd can export it; the symptom is palera1n/checkm8 hanging in the DFU stage.
#
#   powershell -ExecutionPolicy Bypass -File .\windows\remove-usbdk.ps1
#
# Run from an elevated prompt. UsbDk can be reinstalled from its official MSI if
# another tool (e.g. a paid unlock suite) needs it back.

$product = '{6D4A6ED0-CF41-4615-A4B3-BDA018C3C1CD}'
$key = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{36fc9e60-c465-11cf-8056-444553540000}'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error 'Run this from an elevated PowerShell (administrator).'
    exit 1
}

$installed = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -eq $product -or $_.DisplayName -like '*UsbDk*' }

if ($installed) {
    Write-Host '==> uninstalling UsbDk...'
    Start-Process msiexec.exe -ArgumentList "/x $product /qn /norestart" -Wait
} else {
    Write-Host '==> UsbDk is not installed'
}

$filters = @((Get-ItemProperty $key).UpperFilters | Where-Object { $_ })
$blocked = @($filters | Where-Object { $_ -eq 'UsbDk' })
if ($blocked.Count -gt 0) {
    Write-Host '==> removing the UsbDk filter entry'
    $keep = @($filters | Where-Object { $_ -ne 'UsbDk' })
    if ($keep.Count -eq 0) {
        Remove-ItemProperty -Path $key -Name UpperFilters -ErrorAction SilentlyContinue
    } else {
        Set-ItemProperty -Path $key -Name UpperFilters -Value $keep
    }
}

$now = @((Get-ItemProperty $key).UpperFilters | Where-Object { $_ })
Write-Host ("UpperFilters now: [{0}]" -f ($now -join ','))
Write-Host ("UsbDk.sys present: {0}" -f (Test-Path 'C:\Windows\System32\drivers\UsbDk.sys'))
Write-Host 'Done. Reboot before retrying the DFU passthrough.'
