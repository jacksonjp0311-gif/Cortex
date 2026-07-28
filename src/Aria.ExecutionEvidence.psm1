Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSha256Text -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command New-AriaSignalSubset -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.SignalSubset.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command Test-AriaGlyphCard -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.GlyphMemory.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command Test-AriaEvent -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.EventSpine.psm1') -Force -DisableNameChecking
}

function Get-AriaExecutionEvidenceProperty {
    param($Object,[string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object -is [Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    $null
}

function ConvertTo-AriaEvidenceIdentity {
    param([AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    if ($Value -match '^sha256:[a-f0-9]{64}$') { return $Value }
    if ($Value -match '^[a-f0-9]{64}$') { return ('sha256:' + $Value) }
    throw "ARIA execution evidence requires a SHA-256 identity; received '$Value'."
}

function Get-AriaRuntimeVersion {
    '0.1.0-alpha.14'
}

function ConvertTo-AriaExecutionCounts {
    param($Counts)
    $body = [ordered]@{}
    $names = @(
        if ($Counts -is [Collections.IDictionary]) {
            $Counts.Keys | ForEach-Object { [string]$_ }
        }
        elseif ($null -ne $Counts) {
            $Counts.PSObject.Properties | ForEach-Object { [string]$_.Name }
        }
    ) | Sort-Object -Unique
    foreach ($name in $names) {
        if ($name -notmatch '^[a-z][A-Za-z0-9]*Count$') {
            throw "ARIA execution evidence count '$name' is not a bounded aggregate count."
        }
        $value = Get-AriaExecutionEvidenceProperty $Counts $name
        if ($value -isnot [byte] -and $value -isnot [int16] -and
            $value -isnot [int32] -and $value -isnot [int64]) {
            throw "ARIA execution evidence count '$name' is not an integer."
        }
        if ([int64]$value -lt 0 -or [int64]$value -gt 1048576) {
            throw "ARIA execution evidence count '$name' is outside its bound."
        }
        $body[$name] = [int64]$value
    }
    [pscustomobject]$body
}

function Get-AriaCardAdmissionTestReceipt {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Card)
    $claims = @(@($Card.tests) | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    $body = [pscustomobject][ordered]@{
        format = 'aria.card-admission-test-receipt'
        version = 1
        cardId = [string]$Card.id
        cardDigest = [string]$Card.digest
        lifecycleState = [string]$Card.status
        claims = $claims
        claimCount = $claims.Count
    }
    [pscustomobject][ordered]@{
        body = $body
        digest = ('sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $body)))
    }
}

function ConvertTo-AriaCardExecutionEvidenceBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Evidence)
    [pscustomobject][ordered]@{
        format = [string]$Evidence.format
        version = [int]$Evidence.version
        card = $Evidence.card
        toolchain = $Evidence.toolchain
        program = $Evidence.program
        policyDigest = [string]$Evidence.policyDigest
        admissionTestReceiptDigest = [string]$Evidence.admissionTestReceiptDigest
        operation = $Evidence.operation
        outcome = [string]$Evidence.outcome
        counts = $Evidence.counts
        terminalEvent = [pscustomobject][ordered]@{
            operationId = [string]$Evidence.terminalEvent.operationId
            sequence = [int]$Evidence.terminalEvent.sequence
            operationSequence = [int]$Evidence.terminalEvent.operationSequence
            occurredAt = if ($Evidence.terminalEvent.occurredAt -is [datetime]) {
                ([datetime]$Evidence.terminalEvent.occurredAt).
                    ToUniversalTime().
                    ToString('o',[Globalization.CultureInfo]::InvariantCulture)
            }
            else {
                [string]$Evidence.terminalEvent.occurredAt
            }
            state = [string]$Evidence.terminalEvent.state
            digest = [string]$Evidence.terminalEvent.digest
        }
        signalSubset = $Evidence.signalSubset
        authority = $Evidence.authority
    }
}

function Get-AriaCardExecutionEvidenceDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Evidence)
    'sha256:' + (
        Get-AriaSha256Text (
            ConvertTo-AriaJson (
                ConvertTo-AriaCardExecutionEvidenceBody -Evidence $Evidence
            )
        )
    )
}

function New-AriaCardExecutionEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Card,
        [Parameter(Mandatory=$true)][string]$CompilerVersion,
        [Parameter(Mandatory=$true)][string]$SourceHash,
        [Parameter(Mandatory=$true)][string]$IrHash,
        [Parameter(Mandatory=$true)][string]$ArtifactHash,
        [Parameter(Mandatory=$true)][string]$EffectGraphDigest,
        [Parameter(Mandatory=$true)][string]$PolicyDigest,
        [Parameter(Mandatory=$true)]$TerminalEvent,
        [Parameter(Mandatory=$true)]
        [ValidateSet('completed','fractured')][string]$Outcome,
        [Parameter(Mandatory=$true)]
        [ValidateSet('map','filter','reduce')][string]$OperationKind,
        [Parameter(Mandatory=$true)][string]$Target,
        [ValidateRange(0,2147483647)][int]$Line,
        $Counts = $null
    )
    $cardValidation = Test-AriaGlyphCard -Card $Card
    if (-not [bool]$cardValidation.valid) {
        throw ('ARIA execution evidence rejected its card: ' + (@($cardValidation.errors) -join ', '))
    }
    if ([string]$Card.status -ne 'verified') {
        throw "ARIA execution evidence cannot exercise unverified card '$($Card.id)'."
    }
    $eventValidation = Test-AriaEvent -Event $TerminalEvent
    if (-not [bool]$eventValidation.valid) {
        throw ('ARIA execution evidence rejected its terminal event: ' + (@($eventValidation.errors) -join ', '))
    }
    $expectedState = if ($Outcome -eq 'completed') { 'PASS' } else { 'FAIL' }
    if ([string]$TerminalEvent.state -ne $expectedState) {
        throw "ARIA execution evidence outcome '$Outcome' does not match terminal event state '$($TerminalEvent.state)'."
    }
    $expectedCard = 'algorithm.' + $OperationKind
    if ([string]$Card.id -ne $expectedCard) {
        throw "ARIA execution evidence operation '$OperationKind' does not match card '$($Card.id)'."
    }

    $subset = New-AriaSignalSubset `
        -Items @($TerminalEvent) `
        -Fields @('sequence','operationId','operationSequence','domain','phase','state','digest') `
        -Purpose 'card-execution-terminal-event' `
        -Source 'aria.event-spine' `
        -ConsentBasis 'local-runtime-observation' `
        -ConsentScope 'bounded-terminal-event-identity' `
        -Limit 1 `
        -Retention session
    $testReceipt = Get-AriaCardAdmissionTestReceipt -Card $Card
    $evidence = [pscustomobject][ordered]@{
        format = 'aria.card-execution-evidence'
        version = 1
        card = [pscustomobject][ordered]@{
            id = [string]$Card.id
            digest = [string]$Card.digest
            symbol = [string]$Card.symbol
        }
        toolchain = [pscustomobject][ordered]@{
            compilerVersion = $CompilerVersion
            runtimeVersion = Get-AriaRuntimeVersion
        }
        program = [pscustomobject][ordered]@{
            sourceHash = ConvertTo-AriaEvidenceIdentity $SourceHash
            irHash = ConvertTo-AriaEvidenceIdentity $IrHash
            artifactHash = ConvertTo-AriaEvidenceIdentity $ArtifactHash
            effectGraphDigest = ConvertTo-AriaEvidenceIdentity $EffectGraphDigest
        }
        policyDigest = ConvertTo-AriaEvidenceIdentity $PolicyDigest
        admissionTestReceiptDigest = [string]$testReceipt.digest
        operation = [pscustomobject][ordered]@{
            kind = $OperationKind
            target = $Target
            line = $Line
        }
        outcome = $Outcome
        counts = ConvertTo-AriaExecutionCounts $Counts
        terminalEvent = [pscustomobject][ordered]@{
            operationId = [string]$TerminalEvent.operationId
            sequence = [int]$TerminalEvent.sequence
            operationSequence = [int]$TerminalEvent.operationSequence
            occurredAt = [string]$TerminalEvent.occurredAt
            state = [string]$TerminalEvent.state
            digest = ConvertTo-AriaEvidenceIdentity ([string]$TerminalEvent.digest)
        }
        signalSubset = $subset
        authority = [pscustomobject][ordered]@{
            class = 'observational'
            grantsAuthority = $false
            capabilitiesGranted = @()
        }
        digest = ''
    }
    $evidence.digest = Get-AriaCardExecutionEvidenceDigest -Evidence $evidence
    $evidence
}

