param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\command-centre")

if (-not (Test-Path "node_modules")) {
    npm install --no-audit --no-fund
}

npm run dev -- --host 127.0.0.1 --port $Port
