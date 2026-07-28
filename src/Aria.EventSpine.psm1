Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'Aria.SemanticProjection.psm1') -DisableNameChecking

$script:AriaEventSequence = 0
$script:AriaEventBuffer = New-Object System.Collections.Generic.List[object]
$script:AriaEventSubscribers = New-Object System.Collections.Generic.List[scriptblock]
$script:AriaEventWorkspace = $null
$script:AriaEventProfile = 'compact'
$script:AriaEventPersist = $false
$script:AriaPreviousStateIdentity = ''
$script:AriaPreviousEventDigest = ''
$script:AriaOperationId = ''
$script:AriaOperationSequence = 0
$script:AriaEventLedgerHash = ''
$script:AriaEmptyLedgerHash = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
$script:AriaEventBatchDepth = 0
$script:AriaEventBatchChunkSize = 32
$script:AriaEventBatchRecords = New-Object System.Collections.Generic.List[object]

function New-AriaOperationIdentity {
    param([string]$Name = 'aria.operation')
    $seed = '{0}|{1}|{2}|{3}' -f $Name,[Diagnostics.Process]::GetCurrentProcess().Id,[datetime]::UtcNow.Ticks,[guid]::NewGuid().ToString('N')
    'aria.operation.sha256:' + (Get-AriaSha256Text -Text $seed)
}

function Initialize-AriaEventSpine {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [string]$Profile = 'compact',
        [string]$OperationId,
        [switch]$Persist
    )

    $script:AriaEventWorkspace = [IO.Path]::GetFullPath($WorkspaceRoot)
    $script:AriaEventProfile = $Profile
    $script:AriaEventPersist = [bool]$Persist
    $script:AriaEventSequence = 0
    $script:AriaPreviousStateIdentity = ''
    $script:AriaPreviousEventDigest = ''
    $script:AriaOperationId = if ($OperationId) { $OperationId } else { New-AriaOperationIdentity -Name 'aria.cli' }
    $script:AriaOperationSequence = 0
    $script:AriaEventLedgerHash = ''
    $script:AriaEventBatchDepth = 0
    $script:AriaEventBatchRecords.Clear()
    $script:AriaEventBuffer.Clear()
    $script:AriaEventSubscribers.Clear()

    if ($script:AriaEventPersist) {
        $folder = Join-Path $script:AriaEventWorkspace '.aria/events'
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        $existing = @(Read-AriaEventLedger -WorkspaceRoot $script:AriaEventWorkspace)
        if ($existing.Count -gt 0) {
            $script:AriaEventSequence = $existing.Count
            $script:AriaPreviousEventDigest = [string]$existing[$existing.Count - 1].digest
        }
        $ledger = Join-Path $folder 'aria.events.ndjson'
        if (Test-Path -LiteralPath $ledger -PathType Leaf) {
            $script:AriaEventLedgerHash = Get-AriaSha256File -Path $ledger
        }
        else {
            $script:AriaEventLedgerHash = $script:AriaEmptyLedgerHash
        }
    }

    [pscustomobject][ordered]@{
        format = 'aria.event-spine'
        version = 1
        workspace = $script:AriaEventWorkspace
        profile = $script:AriaEventProfile
        persistent = $script:AriaEventPersist
        operationId = $script:AriaOperationId
        nextLedgerSequence = ($script:AriaEventSequence + 1)
    }
}

function Start-AriaEventOperation {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Name,[string]$OperationId)
    $script:AriaOperationId = if ($OperationId) { $OperationId } else { New-AriaOperationIdentity -Name $Name }
    $script:AriaOperationSequence = 0
    $script:AriaPreviousStateIdentity = ''
    $script:AriaOperationId
}

