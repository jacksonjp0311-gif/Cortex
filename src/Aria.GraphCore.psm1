Set-StrictMode -Version Latest

$typedCorePath = Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if (-not (Get-Module Aria.TypedCore)) {
    Import-Module $typedCorePath -DisableNameChecking
}

function New-AriaGraphSchema {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string[]]$NodeTypes,
        [Parameter(Mandatory=$true)][object[]]$EdgeTypes
    )

    [pscustomobject][ordered]@{
        schema = 'aria.graph-schema/0.3'
        nodeTypes = @($NodeTypes | Sort-Object -Unique)
        edgeTypes = @($EdgeTypes | Sort-Object name)
    }
}

function New-AriaGraph {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Schema,
        [object[]]$Nodes = @(),
        [object[]]$Edges = @()
    )

    [pscustomobject][ordered]@{
        schema = $Schema
        nodes = @($Nodes)
        edges = @($Edges)
    }
}

function Copy-AriaGraph {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Graph)

    $json = ConvertTo-AriaStableJson $Graph
    $json | ConvertFrom-Json
}

function Get-AriaGraphDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Graph)

    Get-AriaSha256Hex (ConvertTo-AriaStableJson $Graph)
}

function Get-AriaGraphNode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)][string]$Id
    )

    @($Graph.nodes | Where-Object { [string]$_.id -ceq $Id }) | Select-Object -First 1
}

function Get-AriaGraphEdgeSchema {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Schema,
        [Parameter(Mandatory=$true)][string]$Name
    )

    @($Schema.edgeTypes | Where-Object { [string]$_.name -ceq $Name }) | Select-Object -First 1
}

function Test-AriaGraph {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Graph)

    $errors = New-Object 'System.Collections.Generic.List[object]'
    $nodeIds = @{}

    foreach($node in @($Graph.nodes)){
        if([string]::IsNullOrWhiteSpace([string]$node.id)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_GRAPH_NODE_ID' -Message 'Graph node id is required.' -Path '$.nodes'))
            continue
        }

        if($nodeIds.ContainsKey([string]$node.id)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_NODE_DUPLICATE' `
                -Message "Duplicate node id '$($node.id)'." `
                -Path '$.nodes'))
        }
        else{
            $nodeIds[[string]$node.id] = $node
        }

        if([string]$node.type -notin @($Graph.schema.nodeTypes)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_NODE_TYPE' `
                -Message "Unknown node type '$($node.type)'." `
                -Path ("$.nodes.{0}.type" -f $node.id)))
        }
    }

    $edgeIds = @{}
    foreach($edge in @($Graph.edges)){
        if([string]::IsNullOrWhiteSpace([string]$edge.id)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_GRAPH_EDGE_ID' -Message 'Graph edge id is required.' -Path '$.edges'))
            continue
        }

        if($edgeIds.ContainsKey([string]$edge.id)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_EDGE_DUPLICATE' `
                -Message "Duplicate edge id '$($edge.id)'." `
                -Path '$.edges'))
        }
        else{
            $edgeIds[[string]$edge.id] = $true
        }

        $source = if($nodeIds.ContainsKey([string]$edge.source)){$nodeIds[[string]$edge.source]}else{$null}
        $target = if($nodeIds.ContainsKey([string]$edge.target)){$nodeIds[[string]$edge.target]}else{$null}

        if($null-eq$source -or $null-eq$target){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_EDGE_DANGLING' `
                -Message "Edge '$($edge.id)' references a missing node." `
                -Path ("$.edges.{0}" -f $edge.id)))
            continue
        }

        $edgeSchema = Get-AriaGraphEdgeSchema -Schema $Graph.schema -Name ([string]$edge.type)
        if($null-eq$edgeSchema){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_EDGE_TYPE' `
                -Message "Unknown edge type '$($edge.type)'." `
                -Path ("$.edges.{0}.type" -f $edge.id)))
            continue
        }

        if([string]$source.type -ne [string]$edgeSchema.sourceType -or
           [string]$target.type -ne [string]$edgeSchema.targetType){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_EDGE_ENDPOINT' `
                -Message "Edge '$($edge.id)' violates endpoint typing." `
                -Path ("$.edges.{0}" -f $edge.id) `
                -Evidence @{
                    expected = "$($edgeSchema.sourceType)->$($edgeSchema.targetType)"
                    actual = "$($source.type)->$($target.type)"
                }))
        }
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray())
        digest = Get-AriaGraphDigest $Graph
    }
}

function Test-AriaPatternPredicate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Value,
        [object]$Predicate = $null
    )

    if($null-eq$Predicate){return $true}

    if($Predicate-is[Collections.IDictionary]){
        foreach($key in @($Predicate.Keys)){
            $property = $Value.PSObject.Properties[[string]$key]
            if($null-eq$property){return $false}
            if([string]$property.Value -cne [string]$Predicate[$key]){return $false}
        }
        return $true
    }

    foreach($predicateProperty in @($Predicate.PSObject.Properties)){
        $property = $Value.PSObject.Properties[[string]$predicateProperty.Name]
        if($null-eq$property){return $false}
        if([string]$property.Value -cne [string]$predicateProperty.Value){return $false}
    }

    return $true
}

