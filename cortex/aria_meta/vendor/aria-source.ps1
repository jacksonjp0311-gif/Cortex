[CmdletBinding()]
param(
    [Parameter(Position=0)][ValidateSet('run','check','ir')][string]$Command='run',
    [Parameter(Position=1,Mandatory=$true)][string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $root 'src/Aria.SourceCore.psm1') -Force -DisableNameChecking

$result=Invoke-AriaSourceFile -Path $Path
if(-not$result.valid){
    foreach($error in @($result.errors)){
        Write-Host ("⬗  {0}  {1}" -f $error.code,$error.message) -ForegroundColor Red
    }
    exit 1
}

switch($Command){
    'check' {
        Write-Host "◆  SOURCE VERIFIED" -ForegroundColor Green
        Write-Host ("└─ ◇  {0}" -f $Path) -ForegroundColor DarkGray
    }
    'ir' {
        $result.ir | ConvertTo-Json -Depth 64
    }
    'run' {
        foreach($item in @($result.output)){
            if($item-is[bool]){
                Write-Output $item.ToString().ToLowerInvariant()
            }
            else{
                Write-Output $item
            }
        }
    }
}