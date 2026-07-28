Import-Module (Join-Path $PSScriptRoot 'Aria.Etherflow.psm1') -Force -DisableNameChecking
Set-StrictMode -Version 2.0

$script:Esc = [char]27
$script:SupportsAnsi = $false
if (-not $env:NO_COLOR -and $env:ARIA_COLOR -ne '0') {
    try {
        if ($Host.UI.PSObject.Properties.Name -contains 'SupportsVirtualTerminal') {
            $script:SupportsAnsi = [bool]$Host.UI.SupportsVirtualTerminal
        }
    }
    catch { $script:SupportsAnsi = $false }
    if (-not $script:SupportsAnsi -and ($env:WT_SESSION -or $env:ANSICON -or $env:ConEmuANSI -eq 'ON' -or $env:TERM -match 'xterm|ansi|color')) {
        $script:SupportsAnsi = $true
    }
}

function Get-AriaConsoleColor {
    param([string]$Name)
    switch ($Name) {
        'Cyan' { return 'Cyan' }
        'Magenta' { return 'Magenta' }
        'Green' { return 'Green' }
        'Yellow' { return 'Yellow' }
        'Red' { return 'Red' }
        'Gray' { return 'DarkGray' }
        default { return 'White' }
    }
}

function Get-AriaAnsiColor {
    param([string]$Name)
    switch ($Name) {
        'Cyan' { return '96' }
        'Magenta' { return '95' }
        'Green' { return '92' }
        'Yellow' { return '93' }
        'Red' { return '91' }
        'Gray' { return '90' }
        default { return '97' }
    }
}

function Write-AriaPaint {
    param(
        [Parameter(Mandatory=$true)][AllowEmptyString()][string]$Text,
        [string]$Color = 'White',
        [switch]$Bold,
        [switch]$Pulse,
        [switch]$NoNewline
    )
    if ($script:SupportsAnsi) {
        $codes = New-Object System.Collections.Generic.List[string]
        $codes.Add((Get-AriaAnsiColor -Name $Color))
        if ($Bold) { $codes.Add('1') }
        if ($Pulse) { $codes.Add('5') }
        $painted = "$script:Esc[$($codes -join ';')m$Text$script:Esc[0m"
        Write-Host $painted -NoNewline:$NoNewline
    }
    else {
        Write-Host $Text -ForegroundColor (Get-AriaConsoleColor -Name $Color) -NoNewline:$NoNewline
    }
}

function Format-AriaDuration {
    param($Duration)
    if ($null -eq $Duration) { return '' }
    if ($Duration.TotalSeconds -ge 1) { return ('{0:0.00}s' -f $Duration.TotalSeconds) }
    return ('{0}ms' -f [math]::Max(1, [int][math]::Round($Duration.TotalMilliseconds)))
}

function Write-AriaBanner {
    param(
        [Parameter(Mandatory=$true)][string]$Title,
        [string]$Subtitle = 'gated compiler · compressed bytecode · local virtual machine'
    )

    $profile = Get-AriaDisplayProfile
    $mode = Get-AriaBannerSignalMode -Title $Title
    $style = Get-AriaSignalStyle -Mode $mode

    Write-Host ''

    Write-AriaPaint `
        -Text $style.glyph `
        -Color $style.color `
        -Bold `
        -NoNewline

    Write-AriaPaint `
        -Text ('  {0}' -f $Title.ToUpperInvariant()) `
        -Color Cyan `
        -Bold `
        -NoNewline

    if ($profile.verbose -and $Subtitle) {
        Write-AriaPaint `
            -Text ('   {0}' -f $Subtitle) `
            -Color Gray
    }
    else {
        Write-Host ''
    }

    $script:AriaSignalState.previousMode = $style.mode
    $script:AriaSignalState.previousGlyph = $style.glyph
}

$script:AriaSignalState = [pscustomobject][ordered]@{
    sequence = 0
    previousMode = $null
    previousGlyph = $null
}

