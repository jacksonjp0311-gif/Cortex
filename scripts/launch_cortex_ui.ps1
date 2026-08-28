$ErrorActionPreference = "Stop"

$cortexRoot = Split-Path -Parent $PSScriptRoot
$cortexUrl = "http://127.0.0.1:58790/"

try {
    $response = Invoke-WebRequest -Uri "$cortexUrl/v1/status" -UseBasicParsing -TimeoutSec 1
    if ($response.StatusCode -eq 200) {
        Start-Process $cortexUrl
        exit 0
    }
} catch {
    # No active Cortex UI is listening. Start the local loopback service below.
}

Set-Location -LiteralPath $cortexRoot
python -m cortex ui --repo Cortex --port 58790
