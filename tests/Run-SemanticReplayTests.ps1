Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticContinuity.psm1') -Force -DisableNameChecking
$script:Passed=0;$script:Failed=0;$script:Expected=8
function Test-R([string]$Name,[scriptblock]$Body){try{&$Body;$script:Passed++;Write-Host("◆  {0}"-f$Name)-ForegroundColor Green}catch{$script:Failed++;Write-Host("⬗  {0} · {1}"-f$Name,$_.Exception.Message)-ForegroundColor Magenta}}
function Assert-T([bool]$Value,[string]$Message){if(-not$Value){throw$Message}}
function Assert-E($Expected,$Actual,[string]$Message){if((ConvertTo-AriaJson ([pscustomobject]@{v=$Expected}))-cne(ConvertTo-AriaJson ([pscustomobject]@{v=$Actual}))){throw"$Message Expected=$Expected Actual=$Actual"}}
$d='sha256:'+('a'*64);$d2='sha256:'+('b'*64);$d3='sha256:'+('c'*64)
function New-ReplayFixture{New-AriaSemanticReplay -HandshakeDigest $d -SessionId 'session:alpha14' -BaselineDigest $d -IntentDigest $d -InterpretationDigest $d -ProposalDigest $d -ConsentDigest $d -PolicyDigest $d -EvidenceDigests @($d2) -StateDigest $d3}
Test-R 'semantic replay schema is machine readable'{$s=Read-AriaUtf8Text (Join-Path $root 'schemas/semantic-replay.schema.json')|ConvertFrom-Json;Assert-E 'aria.semantic-replay/1' $s.properties.schema.const 'Replay schema identity changed.'}
Test-R 'semantic replay factory emits a valid record'{$r=New-ReplayFixture;$v=Test-AriaSemanticReplay $r;Assert-T $v.valid (@($v.errors)-join', ')}
Test-R 'semantic replay identity is deterministic'{$a=New-ReplayFixture;$b=New-ReplayFixture;Assert-E $a.digest $b.digest 'Replay identity changed.'}
Test-R 'semantic replay never repeats external effects'{$r=New-ReplayFixture;Assert-T (-not$r.replay.repeatsExternalEffects) 'Replay repeated an effect.';Assert-E 'verify-only' $r.replay.mode 'Replay mode changed.'}
Test-R 'semantic replay grants no authority'{$r=New-ReplayFixture;Assert-T (-not$r.authority.grantsAuthority) 'Replay granted authority.';Assert-E 0 @($r.authority.capabilities).Count 'Replay carried capabilities.'}
Test-R 'identical semantic states replay coherently'{$a=New-ReplayFixture;$b=New-ReplayFixture;$c=Compare-AriaSemanticReplay $a $b;Assert-T $c.coherent 'Identical replay drifted.'}
Test-R 'semantic replay identifies the first exact drift boundary'{$a=New-ReplayFixture;$b=New-ReplayFixture;$b.proposalDigest=$d2;$b.stateDigest=$d2;$c=Compare-AriaSemanticReplay $a $b;Assert-E 'proposalDigest' $c.firstBoundary 'Replay reported the wrong first drift.'}
Test-R 'tampered semantic replay is rejected'{$r=New-ReplayFixture;$r.stateDigest=$d2;$v=Test-AriaSemanticReplay $r;Assert-T (-not$v.valid) 'Tampered replay passed.';Assert-T ('E_REPLAY_DIGEST'-in@($v.errors)) 'Replay digest fracture missing.'}
Write-Host("⧉  semantic-replay lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'}))-ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Passed+$script:Failed-ne$script:Expected){throw'Semantic replay test count diverged.'};if($script:Failed){throw"Semantic replay lattice failed: $script:Failed failure(s)."}
