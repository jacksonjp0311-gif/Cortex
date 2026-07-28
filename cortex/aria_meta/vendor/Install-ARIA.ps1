[CmdletBinding()]
param([switch]$SkipShortcut, [switch]$VerboseOutput)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Get-ChildItem -LiteralPath $root -Recurse -Force -File | Unblock-File -ErrorAction SilentlyContinue
Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking

$clock = [Diagnostics.Stopwatch]::StartNew()
Write-AriaBanner -Title 'ARIA / INSTALL' -Subtitle 'strict gate · conformance · desktop operator link'
Write-AriaStage -Name 'installation lattice' -State Pulse -Detail $root

& (Join-Path $root 'aria.ps1') doctor -Strict -VerboseOutput:$VerboseOutput
if (-not $?) { throw 'ARIA doctor gate failed.' }
& (Join-Path $root 'aria.ps1') test -VerboseOutput:$VerboseOutput
if (-not $?) { throw 'ARIA test gate failed.' }

if (-not $SkipShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktop 'ARIA Language Laboratory.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $root 'Start-ARIA.cmd'
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = 'ARIA gated compiler, compressed bytecode, and local virtual machine'
    $shortcut.Save()
    Write-AriaStage -Name 'desktop shortcut' -State Pass -Detail $shortcutPath
}

$clock.Stop()
Write-AriaSummary -Title 'ARIA INSTALLED' -Passed $true -Detail $root -Duration $clock.Elapsed
Write-AriaKeyValue -Key 'Launch' -Value 'Start-ARIA.cmd or .\aria.cmd'