function Get-AriaGlyphRegistry {
    [CmdletBinding()]
    param()

    $definitions = @(
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Observe'
            glyph        = '🜁'
            color        = 'Magenta'
            label        = 'OBSERVE'
            coherence    = 'measuring'
            motion       = 'Pulse'
            cognitiveCue = 'orient attention'
            domain       = 'analysis'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Bind'
            glyph        = '🜃'
            color        = 'Magenta'
            label        = 'BOUND'
            coherence    = 'bounded'
            motion       = 'Clamp'
            cognitiveCue = 'mark constraint'
            domain       = 'authority'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Emit'
            glyph        = '🜂'
            color        = 'Magenta'
            label        = 'EMIT'
            coherence    = 'transmitting'
            motion       = 'Wave'
            cognitiveCue = 'signal initiation'
            domain       = 'transmission'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Retain'
            glyph        = '🜄'
            color        = 'Green'
            label        = 'RETAIN'
            coherence    = 'retained'
            motion       = 'Settle'
            cognitiveCue = 'encode persistence'
            domain       = 'memory'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Attest'
            glyph        = '🜍'
            color        = 'Green'
            label        = 'ATTEST'
            coherence    = 'verified'
            motion       = 'Pulse'
            cognitiveCue = 'confirm identity'
            domain       = 'verification'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Evolve'
            glyph        = '∿'
            color        = 'Magenta'
            label        = 'EVOLVE'
            coherence    = 'transitioning'
            motion       = 'Wave'
            cognitiveCue = 'indicate transformation'
            domain       = 'evolution'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Seal'
            glyph        = '◆'
            color        = 'Green'
            label        = 'SEALED'
            coherence    = 'coherent'
            motion       = 'Settle'
            cognitiveCue = 'signal completion'
            domain       = 'artifact'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Fracture'
            glyph        = '⬗'
            color        = 'Red'
            label        = 'FRACTURE'
            coherence    = 'fractured'
            motion       = 'Shake'
            cognitiveCue = 'interrupt and warn'
            domain       = 'failure'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'System'
            glyph        = '⌬'
            color        = 'Cyan'
            label        = 'SYSTEM'
            coherence    = 'online'
            motion       = 'Orbit'
            cognitiveCue = 'establish system frame'
            domain       = 'system'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Operator'
            glyph        = '◉'
            color        = 'Magenta'
            label        = 'OPERATOR'
            coherence    = 'present'
            motion       = 'Pulse'
            cognitiveCue = 'center human agency'
            domain       = 'human'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Agent'
            glyph        = '⟁'
            color        = 'Magenta'
            label        = 'AGENT'
            coherence    = 'engaged'
            motion       = 'Pulse'
            cognitiveCue = 'mark delegated agency'
            domain       = 'agent'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Repository'
            glyph        = '▧'
            color        = 'Cyan'
            label        = 'REPOSITORY'
            coherence    = 'tracked'
            motion       = 'Clamp'
            cognitiveCue = 'anchor provenance'
            domain       = 'repository'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Service'
            glyph        = 'ϟ'
            color        = 'Magenta'
            label        = 'SERVICE'
            coherence    = 'active'
            motion       = 'Spark'
            cognitiveCue = 'signal external action'
            domain       = 'service'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Surface'
            glyph        = '◇'
            color        = 'Cyan'
            label        = 'SURFACE'
            coherence    = 'visible'
            motion       = 'Pulse'
            cognitiveCue = 'present information'
            domain       = 'surface'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Memory'
            glyph        = '⊙'
            color        = 'Green'
            label        = 'MEMORY'
            coherence    = 'continuous'
            motion       = 'Orbit'
            cognitiveCue = 'cue continuity'
            domain       = 'memory'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Artifact'
            glyph        = '◆'
            color        = 'Green'
            label        = 'ARTIFACT'
            coherence    = 'materialized'
            motion       = 'Settle'
            cognitiveCue = 'mark produced evidence'
            domain       = 'artifact'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Policy'
            glyph        = '⛨'
            color        = 'Magenta'
            label        = 'POLICY'
            coherence    = 'governing'
            motion       = 'Clamp'
            cognitiveCue = 'mark rule boundary'
            domain       = 'policy'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Stream'
            glyph        = '∿'
            color        = 'Magenta'
            label        = 'STREAM'
            coherence    = 'flowing'
            motion       = 'Wave'
            cognitiveCue = 'show continuous flow'
            domain       = 'stream'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Connect'
            glyph        = '↔'
            color        = 'Magenta'
            label        = 'CONNECT'
            coherence    = 'linked'
            motion       = 'Bridge'
            cognitiveCue = 'show relationship'
            domain       = 'connection'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Parallel'
            glyph        = '⧉'
            color        = 'Magenta'
            label        = 'PARALLEL'
            coherence    = 'distributed'
            motion       = 'Orbit'
            cognitiveCue = 'show concurrent work'
            domain       = 'coordination'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Converge'
            glyph        = '⧉'
            color        = 'Green'
            label        = 'CONVERGED'
            coherence    = 'integrated'
            motion       = 'Settle'
            cognitiveCue = 'show coherent joining'
            domain       = 'coordination'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Sync'
            glyph        = '⌁'
            color        = 'Cyan'
            label        = 'SYNC'
            coherence    = 'aligned'
            motion       = 'Wave'
            cognitiveCue = 'cue synchronization'
            domain       = 'coordination'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Retry'
            glyph        = '⟲'
            color        = 'Magenta'
            label        = 'RETRY'
            coherence    = 're-entering'
            motion       = 'Orbit'
            cognitiveCue = 'cue another attempt'
            domain       = 'recovery'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Wait'
            glyph        = '⧖'
            color        = 'Cyan'
            label        = 'WAIT'
            coherence    = 'pending'
            motion       = 'Pulse'
            cognitiveCue = 'hold attention gently'
            domain       = 'latency'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Discover'
            glyph        = '⟡'
            color        = 'Cyan'
            label        = 'DISCOVER'
            coherence    = 'revealed'
            motion       = 'Spark'
            cognitiveCue = 'mark new information'
            domain       = 'discovery'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Focus'
            glyph        = '◎'
            color        = 'Magenta'
            label        = 'FOCUS'
            coherence    = 'centered'
            motion       = 'Pulse'
            cognitiveCue = 'direct focal attention'
            domain       = 'attention'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Gate'
            glyph        = '⚑'
            color        = 'Magenta'
            label        = 'GATE'
            coherence    = 'evaluating'
            motion       = 'Clamp'
            cognitiveCue = 'mark decision point'
            domain       = 'verification'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Isolate'
            glyph        = '⊗'
            color        = 'Red'
            label        = 'ISOLATE'
            coherence    = 'contained'
            motion       = 'Clamp'
            cognitiveCue = 'mark containment'
            domain       = 'safety'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Merge'
            glyph        = '⊕'
            color        = 'Green'
            label        = 'MERGE'
            coherence    = 'combined'
            motion       = 'Bridge'
            cognitiveCue = 'show composition'
            domain       = 'integration'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Measure'
            glyph        = '⏱'
            color        = 'Cyan'
            label        = 'MEASURE'
            coherence    = 'timed'
            motion       = 'Pulse'
            cognitiveCue = 'cue quantitative state'
            domain       = 'measurement'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Authorize'
            glyph        = '⛨'
            color        = 'Green'
            label        = 'AUTHORIZE'
            coherence    = 'granted'
            motion       = 'Pulse'
            cognitiveCue = 'confirm permission'
            domain       = 'authority'
        }
        [pscustomobject][ordered]@{
            schema       = 'aria.display-glyph-registry/0.2'
            mode         = 'Deny'
            glyph        = '⊘'
            color        = 'Red'
            label        = 'DENY'
            coherence    = 'withheld'
            motion       = 'Shake'
            cognitiveCue = 'interrupt unsafe action'
            domain       = 'authority'
        }
    )

    return $definitions
}

function Get-AriaSignalStyle {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Mode
    )

    $style = @(
        Get-AriaGlyphRegistry |
            Where-Object {
                $_.mode -eq $Mode
            }
    )

    if ($style.Count -ne 1) {
        throw "Unknown or ambiguous ARIA signal mode '$Mode'."
    }

    return $style[0]
}

function Get-AriaDisplayProfile {
    [CmdletBinding()]
    param()

    $requested = [string]$env:ARIA_DISPLAY
    $verbose = (
        $env:ARIA_VERBOSE -eq '1' -or
        $requested -eq 'verbose' -or
        $requested -eq 'expanded'
    )

    $mode = if ($verbose) {
        'verbose'
    }
    else {
        'compact'
    }

    [pscustomobject][ordered]@{
        schema = 'aria.display-profile/0.1'
        mode = $mode
        verbose = $verbose
        compact = (-not $verbose)
        successExpansion = $verbose
        fractureExpansion = $true
    }
}

