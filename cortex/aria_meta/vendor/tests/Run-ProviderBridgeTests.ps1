Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticContinuity.psm1') -Force -DisableNameChecking
$script:Passed=0;$script:Failed=0;$script:Expected=8
function Test-B([string]$Name,[scriptblock]$Body){try{&$Body;$script:Passed++;Write-Host("◆  {0}"-f$Name)-ForegroundColor Green}catch{$script:Failed++;Write-Host("⬗  {0} · {1}"-f$Name,$_.Exception.Message)-ForegroundColor Magenta}}
function Assert-T([bool]$Value,[string]$Message){if(-not$Value){throw$Message}}
function Assert-E($Expected,$Actual,[string]$Message){if((ConvertTo-AriaJson ([pscustomobject]@{v=$Expected}))-cne(ConvertTo-AriaJson ([pscustomobject]@{v=$Actual}))){throw"$Message Expected=$Expected Actual=$Actual"}}
$d='sha256:'+('a'*64)
function New-BridgeFixture{New-AriaProviderBridge -HandoffDigest $d -ProviderId 'provider:neutral' -ModelId 'model:declared' -Operation 'interpret.intent' -RequestedCapabilities @('context.read') -CapabilityCeiling @('context.read') -ConsentDigest $d}
Test-B 'provider bridge schema is machine readable'{$s=Read-AriaUtf8Text (Join-Path $root 'schemas/provider-bridge.schema.json')|ConvertFrom-Json;Assert-E 'aria.provider-bridge/1' $s.properties.schema.const 'Bridge schema identity changed.'}
Test-B 'bounded provider request becomes eligible'{$b=New-BridgeFixture;$v=Test-AriaProviderBridge $b;Assert-T $v.valid (@($v.errors)-join', ');Assert-E 'eligible' $b.decision 'Bounded request rejected.'}
Test-B 'excess provider capability is deterministically rejected'{$b=New-AriaProviderBridge -HandoffDigest $d -ProviderId p -ModelId m -Operation o -RequestedCapabilities @('secret.read') -CapabilityCeiling @('context.read') -ConsentDigest $d;Assert-E 'rejected' $b.decision 'Excess capability passed.'}
Test-B 'provider membrane performs no network execution'{$b=New-BridgeFixture;Assert-T (-not$b.transport.networkExecution-and-not$b.transport.providerCalled) 'Provider was called.'}
Test-B 'provider membrane contains no model payload'{$b=New-BridgeFixture;Assert-T (-not$b.transport.payloadIncluded) 'Bridge embedded a payload.'}
Test-B 'provider eligibility grants no authority'{$b=New-BridgeFixture;Assert-T (-not$b.authority.grantsAuthority) 'Bridge granted authority.';Assert-E 0 @($b.authority.capabilitiesActivated).Count 'Bridge activated a capability.'}
Test-B 'provider bridge identity is deterministic'{$a=New-BridgeFixture;$b=New-BridgeFixture;Assert-E $a.digest $b.digest 'Bridge identity changed.'}
Test-B 'tampered provider bridge is rejected'{$b=New-BridgeFixture;$b.transport.providerCalled=$true;$v=Test-AriaProviderBridge $b;Assert-T ('E_BRIDGE_TRANSPORT'-in@($v.errors)) 'Transport tampering passed.';Assert-T ('E_BRIDGE_DIGEST'-in@($v.errors)) 'Bridge digest fracture missing.'}
Write-Host("⧉  provider-bridge lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'}))-ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Passed+$script:Failed-ne$script:Expected){throw'Provider bridge test count diverged.'};if($script:Failed){throw"Provider bridge lattice failed: $script:Failed failure(s)."}
