Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'aria.ps1') doctor -Strict
if (-not $?) { throw 'ARIA release gate failed.' }
& (Join-Path $root 'aria.ps1') verify
if (-not $?) { throw 'ARIA release gate failed.' }
& (Join-Path $root 'aria.ps1') test
if (-not $?) { throw 'ARIA release gate failed.' }
& (Join-Path $root 'aria.ps1') compile (Join-Path $root 'examples/hello.aria') -Strict
if (-not $?) { throw 'ARIA release gate failed.' }
& (Join-Path $root 'scripts/Package-Aria.ps1')
