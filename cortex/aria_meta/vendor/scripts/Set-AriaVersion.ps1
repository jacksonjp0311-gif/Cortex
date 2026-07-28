[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$NewVersion)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force
if (-not (Test-AriaSemanticVersion -Version $NewVersion)) { throw "Invalid semantic version: $NewVersion" }
Write-AriaUtf8NoBom -Path (Join-Path $root 'VERSION') -Text ($NewVersion + "`n")
$lockPath = Join-Path $root 'aria.lock.json'
$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
$lock.compilerVersion = $NewVersion
Write-AriaUtf8NoBom -Path $lockPath -Text (($lock | ConvertTo-Json -Depth 20) + "`n")
Write-Host "ARIA compiler version set to $NewVersion. Update CHANGELOG.md before release."
