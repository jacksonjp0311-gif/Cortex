Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProjection.psm1') -Force -DisableNameChecking

$script:passed = 0
$script:failed = 0

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param($Expected,$Actual,[string]$Message)
    if ([string]$Expected -cne [string]$Actual) { throw "$Message Expected '$Expected', got '$Actual'." }
}

function Test-Case {
    param([string]$Name,[scriptblock]$Body)
    try {
        & $Body
        $script:passed++
        Write-Host ("PASS  {0}" -f $Name) -ForegroundColor Green
    }
    catch {
        $script:failed++
        Write-Host ("FAIL  {0}: {1}" -f $Name,$_.Exception.Message) -ForegroundColor Red
    }
}

function New-FixedEvent {
    param([string]$Domain='compiler',[string]$Phase='compile',[string]$State='ACTIVE',$Data=$null)
    New-AriaEvent -Domain $Domain -Phase $Phase -State $State -Energy measure -Information bounded -Coherence observed -Data $Data -OccurredAt ([datetime]'2026-01-01T00:00:00Z')
}

Test-Case 'semantic cue registry verifies cryptographic identities' {
    $registry = Import-AriaSemanticCueRegistry
    Assert-True (Test-AriaSemanticCueRegistry $registry).valid 'Registry verification failed.'
}
Test-Case 'semantic cue identities are unique' {
    $registry = Import-AriaSemanticCueRegistry
    Assert-Equal @($registry.cues).Count @($registry.cues.id | Select-Object -Unique).Count 'Cue identities collide.'
}
Test-Case 'identical state produces identical projection' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $one = New-FixedEvent
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $two = New-FixedEvent
    Assert-Equal $one.projection.digest $two.projection.digest 'Projection identity drifted.'
}
Test-Case 'active compiler state maps to transmission' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    Assert-Equal 'signal.transmit' (New-FixedEvent).projection.cue.id 'Active compiler cue mismatch.'
}
Test-Case 'authority evaluation does not claim permission' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $projection = (New-FixedEvent -Domain authority -Phase check -State ACTIVE).projection
    Assert-Equal 'authority.evaluate' $projection.cue.id 'Authority cue mismatch.'
    Assert-True ($projection.explanation.boundary -match 'not been granted') 'Authority boundary was lost.'
}
Test-Case 'pass state maps to bounded verification seal' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $projection = (New-FixedEvent -Domain verifier -Phase semantics -State PASS).projection
    Assert-Equal 'verification.seal' $projection.cue.id 'Verification seal mismatch.'
    Assert-True ($projection.explanation.boundary -match 'not universal truth') 'Seal overclaims truth.'
}
Test-Case 'lifecycle closure has a distinct cue' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    Assert-Equal 'execution.closure' (New-FixedEvent -Domain vm -Phase halt -State PASS).projection.cue.id 'Closure cue mismatch.'
}
Test-Case 'failed invariant maps to fracture' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    Assert-Equal 'invariant.fracture' (New-FixedEvent -Domain verifier -Phase invariant -State FAIL).projection.cue.id 'Fracture cue mismatch.'
}
Test-Case 'warning remains distinct from failure' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $projection = (New-FixedEvent -State WARN).projection
    Assert-Equal 'boundary.warning' $projection.cue.id 'Warning cue mismatch.'
    Assert-True ($projection.explanation.boundary -match 'Failure.*not implied') 'Warning boundary mismatch.'
}
Test-Case 'every projection has static color-independent parity' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $projection = (New-FixedEvent).projection
    Assert-True ([bool]$projection.accessibility.colorIndependent) 'Color is the sole carrier.'
    Assert-True (-not [string]::IsNullOrWhiteSpace($projection.accessibility.static)) 'Static equivalent is absent.'
}
Test-Case 'projection rejects digest tampering' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $projection = (New-FixedEvent).projection
    $projection.explanation.meaning = 'decorative'
    Assert-True (-not (Test-AriaSemanticProjection $projection).valid) 'Tampered projection passed.'
}
Test-Case 'event identity binds its semantic projection' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $event = New-FixedEvent
    $event.projection.glyph.label = 'DRIFT'
    Assert-True (-not (Test-AriaEvent $event).valid) 'Event accepted projection drift.'
}
Test-Case 'secret-shaped detail is redacted before persistence' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $event = New-FixedEvent -Data ([pscustomobject][ordered]@{token='do-not-store';branch='main'})
    Assert-Equal '[REDACTED]' $event.data.token 'Token was not redacted.'
    Assert-Equal 'main' $event.data.branch 'Allowed bounded detail was lost.'
    $lane = New-AriaEvent -Domain runtime -Phase privacy -State INFO -Energy observe -Information 'Bearer secret-access-token' -Coherence bounded
    Assert-Equal '[REDACTED:INFORMATION]' $lane.information 'Secret-shaped signal lane was not redacted.'
}
Test-Case 'long detail is deterministically bounded' {
    $bounded = ConvertTo-AriaBoundedSignalData -Value ('x' * 700)
    Assert-True ($bounded.Length -lt 700) 'Long detail remained unbounded.'
    Assert-True ($bounded -match '\[BOUNDED\]$') 'Bound marker is absent.'
}
Test-Case 'engagement contract rejects manipulative pressure' {
    $registry = Import-AriaSemanticCueRegistry
    $copy = ($registry | ConvertTo-Json -Depth 100 | ConvertFrom-Json)
    $copy.engagementContract.fakeUrgency = $true
    Assert-True (-not (Test-AriaSemanticCueRegistry $copy).valid) 'Fake urgency was admitted.'
}
Test-Case 'transition delta names actual state change' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $null = New-FixedEvent -State ACTIVE
    $next = New-FixedEvent -Domain verifier -Phase semantics -State PASS
    Assert-True ([bool]$next.projection.transition.changed) 'State change was not recorded.'
    Assert-Equal 'state-changed' $next.projection.transition.reason 'Transition reason mismatch.'
}
Test-Case 'repeated state is a new information event, not false change' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $null = New-FixedEvent
    $next = New-FixedEvent
    Assert-True (-not [bool]$next.projection.transition.changed) 'Repeated state claimed a state change.'
    Assert-Equal 'new-information-recorded' $next.projection.transition.reason 'Repeated event reason mismatch.'
}
Test-Case 'latency timing is measured only when evidence exists' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $unmeasured = New-FixedEvent
    Assert-Equal 'event-boundary' $unmeasured.projection.transition.timing 'Unmeasured event claimed latency.'
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $measured = New-FixedEvent -Data ([pscustomobject][ordered]@{durationMs=42})
    Assert-Equal 'measured-latency' $measured.projection.transition.timing 'Measured latency was not represented.'
    Assert-Equal 42 $measured.projection.metrics.durationMs 'Latency metric mismatch.'
}
Test-Case 'projection survives JSON materialization' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $event = New-FixedEvent
    $copy = $event | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    Assert-True (Test-AriaEvent $copy).valid 'Materialized projection failed verification.'
    $legacy = [pscustomobject][ordered]@{
        format='aria.event';version=1;sequence=1;domain='runtime';phase='legacy';state='INFO'
        energy='observe';information='legacy';coherence='bounded';source='aria.runtime'
        occurredAt='2026-01-01T00:00:00.0000000Z';data=$null;digest=''
    }
    $legacy.digest = Get-AriaEventDigest $legacy
    Assert-True (Test-AriaEvent $legacy).valid 'Legacy event v1 compatibility failed.'
}
Test-Case 'event journal and human renderer consume the same cue identity' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $event = New-FixedEvent -Domain vm -Phase halt -State PASS
    $ether = ConvertTo-AriaEtherEvent $event
    Assert-Equal $event.projection.cue.id $ether.projection.cue.id 'Renderer projection diverged from journal event.'
}

Write-Host ''
Write-Host ("Semantic Projection lattice: {0} passed, {1} failed" -f $script:passed,$script:failed)
if ($script:failed -gt 0) { exit 1 }
