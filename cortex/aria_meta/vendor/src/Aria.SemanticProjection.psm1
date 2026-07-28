Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -DisableNameChecking
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:AriaVerifiedSemanticCueRegistry = $null
$script:AriaVerifiedSemanticCueRegistryPath = ''

function Get-AriaSemanticCueRegistryPath {
    Join-Path (Get-AriaRepositoryRoot) 'grammar/semantic-cues.json'
}

function Get-AriaSemanticCueBody {
    param([Parameter(Mandatory=$true)]$Cue)
    [pscustomobject][ordered]@{
        id = [string]$Cue.id
        states = @($Cue.states)
        domains = @($Cue.domains)
        phases = @($Cue.phases)
        glyph = [string]$Cue.glyph
        label = [string]$Cue.label
        colorRole = [string]$Cue.colorRole
        motion = $Cue.motion
        rhythm = $Cue.rhythm
        meaning = [string]$Cue.meaning
        nonMeaning = [string]$Cue.nonMeaning
        staticFallback = [string]$Cue.staticFallback
        contexts = @($Cue.contexts)
        prohibitedInterpretations = @($Cue.prohibitedInterpretations)
    }
}

function Get-AriaSemanticCueDigest {
    param([Parameter(Mandatory=$true)]$Cue)
    'sha256:' + (Get-AriaSha256Text -Text (ConvertTo-AriaJson -Value (Get-AriaSemanticCueBody -Cue $Cue)))
}

function Get-AriaSemanticRegistryBody {
    param([Parameter(Mandatory=$true)]$Registry)
    [pscustomobject][ordered]@{
        format = [string]$Registry.format
        version = [int]$Registry.version
        cues = @($Registry.cues)
        engagementContract = $Registry.engagementContract
    }
}

function Get-AriaSemanticRegistryDigest {
    param([Parameter(Mandatory=$true)]$Registry)
    'sha256:' + (Get-AriaSha256Text -Text (ConvertTo-AriaJson -Value (Get-AriaSemanticRegistryBody -Registry $Registry)))
}

function Import-AriaSemanticCueRegistry {
    [CmdletBinding()]
    param([string]$Path = (Get-AriaSemanticCueRegistryPath))
    Read-AriaUtf8Text -Path $Path | ConvertFrom-Json
}

function Get-AriaVerifiedSemanticCueRegistry {
    [CmdletBinding()]
    param([string]$Path = (Get-AriaSemanticCueRegistryPath))

    $resolved = [IO.Path]::GetFullPath($Path)
    if (
        $null -ne $script:AriaVerifiedSemanticCueRegistry -and
        [string]::Equals(
            $resolved,
            $script:AriaVerifiedSemanticCueRegistryPath,
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        return $script:AriaVerifiedSemanticCueRegistry
    }

    $registry = Import-AriaSemanticCueRegistry -Path $resolved
    $verification = Test-AriaSemanticCueRegistry -Registry $registry
    if (-not $verification.valid) {
        throw ('Semantic cue registry rejected: ' + ($verification.errors -join '; '))
    }
    $script:AriaVerifiedSemanticCueRegistry = $registry
    $script:AriaVerifiedSemanticCueRegistryPath = $resolved
    return $registry
}

function Test-AriaSemanticCueRegistry {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Registry)

    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Registry.format -ne 'aria.semantic-cue-registry') { $errors.Add('format must be aria.semantic-cue-registry') }
    if ([int]$Registry.version -ne 1) { $errors.Add('version must be 1') }
    $ids = @{}
    foreach ($cue in @($Registry.cues)) {
        $id = [string]$cue.id
        if ($id -notmatch '^[a-z][a-z0-9.-]+$') { $errors.Add("cue id '$id' is invalid") }
        if ($ids.ContainsKey($id)) { $errors.Add("duplicate cue id '$id'") } else { $ids[$id] = $true }
        if (-not $cue.meaning) { $errors.Add("cue '$id' has no meaning") }
        if (-not $cue.nonMeaning) { $errors.Add("cue '$id' has no non-meaning boundary") }
        if (-not $cue.staticFallback) { $errors.Add("cue '$id' has no static fallback") }
        if ([bool]$cue.rhythm.falseProgress) { $errors.Add("cue '$id' permits false progress") }
        $expectedCue = Get-AriaSemanticCueDigest -Cue $cue
        if ([string]$cue.digest -ne $expectedCue) { $errors.Add("cue '$id' digest mismatch") }
    }
    $contract = $Registry.engagementContract
    if ([string]$contract.rewardPattern -ne 'none') { $errors.Add('variable reward patterns are prohibited') }
    foreach ($field in @('fakeUrgency','artificialScarcity','streakMechanics','surpriseReinforcement','unboundedLoops')) {
        if ([bool]$contract.$field) { $errors.Add("engagement contract enables prohibited '$field'") }
    }
    $expected = Get-AriaSemanticRegistryDigest -Registry $Registry
    if ([string]$Registry.digest -ne $expected) { $errors.Add('registry digest mismatch') }
    [pscustomobject][ordered]@{ valid = ($errors.Count -eq 0); errors = $errors.ToArray(); digest = $expected }
}

