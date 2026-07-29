<#
.SYNOPSIS
  Deliberate INTERNAL ARIA META-LANGUAGE vendor snapshot bump.

.DESCRIPTION
  Copies a source ARIA tree into cortex/aria_meta/vendor, regenerates
  MANIFEST.sha256, refreshes INTERNAL_ARIA.json source fields, and verifies
  the bundle. Never mixes Cortex core edits into this ritual—run as its own
  commit when possible.

.PARAMETER Source
  Path to an ARIA repository root (must contain MANIFEST.sha256 and ARIA-RUNTIME.json).

.PARAMETER SourceCommit
  Optional git commit recorded in INTERNAL_ARIA.json.

.PARAMETER SourceRelease
  Optional release label recorded in INTERNAL_ARIA.json.

.EXAMPLE
  .\scripts\powershell\Bump-AriaSnapshot.ps1 -Source C:\path\to\ARIA -SourceCommit abc123 -SourceRelease 0.1.0-alpha.18
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [string]$SourceCommit = "",
    [string]$SourceRelease = "",
    [string]$EvolutionLabel = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Vendor = Join-Path $RepoRoot "cortex\aria_meta\vendor"
$IdentityPath = Join-Path $RepoRoot "cortex\aria_meta\INTERNAL_ARIA.json"
$SourceRoot = (Resolve-Path $Source).Path

foreach ($required in @("MANIFEST.sha256", "ARIA-RUNTIME.json", "ARIA-CONNECT.json", "LICENSE")) {
    if (-not (Test-Path (Join-Path $SourceRoot $required))) {
        throw "Source ARIA tree missing required file: $required"
    }
}

Write-Host "Bumping ARIA snapshot from $SourceRoot -> $Vendor"

# Mirror source into vendor (exclude runtime/cache surfaces Cortex never ships).
$exclude = @(
    ".git", ".aria", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"
)
if (Test-Path $Vendor) {
    Get-ChildItem -Path $Vendor -Force | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
} else {
    New-Item -ItemType Directory -Path $Vendor | Out-Null
}

robocopy $SourceRoot $Vendor /E /XD @exclude /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}

# Regenerate MANIFEST.sha256 over shipped files only.
$manifestLines = @()
Get-ChildItem -Path $Vendor -Recurse -File | Sort-Object FullName | ForEach-Object {
    $relative = $_.FullName.Substring($Vendor.Length).TrimStart("\", "/").Replace("\", "/")
    if ($relative -eq "MANIFEST.sha256") { return }
    if ($relative -match '(^|/)(\.git|\.aria|__pycache__)(/|$)') { return }
    $hash = (Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash.ToLowerInvariant()
    $manifestLines += "$hash  $relative"
}
$manifestPath = Join-Path $Vendor "MANIFEST.sha256"
$manifestLines -join "`n" | Set-Content -Path $manifestPath -Encoding utf8NoBOM
Write-Host "Wrote $($manifestLines.Count) manifest entries"

# Refresh identity metadata without rewriting the whole contract.
$identity = Get-Content $IdentityPath -Raw | ConvertFrom-Json
if ($SourceCommit) { $identity.source_commit = $SourceCommit }
if ($SourceRelease) { $identity.source_release = $SourceRelease }
if ($EvolutionLabel) { $identity.source_language_evolution = $EvolutionLabel }
$identity.vendoring = "git-subtree-squash"
$identity.external_runtime_dependency = $false
$identity | ConvertTo-Json -Depth 8 | Set-Content -Path $IdentityPath -Encoding utf8

# Verify through Cortex.
Push-Location $RepoRoot
try {
    $verify = python -c "from cortex.aria_meta import verify_bundle; import json; print(json.dumps(verify_bundle()))"
    Write-Host $verify
    $payload = $verify | ConvertFrom-Json
    if (-not $payload.valid) {
        throw "ARIA bundle verification failed"
    }
    Write-Host "Bump complete: $($payload.checked_files) files verified."
    Write-Host "Commit this vendor tree separately from Cortex core when practical:"
    Write-Host "  git add cortex/aria_meta/vendor cortex/aria_meta/INTERNAL_ARIA.json"
    Write-Host "  git commit -m `"chore: bump INTERNAL ARIA snapshot`""
} finally {
    Pop-Location
}
