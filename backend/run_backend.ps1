$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $backendRoot "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv (Join-Path $backendRoot "venv")
}

& $venvPython -m pip install -r (Join-Path $backendRoot "requirements.txt")
& $venvPython (Join-Path $backendRoot "server.py")
