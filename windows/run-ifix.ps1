# Launches the iFix GUI from Windows, running inside WSL 2 (WSLg shows the window).
#
#   powershell -ExecutionPolicy Bypass -File .\windows\run-ifix.ps1
#   powershell -ExecutionPolicy Bypass -File .\windows\run-ifix.ps1 --doctor
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

$repo = Split-Path -Parent $PSScriptRoot
$mapped = (& wsl -e wslpath -a $repo | Out-String).Trim()

if (-not $mapped) {
    Write-Error 'Could not map the repository path into WSL. Is WSL installed? Run windows\install.ps1 first.'
    exit 1
}

$extra = if ($Arguments) { ' ' + ($Arguments -join ' ') } else { '' }
& wsl -e bash -lc "cd '$mapped' && exec python3 iFix.py$extra"
exit $LASTEXITCODE
