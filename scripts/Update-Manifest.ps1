Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force
$count = Update-AriaManifest -Root $root
Write-Host "ARIA manifest updated: $count files"
