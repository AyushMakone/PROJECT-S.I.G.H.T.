param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found on PATH. Install Python 3.12+ or activate the project environment."
}

$env:SIMULATOR_MODE = "local"
python -m uvicorn backend.main:app --host $Host --port $Port
