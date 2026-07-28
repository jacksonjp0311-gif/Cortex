Set-StrictMode -Version Latest

function Get-AriaEtherPalette {
    [ordered]@{
        Energy = "Yellow"
        Information = "Cyan"
        Coherence = "Magenta"
        Pass = "Green"
        Warn = "DarkYellow"
        Fail = "Red"
        Active = "Magenta"
        Meta = "Gray"
    }
}

function Get-AriaOperatorProfile {
    $interactive = $Host.Name -notmatch 'ServerRemoteHost'
    $width = 80
    if ($Host.UI -and $Host.UI.RawUI) {
        try { $width = [int]$Host.UI.RawUI.WindowSize.Width } catch {}
    }

    $ci = [string]::Equals($env:CI,'true',[System.StringComparison]::OrdinalIgnoreCase)
    if ($ci) { return 'ci' }
    if ($env:ARIA_PROFILE) { return $env:ARIA_PROFILE.ToLowerInvariant() }
    if ($width -le 90) { return 'compact' }
    if ($interactive) { return 'ether' }
    return 'operator'
}

function Format-AriaTriadicTransmission {
    param(
        [Parameter(Mandatory=$true)]$Event,
        [string]$Profile = (Get-AriaOperatorProfile)
    )

    $palette = Get-AriaEtherPalette
    $phase = if ($Event.phase) { [string]$Event.phase } else { "signal" }
    $name  = if ($Event.name) { [string]$Event.name } else { "event" }
    $state = if ($Event.state) { [string]$Event.state } else { "INFO" }
    $energy = if ($Event.energy) { [string]$Event.energy } else { $phase }
    $info = if ($Event.information) { [string]$Event.information } else { $name }
    $coherence = if ($Event.coherence) { [string]$Event.coherence } else { $state }

    $glyph = "◈"
    $cueId = ''
    $boundary = ''
    if ($Event.PSObject.Properties['projection'] -and $Event.projection) {
        $glyph = [string]$Event.projection.glyph.symbol
        $cueId = [string]$Event.projection.cue.id
        $boundary = [string]$Event.projection.explanation.boundary
    }
    else {
        if ($state -eq "PASS") { $glyph = "◆" }
        if ($state -eq "FAIL" -or $state -eq "REJECT") { $glyph = "⬗" }
        if ($state -eq "WARN") { $glyph = "⬖" }
    }

    if ($Profile -eq "ci" -or $Profile -eq "compact") {
        $suffix = if ($cueId) { " │ cue $cueId" } else { '' }
        return ("{0}  {1} │ 🜂 {2} │ ∿ {3} │ 🜄 {4}{5}" -f $glyph,$phase,$energy,$info,$coherence,$suffix)
    }

    return [PSCustomObject]@{
        Glyph = $glyph
        Phase = $phase
        Energy = $energy
        Information = $info
        Coherence = $coherence
        State = $state
        CueId = $cueId
        Boundary = $boundary
    }
}

function Write-AriaTriadicTransmission {
    param(
        [Parameter(Mandatory=$true)]$Event,
        [string]$Profile = (Get-AriaOperatorProfile)
    )

    $palette = Get-AriaEtherPalette
    if ($Event.PSObject.Properties['projection'] -and $Event.projection -and (Get-Command Invoke-AriaGlyphMotion -ErrorAction SilentlyContinue)) {
        $color = switch ([string]$Event.projection.glyph.colorRole) {
            'signal.pass' { 'Green' }
            'signal.warning' { 'Yellow' }
            'signal.failure' { 'Red' }
            'signal.information' { 'Cyan' }
            'signal.closure' { 'Green' }
            default { 'Magenta' }
        }
        $style = [pscustomobject][ordered]@{
            mode = [string]$Event.projection.cue.id
            glyph = [string]$Event.projection.glyph.symbol
            color = $color
            motion = [string]$Event.projection.motion.kind
        }
        Invoke-AriaGlyphMotion -Style $style
    }
    $formatted = Format-AriaTriadicTransmission -Event $Event -Profile $Profile

    if ($formatted -is [string]) {
        $color = $palette.Meta
        if ($Event.state -eq 'PASS') { $color = $palette.Pass }
        if ($Event.state -eq 'WARN') { $color = $palette.Warn }
        if ($Event.state -eq 'FAIL' -or $Event.state -eq 'REJECT') { $color = $palette.Fail }
        if ($Event.state -eq 'ACTIVE') { $color = $palette.Active }
        Write-Host $formatted -ForegroundColor $color
        return
    }

    $line = "{0}  {1,-16} │ " -f $formatted.Glyph, $formatted.Phase
    Write-Host -NoNewline $line -ForegroundColor White
    Write-Host -NoNewline ("🜂 {0,-18}" -f $formatted.Energy) -ForegroundColor $palette.Energy
    Write-Host -NoNewline " │ " -ForegroundColor DarkGray
    Write-Host -NoNewline ("∿ {0,-32}" -f $formatted.Information) -ForegroundColor $palette.Information
    Write-Host -NoNewline " │ " -ForegroundColor DarkGray
    $stateColor = $palette.Coherence
    if ($formatted.State -eq 'PASS') { $stateColor = $palette.Pass }
    if ($formatted.State -eq 'WARN') { $stateColor = $palette.Warn }
    if ($formatted.State -eq 'FAIL' -or $formatted.State -eq 'REJECT') { $stateColor = $palette.Fail }
    if ($formatted.State -eq 'ACTIVE') { $stateColor = $palette.Active }
    Write-Host ("🜄 {0}" -f $formatted.Coherence) -ForegroundColor $stateColor
    if ($formatted.CueId) {
        Write-Host ("   cue {0} · boundary: {1}" -f $formatted.CueId,$formatted.Boundary) -ForegroundColor DarkGray
    }
}

function Get-AriaTriadicEventsFromTransmission {
    param([Parameter(Mandatory=$true)]$Transmission)

    $body = $Transmission
    if ($Transmission.PSObject.Properties['body']) { $body = $Transmission.body }

    $provider = if ($body.provider) { [string]$body.provider } else { "provider" }
    $artifact = if ($body.artifact) { [string]$body.artifact } else { "artifact" }
    $digest = if ($body.digest) { [string]$body.digest } else { "digest" }
    $state = if ($body.state) { [string]$body.state } else { "PASS" }

    @(
        [PSCustomObject]@{
            phase = "transmission"
            name = "provider-envelope"
            state = "ACTIVE"
            energy = "handshake"
            information = $provider
            coherence = "membrane open"
        }
        [PSCustomObject]@{
            phase = "artifact"
            name = "compressed-body"
            state = $state
            energy = "compression"
            information = $artifact
            coherence = "payload sealed"
        }
        [PSCustomObject]@{
            phase = "provenance"
            name = "canonical-digest"
            state = "PASS"
            energy = "verification"
            information = $digest
            coherence = "integrity confirmed"
        }
    )
}

Export-ModuleMember -Function `
    Get-AriaEtherPalette, `
    Get-AriaOperatorProfile, `
    Format-AriaTriadicTransmission, `
    Write-AriaTriadicTransmission, `
    Get-AriaTriadicEventsFromTransmission
