[CmdletBinding()]
param([string]$Destination)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'aria.ps1') verify
if (-not $?) { throw 'Manifest gate failed; package gate closed.' }
& (Join-Path $root 'aria.ps1') test
if (-not $?) { throw 'Tests failed; package gate closed.' }
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
if (-not $Destination) { $Destination = Join-Path (Join-Path $root 'dist') ("aria-language-$version.zip") }
$staging = Join-Path $env:TEMP ('aria-package-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    $target = Join-Path $staging 'aria-language'
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Get-ChildItem -LiteralPath $root -Force | Where-Object { $_.Name -notin @('.git','.aria','dist') } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
    }
    $parent = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Compress-Archive -Path $target -DestinationPath $Destination -Force
    Write-Host "Packaged $Destination"
}
finally { Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue }
