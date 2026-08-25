# run.ps1 — Launch BUG using the project virtual environment
# Usage: .\run.ps1
# Or from any terminal: powershell -File run.ps1

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$AppMain    = Join-Path $PSScriptRoot "app\main.py"

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv not found at: $VenvPython`nRun: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "[BUG] Starting with venv Python: $VenvPython" -ForegroundColor Cyan
& $VenvPython $AppMain @args