function Get-AriaEventDigest {
    param([Parameter(Mandatory=$true)]$Event)

    $body = [pscustomobject][ordered]@{
        format = [string]$Event.format
        version = [int]$Event.version
        sequence = [int]$Event.sequence
        domain = [string]$Event.domain
        phase = [string]$Event.phase
        state = [string]$Event.state
        energy = [string]$Event.energy
        information = [string]$Event.information
        coherence = [string]$Event.coherence
        source = [string]$Event.source
        occurredAt = if ($Event.occurredAt -is [datetime]) {
            ([datetime]$Event.occurredAt).ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        }
        else {
            $rawOccurredAt = [string]$Event.occurredAt
            $parsedOccurredAt = [datetime]::MinValue
            if ([datetime]::TryParse(
                $rawOccurredAt,
                [Globalization.CultureInfo]::InvariantCulture,
                [Globalization.DateTimeStyles]::RoundtripKind,
                [ref]$parsedOccurredAt
            )) {
                $parsedOccurredAt.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
            }
            else {
                $rawOccurredAt
            }
        }
        data = $Event.data
    }
    if ([int]$Event.version -ge 3) {
        $body | Add-Member -NotePropertyName operationId -NotePropertyValue ([string]$Event.operationId)
        $body | Add-Member -NotePropertyName operationSequence -NotePropertyValue ([int]$Event.operationSequence)
        $body | Add-Member -NotePropertyName previousDigest -NotePropertyValue ([string]$Event.previousDigest)
    }
    if ([int]$Event.version -ge 2) {
        $body | Add-Member -NotePropertyName projection -NotePropertyValue $Event.projection
    }
    $json = ConvertTo-AriaJson -Value $body
    Get-AriaSha256Bytes -Bytes ([Text.Encoding]::UTF8.GetBytes($json))
}

function New-AriaEvent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9._-]*$')][string]$Domain,
        [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9._-]*$')][string]$Phase,
        [ValidateSet('ACTIVE','PASS','REJECT','WARN','FAIL','INFO')][string]$State = 'INFO',
        [Parameter(Mandatory=$true)][string]$Energy,
        [Parameter(Mandatory=$true)][string]$Information,
        [Parameter(Mandatory=$true)][string]$Coherence,
        [string]$Source = 'aria.runtime',
        $Data = $null,
        [datetime]$OccurredAt = ([datetime]::UtcNow)
    )

    if (-not $script:AriaOperationId) {
        $script:AriaOperationId = New-AriaOperationIdentity -Name 'aria.runtime'
        $script:AriaOperationSequence = 0
        $script:AriaPreviousStateIdentity = ''
    }
    $script:AriaEventSequence++
    $script:AriaOperationSequence++
    $event = [pscustomobject][ordered]@{
        format = 'aria.event'
        version = 3
        sequence = $script:AriaEventSequence
        operationId = $script:AriaOperationId
        operationSequence = $script:AriaOperationSequence
        previousDigest = $script:AriaPreviousEventDigest
        domain = $Domain.ToLowerInvariant()
        phase = $Phase.ToLowerInvariant()
        state = $State.ToUpperInvariant()
        energy = ConvertTo-AriaBoundedSignalText -Value $Energy -Role energy
        information = ConvertTo-AriaBoundedSignalText -Value $Information -Role information
        coherence = ConvertTo-AriaBoundedSignalText -Value $Coherence -Role coherence
        source = ConvertTo-AriaBoundedSignalText -Value $Source -Role source
        occurredAt = $OccurredAt.ToUniversalTime().ToString('o')
        data = ConvertTo-AriaBoundedSignalData -Value $Data
        projection = $null
        digest = ''
    }
    $event.projection = New-AriaSemanticProjection -Event $event -PreviousStateIdentity $script:AriaPreviousStateIdentity
    $script:AriaPreviousStateIdentity = [string]$event.projection.stateIdentity
    $event.digest = Get-AriaEventDigest -Event $event
    $script:AriaPreviousEventDigest = [string]$event.digest
    $event
}

