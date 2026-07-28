Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticContinuity.psm1') -Force -DisableNameChecking
$script:Passed=0;$script:Failed=0;$script:Expected=8
function Test-M([string]$Name,[scriptblock]$Body){try{&$Body;$script:Passed++;Write-Host("◆  {0}"-f$Name)-ForegroundColor Green}catch{$script:Failed++;Write-Host("⬗  {0} · {1}"-f$Name,$_.Exception.Message)-ForegroundColor Magenta}}
function Assert-T([bool]$Value,[string]$Message){if(-not$Value){throw$Message}}
function Assert-E($Expected,$Actual,[string]$Message){if((ConvertTo-AriaJson ([pscustomobject]@{v=$Expected}))-cne(ConvertTo-AriaJson ([pscustomobject]@{v=$Actual}))){throw"$Message Expected=$Expected Actual=$Actual"}}
$a='sha256:'+('a'*64);$b='sha256:'+('b'*64);$c='sha256:'+('c'*64);$members=@([pscustomobject][ordered]@{id='agent:producer';role='producer';artifactDigest=$a},[pscustomobject][ordered]@{id='agent:critic';role='critic';artifactDigest=$b},[pscustomobject][ordered]@{id='human:operator';role='human';artifactDigest=$c})
function New-MeshFixture{New-AriaCooperativeMesh -SharedStateDigest $a -Members $members -BridgeDigests @($b,$c)}
Test-M 'cooperative mesh schema is machine readable'{$s=Read-AriaUtf8Text (Join-Path $root 'schemas/cooperative-mesh.schema.json')|ConvertFrom-Json;Assert-E 'aria.cooperative-mesh/1' $s.properties.schema.const 'Mesh schema identity changed.'}
Test-M 'cooperative mesh factory emits a valid record'{$m=New-MeshFixture;$v=Test-AriaCooperativeMesh $m;Assert-T $v.valid (@($v.errors)-join', ')}
Test-M 'cooperative mesh identity is deterministic'{$x=New-MeshFixture;$y=New-MeshFixture;Assert-E $x.digest $y.digest 'Mesh identity changed.'}
Test-M 'cooperative mesh requires producer critic and human'{$bad=@($members|Where-Object{$_.role-ne'critic'});try{$null=New-AriaCooperativeMesh -SharedStateDigest $a -Members $bad -BridgeDigests @($b,$c);throw'Mesh without critic passed.'}catch{Assert-T ($_.Exception.Message-match'E_MESH_ROLES|Invalid cooperative mesh') 'Wrong missing-role failure.'}}
Test-M 'cooperative mesh makes independent challenge explicit'{$m=New-MeshFixture;Assert-T ('critic'-in@($m.members.role)) 'Critic missing.';Assert-T (-not$m.coordination.selfApprovalAllowed) 'Self approval allowed.'}
Test-M 'material disagreement requires human resolution'{$m=New-MeshFixture;Assert-E 'human-required' $m.coordination.conflictResolution 'Human resolution changed.';Assert-T $m.consensus.materialDisagreementBlocks 'Material disagreement did not block.'}
Test-M 'cooperative mesh cannot aggregate authority or claim consensus'{$m=New-MeshFixture;Assert-T (-not$m.authority.aggregationAllowed-and-not$m.authority.grantsAuthority-and-not$m.consensus.claimed) 'Mesh manufactured trust or authority.'}
Test-M 'duplicate provider bridges are rejected' {try{$null=New-AriaCooperativeMesh -SharedStateDigest $a -Members $members -BridgeDigests @($b,$b);throw'Duplicate bridge passed.'}catch{Assert-T ($_.Exception.Message-match'E_MESH_BRIDGES|Invalid cooperative mesh') 'Wrong duplicate-bridge failure.'}}
Write-Host("⧉  cooperative-mesh lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'}))-ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Passed+$script:Failed-ne$script:Expected){throw'Cooperative mesh test count diverged.'};if($script:Failed){throw"Cooperative mesh lattice failed: $script:Failed failure(s)."}
