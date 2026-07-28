Set-StrictMode -Version Latest

$typedCorePath = Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if (-not (Get-Module Aria.TypedCore)) {
    Import-Module $typedCorePath -DisableNameChecking
}

$graphCorePath = Join-Path $PSScriptRoot 'Aria.GraphCore.psm1'
if (-not (Get-Module Aria.GraphCore)) {
    Import-Module $graphCorePath -DisableNameChecking
}

function Get-AriaObjectMap {
    [CmdletBinding()]
    param(
        [object[]]$Items = @(),
        [string]$IdentityProperty = 'id'
    )

    $map = @{}
    foreach($item in @($Items)){
        $property = $item.PSObject.Properties[$IdentityProperty]
        if($null-eq$property){continue}
        $map[[string]$property.Value] = $item
    }
    return $map
}

function Compare-AriaGraphSemantic {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Before,
        [Parameter(Mandatory=$true)]$After
    )

    $beforeValidation = Test-AriaGraph $Before
    $afterValidation = Test-AriaGraph $After
    $errors = @($beforeValidation.errors) + @($afterValidation.errors)

    if($errors.Count){
        return [pscustomobject][ordered]@{
            valid = $false
            errors = @($errors)
            beforeDigest = $beforeValidation.digest
            afterDigest = $afterValidation.digest
            nodes = $null
            edges = $null
            changed = $false
        }
    }

    $beforeNodes = Get-AriaObjectMap -Items $Before.nodes
    $afterNodes = Get-AriaObjectMap -Items $After.nodes
    $beforeEdges = Get-AriaObjectMap -Items $Before.edges
    $afterEdges = Get-AriaObjectMap -Items $After.edges

    function Compare-Map($Left,$Right){
        $added = New-Object 'System.Collections.Generic.List[object]'
        $removed = New-Object 'System.Collections.Generic.List[object]'
        $modified = New-Object 'System.Collections.Generic.List[object]'

        foreach($id in @($Right.Keys | Sort-Object)){
            if(-not$Left.ContainsKey($id)){
                [void]$added.Add($Right[$id])
                continue
            }

            $leftCanonical = ConvertTo-AriaStableJson $Left[$id]
            $rightCanonical = ConvertTo-AriaStableJson $Right[$id]
            if($leftCanonical -cne $rightCanonical){
                [void]$modified.Add([pscustomobject][ordered]@{
                    id = $id
                    before = $Left[$id]
                    after = $Right[$id]
                })
            }
        }

        foreach($id in @($Left.Keys | Sort-Object)){
            if(-not$Right.ContainsKey($id)){
                [void]$removed.Add($Left[$id])
            }
        }

        [pscustomobject][ordered]@{
            added = @($added.ToArray())
            removed = @($removed.ToArray())
            modified = @($modified.ToArray())
        }
    }

    $nodes = Compare-Map $beforeNodes $afterNodes
    $edges = Compare-Map $beforeEdges $afterEdges
    $changed = (
        @($nodes.added).Count +
        @($nodes.removed).Count +
        @($nodes.modified).Count +
        @($edges.added).Count +
        @($edges.removed).Count +
        @($edges.modified).Count
    ) -gt 0

    [pscustomobject][ordered]@{
        valid = $true
        errors = @()
        beforeDigest = $beforeValidation.digest
        afterDigest = $afterValidation.digest
        nodes = $nodes
        edges = $edges
        changed = $changed
    }
}

function New-AriaGraphTransition {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][int]$Sequence,
        [Parameter(Mandatory=$true)][string]$Parent,
        [Parameter(Mandatory=$true)]$BeforeGraph,
        [Parameter(Mandatory=$true)]$Rule,
        [string[]]$GrantedCapabilities = @()
    )

    $result = Invoke-AriaGraphRewrite `
        -Graph $BeforeGraph `
        -Rule $Rule `
        -GrantedCapabilities $GrantedCapabilities

    if(-not[bool]$result.committed){
        return [pscustomobject][ordered]@{
            committed = $false
            errors = @($result.errors)
            reason = [string]$result.reason
            transition = $null
            graph = $BeforeGraph
        }
    }

    $identity = [ordered]@{
        schema = 'aria.graph-transition/0.4'
        sequence = $Sequence
        parent = $Parent
        rule = $Rule
        grantedCapabilities = @($GrantedCapabilities | Sort-Object -Unique)
        beforeDigest = [string]$result.beforeDigest
        afterDigest = [string]$result.afterDigest
        semanticDiff = Compare-AriaGraphSemantic -Before $BeforeGraph -After $result.graph
    }

    $digest = Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity)
    $transition = [pscustomobject][ordered]@{
        schema = $identity.schema
        sequence = $identity.sequence
        parent = $identity.parent
        rule = $identity.rule
        grantedCapabilities = @($identity.grantedCapabilities)
        beforeDigest = $identity.beforeDigest
        afterDigest = $identity.afterDigest
        semanticDiff = $identity.semanticDiff
        id = "sha256:$digest"
    }

    [pscustomobject][ordered]@{
        committed = $true
        errors = @()
        reason = 'committed'
        transition = $transition
        graph = $result.graph
    }
}

function Test-AriaGraphTransition {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Transition)

    $errors = New-Object 'System.Collections.Generic.List[object]'

    if([string]$Transition.schema -ne 'aria.graph-transition/0.4'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_REPLAY_SCHEMA' `
            -Message 'Unsupported graph transition schema.' `
            -Path '$.schema'))
    }

    if([int]$Transition.sequence -lt 1){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_REPLAY_SEQUENCE' `
            -Message 'Graph transition sequence must be positive.' `
            -Path '$.sequence'))
    }

    if([string]::IsNullOrWhiteSpace([string]$Transition.parent)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_REPLAY_PARENT' `
            -Message 'Graph transition parent identity is required.' `
            -Path '$.parent'))
    }

    $identity = [ordered]@{
        schema = $Transition.schema
        sequence = $Transition.sequence
        parent = $Transition.parent
        rule = $Transition.rule
        grantedCapabilities = @($Transition.grantedCapabilities)
        beforeDigest = $Transition.beforeDigest
        afterDigest = $Transition.afterDigest
        semanticDiff = $Transition.semanticDiff
    }

    $expected = "sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string]$Transition.id -cne $expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_REPLAY_IDENTITY' `
            -Message 'Graph transition identity mismatch.' `
            -Path '$.id' `
            -Evidence @{ expected=$expected; actual=[string]$Transition.id }))
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray())
        expectedId = $expected
    }
}

