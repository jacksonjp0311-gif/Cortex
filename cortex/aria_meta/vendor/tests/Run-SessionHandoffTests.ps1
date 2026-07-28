Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticContinuity.psm1') -Force -DisableNameChecking
$script:Passed=0;$script:Failed=0;$script:Expected=8
function Test-H([string]$Name,[scriptblock]$Body){try{&$Body;$script:Passed++;Write-Host("◆  {0}"-f$Name)-ForegroundColor Green}catch{$script:Failed++;Write-Host("⬗  {0} · {1}"-f$Name,$_.Exception.Message)-ForegroundColor Magenta}}
function Assert-T([bool]$Value,[string]$Message){if(-not$Value){throw$Message}}
function Assert-E($Expected,$Actual,[string]$Message){if((ConvertTo-AriaJson ([pscustomobject]@{v=$Expected}))-cne(ConvertTo-AriaJson ([pscustomobject]@{v=$Actual}))){throw"$Message Expected=$Expected Actual=$Actual"}}
$d='sha256:'+('a'*64);$d2='sha256:'+('b'*64)
function New-HandoffFixture{New-AriaSessionHandoff -ReplayDigest $d -FromAgent 'agent:producer' -ToAgent 'agent:successor' -ContextRefs @([pscustomobject][ordered]@{kind='replay';digest=$d},[pscustomobject][ordered]@{kind='evidence';digest=$d2}) -ContinuationBoundary 'align.intent'}
Test-H 'session handoff schema is machine readable'{$s=Read-AriaUtf8Text (Join-Path $root 'schemas/session-handoff.schema.json')|ConvertFrom-Json;Assert-E 'aria.session-handoff/1' $s.properties.schema.const 'Handoff schema identity changed.'}
Test-H 'session handoff factory emits a valid record'{$h=New-HandoffFixture;$v=Test-AriaSessionHandoff $h;Assert-T $v.valid (@($v.errors)-join', ')}
Test-H 'session handoff identity is deterministic'{$a=New-HandoffFixture;$b=New-HandoffFixture;Assert-E $a.digest $b.digest 'Handoff identity changed.'}
Test-H 'session handoff excludes private conversational material'{$h=New-HandoffFixture;foreach($x in @('prompts','secrets','credentials','private-payloads','unrelated-history')){Assert-T ($x-in@($h.exclusions)) "Missing privacy exclusion $x."}}
Test-H 'session handoff carries references without payloads'{$h=New-HandoffFixture;foreach($r in @($h.contextRefs)){Assert-E @('kind','digest') @($r.PSObject.Properties.Name) 'Handoff context carried extra fields.'}}
Test-H 'session handoff requires distinct participants'{$h=New-HandoffFixture;$h.toAgent=$h.fromAgent;$h.digest='';$h.digest='sha256:'+(Get-AriaSha256Text (ConvertTo-AriaJson ([pscustomobject][ordered]@{schema=$h.schema;protocol=$h.protocol;replayDigest=$h.replayDigest;fromAgent=$h.fromAgent;toAgent=$h.toAgent;contextRefs=$h.contextRefs;continuationBoundary=$h.continuationBoundary;exclusions=$h.exclusions;session=$h.session;authority=$h.authority})));$v=Test-AriaSessionHandoff $h;Assert-T ('E_HANDOFF_PARTICIPANTS'-in@($v.errors)) 'Self-handoff passed.'}
Test-H 'session handoff transfers neither consent nor authority'{$h=New-HandoffFixture;Assert-T (-not$h.authority.grantsAuthority-and-not$h.authority.consentTransfers) 'Handoff transferred authority.';Assert-E 0 @($h.authority.capabilities).Count 'Handoff carried capabilities.'}
Test-H 'tampered session handoff is rejected'{$h=New-HandoffFixture;$h.continuationBoundary='execute';$v=Test-AriaSessionHandoff $h;Assert-T ('E_HANDOFF_DIGEST'-in@($v.errors)) 'Handoff digest fracture missing.'}
Write-Host("⧉  session-handoff lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'}))-ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Passed+$script:Failed-ne$script:Expected){throw'Session handoff test count diverged.'};if($script:Failed){throw"Session handoff lattice failed: $script:Failed failure(s)."}