function Test-AriaCardExecutionEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Evidence,
        $Registry
    )
    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Evidence.format -ne 'aria.card-execution-evidence') { $errors.Add('E_CARD_EVIDENCE_FORMAT') }
    if ([int]$Evidence.version -ne 1) { $errors.Add('E_CARD_EVIDENCE_VERSION') }
    if ([string]$Evidence.card.id -notmatch '^algorithm\.(map|filter|reduce)$') { $errors.Add('E_CARD_EVIDENCE_CARD') }
    if ([string]$Evidence.card.digest -notmatch '^sha256:[a-f0-9]{64}$') { $errors.Add('E_CARD_EVIDENCE_CARD_DIGEST') }
    if ([string]$Evidence.outcome -notin @('completed','fractured')) { $errors.Add('E_CARD_EVIDENCE_OUTCOME') }
    foreach ($identity in @(
        [string]$Evidence.program.sourceHash,
        [string]$Evidence.program.irHash,
        [string]$Evidence.program.artifactHash,
        [string]$Evidence.program.effectGraphDigest,
        [string]$Evidence.policyDigest,
        [string]$Evidence.admissionTestReceiptDigest,
        [string]$Evidence.terminalEvent.digest
    )) {
        if ($identity -notmatch '^sha256:[a-f0-9]{64}$') { $errors.Add('E_CARD_EVIDENCE_IDENTITY') }
    }
    if ([string]$Evidence.authority.class -ne 'observational' -or
        [bool]$Evidence.authority.grantsAuthority -or
        @($Evidence.authority.capabilitiesGranted).Count -ne 0) {
        $errors.Add('E_CARD_EVIDENCE_AUTHORITY')
    }
    try {
        $null = ConvertTo-AriaExecutionCounts $Evidence.counts
    }
    catch { $errors.Add('E_CARD_EVIDENCE_COUNTS') }
    $subsetValidation = Test-AriaSignalSubset -Subset $Evidence.signalSubset
    if (-not [bool]$subsetValidation.valid) { $errors.Add('E_CARD_EVIDENCE_SUBSET') }

    try {
        if ($null -eq $Registry) { $Registry = Read-AriaGlyphCardRegistry }
        $card = Get-AriaGlyphCard -Id ([string]$Evidence.card.id) -Registry $Registry
        if ([string]$card.status -ne 'verified' -or
            [string]$card.digest -ne [string]$Evidence.card.digest -or
            [string]$card.symbol -ne [string]$Evidence.card.symbol) {
            $errors.Add('E_CARD_EVIDENCE_CARD_BINDING')
        }
        $testReceipt = Get-AriaCardAdmissionTestReceipt -Card $card
        if ([string]$testReceipt.digest -ne [string]$Evidence.admissionTestReceiptDigest) {
            $errors.Add('E_CARD_EVIDENCE_TEST_RECEIPT')
        }
    }
    catch { $errors.Add('E_CARD_EVIDENCE_CARD_LOOKUP') }

    $expected = ''
    try { $expected = Get-AriaCardExecutionEvidenceDigest -Evidence $Evidence }
    catch { $errors.Add('E_CARD_EVIDENCE_DIGEST_CALCULATION') }
    if ($expected -and [string]$Evidence.digest -ne $expected) { $errors.Add('E_CARD_EVIDENCE_DIGEST') }
    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
        digest = $expected
    }
}

Export-ModuleMember -Function `
    Get-AriaRuntimeVersion, `
    Get-AriaCardAdmissionTestReceipt, `
    ConvertTo-AriaCardExecutionEvidenceBody, `
    Get-AriaCardExecutionEvidenceDigest, `
    New-AriaCardExecutionEvidence, `
    Test-AriaCardExecutionEvidence