function Test-AriaEvent {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Event)

    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Event.format -ne 'aria.event') { $errors.Add('format must be aria.event') }
    if ([int]$Event.version -notin @(1,2,3)) { $errors.Add('version must be 1, 2, or 3') }
    if ([int]$Event.sequence -lt 1) { $errors.Add('sequence must be positive') }
    if ([string]$Event.domain -notmatch '^[a-z][a-z0-9._-]*$') { $errors.Add('domain is invalid') }
    if ([string]$Event.phase -notmatch '^[a-z][a-z0-9._-]*$') { $errors.Add('phase is invalid') }
    if ([string]$Event.state -notin @('ACTIVE','PASS','REJECT','WARN','FAIL','INFO')) { $errors.Add('state is invalid') }
    if ([int]$Event.version -ge 3) {
        if ([string]$Event.operationId -notmatch '^aria\.operation\.[a-z0-9._-]+:[a-f0-9]{64}$') { $errors.Add('operation identity is invalid') }
        if ([int]$Event.operationSequence -lt 1) { $errors.Add('operation sequence must be positive') }
        if ([string]$Event.previousDigest -and [string]$Event.previousDigest -notmatch '^[a-f0-9]{64}$') { $errors.Add('previous digest is invalid') }
    }
    if ([int]$Event.version -ge 2 -and -not $Event.PSObject.Properties['projection']) {
        $errors.Add('semantic projection is required')
    }
    elseif ([int]$Event.version -ge 2) {
        $projectionVerification = Test-AriaSemanticProjection -Projection $Event.projection
        if (-not $projectionVerification.valid) { $errors.Add('semantic projection rejected: ' + ($projectionVerification.errors -join ', ')) }
        if ([int]$Event.projection.sequence -ne [int]$Event.sequence) { $errors.Add('projection sequence mismatch') }
        if ([string]$Event.projection.state -ne [string]$Event.state) { $errors.Add('projection state mismatch') }
    }

    $expected = ''
    try { $expected = Get-AriaEventDigest -Event $Event }
    catch { $errors.Add($_.Exception.Message) }
    if ($expected -and [string]$Event.digest -ne $expected) { $errors.Add('digest mismatch') }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors)
        digest = $expected
    }
}

function Register-AriaEventSubscriber {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][scriptblock]$Handler)
    $script:AriaEventSubscribers.Add($Handler)
    $script:AriaEventSubscribers.Count
}

function ConvertTo-AriaEtherEvent {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Event)

    [pscustomobject][ordered]@{
        phase = ("{0}.{1}" -f $Event.domain,$Event.phase)
        name = $Event.source
        state = $Event.state
        energy = $Event.energy
        information = $Event.information
        coherence = $Event.coherence
        projection = if ($Event.PSObject.Properties['projection']) { $Event.projection } else { $null }
    }
}

function Assert-AriaEventLedgerContinuity {
    param(
        [Parameter(Mandatory=$true)]$Event,
        [Parameter(Mandatory=$true)][int]$LineNumber,
        [AllowEmptyString()][string]$PriorDigest,
        [Parameter(Mandatory=$true)][hashtable]$OperationSequences
    )

    if ([int]$Event.version -lt 3) { return }
    if ([int]$Event.sequence -ne $LineNumber) {
        throw "ARIA event ledger sequence fracture at line $LineNumber."
    }
    if ([string]$Event.previousDigest -ne $PriorDigest) {
        throw "ARIA event ledger digest-chain fracture at line $LineNumber."
    }

    $operationId = [string]$Event.operationId
    $expectedOperationSequence = if ($OperationSequences.ContainsKey($operationId)) {
        [int]$OperationSequences[$operationId] + 1
    }
    else {
        1
    }
    if ([int]$Event.operationSequence -ne $expectedOperationSequence) {
        throw "ARIA event ledger operation-sequence fracture at line $LineNumber."
    }
    $OperationSequences[$operationId] = $expectedOperationSequence
}

