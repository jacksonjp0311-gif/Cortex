[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$policyPath = Join-Path $root 'aria.policy.json'
$sourcePath = Join-Path $root 'examples/verified-reduce.aria'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aria-card-evidence-' + [guid]::NewGuid().ToString('N'))

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProjection.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SignalSubset.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GlyphMemory.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.ExecutionEvidence.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking

$script:Passed = 0
$script:Failed = 0
$script:Expected = 20

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Equal {
    param($Expected,$Actual,[string]$Message)
    $expectedJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=$Expected})
    $actualJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=$Actual})
    if ($expectedJson -ne $actualJson) {
        throw "$Message Expected=$expectedJson Actual=$actualJson"
    }
}
function Copy-JsonValue {
    param($Value)
    $Value | ConvertTo-Json -Depth 100 | ConvertFrom-Json
}
function Test-EvidenceCase {
    param([string]$Name,[scriptblock]$Body)
    try {
        & $Body
        $script:Passed++
        Write-Host ("◆  {0}" -f $Name) -ForegroundColor Green
    }
    catch {
        $script:Failed++
        Write-Host ("⬗  {0} · {1}" -f $Name,$_.Exception.Message) -ForegroundColor Magenta
    }
}
function Get-PropertyNamesRecursive {
    param($Value)
    $names = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Value -or $Value -is [string] -or $Value -is [ValueType]) {
        return $names.ToArray()
    }
    if ($Value -is [Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            $names.Add([string]$key)
            foreach ($child in @(Get-PropertyNamesRecursive $Value[$key])) { $names.Add($child) }
        }
        return $names.ToArray()
    }
    if ($Value -is [Collections.IEnumerable]) {
        foreach ($item in $Value) {
            foreach ($child in @(Get-PropertyNamesRecursive $item)) { $names.Add($child) }
        }
        return $names.ToArray()
    }
    foreach ($property in $Value.PSObject.Properties) {
        $names.Add([string]$property.Name)
        foreach ($child in @(Get-PropertyNamesRecursive $property.Value)) { $names.Add($child) }
    }
    $names.ToArray()
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $gate = Invoke-AriaGate -SourcePath $sourcePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    Initialize-AriaEventSpine -WorkspaceRoot $tempRoot -Persist | Out-Null
    $result = Invoke-AriaContainer -Container $container -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
    $receipts = @($result.executionEvidence)
    $registry = Read-AriaGlyphCardRegistry -Root $root

    Write-Host '⧉  card-execution-evidence lattice ×20' -ForegroundColor DarkGray

    Test-EvidenceCase 'execution evidence schema is machine readable' {
        $schema = Read-AriaUtf8Text (Join-Path $root 'schemas/card-execution-evidence.schema.json') | ConvertFrom-Json
        Assert-Equal 'ARIA per-card execution evidence' $schema.title 'Evidence schema title mismatch.'
        Assert-True ('digest' -in @($schema.required)) 'Evidence schema does not require its identity.'
    }
    Test-EvidenceCase 'map filter reduce each emit one receipt' {
        Assert-Equal 3 $receipts.Count 'Pipeline receipt count mismatch.'
        Assert-Equal @('algorithm.map','algorithm.filter','algorithm.reduce') @($receipts.card.id) 'Card receipt order mismatch.'
    }
    Test-EvidenceCase 'receipts bind exact verified cards and symbols' {
        foreach ($receipt in $receipts) {
            $card = Get-AriaGlyphCard -Id $receipt.card.id -Registry $registry
            Assert-Equal 'verified' $card.status 'Receipt referenced an unverified card.'
            Assert-Equal $card.digest $receipt.card.digest 'Card digest binding mismatch.'
            Assert-Equal $card.symbol $receipt.card.symbol 'Card symbol binding mismatch.'
        }
    }
    Test-EvidenceCase 'receipts bind source IR artifact and effect graph' {
        foreach ($receipt in $receipts) {
            Assert-Equal ('sha256:' + $gate.sourceHash) $receipt.program.sourceHash 'Source identity mismatch.'
            Assert-Equal ('sha256:' + $gate.irHash) $receipt.program.irHash 'IR identity mismatch.'
            Assert-Equal ('sha256:' + $gate.buildHash) $receipt.program.artifactHash 'Artifact identity mismatch.'
            Assert-Equal $gate.effectGraph.digest $receipt.program.effectGraphDigest 'Effect graph identity mismatch.'
        }
    }
    Test-EvidenceCase 'receipts bind policy and toolchain versions' {
        $policyDigest = 'sha256:' + (Get-AriaSha256File -Path $policyPath)
        foreach ($receipt in $receipts) {
            Assert-Equal $policyDigest $receipt.policyDigest 'Policy identity mismatch.'
            Assert-Equal (Get-AriaCompilerVersion) $receipt.toolchain.compilerVersion 'Compiler version mismatch.'
            Assert-Equal (Get-AriaRuntimeVersion) $receipt.toolchain.runtimeVersion 'Runtime version mismatch.'
        }
    }
    Test-EvidenceCase 'admission test receipt identity is independently derived' {
        foreach ($receipt in $receipts) {
            $card = Get-AriaGlyphCard -Id $receipt.card.id -Registry $registry
            $admission = Get-AriaCardAdmissionTestReceipt -Card $card
            Assert-Equal $admission.digest $receipt.admissionTestReceiptDigest 'Admission test identity mismatch.'
            Assert-True ([int]$admission.body.claimCount -gt 0) 'Admission receipt has no test claims.'
        }
    }
    Test-EvidenceCase 'aggregate counts describe actual completed operations' {
        Assert-Equal 4 $receipts[0].counts.inputCount 'Map input count mismatch.'
        Assert-Equal 4 $receipts[0].counts.outputCount 'Map output count mismatch.'
        Assert-Equal 2 $receipts[1].counts.selectedCount 'Filter selection count mismatch.'
        Assert-Equal 2 $receipts[2].counts.completedCount 'Reduce completion count mismatch.'
        Assert-Equal 1 $receipts[2].counts.outputCount 'Reduce output count mismatch.'
    }
    Test-EvidenceCase 'terminal event subset uses an exact allowlist' {
        $fields = @('digest','domain','operationId','operationSequence','phase','sequence','state')
        foreach ($receipt in $receipts) {
            Assert-Equal $fields @($receipt.signalSubset.fields) 'SignalSubset field allowlist mismatch.'
            Assert-Equal 1 $receipt.signalSubset.emittedCount 'SignalSubset emitted count mismatch.'
            Assert-True (Test-AriaSignalSubset $receipt.signalSubset).valid 'SignalSubset did not verify.'
        }
    }
    Test-EvidenceCase 'terminal subset explicitly excludes event payload and projection' {
        foreach ($receipt in $receipts) {
            Assert-True ('data' -in @($receipt.signalSubset.excludedFields)) 'Event data was not explicitly excluded.'
            Assert-True ('projection' -in @($receipt.signalSubset.excludedFields)) 'Projection was not explicitly excluded.'
            Assert-True ('information' -in @($receipt.signalSubset.excludedFields)) 'Information text was not explicitly excluded.'
        }
    }
    Test-EvidenceCase 'Event Spine seals one evidence event per receipt' {
        $events = @(Get-AriaEventBuffer | Where-Object { $_.domain -eq 'evidence' -and $_.phase -eq 'card.execution' })
        Assert-Equal 3 $events.Count 'Evidence event count mismatch.'
        Assert-Equal @($receipts.digest) @($events.data.receiptDigest) 'Evidence event receipt links mismatch.'
    }
    Test-EvidenceCase 'persistent Event Spine replays card evidence exactly' {
        $events = @(Read-AriaEventLedger -WorkspaceRoot $tempRoot | Where-Object { $_.domain -eq 'evidence' })
        Assert-Equal 3 $events.Count 'Persistent evidence replay count mismatch.'
        Assert-Equal @($receipts.digest) @($events.data.receiptDigest) 'Persistent evidence receipt links mismatch.'
    }
    Test-EvidenceCase 'receipt verification is deterministic over identical evidence' {
        foreach ($receipt in $receipts) {
            $clone = Copy-JsonValue $receipt
            # PowerShell 7 materializes ISO timestamps as DateTime while
            # Windows PowerShell 5.1 preserves strings.
            if ($clone.terminalEvent.occurredAt -isnot [datetime]) {
                $clone.terminalEvent.occurredAt = [datetime]::Parse(
                    [string]$clone.terminalEvent.occurredAt,
                    [Globalization.CultureInfo]::InvariantCulture,
                    [Globalization.DateTimeStyles]::RoundtripKind
                )
            }
            Assert-Equal $receipt.digest (Get-AriaCardExecutionEvidenceDigest $clone) 'Receipt digest changed across JSON round trip.'
            Assert-True (Test-AriaCardExecutionEvidence -Evidence $clone -Registry $registry).valid 'Round-tripped receipt failed.'
        }
    }
    Test-EvidenceCase 'tampered card identity is rejected' {
        $copy = Copy-JsonValue $receipts[0]
        $copy.card.digest = 'sha256:' + ('0' * 64)
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Tampered card digest verified.'
    }
    Test-EvidenceCase 'tampered artifact identity is rejected' {
        $copy = Copy-JsonValue $receipts[0]
        $copy.program.artifactHash = 'sha256:' + ('1' * 64)
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Tampered artifact identity verified.'
    }
    Test-EvidenceCase 'negative or invented aggregate counts are rejected' {
        $copy = Copy-JsonValue $receipts[0]
        $copy.counts.inputCount = -1
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Negative count verified.'
        $copy = Copy-JsonValue $receipts[0]
        $copy.counts | Add-Member -NotePropertyName rawValue -NotePropertyValue 4
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Non-aggregate count verified.'
    }
    Test-EvidenceCase 'tampered SignalSubset is rejected' {
        $copy = Copy-JsonValue $receipts[0]
        $copy.signalSubset.items[0].state = 'FAIL'
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Tampered SignalSubset verified.'
    }
    Test-EvidenceCase 'evidence cannot claim or carry authority' {
        $copy = Copy-JsonValue $receipts[0]
        $copy.authority.grantsAuthority = $true
        Assert-True (-not (Test-AriaCardExecutionEvidence $copy $registry).valid) 'Authority-bearing evidence verified.'
        foreach ($receipt in $receipts) {
            Assert-Equal 0 @($receipt.authority.capabilitiesGranted).Count 'Receipt granted a capability.'
        }
    }
    Test-EvidenceCase 'factory rejects outcome and terminal-state disagreement' {
        $terminal = @(Get-AriaEventBuffer | Where-Object phase -eq 'map.complete')[0]
        $card = Get-AriaGlyphCard -Id algorithm.map -Registry $registry
        $rejected = $false
        try {
            $null = New-AriaCardExecutionEvidence -Card $card -CompilerVersion (Get-AriaCompilerVersion) -SourceHash $gate.sourceHash -IrHash $gate.irHash -ArtifactHash $gate.buildHash -EffectGraphDigest $gate.effectGraph.digest -PolicyDigest (Get-AriaSha256File $policyPath) -TerminalEvent $terminal -Outcome fractured -OperationKind map -Target Double -Line 20 -Counts ([pscustomobject]@{inputCount=4})
        }
        catch { $rejected = $true }
        Assert-True $rejected 'Outcome and terminal-state disagreement was accepted.'
    }
    Test-EvidenceCase 'receipt property graph excludes runtime values and messages' {
        $forbidden = @('value','values','initial','accumulator','element','text','information','data','projection')
        foreach ($receipt in $receipts) {
            $names = @(Get-PropertyNamesRecursive (ConvertTo-AriaCardExecutionEvidenceBody $receipt))
            foreach ($name in $forbidden) {
                Assert-True ($name -notin $names) "Receipt exposed forbidden property '$name'."
            }
        }
    }
    Test-EvidenceCase 'observational receipts do not alter pipeline behavior' {
        Assert-Equal @('6') @($result.outputs) 'Pipeline output changed.'
        Assert-Equal 0 @($gate.bytecode.capabilities).Count 'Evidence introduced bytecode authority.'
        foreach ($receipt in $receipts) {
            Assert-Equal 'completed' $receipt.outcome 'Successful pipeline produced non-completion evidence.'
            Assert-True (Test-AriaCardExecutionEvidence $receipt $registry).valid 'Runtime returned invalid evidence.'
        }
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw "Card execution evidence test count diverged. Expected=$script:Expected Observed=$($script:Passed + $script:Failed)"
    }
    Write-Host ("⧉  card-execution-evidence lattice {0}/{1} · {2}" -f $script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'})) -ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
    if ($script:Failed -gt 0) { throw "Card execution evidence lattice failed: $script:Failed failure(s)." }
}
finally {
    if (Test-Path -LiteralPath $tempRoot -PathType Container) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
