$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run: python -m venv .venv"
}

Set-Location $projectRoot
& $venvPython -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