function Get-AriaMotionPolicy {
    [CmdletBinding()]
    param()

    $requested = [string]$env:ARIA_MOTION
    $reduced = (
        $env:ARIA_REDUCED_MOTION -eq '1' -or
        $env:ARIA_NO_ANIMATION -eq '1' -or
        $env:ARIA_ANIMATION -eq '0' -or
        $requested -eq '0' -or
        $requested -eq 'off'
    )

    $interactive = (
        [Environment]::UserInteractive -and
        -not [Console]::IsOutputRedirected -and
        $env:CI -ne 'true'
    )

    $enabled = (
        -not $reduced -and
        $interactive
    )

    $intensity = [string]$env:ARIA_MOTION_INTENSITY

    if ([string]::IsNullOrWhiteSpace($intensity)) {
        $intensity = 'normal'
    }

    $delayMs = switch ($intensity.ToLowerInvariant()) {
        'subtle' { 28 }
        'strong' { 52 }
        default  { 38 }
    }

    $maxFrames = switch ($intensity.ToLowerInvariant()) {
        'subtle' { 1 }
        'strong' { 3 }
        default  { 2 }
    }

    [pscustomobject][ordered]@{
        schema = 'aria.display-motion-policy/0.2'
        enabled = $enabled
        reducedMotion = $reduced
        interactive = $interactive
        intensity = $intensity
        delayMs = $delayMs
        maxFrames = $maxFrames
    }
}

function Get-AriaMotionFrames {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Style,
        [AllowNull()]$PreviousStyle
    )

    $frames = New-Object System.Collections.Generic.List[string]

    if (
        $null -ne $PreviousStyle -and
        [string]$PreviousStyle.mode -ne [string]$Style.mode
    ) {
        [void]$frames.Add(
            ('{0}›{1}' -f $PreviousStyle.glyph, $Style.glyph)
        )
    }

    switch ([string]$Style.motion) {
        'Pulse' {
            [void]$frames.Add('·')
            [void]$frames.Add([string]$Style.glyph)
            [void]$frames.Add('◆')
            [void]$frames.Add([string]$Style.glyph)
        }

        'Shake' {
            [void]$frames.Add((' {0}' -f $Style.glyph))
            [void]$frames.Add(('{0} ' -f $Style.glyph))
            [void]$frames.Add((' {0}' -f $Style.glyph))
            [void]$frames.Add([string]$Style.glyph)
        }

        'Wave' {
            [void]$frames.Add('·')
            [void]$frames.Add('∿')
            [void]$frames.Add([string]$Style.glyph)
            [void]$frames.Add('∿')
        }

        'Orbit' {
            [void]$frames.Add(('◜{0}' -f $Style.glyph))
            [void]$frames.Add(('◝{0}' -f $Style.glyph))
            [void]$frames.Add(('◞{0}' -f $Style.glyph))
            [void]$frames.Add(('◟{0}' -f $Style.glyph))
        }

        'Spark' {
            [void]$frames.Add('·')
            [void]$frames.Add('✦')
            [void]$frames.Add([string]$Style.glyph)
            [void]$frames.Add('✦')
        }

        'Clamp' {
            [void]$frames.Add(('⟦ {0} ⟧' -f $Style.glyph))
            [void]$frames.Add(('⟦{0}⟧' -f $Style.glyph))
        }

        'Settle' {
            [void]$frames.Add('◇')
            [void]$frames.Add([string]$Style.glyph)
            [void]$frames.Add('◆')
        }

        'Bridge' {
            [void]$frames.Add(('·{0}·' -f $Style.glyph))
            [void]$frames.Add(('─{0}─' -f $Style.glyph))
        }

        default {
            [void]$frames.Add([string]$Style.glyph)
        }
    }

    return $frames.ToArray()
}

function Invoke-AriaGlyphMotion {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Style,
        [AllowEmptyString()][string]$Prefix = ''
    )

    $policy = Get-AriaMotionPolicy

    if (-not $policy.enabled) {
        return
    }

    $previousStyle = $null

    if ($script:AriaSignalState.previousMode) {
        try {
            $previousStyle = Get-AriaSignalStyle `
                -Mode $script:AriaSignalState.previousMode
        }
        catch {
            $previousStyle = $null
        }
    }

    $frames = @(
        Get-AriaMotionFrames `
            -Style $Style `
            -PreviousStyle $previousStyle |
            Select-Object -First $policy.maxFrames
    )

    $clearWidth = 12

    foreach ($frame in $frames) {
        Write-Host "`r" -NoNewline

        if ($Prefix) {
            Write-AriaPaint `
                -Text $Prefix `
                -Color Gray `
                -NoNewline
        }

        Write-AriaPaint `
            -Text ([string]$frame) `
            -Color $Style.color `
            -Bold `
            -NoNewline

        Write-Host (' ' * $clearWidth) -NoNewline
        Start-Sleep -Milliseconds $policy.delayMs
    }

    Write-Host "`r" -NoNewline
}

function Get-AriaBannerSignalMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Title
    )

    switch -Regex ($Title.ToUpperInvariant()) {
        'CONFORMANCE|TEST|LATTICE' {
            return 'Parallel'
        }

        'MANIFEST|REPOSITORY|GIT' {
            return 'Repository'
        }

        'DOCTOR|SYSTEM|VERIFY|VERSION' {
            return 'System'
        }

        'EVOLUTION|EVOLVE' {
            return 'Evolve'
        }

        'TRANSMISSION|SEND|PUSH|PULL' {
            return 'Emit'
        }

        'SYNC' {
            return 'Sync'
        }

        'POLICY|AUTHORITY|CONSENT' {
            return 'Policy'
        }

        'MEMORY|RECALL|REMEMBER' {
            return 'Memory'
        }

        'COMPILE|BUILD|ARTIFACT|CONTAINER' {
            return 'Artifact'
        }

        'AGENT' {
            return 'Agent'
        }

        default {
            return 'System'
        }
    }
}