function Add-AriaEventLedgerRecords {
    param(
        [Parameter(Mandatory=$true)][string]$LedgerPath,
        [Parameter(Mandatory=$true)][object[]]$Events
    )
    if ($Events.Count -eq 0) { return }

    $stream = [IO.FileStream]::new(
        $LedgerPath,
        [IO.FileMode]::OpenOrCreate,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
    try {
        $existingText = ''
        [byte[]]$existingBytes = @()
        if ($stream.Length -gt 0) {
            $existingBytes = New-Object byte[] ([int]$stream.Length)
            $stream.Position = 0
            $read = $stream.Read($existingBytes,0,$existingBytes.Length)
            if ($read -ne $existingBytes.Length) { throw 'ARIA event ledger could not be read completely under lock.' }
            $existingText = [Text.Encoding]::UTF8.GetString($existingBytes)
        }

        $existingHash = if ($existingBytes.Length -eq 0) {
            $script:AriaEmptyLedgerHash
        }
        else {
            Get-AriaSha256Bytes -Bytes $existingBytes
        }
        if ($script:AriaEventLedgerHash -and $existingHash -ne $script:AriaEventLedgerHash) {
            throw 'ARIA event append rejected changed ledger bytes after initialization.'
        }

        $lines = @($existingText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        $expectedSequence = $lines.Count + 1
        $priorDigest = ''
        if ($lines.Count -gt 0) {
            $tail = $lines[$lines.Count - 1] | ConvertFrom-Json
            $tailVerification = Test-AriaEvent -Event $tail
            if (-not $tailVerification.valid) { throw ('ARIA event ledger tail rejected under append lock: ' + ($tailVerification.errors -join '; ')) }
            $priorDigest = [string]$tail.digest
        }

        $records = New-Object Text.StringBuilder
        foreach ($event in $Events) {
            if ([int]$event.sequence -ne $expectedSequence) {
                throw "ARIA event append expected ledger sequence $expectedSequence, received $($event.sequence)."
            }
            if ([string]$event.previousDigest -ne $priorDigest) {
                throw 'ARIA event append rejected a stale previous digest.'
            }
            [void]$records.Append(($event | ConvertTo-Json -Depth 100 -Compress))
            [void]$records.Append([Environment]::NewLine)
            $priorDigest = [string]$event.digest
            $expectedSequence++
        }

        [byte[]]$recordBytes = [Text.UTF8Encoding]::new($false).GetBytes($records.ToString())
        $stream.Position = $stream.Length
        $stream.Write($recordBytes,0,$recordBytes.Length)
        $stream.Flush()
        [byte[]]$sealedBytes = New-Object byte[] ($existingBytes.Length + $recordBytes.Length)
        if ($existingBytes.Length -gt 0) { [Array]::Copy($existingBytes,0,$sealedBytes,0,$existingBytes.Length) }
        [Array]::Copy($recordBytes,0,$sealedBytes,$existingBytes.Length,$recordBytes.Length)
        $script:AriaEventLedgerHash = Get-AriaSha256Bytes -Bytes $sealedBytes
    }
    finally {
        $stream.Dispose()
    }
}

function Add-AriaEventLedgerRecord {
    param(
        [Parameter(Mandatory=$true)][string]$LedgerPath,
        [Parameter(Mandatory=$true)]$Event
    )
    Add-AriaEventLedgerRecords -LedgerPath $LedgerPath -Events @($Event)
}

function Flush-AriaEventBatch {
    if (
        -not $script:AriaEventPersist -or
        -not $script:AriaEventWorkspace -or
        $script:AriaEventBatchRecords.Count -eq 0
    ) {
        $script:AriaEventBatchRecords.Clear()
        return
    }
    $folder = Join-Path $script:AriaEventWorkspace '.aria/events'
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $ledger = Join-Path $folder 'aria.events.ndjson'
    $records = @($script:AriaEventBatchRecords.ToArray())
    Add-AriaEventLedgerRecords -LedgerPath $ledger -Events $records
    $script:AriaEventBatchRecords.Clear()
}

function Start-AriaEventBatch {
    [CmdletBinding()]
    param([ValidateRange(1,256)][int]$ChunkSize = 32)
    if ($script:AriaEventBatchDepth -eq 0) {
        $script:AriaEventBatchRecords.Clear()
        $script:AriaEventBatchChunkSize = $ChunkSize
    }
    $script:AriaEventBatchDepth++
}

function Complete-AriaEventBatch {
    [CmdletBinding()]
    param()
    if ($script:AriaEventBatchDepth -gt 0) {
        $script:AriaEventBatchDepth--
    }
    if ($script:AriaEventBatchDepth -eq 0) {
        Flush-AriaEventBatch
    }
}

function Publish-AriaConstructedEvent {
    param(
        [Parameter(Mandatory=$true)]$Event,
        [switch]$Render,
        [switch]$Replay,
        [switch]$PassThru
    )

    if (-not $Replay) {
        $script:AriaEventBuffer.Add($Event)

        if ($script:AriaEventPersist -and $script:AriaEventWorkspace) {
            if ($script:AriaEventBatchDepth -gt 0) {
                $script:AriaEventBatchRecords.Add($Event)
                if ($script:AriaEventBatchRecords.Count -ge $script:AriaEventBatchChunkSize) {
                    Flush-AriaEventBatch
                }
            }
            else {
                $folder = Join-Path $script:AriaEventWorkspace '.aria/events'
                New-Item -ItemType Directory -Path $folder -Force | Out-Null
                $ledger = Join-Path $folder 'aria.events.ndjson'
                Add-AriaEventLedgerRecord -LedgerPath $ledger -Event $Event
            }
        }

        foreach ($subscriber in $script:AriaEventSubscribers.ToArray()) {
            & $subscriber $Event
        }
    }

    if ($Render) {
        $ether = ConvertTo-AriaEtherEvent -Event $Event
        Write-AriaTriadicTransmission -Event $ether -Profile $script:AriaEventProfile
    }

    if ($PassThru) { $Event }
}

function Publish-AriaEvent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Event,
        [switch]$Render,
        [switch]$Replay,
        [switch]$PassThru
    )

    $verification = Test-AriaEvent -Event $Event
    if (-not $verification.valid) { throw ('ARIA event rejected: ' + ($verification.errors -join '; ')) }
    Publish-AriaConstructedEvent -Event $Event -Render:$Render -Replay:$Replay -PassThru:$PassThru
}

