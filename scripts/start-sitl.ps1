param(
    [string]$Connection = "udp:127.0.0.1:14550"
)

$ErrorActionPreference = "Stop"

if (-not $env:ARDUPILOT_SITL_PATH) {
    throw "ARDUPILOT_SITL_PATH is not set. Install ArduPilot SITL and set it to the directory containing ArduCopter (or run SITL in WSL and start it there). Expected MAVLink endpoint: $Connection"
}

$sitlPath = $env:ARDUPILOT_SITL_PATH
if (-not (Test-Path $sitlPath)) {
    throw "ARDUPILOT_SITL_PATH does not exist: $sitlPath"
}

$binary = Get-ChildItem -Path $sitlPath -Filter "ArduCopter*" -File -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $binary) {
    throw "No ArduCopter SITL binary was found in $sitlPath. Set ARDUPILOT_SITL_PATH to the built SITL directory."
}

Write-Host "Starting ArduPilot SITL from $($binary.FullName)"
Write-Host "The FastAPI backend must connect to $Connection after a heartbeat is available."
& $binary.FullName