function Write-AriaSignal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Mode,
        [Parameter(Mandatory=$true)][string]$Name,
        [AllowEmptyString()][string]$Value = '',
        [AllowEmptyString()][string]$Detail = '',
        $Duration,
        [AllowEmptyString()][string]$Prefix = '',
        [switch]$PassThru
    )

    $style = Get-AriaSignalStyle -Mode $Mode
    $durationText = Format-AriaDuration -Duration $Duration

    if ($Prefix) {
        Write-AriaPaint `
            -Text $Prefix `
            -Color Gray `
            -NoNewline
    }

    Write-AriaPaint `
        -Text $style.glyph `
        -Color $style.color `
        -Bold `
        -NoNewline

    Write-AriaPaint `
        -Text ('  {0,-18} ' -f $Name) `
        -Color White `
        -NoNewline

    $signalValue = if ($Value) {
        $Value
    }
    else {
        $style.label
    }

    Write-AriaPaint `
        -Text $signalValue `
        -Color $style.color `
        -Bold `
        -NoNewline

    $tail = New-Object System.Collections.Generic.List[string]

    if ($durationText) {
        [void]$tail.Add($durationText)
    }

    if ($Detail) {
        [void]$tail.Add($Detail)
    }

    if ($tail.Count -gt 0) {
        Write-AriaPaint `
            -Text (' · ' + ($tail -join ' · ')) `
            -Color Gray
    }
    else {
        Write-Host ''
    }

    $previousMode = $script:AriaSignalState.previousMode
    $script:AriaSignalState.sequence++
    $script:AriaSignalState.previousMode = $style.mode
    $script:AriaSignalState.previousGlyph = $style.glyph

    if ($PassThru) {
        return [pscustomobject][ordered]@{
            schema         = 'aria.display-signal/0.3'
            sequence       = $script:AriaSignalState.sequence
            mode           = $style.mode
            glyph          = $style.glyph
            color          = $style.color
            label          = $style.label
            coherence      = $style.coherence
            motion         = $style.motion
            cognitiveCue   = $style.cognitiveCue
            domain         = $style.domain
            transitionFrom = $previousMode
            name           = $Name
            value          = $Value
            detail         = $Detail
            duration       = $durationText
        }
    }
}

function Write-AriaStage {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][ValidateSet('Pulse','Pass','Reject','Fail','Warn','Info')][string]$State,
        [string]$Detail = '',
        $Duration,
        [string]$Prefix = ''
    )

    $profile = Get-AriaDisplayProfile

    if (
        $profile.compact -and
        $State -notin @('Reject', 'Fail', 'Warn')
    ) {
        return
    }

    $glyph = '◇'
    $color = 'Cyan'
    $label = 'READY'
    $pulse = $false

    switch ($State) {
        'Pulse' {
            $glyph = '◈'
            $color = 'Magenta'
            $label = 'ACTIVE'
            $pulse = $true
        }

        'Pass' {
            $glyph = '◆'
            $color = 'Green'
            $label = 'PASS'
        }

        'Reject' {
            $glyph = '⊘'
            $color = 'Red'
            $label = 'REJECT'
        }

        'Fail' {
            $glyph = '⬗'
            $color = 'Red'
            $label = 'FAIL'
        }

        'Warn' {
            $glyph = '◇'
            $color = 'Magenta'
            $label = 'WARN'
        }

        'Info' {
            $glyph = '◇'
            $color = 'Cyan'
            $label = 'INFO'
        }
    }

    $durationText = Format-AriaDuration -Duration $Duration
    $suffixParts = New-Object System.Collections.Generic.List[string]

    if ($durationText) {
        [void]$suffixParts.Add($durationText)
    }

    if ($Detail) {
        [void]$suffixParts.Add($Detail)
    }

    $suffix = if ($suffixParts.Count -gt 0) {
        '  ' + ($suffixParts -join ' · ')
    }
    else {
        ''
    }

    if ($Prefix) {
        Write-AriaPaint `
            -Text $Prefix `
            -Color Gray `
            -NoNewline
    }

    Write-AriaPaint `
        -Text $glyph `
        -Color $color `
        -Bold `
        -Pulse:$pulse `
        -NoNewline

    Write-AriaPaint `
        -Text ('  {0,-22} ' -f $Name) `
        -Color White `
        -NoNewline

    Write-AriaPaint `
        -Text ('{0,-9}' -f $label) `
        -Color $color `
        -Bold `
        -NoNewline

    Write-AriaPaint `
        -Text $suffix `
        -Color Gray
}


function Get-AriaTreePrefix {
    param([int]$Depth = 0, [switch]$Last)
    $parts = New-Object System.Collections.Generic.List[string]
    for ($index = 0; $index -lt $Depth; $index++) { $parts.Add('│  ') }
    $parts.Add($(if ($Last) { '└─ ' } else { '├─ ' }))
    return ($parts -join '')
}

function Write-AriaTreeStage {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][ValidateSet('Pulse','Pass','Reject','Fail','Warn','Info')][string]$State,
        [string]$Detail = '',
        $Duration,
        [int]$Depth = 0,
        [switch]$Last
    )
    Write-AriaStage -Name $Name -State $State -Detail $Detail -Duration $Duration -Prefix (Get-AriaTreePrefix -Depth $Depth -Last:$Last)
}

function Write-AriaTreeText {
    param(
        [Parameter(Mandatory=$true)][AllowEmptyString()][string]$Text,
        [string]$Glyph = '◇',
        [string]$Color = 'Cyan',
        [int]$Depth = 0,
        [switch]$Last
    )
    Write-AriaPaint -Text (Get-AriaTreePrefix -Depth $Depth -Last:$Last) -Color Gray -NoNewline
    Write-AriaPaint -Text $Glyph -Color $Color -Bold -NoNewline
    Write-AriaPaint -Text ('  ' + $Text) -Color White
}

function Write-AriaTrunk {
    param([int]$Depth = 0)
    $prefix = ''
    for ($index = 0; $index -lt $Depth; $index++) { $prefix += '│  ' }
    Write-AriaPaint -Text ($prefix + '│') -Color Gray
}

function Write-AriaKeyValue {
    param(
        [string]$Key,
        [AllowEmptyString()][string]$Value
    )

    $profile = Get-AriaDisplayProfile

    if ($profile.compact) {
        return
    }

    Write-AriaPaint `
        -Text '◇' `
        -Color Cyan `
        -NoNewline

    Write-AriaPaint `
        -Text ('  {0,-14}' -f $Key) `
        -Color Gray `
        -NoNewline

    Write-AriaPaint `
        -Text $Value `
        -Color White
}

function Write-AriaSummary {
    param(
        [Parameter(Mandatory=$true)][string]$Title,
        [Parameter(Mandatory=$true)][bool]$Passed,
        [string]$Detail = '',
        $Duration
    )

    $profile = Get-AriaDisplayProfile
    Write-Host ''

    if ($profile.verbose) {
        Write-AriaStage `
            -Name $Title `
            -State $(if ($Passed) { 'Pass' } else { 'Fail' }) `
            -Detail $Detail `
            -Duration $Duration

        return
    }

    Write-AriaSignal `
        -Mode $(if ($Passed) { 'Seal' } else { 'Fracture' }) `
        -Name $Title `
        -Value $(if ($Detail) { $Detail } elseif ($Passed) { 'ONLINE' } else { 'FAILED' }) `
        -Duration $Duration
}

function Write-AriaStream {
    param([Parameter(Mandatory=$true)][AllowEmptyString()][string]$Text)
    Write-AriaPaint -Text '∿' -Color Magenta -NoNewline
    Write-AriaPaint -Text ('  ' + $Text) -Color White
}


$script:AriaEnumeration = $null

function Start-AriaEnumerator {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [int]$Expected = 0,
        [string]$Domain = 'runtime'
    )

    $script:AriaEnumeration = [pscustomobject][ordered]@{
        Name = $Name
        Domain = $Domain
        Expected = $Expected
        Passed = 0
        Failed = 0
        Started = [Diagnostics.Stopwatch]::StartNew()
        Items = New-Object System.Collections.Generic.List[object]
        TransmissionTotal = 0
        TransmissionPassed = 0
        TransmissionFailed = 0
        TransmissionDurationMs = [int64]0
        TransmissionBytes = [int64]0
    }

    $style = Get-AriaSignalStyle -Mode Parallel
    Invoke-AriaGlyphMotion -Style $style

    Write-AriaPaint `
        -Text $style.glyph `
        -Color $style.color `
        -Bold `
        -NoNewline

    Write-AriaPaint `
        -Text ("  {0}" -f $Name) `
        -Color White `
        -NoNewline

    if ($Expected -gt 0) {
        Write-AriaPaint `
            -Text ("  ×{0}" -f $Expected) `
            -Color Gray
    }
    else {
        Write-Host ''
    }

    $script:AriaSignalState.previousMode = 'Parallel'
    $script:AriaSignalState.previousGlyph = $style.glyph
}

