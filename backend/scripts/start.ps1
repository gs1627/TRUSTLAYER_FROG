$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating Python virtual environment..."
    py -3.11 -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"

Write-Host "Installing backend dependencies..."
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Add DETECTIF_API_KEY before testing provider endpoints."
}

Write-Host "Starting TRUSTLAYER backend at http://127.0.0.1:8000 ..."
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