function Test-AriaGraphTransitionChain {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$InitialGraphDigest,
        [object[]]$Transitions = @()
    )

    $errors = New-Object 'System.Collections.Generic.List[object]'
    $expectedParent = "sha256:$InitialGraphDigest"
    $expectedBefore = $InitialGraphDigest
    $expectedSequence = 1

    foreach($transition in @($Transitions)){
        $validation = Test-AriaGraphTransition $transition
        foreach($error in @($validation.errors)){[void]$errors.Add($error)}

        if([int]$transition.sequence -ne $expectedSequence){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_REPLAY_CHAIN_SEQUENCE' `
                -Message "Expected sequence $expectedSequence." `
                -Path '$.sequence'))
        }

        if([string]$transition.parent -cne $expectedParent){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_REPLAY_CHAIN_PARENT' `
                -Message 'Transition parent does not match prior identity.' `
                -Path '$.parent'))
        }

        if([string]$transition.beforeDigest -cne $expectedBefore){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_REPLAY_CHAIN_DIGEST' `
                -Message 'Transition before digest does not match prior graph state.' `
                -Path '$.beforeDigest'))
        }

        $expectedParent = [string]$transition.id
        $expectedBefore = [string]$transition.afterDigest
        $expectedSequence++
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray())
        head = $expectedParent
        finalDigest = $expectedBefore
        count = @($Transitions).Count
    }
}

function Invoke-AriaGraphReplay {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$InitialGraph,
        [object[]]$Transitions = @(),
        [int]$UntilSequence = [int]::MaxValue
    )

    $initialValidation = Test-AriaGraph $InitialGraph
    if(-not[bool]$initialValidation.valid){
        return [pscustomobject][ordered]@{
            valid = $false
            errors = @($initialValidation.errors)
            graph = $InitialGraph
            digest = $initialValidation.digest
            applied = 0
        }
    }

    $chain = Test-AriaGraphTransitionChain `
        -InitialGraphDigest $initialValidation.digest `
        -Transitions $Transitions

    if(-not[bool]$chain.valid){
        return [pscustomobject][ordered]@{
            valid = $false
            errors = @($chain.errors)
            graph = $InitialGraph
            digest = $initialValidation.digest
            applied = 0
        }
    }

    $graph = Copy-AriaGraph $InitialGraph
    $applied = 0

    foreach($transition in @($Transitions | Sort-Object sequence)){
        if([int]$transition.sequence -gt $UntilSequence){break}

        $beforeDigest = Get-AriaGraphDigest $graph
        if($beforeDigest -cne [string]$transition.beforeDigest){
            return [pscustomobject][ordered]@{
                valid = $false
                errors = @(New-AriaStructuredError `
                    -Code 'E_REPLAY_STATE' `
                    -Message 'Replay state diverged before transition.' `
                    -Path '$.beforeDigest')
                graph = $graph
                digest = $beforeDigest
                applied = $applied
            }
        }

        $result = Invoke-AriaGraphRewrite `
            -Graph $graph `
            -Rule $transition.rule `
            -GrantedCapabilities @($transition.grantedCapabilities)

        if(-not[bool]$result.committed){
            return [pscustomobject][ordered]@{
                valid = $false
                errors = @($result.errors)
                graph = $graph
                digest = $beforeDigest
                applied = $applied
            }
        }

        if([string]$result.afterDigest -cne [string]$transition.afterDigest){
            return [pscustomobject][ordered]@{
                valid = $false
                errors = @(New-AriaStructuredError `
                    -Code 'E_REPLAY_DIVERGENCE' `
                    -Message 'Replay output digest does not match recorded transition.' `
                    -Path '$.afterDigest' `
                    -Evidence @{expected=[string]$transition.afterDigest;actual=[string]$result.afterDigest})
                graph = $graph
                digest = $beforeDigest
                applied = $applied
            }
        }

        $graph = $result.graph
        $applied++
    }

    [pscustomobject][ordered]@{
        valid = $true
        errors = @()
        graph = $graph
        digest = Get-AriaGraphDigest $graph
        applied = $applied
    }
}

function Get-AriaGraphStateAt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$InitialGraph,
        [object[]]$Transitions = @(),
        [Parameter(Mandatory=$true)][ValidateRange(0,[int]::MaxValue)][int]$Sequence
    )

    Invoke-AriaGraphReplay `
        -InitialGraph $InitialGraph `
        -Transitions $Transitions `
        -UntilSequence $Sequence
}

Export-ModuleMember -Function `
    Compare-AriaGraphSemantic, `
    New-AriaGraphTransition, `
    Test-AriaGraphTransition, `
    Test-AriaGraphTransitionChain, `
    Invoke-AriaGraphReplay, `
    Get-AriaGraphStateAt