function Add-AriaEnumerationItem {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][ValidateSet('Pass','Fail','Warn','Info')][string]$State,
        [string]$Detail = '',
        $Duration
    )

    if($null -eq $script:AriaEnumeration){ throw 'ARIA enumerator is not active.' }

    $item=[pscustomobject][ordered]@{
        Name=$Name
        State=$State
        Detail=$Detail
        Duration=$Duration
    }
    $script:AriaEnumeration.Items.Add($item)

    if($State -eq 'Pass'){
        $script:AriaEnumeration.Passed++
        if($env:ARIA_VERBOSE -eq '1'){
            Write-AriaStage -Name $Name -State Pass -Detail $Detail -Duration $Duration -Prefix '│  '
        }
        return
    }

    if($State -eq 'Fail'){ $script:AriaEnumeration.Failed++ }
    Write-AriaStage -Name $Name -State $State -Detail $Detail -Duration $Duration -Prefix '│  '
}

function Complete-AriaEnumerator {
    param(
        [string]$Detail = ''
    )

    if ($null -eq $script:AriaEnumeration) {
        throw 'ARIA enumerator is not active.'
    }

    $script:AriaEnumeration.Started.Stop()

    $total = $script:AriaEnumeration.Items.Count
    $passed = $script:AriaEnumeration.Passed
    $failed = $script:AriaEnumeration.Failed
    $duration = Format-AriaDuration `
        -Duration $script:AriaEnumeration.Started.Elapsed

    $mode = if ($failed -eq 0) {
        'Converge'
    }
    else {
        'Fracture'
    }

    $coherence = if ($failed -eq 0) {
        'coherent'
    }
    else {
        "$failed fracture(s)"
    }

    $tail = New-Object System.Collections.Generic.List[string]
    [void]$tail.Add($duration)
    [void]$tail.Add($coherence)

    if ($script:AriaEnumeration.TransmissionTotal -gt 0) {
        [void]$tail.Add(
            (
                'tx {0}/{1}' -f `
                    $script:AriaEnumeration.TransmissionPassed,
                    $script:AriaEnumeration.TransmissionTotal
            )
        )

        [void]$tail.Add(
            ('{0}B' -f $script:AriaEnumeration.TransmissionBytes)
        )
    }

    if (
        (Get-AriaDisplayProfile).verbose -and
        $Detail
    ) {
        [void]$tail.Add($Detail)
    }

    Write-AriaSignal `
        -Mode $mode `
        -Name $script:AriaEnumeration.Name `
        -Value ("{0}/{1}" -f $passed, $total) `
        -Detail ($tail -join ' · ')

    $result = $script:AriaEnumeration
    $script:AriaEnumeration = $null

    return $result
}

function Write-AriaCausalFrame {
    param(
        [Parameter(Mandatory=$true)][string]$Domain,
        [Parameter(Mandatory=$true)][string]$Phase,
        [Parameter(Mandatory=$true)][string]$State,
        [Parameter(Mandatory=$true)][string]$Information,
        [string]$Cause='',
        [string]$Effect='',
        $Duration
    )

    $glyph=if($State -eq 'PASS'){'◆'}elseif($State -eq 'FAIL'){'⬗'}else{'◈'}
    $color=if($State -eq 'PASS'){'Green'}elseif($State -eq 'FAIL'){'Red'}else{'Magenta'}
    $time=Format-AriaDuration -Duration $Duration
    $causal=''
    if($Cause -or $Effect){$causal=("  {0}→{1}" -f $Cause,$Effect)}
    if($time){$causal+="  @$time"}

    Write-AriaPaint -Text $glyph -Color $color -Bold -NoNewline
    Write-AriaPaint -Text ("  {0}.{1}" -f $Domain,$Phase) -Color Cyan -NoNewline
    Write-AriaPaint -Text ("  ∿ {0}" -f $Information) -Color White -NoNewline
    Write-AriaPaint -Text $causal -Color Gray
}
Export-ModuleMember -Function Write-AriaPaint, Write-AriaBanner, Write-AriaStage, Write-AriaTreeStage, Write-AriaTreeText, Write-AriaTrunk, Write-AriaKeyValue, Write-AriaSummary, Write-AriaStream, Format-AriaDuration, Start-AriaEnumerator, Add-AriaEnumerationItem, Complete-AriaEnumerator, Write-AriaCausalFrame

