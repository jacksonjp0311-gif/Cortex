#Requires -Version 5.1
<#
.SYNOPSIS
  Cortex Desktop embed — clone jacksonjp0311-gif/Cortex to your Desktop.

.DESCRIPTION
  First-party installer script. Run deliberately after downloading from the
  Cortex embed HUD (GitHub Pages). Does not phone home except git clone/pull.

  Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File .\embed-cortex.ps1
#>
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/jacksonjp0311-gif/Cortex.git"
$Dest = Join-Path ([Environment]::GetFolderPath("Desktop")) "Cortex"

Write-Host ""
Write-Host "  CORTEX // DESKTOP EMBED" -ForegroundColor Cyan
Write-Host "  target: $Dest" -ForegroundColor DarkGray
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: git not found on PATH. Install Git for Windows, then re-run." -ForegroundColor Red
    exit 1
}

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "  existing clone detected — git pull" -ForegroundColor Yellow
    Push-Location $Dest
    try {
        git pull --ff-only
    } finally {
        Pop-Location
    }
} elseif (Test-Path $Dest) {
    Write-Host "  ERROR: $Dest exists but is not a git repo. Move/rename it, then re-run." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  cloning…" -ForegroundColor Cyan
    git clone $RepoUrl $Dest
}

Write-Host ""
Write-Host "  ◈ CORTEX EMBEDDED ON DESKTOP" -ForegroundColor Magenta
Write-Host "  path: $Dest" -ForegroundColor Green
Write-Host ""
Write-Host "  next:" -ForegroundColor DarkGray
Write-Host "    cd `"$Dest`"" -ForegroundColor White
Write-Host "    pip install -e ." -ForegroundColor White
Write-Host "    python -m cortex bootstrap . --name Cortex --json" -ForegroundColor White
Write-Host ""
