Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$policy = Join-Path $root 'aria.policy.json'

Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Etherflow.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProjection.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking

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
function New-TestWorkspace {
    $path = Join-Path ([IO.Path]::GetTempPath()) ('aria-signal-integrity-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    [IO.Path]::GetFullPath($path)
}
function Remove-TestWorkspace {
    param([string]$Path)
    if ($Path -and (Test-Path -LiteralPath $Path -PathType Container)) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}
function Send-ProbeEvent {
    param([string]$Phase='probe',[string]$State='INFO')
    Send-AriaEvent -Domain runtime -Phase $Phase -State $State -Energy observe -Information bounded -Coherence recorded -PassThru
}
function Get-LedgerPath {
    param([string]$Workspace)
    Join-Path $Workspace '.aria/events/aria.events.ndjson'
}
function Write-LedgerLines {
    param([string]$Path,[string[]]$Lines)
    [IO.File]::WriteAllText($Path,(($Lines -join [Environment]::NewLine) + [Environment]::NewLine),[Text.UTF8Encoding]::new($false))
}
function Assert-LedgerRejected {
    param([string]$Workspace,[string]$Message)
    $rejected = $false
    try { $null = @(Read-AriaEventLedger -WorkspaceRoot $Workspace) } catch { $rejected = $true }
    Assert-True $rejected $Message
}

Test-Case 'event v3 carries ledger and operation continuity fields' {
    Initialize-AriaEventSpine -WorkspaceRoot $root -OperationId ('aria.operation.test:' + ('1' * 64)) | Out-Null
    $event = Send-ProbeEvent
    Assert-Equal 3 $event.version 'Event version mismatch.'
    Assert-Equal 1 $event.sequence 'Ledger sequence mismatch.'
    Assert-Equal 1 $event.operationSequence 'Operation sequence mismatch.'
    Assert-Equal '' $event.previousDigest 'First previous digest must be empty.'
}
Test-Case 'in-memory event chain binds the previous digest' {
    Initialize-AriaEventSpine -WorkspaceRoot $root -OperationId ('aria.operation.test:' + ('2' * 64)) | Out-Null
    $one = Send-ProbeEvent -Phase one
    $two = Send-ProbeEvent -Phase two
    Assert-Equal $one.digest $two.previousDigest 'Previous event digest was not chained.'
}
Test-Case 'operation sequence advances inside one operation' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $null = Send-ProbeEvent -Phase one
    $two = Send-ProbeEvent -Phase two
    Assert-Equal 2 $two.operationSequence 'Operation sequence did not advance.'
}
Test-Case 'new operation resets only operation-local transition state' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $one = Send-ProbeEvent -Phase one
    $null = Start-AriaEventOperation -Name second
    $two = Send-ProbeEvent -Phase two
    Assert-Equal 2 $two.sequence 'Ledger sequence reset across operations.'
    Assert-Equal 1 $two.operationSequence 'Operation sequence did not reset.'
    Assert-Equal '' $two.projection.transition.from 'New operation inherited an unrelated state.'
    Assert-Equal $one.digest $two.previousDigest 'Ledger chain broke across operations.'
}
Test-Case 'persistent ledger sequence resumes across sessions' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $one = Send-ProbeEvent -Phase one
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $two = Send-ProbeEvent -Phase two
        Assert-Equal 2 $two.sequence 'Persistent sequence did not resume.'
        Assert-Equal $one.digest $two.previousDigest 'Persistent digest chain did not resume.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'persistent ledger round trip verifies every event' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $null = Send-ProbeEvent -Phase one
        $null = Send-ProbeEvent -Phase two -State PASS
        $events = @(Read-AriaEventLedger $workspace)
        Assert-Equal 2 $events.Count 'Ledger count mismatch.'
        Assert-True (Test-AriaEvent $events[1]).valid 'Persisted event failed verification.'
        Publish-AriaEvent -Event $events[0] -Replay
        Assert-Equal 2 @(Read-AriaEventLedger $workspace).Count 'Replay mutated the ledger.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'batched persistence preserves exact replay and rejects changed ledger bytes' {
    $workspace = New-TestWorkspace
    $tamperWorkspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        Start-AriaEventBatch -ChunkSize 32
        foreach ($phase in @('one','two','three','four','five')) {
            $null = Send-ProbeEvent -Phase $phase
        }
        Complete-AriaEventBatch
        $events = @(Read-AriaEventLedger $workspace)
        Assert-Equal 5 $events.Count 'Batched ledger count mismatch.'
        Assert-Equal 'five' $events[4].phase 'Batched event order changed.'
        Assert-True (Test-AriaEvent $events[4]).valid 'Batched tail event failed verification.'

        Initialize-AriaEventSpine -WorkspaceRoot $tamperWorkspace -Persist | Out-Null
        $null = Send-ProbeEvent -Phase anchor
        Start-AriaEventBatch -ChunkSize 32
        $null = Send-ProbeEvent -Phase pending
        $path = Get-LedgerPath $tamperWorkspace
        $text = [IO.File]::ReadAllText($path).Replace('"phase":"anchor"','"phase":"tamper"')
        [IO.File]::WriteAllText($path,$text,[Text.UTF8Encoding]::new($false))
        $rejected = $false
        try { Complete-AriaEventBatch } catch { $rejected = $true }
        Assert-True $rejected 'Batch flush accepted changed ledger bytes.'
    }
    finally {
        Remove-TestWorkspace $workspace
        Remove-TestWorkspace $tamperWorkspace
    }
}
Test-Case 'ledger rejects reordered events' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $null = Send-ProbeEvent -Phase one
        $null = Send-ProbeEvent -Phase two
        $path = Get-LedgerPath $workspace
        $lines = @(Get-Content -LiteralPath $path)
        Write-LedgerLines $path @($lines[1],$lines[0])
        Assert-LedgerRejected $workspace 'Reordered ledger was accepted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'ledger rejects a deleted middle event' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $null = Send-ProbeEvent -Phase one
        $null = Send-ProbeEvent -Phase two
        $null = Send-ProbeEvent -Phase three
        $path = Get-LedgerPath $workspace
        $lines = @(Get-Content -LiteralPath $path)
        Write-LedgerLines $path @($lines[0],$lines[2])
        Assert-LedgerRejected $workspace 'Ledger with a deleted event was accepted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'ledger rejects duplicated events' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $null = Send-ProbeEvent -Phase one
        $null = Send-ProbeEvent -Phase two
        $path = Get-LedgerPath $workspace
        $lines = @(Get-Content -LiteralPath $path)
        Write-LedgerLines $path @($lines[0],$lines[0],$lines[1])
        Assert-LedgerRejected $workspace 'Duplicated ledger event was accepted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'ledger rejects event content tampering' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $null = Send-ProbeEvent
        $path = Get-LedgerPath $workspace
        $originalLine = Get-Content -LiteralPath $path -Raw
        $line = $originalLine.Replace('"information":"bounded"','"information":"mutated"')
        [IO.File]::WriteAllText($path,$line,[Text.UTF8Encoding]::new($false))
        Assert-LedgerRejected $workspace 'Tampered ledger event was accepted.'
        $appendRejected = $false
        try { $null = Send-ProbeEvent -Phase after-tamper } catch { $appendRejected = $true }
        Assert-True $appendRejected 'Append accepted ledger bytes changed after initialization.'

        $event = $originalLine | ConvertFrom-Json
        $event.operationSequence = 2
        $event.digest = Get-AriaEventDigest $event
        Write-LedgerLines $path @(($event | ConvertTo-Json -Depth 100 -Compress))
        Assert-LedgerRejected $workspace 'Rehashed invalid operation sequence was accepted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'append rejects a stale previous digest' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace -Persist | Out-Null
        $event = New-AriaEvent -Domain runtime -Phase stale -State INFO -Energy observe -Information stale -Coherence bounded
        $event.previousDigest = 'b' * 64
        $event.digest = Get-AriaEventDigest $event
        $rejected = $false
        try { Publish-AriaEvent -Event $event } catch { $rejected = $true }
        Assert-True $rejected 'Stale append was accepted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'legacy event v1 remains individually verifiable' {
    $legacy = [pscustomobject][ordered]@{
        format='aria.event';version=1;sequence=1;domain='runtime';phase='legacy';state='INFO'
        energy='observe';information='legacy';coherence='bounded';source='aria.runtime'
        occurredAt='2026-01-01T00:00:00.0000000Z';data=$null;digest=''
    }
    $legacy.digest = Get-AriaEventDigest $legacy
    Assert-True (Test-AriaEvent $legacy).valid 'Legacy v1 event was rejected.'
}
Test-Case 'legacy event v2 projection remains verifiable' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $current = Send-ProbeEvent
    $legacy = [pscustomobject][ordered]@{
        format=$current.format;version=2;sequence=1;domain=$current.domain;phase=$current.phase;state=$current.state
        energy=$current.energy;information=$current.information;coherence=$current.coherence;source=$current.source
        occurredAt=$current.occurredAt;data=$current.data;projection=$current.projection;digest=''
    }
    $legacy.digest = Get-AriaEventDigest $legacy
    Assert-True (Test-AriaEvent $legacy).valid 'Legacy v2 event was rejected.'
}
Test-Case 'buffer exposes only pending while active' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    for ($index=0;$index-lt20;$index++) {
        Assert-Equal 'pending' (Get-AriaTransmissionPhase $state) 'Buffer invented a phase.'
        $null = Step-AriaTransmissionBuffer $state
    }
}
Test-Case 'buffer heartbeat freezes after closure' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    $null = Step-AriaTransmissionBuffer $state
    $state.active = $false
    $position = $state.position
    $heartbeats = $state.heartbeatCount
    $null = Step-AriaTransmissionBuffer $state
    Assert-Equal $position $state.position 'Closed buffer moved.'
    Assert-Equal $heartbeats $state.heartbeatCount 'Closed buffer counted a heartbeat.'
}
Test-Case 'buffer frame reports elapsed time without percentage' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    $frame = Get-AriaTransmissionFrame $state
    Assert-True ($frame -match 'elapsed:') 'Elapsed time is absent.'
    Assert-True ($frame -notmatch '%|mesh|transmit|align|verify') 'Frame contains false progress.'
}
Test-Case 'reduced motion disables live buffer but preserves state' {
    $prior = $env:ARIA_REDUCED_MOTION
    try {
        $env:ARIA_REDUCED_MOTION = '1'
        Assert-True (-not (Test-AriaInteractiveBuffer)) 'Reduced motion did not suppress live frames.'
        $state = New-AriaTransmissionBuffer -Label probe
        Assert-Equal 'pending' (Get-AriaTransmissionPhase $state) 'Static state lost pending semantics.'
    }
    finally { $env:ARIA_REDUCED_MOTION = $prior }
}
Test-Case 'receipt projects measured metrics without raw output' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $receipt = New-AriaTransmissionReceipt -Label probe -Mode verification -ExitCode 0 -StartedAt ([datetime]'2026-01-01T00:00:00Z') -CompletedAt ([datetime]'2026-01-01T00:00:00.042Z') -Stdout 'private output' -Stderr '' -HeartbeatCount 3
    Write-AriaTransmissionReceipt $receipt
    $event = @(Get-AriaEventBuffer)[0]
    Assert-Equal 42 $event.projection.metrics.durationMs 'Measured duration missing.'
    Assert-Equal 3 $event.projection.metrics.heartbeatCount 'Heartbeat metric missing.'
    Assert-True (($event | ConvertTo-Json -Depth 100) -notmatch 'private output') 'Raw output leaked into event.'
}
Test-Case 'failed receipt produces a fracture projection' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    $receipt = New-AriaTransmissionReceipt -Label probe -Mode runtime -ExitCode 1 -StartedAt ([datetime]'2026-01-01T00:00:00Z') -CompletedAt ([datetime]'2026-01-01T00:00:00.010Z')
    Write-AriaTransmissionReceipt $receipt
    $event = @(Get-AriaEventBuffer)[0]
    Assert-Equal 'invariant.fracture' $event.projection.cue.id 'Failed receipt did not fracture.'
}
Test-Case 'VM signals carry event and projection identities' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/hello.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        $signal = @($result.events | Where-Object { $_.kind -eq 'signal' })[0]
        Assert-True ([string]$signal.eventDigest -match '^[a-f0-9]{64}$') 'VM signal lacks event identity.'
        Assert-True ([string]$signal.projectionDigest -match '^sha256:[a-f0-9]{64}$') 'VM signal lacks projection identity.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'source-authored pass signal cannot manufacture a seal' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/hello.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        $passSignal = @($result.events | Where-Object { $_.kind -eq 'signal' -and $_.state -eq 'pass' })[0]
        Assert-Equal 'observation.info' $passSignal.cueId 'Source signal manufactured verification evidence.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'withheld consent becomes rejection evidence' {
    $workspace = New-TestWorkspace
    try {
        $sourcePath = Join-Path $workspace 'withheld.aria'
        Write-AriaUtf8NoBom -Path $sourcePath -Text @'
aria 0.4.0
program WithheldSignalIntegrity version 0.6.1
entry Main
agent Architect {
}
connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}
flow Main {
  connect HumanAI
  intent HumanAI <- "inspect"
  propose HumanAI <- "change"
  consent HumanAI <- false
  disconnect HumanAI
  halt
}
'@
        Initialize-AriaEventSpine -WorkspaceRoot $workspace | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath $sourcePath -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        $consent = @($result.events | Where-Object { $_.kind -eq 'connection' -and $_.state -eq 'consent' })[0]
        Assert-Equal 'invariant.fracture' $consent.cueId 'Withheld consent did not produce rejection evidence.'
        Assert-Equal $false $consent.approved 'Withheld consent became approval.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'connection lifecycle preserves semantic event order' {
    $workspace = New-TestWorkspace
    try {
        Initialize-AriaEventSpine -WorkspaceRoot $workspace | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/connection.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $null = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        $phases = @((Get-AriaEventBuffer) | Where-Object { $_.domain -eq 'connection' } | ForEach-Object { $_.phase })
        Assert-Equal 'open,intent,proposal,consent,closure' ($phases -join ',') 'Connection semantic order drifted.'
    }
    finally { Remove-TestWorkspace $workspace }
}
Test-Case 'static stage writing does not advance semantic event history' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    Write-AriaStage -Name static-layout -State Pulse
    Assert-Equal 0 @(Get-AriaEventBuffer).Count 'Static layout manufactured an event.'
}
Test-Case 'static signal writing does not advance semantic event history' {
    Initialize-AriaEventSpine -WorkspaceRoot $root | Out-Null
    Write-AriaSignal -Mode Observe -Name static-signal
    Assert-Equal 0 @(Get-AriaEventBuffer).Count 'Legacy static signal manufactured an event.'
}
Test-Case 'signal integrity closure remains authority-stable after reduce' {
    $registry = Read-AriaUtf8Text -Path (Join-Path $root 'grammar/glyph-cards.json') | ConvertFrom-Json
    foreach ($id in @('algorithm.map','algorithm.filter','algorithm.reduce')) {
        $card = @($registry.cards | Where-Object { $_.id -eq $id })[0]
        Assert-Equal 'verified' $card.status "Algorithm card '$id' was not admitted."
        Assert-Equal 0 @($card.capabilities).Count "Algorithm card '$id' introduced authority."
    }
}

Write-Host ''
Write-Host ("Signal Integrity Closure lattice: {0} passed, {1} failed" -f $script:passed,$script:failed)
if ($script:failed -gt 0) { exit 1 }