function Invoke-AriaEtherPreview {
    param([Parameter(Mandatory=$true)]$Transmission)

    $events = Get-AriaTriadicEventsFromTransmission -Transmission $Transmission
    foreach ($event in $events) {
        Write-AriaTriadicTransmission -Event $event
    }
}

function Test-AriaInteractiveBuffer {
    [CmdletBinding()]
    param()

    if (
        $env:CI -or
        $env:GITHUB_ACTIONS -eq 'true' -or
        $env:ARIA_NO_ANIMATION -eq '1' -or
        $env:ARIA_REDUCED_MOTION -eq '1' -or
        $env:ARIA_ANIMATION -eq '0' -or
        $env:ARIA_MOTION -in @('0','off')
    ) {
        return $false
    }

    try {
        return -not [Console]::IsOutputRedirected
    }
    catch {
        return $Host.Name -eq 'ConsoleHost'
    }
}

function New-AriaBufferState {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [ValidateRange(8,48)][int]$Width = 18,
        [ValidateRange(40,1000)][int]$IntervalMs = 90
    )

    [pscustomobject][ordered]@{
        label = $Label
        width = $Width
        intervalMs = $IntervalMs
        position = 0
        direction = 1
        tick = 0
        active = $true
        interactive = [bool](Test-AriaInteractiveBuffer)
        lastLength = 0
    }
}

function Get-AriaBufferFrame {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    $cells = New-Object 'System.Collections.Generic.List[string]'
    for ($index = 0; $index -lt [int]$State.width; $index++) {
        if ($index -eq [int]$State.position) {
            [void]$cells.Add('◆')
        }
        elseif ([math]::Abs($index - [int]$State.position) -eq 1) {
            [void]$cells.Add('·')
        }
        else {
            [void]$cells.Add('∙')
        }
    }

    $phase = @('∿','⌁','∿','⌁')[[int]$State.tick % 4]
    "{0}  {1}  ⟦{2}⟧" -f $phase,[string]$State.label,($cells -join '')
}

function Step-AriaBuffer {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    if (-not [bool]$State.active) { return $State }

    $next = [int]$State.position + [int]$State.direction
    if ($next -ge ([int]$State.width - 1)) {
        $next = [int]$State.width - 1
        [void]($State.direction = -1)
    }
    elseif ($next -le 0) {
        $next = 0
        [void]($State.direction = 1)
    }

    [void]($State.position = $next)
    [void]($State.tick = [int]$State.tick + 1)
    return $State
}

function Write-AriaBufferFrame {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    if (-not [bool]$State.interactive) { return }

    $frame = Get-AriaBufferFrame -State $State
    $padding = ''
    if ([int]$State.lastLength -gt $frame.Length) {
        $padding = ' ' * ([int]$State.lastLength - $frame.Length)
    }

    Write-Host ("`r" + $frame + $padding) -NoNewline -ForegroundColor Cyan
    [void]($State.lastLength = $frame.Length)
}

function Stop-AriaBuffer {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    [void]($State.active = $false)
    if ([bool]$State.interactive) {
        $clearWidth = [math]::Max([int]$State.lastLength,1)
        Write-Host ("`r" + (' ' * $clearWidth) + "`r") -NoNewline
    }
}
Export-ModuleMember -Function Invoke-AriaEtherPreview
# Alpha.12 universal buffering surface.
function New-AriaTransmissionBuffer {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [ValidateSet('local','remote','verification','runtime')][string]$Mode = 'local',
        [ValidateRange(10,36)][int]$Width = 18,
        [ValidateRange(45,500)][int]$IntervalMs = 85
    )

    [pscustomobject][ordered]@{
        label = $Label
        mode = $Mode
        width = $Width
        intervalMs = $IntervalMs
        tick = 0
        heartbeatCount = 0
        position = 0
        direction = 1
        active = $true
        interactive = [bool](Test-AriaInteractiveBuffer)
        lastLength = 0
        startedAt = [datetime]::UtcNow
    }
}

function Get-AriaTransmissionPhase {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    if ([bool]$State.active) { return 'pending' }
    return 'closed'
}

function Get-AriaGearGlyphs {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    $left = @('⧖','·','⧖','∙')[[int]$State.tick % 4]
    $right = @('∙','⧖','·','⧖')[[int]$State.tick % 4]
    [pscustomobject][ordered]@{
        left = $left
        right = $right
    }
}

function Get-AriaTransmissionFrame {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    $phase = Get-AriaTransmissionPhase -State $State
    $gears = Get-AriaGearGlyphs -State $State
    $cells = New-Object 'System.Collections.Generic.List[string]'

    for ($index = 0; $index -lt [int]$State.width; $index++) {
        $distance = [math]::Abs($index - [int]$State.position)

        if ($distance -eq 0) { [void]$cells.Add('⧖') }
        elseif ($distance -eq 1) { [void]$cells.Add('·') }
        else { [void]$cells.Add('∙') }
    }

    $elapsed = [math]::Max(0,([datetime]::UtcNow - [datetime]$State.startedAt).TotalSeconds)
    "{0}{1} {2,-9} {3} ⟦{4}⟧ elapsed:{5,4:N1}s" -f `
        $gears.left, `
        $gears.right, `
        $phase, `
        [string]$State.label, `
        ($cells -join ''), `
        $elapsed
}

function Step-AriaTransmissionBuffer {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    if (-not [bool]$State.active) { return $State }

    $next = [int]$State.position + [int]$State.direction
    if ($next -ge ([int]$State.width - 1)) {
        $next = [int]$State.width - 1
        [void]($State.direction = -1)
    }
    elseif ($next -le 0) {
        $next = 0
        [void]($State.direction = 1)
    }
    [void]($State.position = $next)

    [void]($State.tick = [int]$State.tick + 1)
    [void]($State.heartbeatCount = [int]$State.heartbeatCount + 1)
    return $State
}

function Write-AriaTransmissionFrame {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$State)

    if (-not [bool]$State.interactive) { return }

    $frame = Get-AriaTransmissionFrame -State $State
    $padding = ''
    if ([int]$State.lastLength -gt $frame.Length) {
        $padding = ' ' * ([int]$State.lastLength - $frame.Length)
    }

    Write-Host ("`r" + $frame + $padding) -NoNewline -ForegroundColor Cyan
    [void]($State.lastLength = $frame.Length)
}