function Find-AriaGraphMatches {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)]$Pattern
    )

    $matches = New-Object 'System.Collections.Generic.List[object]'

    foreach($edge in @($Graph.edges)){
        if([string]$edge.type -cne [string]$Pattern.edgeType){continue}

        $source = Get-AriaGraphNode -Graph $Graph -Id ([string]$edge.source)
        $target = Get-AriaGraphNode -Graph $Graph -Id ([string]$edge.target)
        if($null-eq$source -or $null-eq$target){continue}

        if([string]$source.type -cne [string]$Pattern.sourceType){continue}
        if([string]$target.type -cne [string]$Pattern.targetType){continue}
        if(-not(Test-AriaPatternPredicate -Value $source -Predicate $Pattern.sourceWhere)){continue}
        if(-not(Test-AriaPatternPredicate -Value $target -Predicate $Pattern.targetWhere)){continue}

        [void]$matches.Add([pscustomobject][ordered]@{
            source = $source
            edge = $edge
            target = $target
        })
    }

    @($matches.ToArray())
}

function Get-AriaBoundValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Match,
        [Parameter(Mandatory=$true)][string]$Path
    )

    $segments = $Path -split '\.'
    if($segments.Count -lt 1){return $null}

    $cursor = $Match.PSObject.Properties[$segments[0]].Value
    for($index=1;$index-lt$segments.Count;$index++){
        if($null-eq$cursor){return $null}
        $property = $cursor.PSObject.Properties[$segments[$index]]
        if($null-eq$property){return $null}
        $cursor = $property.Value
    }

    return $cursor
}

function Test-AriaGraphGuard {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Guard,
        [Parameter(Mandatory=$true)]$Match
    )

    if([string]$Guard.kind -ne 'eq'){
        return [pscustomobject][ordered]@{
            valid = $false
            value = $false
            error = New-AriaStructuredError -Code 'E_GRAPH_GUARD_KIND' -Message "Unsupported guard '$($Guard.kind)'." -Path '$.guard'
        }
    }

    $left = Get-AriaBoundValue -Match $Match -Path ([string]$Guard.left)
    $right = $Guard.right

    [pscustomobject][ordered]@{
        valid = $true
        value = ([string]$left -ceq [string]$right)
        error = $null
    }
}