function Send-AriaEvent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Domain,
        [Parameter(Mandatory=$true)][string]$Phase,
        [ValidateSet('ACTIVE','PASS','REJECT','WARN','FAIL','INFO')][string]$State = 'INFO',
        [Parameter(Mandatory=$true)][string]$Energy,
        [Parameter(Mandatory=$true)][string]$Information,
        [Parameter(Mandatory=$true)][string]$Coherence,
        [string]$Source = 'aria.runtime',
        $Data = $null,
        [switch]$Render,
        [switch]$PassThru
    )

    $event = New-AriaEvent -Domain $Domain -Phase $Phase -State $State -Energy $Energy -Information $Information -Coherence $Coherence -Source $Source -Data $Data
    # New-AriaEvent constructs and seals this exact object. Public callers that
    # provide an event still cross the full Test-AriaEvent boundary through
    # Publish-AriaEvent; the internal send path avoids hashing the same freshly
    # constructed projection and event a second time.
    Publish-AriaConstructedEvent -Event $event -Render:$Render -PassThru:$PassThru
}

function Get-AriaEventBuffer {
    [CmdletBinding()]
    param()
    $script:AriaEventBuffer.ToArray()
}

function Read-AriaEventLedger {
    [CmdletBinding()]
    param([string]$WorkspaceRoot = $script:AriaEventWorkspace)

    if (-not $WorkspaceRoot) { return @() }
    $ledger = Join-Path ([IO.Path]::GetFullPath($WorkspaceRoot)) '.aria/events/aria.events.ndjson'
    if (-not (Test-Path -LiteralPath $ledger -PathType Leaf)) { return @() }

    $events = New-Object System.Collections.Generic.List[object]
    $priorDigest = ''
    $lineNumber = 0
    $operationSequences = @{}
    foreach ($line in Get-Content -LiteralPath $ledger -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $lineNumber++
        $event = $line | ConvertFrom-Json
        $verification = Test-AriaEvent -Event $event
        if (-not $verification.valid) { throw ('ARIA event ledger rejected at line {0}: {1}' -f $lineNumber,($verification.errors -join '; ')) }
        Assert-AriaEventLedgerContinuity -Event $event -LineNumber $lineNumber -PriorDigest $priorDigest -OperationSequences $operationSequences
        $events.Add($event)
        $priorDigest = [string]$event.digest
    }
    $events.ToArray()
}

Export-ModuleMember -Function New-AriaOperationIdentity,Initialize-AriaEventSpine,Start-AriaEventOperation,Start-AriaEventBatch,Complete-AriaEventBatch,Get-AriaEventDigest,New-AriaEvent,Test-AriaEvent,Register-AriaEventSubscriber,ConvertTo-AriaEtherEvent,Publish-AriaEvent,Send-AriaEvent,Get-AriaEventBuffer,Read-AriaEventLedger