function Complete-AriaTransmissionBuffer {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$State,
        [ValidateSet('PASS','REJECT','WARN','FAIL')][string]$Outcome = 'PASS'
    )

    [void]($State.active = $false)
    if (-not [bool]$State.interactive) { return }

    Write-Host ("`r" + (' ' * [math]::Max([int]$State.lastLength,1)) + "`r") -NoNewline
}

function Invoke-AriaBufferedProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [Parameter(Mandatory=$true)][string]$Label,
        [ValidateSet('local','remote','verification','runtime')][string]$Mode = 'local',
        [switch]$VerboseBuffer
    )

    $stdout = [IO.Path]::GetTempFileName()
    $stderr = [IO.Path]::GetTempFileName()
    $buffer = New-AriaTransmissionBuffer -Label $Label -Mode $Mode
    if (
        (Get-Command Start-AriaEventOperation -ErrorAction SilentlyContinue) -and
        (Get-Command Send-AriaEvent -ErrorAction SilentlyContinue)
    ) {
        $null = Start-AriaEventOperation -Name $Label
        $null = Send-AriaEvent `
            -Domain operation `
            -Phase wait `
            -State ACTIVE `
            -Energy execution `
            -Information $Label `
            -Coherence 'process pending' `
            -Source 'aria.bufferflow' `
            -Data ([pscustomobject][ordered]@{mode=$Mode}) `
            -Render
    }

    try {
        $process = Start-Process `
            -FilePath $FilePath `
            -ArgumentList $ArgumentList `
            -WorkingDirectory $WorkingDirectory `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr

        try {
            while (-not $process.HasExited) {
                Write-AriaTransmissionFrame -State $buffer
                Start-Sleep -Milliseconds ([int]$buffer.intervalMs)
                $null = Step-AriaTransmissionBuffer -State $buffer
                $process.Refresh()
            }

            $process.WaitForExit()
            $process.Refresh()
        }
        catch {
            Complete-AriaTransmissionBuffer -State $buffer -Outcome FAIL
            throw
        }

        $exitCode = [int]$process.ExitCode
        $outText = [IO.File]::ReadAllText($stdout)
        $errText = [IO.File]::ReadAllText($stderr)

        if ($VerboseBuffer -or $env:ARIA_VERBOSE -eq '1') {
            if ($outText) { Write-Host $outText.TrimEnd() -ForegroundColor DarkGray }
            if ($errText) { Write-Host $errText.TrimEnd() -ForegroundColor DarkGray }
        }

        $completedAt = [datetime]::UtcNow
        Complete-AriaTransmissionBuffer -State $buffer -Outcome $(if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' })

        $receipt = New-AriaTransmissionReceipt `
            -Label $Label `
            -Mode $Mode `
            -ExitCode $exitCode `
            -StartedAt ([datetime]$buffer.startedAt) `
            -CompletedAt $completedAt `
            -Stdout $outText `
            -Stderr $errText `
            -HeartbeatCount ([int]$buffer.heartbeatCount)

        Write-AriaTransmissionReceipt -Receipt $receipt

        [pscustomobject][ordered]@{
            exitCode = $exitCode
            stdout = $outText
            stderr = $errText
            filePath = $FilePath
            arguments = @($ArgumentList)
            label = $Label
            mode = $Mode
            receipt = $receipt
        }
    }
    finally {
        Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue
    }
}
Export-ModuleMember -Function `
    Test-AriaInteractiveBuffer, `
    New-AriaBufferState, `
    Get-AriaBufferFrame, `
    Step-AriaBuffer, `
    Write-AriaBufferFrame, `
    Stop-AriaBuffer
# Alpha.13 Bufferflow surface.
function New-AriaTransmissionReceipt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][ValidateSet('local','remote','verification','runtime')][string]$Mode,
        [Parameter(Mandatory=$true)][int]$ExitCode,
        [Parameter(Mandatory=$true)][datetime]$StartedAt,
        [Parameter(Mandatory=$true)][datetime]$CompletedAt,
        [string]$Stdout = '',
        [string]$Stderr = '',
        [int]$HeartbeatCount = 0
    )

    $durationMs = [math]::Max(0,[int][math]::Round(($CompletedAt - $StartedAt).TotalMilliseconds))
    $stdoutBytes = [Text.Encoding]::UTF8.GetByteCount([string]$Stdout)
    $stderrBytes = [Text.Encoding]::UTF8.GetByteCount([string]$Stderr)
    $totalBytes = $stdoutBytes + $stderrBytes
    $outcome = if ($ExitCode -eq 0) { 'PASS' } else { 'FAIL' }
    $coherence = if ($ExitCode -eq 0) { 'exit code 0' } else { "exit code $ExitCode" }

    [pscustomobject][ordered]@{
        label = $Label
        mode = $Mode
        outcome = $outcome
        coherence = $coherence
        exitCode = $ExitCode
        durationMs = $durationMs
        stdoutBytes = $stdoutBytes
        stderrBytes = $stderrBytes
        totalBytes = $totalBytes
        heartbeatCount = $HeartbeatCount
        startedAt = $StartedAt.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        completedAt = $CompletedAt.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
    }
}

function Format-AriaTransmissionReceipt {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Receipt)

    $glyph = if ([string]$Receipt.outcome -eq 'PASS') { '└─ ∿' } else { '└─ ⬗' }
    $authority = switch ([string]$Receipt.mode) {
        'remote' { 'provider' }
        'verification' { 'verifier' }
        'runtime' { 'runtime' }
        default { 'local' }
    }

    "{0} {1} · {2} · {3}ms · {4}B · exit:{5}" -f `
        $glyph, `
        $authority, `
        [string]$Receipt.coherence, `
        [int]$Receipt.durationMs, `
        [int]$Receipt.totalBytes, `
        [int]$Receipt.exitCode
}

function Write-AriaTransmissionReceipt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        $Receipt
    )

    $profile = Get-AriaDisplayProfile
    $passed = ([string]$Receipt.outcome -eq 'PASS')
    $enumerating = ($null -ne $script:AriaEnumeration)
    $projected = $false

    if (Get-Command Send-AriaEvent -ErrorAction SilentlyContinue) {
        $null = Send-AriaEvent `
            -Domain operation `
            -Phase complete `
            -State $(if ($passed) { 'PASS' } else { 'FAIL' }) `
            -Energy completion `
            -Information $(if ($Receipt.label) { [string]$Receipt.label } else { 'operation' }) `
            -Coherence $(if ($Receipt.coherence) { [string]$Receipt.coherence } else { [string]$Receipt.outcome }) `
            -Source 'aria.signalflow' `
            -Data ([pscustomobject][ordered]@{
                mode = [string]$Receipt.mode
                durationMs = [int64]$Receipt.durationMs
                totalBytes = [int64]$Receipt.totalBytes
                stdoutBytes = [int64]$Receipt.stdoutBytes
                stderrBytes = [int64]$Receipt.stderrBytes
                exitCode = [int]$Receipt.exitCode
                heartbeatCount = if ($Receipt.PSObject.Properties['heartbeatCount']) { [int]$Receipt.heartbeatCount } else { 0 }
            }) `
            -Render
        $projected = $true
    }

    if ($enumerating) {
        $script:AriaEnumeration.TransmissionTotal++

        if ($passed) {
            $script:AriaEnumeration.TransmissionPassed++
        }
        else {
            $script:AriaEnumeration.TransmissionFailed++
        }

        if ($null -ne $Receipt.durationMs) {
            $script:AriaEnumeration.TransmissionDurationMs +=
                [int64]$Receipt.durationMs
        }

        if ($null -ne $Receipt.totalBytes) {
            $script:AriaEnumeration.TransmissionBytes +=
                [int64]$Receipt.totalBytes
        }
    }

    if ($projected) { return }

    if (
        $profile.compact -and
        $passed -and
        $enumerating
    ) {
        return
    }

    $detail = New-Object System.Collections.Generic.List[string]

    if ($null -ne $Receipt.durationMs) {
        [void]$detail.Add(
            ('{0}ms' -f [int64]$Receipt.durationMs)
        )
    }

    if ($null -ne $Receipt.totalBytes) {
        [void]$detail.Add(
            ('{0}B' -f [int64]$Receipt.totalBytes)
        )
    }

    if ($null -ne $Receipt.exitCode) {
        [void]$detail.Add(
            ('exit:{0}' -f [int]$Receipt.exitCode)
        )
    }

    Write-AriaSignal `
        -Mode $(if ($passed) { 'Emit' } else { 'Fracture' }) `
        -Name $(if ($Receipt.label) { [string]$Receipt.label } else { 'transmission' }) `
        -Value $(if ($Receipt.coherence) { [string]$Receipt.coherence } else { [string]$Receipt.outcome }) `
        -Detail ($detail -join ' · ') `
        -Prefix $(if ($enumerating) { '└─ ' } else { '' })
}

function Invoke-AriaBufferedItem {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Action,
        [ValidateSet('local','remote','verification','runtime')][string]$Mode = 'local',
        [switch]$VerboseBuffer
    )

    $startedAt = [datetime]::UtcNow
    $stdout = ''
    $stderr = ''
    $exitCode = 0

    $state = New-AriaTransmissionBuffer -Label $Name -Mode $Mode
    try {
        if (
            (Get-Command Start-AriaEventOperation -ErrorAction SilentlyContinue) -and
            (Get-Command Send-AriaEvent -ErrorAction SilentlyContinue)
        ) {
            $null = Start-AriaEventOperation -Name $Name
            $null = Send-AriaEvent `
                -Domain operation `
                -Phase wait `
                -State ACTIVE `
                -Energy execution `
                -Information $Name `
                -Coherence 'item pending' `
                -Source 'aria.bufferflow' `
                -Data ([pscustomobject][ordered]@{mode=$Mode}) `
                -Render
        }
        Write-AriaTransmissionFrame -State $state
        try {
            $output = & $Action 2>&1
            if ($null -ne $output) {
                $stdout = ($output | Out-String).TrimEnd()
            }
        }
        catch {
            $exitCode = 1
            $stderr = $_ | Out-String
        }

        $null = Step-AriaTransmissionBuffer -State $state
        Complete-AriaTransmissionBuffer -State $state -Outcome $(if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' })

        if ($VerboseBuffer -or $env:ARIA_VERBOSE -eq '1') {
            if ($stdout) { Write-Host $stdout -ForegroundColor DarkGray }
            if ($stderr) { Write-Host $stderr -ForegroundColor DarkGray }
        }

        $receipt = New-AriaTransmissionReceipt `
            -Label $Name `
            -Mode $Mode `
            -ExitCode $exitCode `
            -StartedAt $startedAt `
            -CompletedAt ([datetime]::UtcNow) `
            -Stdout $stdout `
            -Stderr $stderr `
            -HeartbeatCount ([int]$state.heartbeatCount)

        Write-AriaTransmissionReceipt -Receipt $receipt

        if ($exitCode -ne 0) {
            throw $stderr.Trim()
        }

        [pscustomobject][ordered]@{
            name = $Name
            output = $stdout
            receipt = $receipt
        }
    }
    finally {
        [void]($state.active = $false)
    }
}