function Test-AriaGraphRule {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Rule,
        [string[]]$GrantedCapabilities = @()
    )

    $errors = New-Object 'System.Collections.Generic.List[object]'

    if([string]$Rule.schema -ne 'aria.graph-rule/0.3'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_GRAPH_RULE_SCHEMA' -Message 'Unsupported graph rule schema.' -Path '$.schema'))
    }

    if([string]::IsNullOrWhiteSpace([string]$Rule.name)){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_GRAPH_RULE_NAME' -Message 'Graph rule name is required.' -Path '$.name'))
    }

    if([string]$Rule.guard.kind -ne 'eq'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_GRAPH_GUARD_KIND' -Message 'Only equality guards are supported in alpha.17.' -Path '$.guard'))
    }

    foreach($capability in @($Rule.capabilities)){
        if([string]$capability -notin @($GrantedCapabilities)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_CAPABILITY' `
                -Message "Graph rule '$($Rule.name)' requires '$capability'." `
                -Path '$.capabilities'))
        }
    }

    foreach($operation in @($Rule.rewrite)){
        if([string]$operation.op -notin @('remove.edge','add.edge')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_GRAPH_REWRITE_OP' `
                -Message "Unsupported graph rewrite operation '$($operation.op)'." `
                -Path '$.rewrite'))
        }
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray())
    }
}

function Resolve-AriaTemplateValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Match,
        [Parameter(Mandatory=$true)]$Value
    )

    if($Value-is[string] -and $Value.StartsWith('$')){
        return Get-AriaBoundValue -Match $Match -Path $Value.Substring(1)
    }

    return $Value
}

function Invoke-AriaGraphRewrite {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)]$Rule,
        [string[]]$GrantedCapabilities = @()
    )

    $beforeValidation = Test-AriaGraph $Graph
    if(-not[bool]$beforeValidation.valid){
        return [pscustomobject][ordered]@{
            committed = $false
            rejected = $true
            reason = 'input-invalid'
            errors = @($beforeValidation.errors)
            graph = $Graph
            beforeDigest = $beforeValidation.digest
            afterDigest = $beforeValidation.digest
            event = $null
        }
    }

    $ruleValidation = Test-AriaGraphRule -Rule $Rule -GrantedCapabilities $GrantedCapabilities
    if(-not[bool]$ruleValidation.valid){
        return [pscustomobject][ordered]@{
            committed = $false
            rejected = $true
            reason = 'rule-invalid'
            errors = @($ruleValidation.errors)
            graph = $Graph
            beforeDigest = $beforeValidation.digest
            afterDigest = $beforeValidation.digest
            event = $null
        }
    }

    $matches = @(Find-AriaGraphMatches -Graph $Graph -Pattern $Rule.pattern)
    if($matches.Count -eq 0){
        return [pscustomobject][ordered]@{
            committed = $false
            rejected = $true
            reason = 'no-match'
            errors = @()
            graph = $Graph
            beforeDigest = $beforeValidation.digest
            afterDigest = $beforeValidation.digest
            event = $null
        }
    }

    $match = $matches[0]
    $guard = Test-AriaGraphGuard -Guard $Rule.guard -Match $match
    if(-not[bool]$guard.valid -or -not[bool]$guard.value){
        return [pscustomobject][ordered]@{
            committed = $false
            rejected = $true
            reason = 'guard-false'
            errors = if($null-ne$guard.error){@($guard.error)}else{@()}
            graph = $Graph
            beforeDigest = $beforeValidation.digest
            afterDigest = $beforeValidation.digest
            event = $null
        }
    }

    $candidate = Copy-AriaGraph $Graph

    foreach($operation in @($Rule.rewrite)){
        if([string]$operation.op -eq 'remove.edge'){
            $edgeId = [string](Resolve-AriaTemplateValue -Match $match -Value $operation.id)
            $candidate.edges = @($candidate.edges | Where-Object { [string]$_.id -cne $edgeId })
        }
        elseif([string]$operation.op -eq 'add.edge'){
            $edge = [pscustomobject][ordered]@{
                id = [string](Resolve-AriaTemplateValue -Match $match -Value $operation.id)
                type = [string](Resolve-AriaTemplateValue -Match $match -Value $operation.type)
                source = [string](Resolve-AriaTemplateValue -Match $match -Value $operation.source)
                target = [string](Resolve-AriaTemplateValue -Match $match -Value $operation.target)
            }
            $candidate.edges = @($candidate.edges) + @($edge)
        }
    }

    $afterValidation = Test-AriaGraph $candidate
    if(-not[bool]$afterValidation.valid){
        return [pscustomobject][ordered]@{
            committed = $false
            rejected = $true
            reason = 'result-invalid'
            errors = @($afterValidation.errors)
            graph = $Graph
            beforeDigest = $beforeValidation.digest
            afterDigest = $beforeValidation.digest
            event = $null
        }
    }

    $eventIdentity = [ordered]@{
        type = 'aria.graph.rewrite.committed'
        rule = [string]$Rule.name
        beforeDigest = [string]$beforeValidation.digest
        afterDigest = [string]$afterValidation.digest
        capabilities = @($Rule.capabilities)
        matchedNodes = @([string]$match.source.id,[string]$match.target.id)
    }
    $eventDigest = Get-AriaSha256Hex (ConvertTo-AriaStableJson $eventIdentity)
    $event = [pscustomobject][ordered]@{
        type = $eventIdentity.type
        rule = $eventIdentity.rule
        beforeDigest = $eventIdentity.beforeDigest
        afterDigest = $eventIdentity.afterDigest
        capabilities = @($eventIdentity.capabilities)
        matchedNodes = @($eventIdentity.matchedNodes)
        transaction = "sha256:$eventDigest"
    }

    [pscustomobject][ordered]@{
        committed = $true
        rejected = $false
        reason = 'committed'
        errors = @()
        graph = $candidate
        beforeDigest = $beforeValidation.digest
        afterDigest = $afterValidation.digest
        event = $event
    }
}

function Invoke-AriaGraphRewriteBuffered {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)]$Rule,
        [string[]]$GrantedCapabilities = @()
    )

    $displayPath = Join-Path $PSScriptRoot 'Aria.Display.psm1'
    if(Test-Path $displayPath){
        Import-Module $displayPath -Force -DisableNameChecking
    }

    $bufferCommand = Get-Command Invoke-AriaBufferedItem -ErrorAction SilentlyContinue
    if($null-eq$bufferCommand){
        return Invoke-AriaGraphRewrite -Graph $Graph -Rule $Rule -GrantedCapabilities $GrantedCapabilities
    }

    $result = Invoke-AriaBufferedItem `
        -Name ("graph.rewrite.{0}" -f $Rule.name) `
        -Mode runtime `
        -Action {
            ConvertTo-AriaStableJson (Invoke-AriaGraphRewrite -Graph $Graph -Rule $Rule -GrantedCapabilities $GrantedCapabilities)
        }

    $result.output | ConvertFrom-Json
}

Export-ModuleMember -Function `
    New-AriaGraphSchema, `
    New-AriaGraph, `
    Copy-AriaGraph, `
    Get-AriaGraphDigest, `
    Get-AriaGraphNode, `
    Get-AriaGraphEdgeSchema, `
    Test-AriaGraph, `
    Find-AriaGraphMatches, `
    Test-AriaGraphGuard, `
    Test-AriaGraphRule, `
    Invoke-AriaGraphRewrite, `
    Invoke-AriaGraphRewriteBuffered