function Update-AriaSemanticCueRegistry {
    [CmdletBinding()]
    param([string]$Path = (Get-AriaSemanticCueRegistryPath))
    $registry = Import-AriaSemanticCueRegistry -Path $Path
    foreach ($cue in @($registry.cues)) { $cue.digest = Get-AriaSemanticCueDigest -Cue $cue }
    $registry.digest = Get-AriaSemanticRegistryDigest -Registry $registry
    Write-AriaUtf8NoBom -Path $Path -Text (($registry | ConvertTo-Json -Depth 100) + [Environment]::NewLine)
    $script:AriaVerifiedSemanticCueRegistry = $null
    $script:AriaVerifiedSemanticCueRegistryPath = ''
    $registry
}

function Resolve-AriaSemanticCue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Registry,
        [Parameter(Mandatory=$true)][string]$Domain,
        [Parameter(Mandatory=$true)][string]$Phase,
        [Parameter(Mandatory=$true)][string]$State
    )
    $domainValue = $Domain.ToLowerInvariant()
    $phaseValue = $Phase.ToLowerInvariant()
    $stateValue = $State.ToUpperInvariant()
    $candidates = @($Registry.cues | Where-Object {
        $stateValue -in @($_.states) -and
        ($domainValue -in @($_.domains) -or '*' -in @($_.domains)) -and
        ($phaseValue -in @($_.phases) -or '*' -in @($_.phases))
    })
    if ($candidates.Count -eq 0) { throw ("No semantic cue maps {0}.{1}:{2}." -f $domainValue,$phaseValue,$stateValue) }
    $ranked = @($candidates | Sort-Object `
        @{Expression={ if ('*' -in @($_.domains)) { 1 } else { 0 } }}, `
        @{Expression={ if ('*' -in @($_.phases)) { 1 } else { 0 } }}, `
        @{Expression={$_.id}})
    $ranked[0]
}

function ConvertTo-AriaBoundedSignalData {
    [CmdletBinding()]
    param(
        [AllowNull()]$Value,
        [int]$Depth = 0,
        [int]$MaxDepth = 4,
        [int]$MaxItems = 32,
        [int]$MaxTextLength = 512
    )
    if ($null -eq $Value) { return $null }
    if ($Depth -ge $MaxDepth) { return '[BOUNDED:DEPTH]' }
    if ($Value -is [string] -or $Value -is [char]) {
        $text = [string]$Value
        if ($text.Length -gt $MaxTextLength) { return $text.Substring(0,$MaxTextLength) + '…[BOUNDED]' }
        return $text
    }
    if ($Value -is [bool] -or $Value -is [byte] -or $Value -is [sbyte] -or
        $Value -is [int16] -or $Value -is [uint16] -or $Value -is [int32] -or
        $Value -is [uint32] -or $Value -is [int64] -or $Value -is [uint64] -or
        $Value -is [single] -or $Value -is [double] -or $Value -is [decimal]) { return $Value }
    if (($Value -is [System.Collections.IEnumerable]) -and -not ($Value -is [System.Collections.IDictionary]) -and -not ($Value -is [pscustomobject])) {
        $items = New-Object System.Collections.Generic.List[object]
        $index = 0
        foreach ($item in $Value) {
            if ($index -ge $MaxItems) { $items.Add('[BOUNDED:ITEMS]'); break }
            $items.Add((ConvertTo-AriaBoundedSignalData -Value $item -Depth ($Depth + 1) -MaxDepth $MaxDepth -MaxItems $MaxItems -MaxTextLength $MaxTextLength))
            $index++
        }
        return $items.ToArray()
    }
    $properties = New-Object System.Collections.Generic.List[object]
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) { $properties.Add([pscustomobject]@{Name=[string]$key;Value=$Value[$key]}) }
    }
    else {
        foreach ($property in $Value.PSObject.Properties) { $properties.Add([pscustomobject]@{Name=$property.Name;Value=$property.Value}) }
    }
    $result = [ordered]@{}
    $count = 0
    foreach ($property in $properties) {
        if ($count -ge $MaxItems) { $result['_bounded'] = 'property limit reached'; break }
        $name = [string]$property.Name
        if ($name -match '(?i)(secret|token|password|credential|private.?key|authorization|raw.?std(out|err)|payload)') {
            $result[$name] = '[REDACTED]'
        }
        else {
            $result[$name] = ConvertTo-AriaBoundedSignalData -Value $property.Value -Depth ($Depth + 1) -MaxDepth $MaxDepth -MaxItems $MaxItems -MaxTextLength $MaxTextLength
        }
        $count++
    }
    [pscustomobject]$result
}

function ConvertTo-AriaBoundedSignalText {
    [CmdletBinding()]
    param(
        [AllowEmptyString()][string]$Value,
        [string]$Role = 'signal',
        [int]$MaxTextLength = 512
    )
    if ($Value -match '(?i)(bearer\s+[a-z0-9._~+/-]+=*|github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9]+|sk-[a-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)') {
        return ('[REDACTED:{0}]' -f $Role.ToUpperInvariant())
    }
    if ($Value.Length -gt $MaxTextLength) { return $Value.Substring(0,$MaxTextLength) + '…[BOUNDED]' }
    $Value
}

function Get-AriaProjectionDigest {
    param([Parameter(Mandatory=$true)]$Projection)
    $body = [pscustomobject][ordered]@{}
    foreach ($property in $Projection.PSObject.Properties) {
        if ($property.Name -ne 'digest') { $body | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value }
    }
    'sha256:' + (Get-AriaSha256Text -Text (ConvertTo-AriaJson -Value $body))
}

function New-AriaSemanticProjection {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Event,
        [AllowEmptyString()][string]$PreviousStateIdentity = '',
        $Registry = $null
    )
    if ($null -eq $Registry) {
        $Registry = Get-AriaVerifiedSemanticCueRegistry
    }
    else {
        $verification = Test-AriaSemanticCueRegistry -Registry $Registry
        if (-not $verification.valid) { throw ('Semantic cue registry rejected: ' + ($verification.errors -join '; ')) }
    }
    $cue = Resolve-AriaSemanticCue -Registry $Registry -Domain $Event.domain -Phase $Event.phase -State $Event.state
    $stateIdentity = ('{0}.{1}:{2}' -f $Event.domain,$Event.phase,$Event.state)
    $metrics = [ordered]@{ sequence = [int]$Event.sequence }
    if ($Event.data) {
        foreach ($metricName in @('durationMs','queueDepth','iteration','iterations','obligationCount','verifiedCount','failedCount','bytes','totalBytes','stdoutBytes','stderrBytes','exitCode','heartbeatCount')) {
            $property = $Event.data.PSObject.Properties[$metricName]
            if ($property -and $property.Value -is [ValueType]) { $metrics[$metricName] = $property.Value }
        }
    }
    $timingMode = if ($metrics.Contains('durationMs')) { 'measured-latency' } else { 'event-boundary' }
    $transitionReason = if (-not $PreviousStateIdentity) { 'initial-observation' } elseif ($PreviousStateIdentity -ne $stateIdentity) { 'state-changed' } else { 'new-information-recorded' }
    $projection = [pscustomobject][ordered]@{
        format = 'aria.semantic-projection'
        version = 1
        sequence = [int]$Event.sequence
        stateIdentity = $stateIdentity
        phase = ('{0}.{1}' -f $Event.domain,$Event.phase)
        state = [string]$Event.state
        source = [string]$Event.source
        cue = [pscustomobject][ordered]@{ id=[string]$cue.id; digest=[string]$cue.digest }
        glyph = [pscustomobject][ordered]@{ symbol=[string]$cue.glyph; label=[string]$cue.label; colorRole=[string]$cue.colorRole }
        motion = $cue.motion
        rhythm = $cue.rhythm
        metrics = [pscustomobject]$metrics
        transition = [pscustomobject][ordered]@{
            from = $PreviousStateIdentity
            to = $stateIdentity
            changed = ($PreviousStateIdentity -ne $stateIdentity)
            reason = $transitionReason
            timing = $timingMode
        }
        record = [pscustomobject][ordered]@{
            energy = [string]$Event.energy
            information = [string]$Event.information
            coherence = [string]$Event.coherence
        }
        explanation = [pscustomobject][ordered]@{ meaning=[string]$cue.meaning; boundary=[string]$cue.nonMeaning }
        accessibility = [pscustomobject][ordered]@{
            static = [string]$cue.staticFallback
            reducedMotion = 'Use the same glyph, label, state, metrics, explanation, and cue identity without temporal frames.'
            colorIndependent = $true
        }
        engagement = $Registry.engagementContract
        digest = ''
    }
    $projection.digest = Get-AriaProjectionDigest -Projection $projection
    $projection
}

function Test-AriaSemanticProjection {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Projection)
    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Projection.format -ne 'aria.semantic-projection') { $errors.Add('format must be aria.semantic-projection') }
    if ([int]$Projection.version -ne 1) { $errors.Add('version must be 1') }
    if ([int]$Projection.sequence -lt 1) { $errors.Add('sequence must be positive') }
    if (-not $Projection.explanation.boundary) { $errors.Add('interpretation boundary is required') }
    if (-not $Projection.accessibility.static) { $errors.Add('static fallback is required') }
    if ([string]$Projection.transition.timing -eq 'measured-latency' -and -not $Projection.metrics.PSObject.Properties['durationMs']) {
        $errors.Add('measured latency requires durationMs evidence')
    }
    $expected = Get-AriaProjectionDigest -Projection $Projection
    if ([string]$Projection.digest -ne $expected) { $errors.Add('projection digest mismatch') }
    [pscustomobject][ordered]@{ valid=($errors.Count -eq 0); errors=$errors.ToArray(); digest=$expected }
}

Export-ModuleMember -Function Get-AriaSemanticCueRegistryPath,Get-AriaSemanticCueDigest,Get-AriaSemanticRegistryDigest,Import-AriaSemanticCueRegistry,Get-AriaVerifiedSemanticCueRegistry,Test-AriaSemanticCueRegistry,Update-AriaSemanticCueRegistry,Resolve-AriaSemanticCue,ConvertTo-AriaBoundedSignalData,ConvertTo-AriaBoundedSignalText,New-AriaSemanticProjection,Test-AriaSemanticProjection,Get-AriaProjectionDigest