function Invoke-AriaBufferedSequence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][object[]]$Items,
        [switch]$VerboseBuffer
    )

    $results = New-Object 'System.Collections.Generic.List[object]'
    foreach ($item in $Items) {
        if ($null -eq $item.name -or $null -eq $item.action) {
            throw 'Each buffered sequence item requires name and action.'
        }

        $mode = if ($null -ne $item.mode) { [string]$item.mode } else { 'local' }
        $result = Invoke-AriaBufferedItem `
            -Name ([string]$item.name) `
            -Action ([scriptblock]$item.action) `
            -Mode $mode `
            -VerboseBuffer:$VerboseBuffer

        [void]$results.Add($result)
    }

    return @($results.ToArray())
}
Export-ModuleMember -Function `
    New-AriaTransmissionBuffer, `
    Get-AriaTransmissionPhase, `
    Get-AriaGearGlyphs, `
    Get-AriaTransmissionFrame, `
    Step-AriaTransmissionBuffer, `
    Write-AriaTransmissionFrame, `
    Complete-AriaTransmissionBuffer, `
    Invoke-AriaBufferedProcess
# Alpha.14 Signalflow surface.
Export-ModuleMember -Function `
    New-AriaTransmissionReceipt, `
    Format-AriaTransmissionReceipt, `
    Write-AriaTransmissionReceipt, `
    Invoke-AriaBufferedItem, `
    Invoke-AriaBufferedSequence
Export-ModuleMember -Function Get-AriaGlyphRegistry, Get-AriaSignalStyle, Get-AriaDisplayProfile, Get-AriaMotionPolicy, Get-AriaMotionFrames, Invoke-AriaGlyphMotion, Write-AriaSignal
