Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-AriaEffectProperty {
    param(
        [Parameter(Mandatory=$true)]$Object,
        [Parameter(Mandatory=$true)][string]$Name
    )

    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Sort-AriaEffectStringsOrdinal {
    param([AllowEmptyCollection()][object[]]$Values = @())

    [string[]]$items = @(
        @($Values) |
            ForEach-Object { [string]$_ } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )

    [Array]::Sort($items,[StringComparer]::Ordinal)
    $result = New-Object System.Collections.Generic.List[string]
    $hasPrevious = $false
    $previous = ''

    foreach ($item in $items) {
        if (
            -not $hasPrevious -or
            -not [string]::Equals(
                $previous,
                $item,
                [StringComparison]::Ordinal
            )
        ) {
            $result.Add($item)
            $previous = $item
            $hasPrevious = $true
        }
    }

    return $result.ToArray()
}

function Add-AriaEffectSetValue {
    param(
        [Parameter(Mandatory=$true)][hashtable]$Set,
        [AllowEmptyString()][string]$Value
    )

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $Set[$Value] = $true
    }
}

function Add-AriaExpressionEffectCalls {
    param(
        $Expression,
        [Parameter(Mandatory=$true)][hashtable]$Calls
    )

    if ($null -eq $Expression) { return }

    switch ([string]$Expression.kind) {
        'call' {
            Add-AriaEffectSetValue -Set $Calls -Value ([string]$Expression.name)
            foreach ($argument in @($Expression.arguments)) {
                Add-AriaExpressionEffectCalls -Expression $argument -Calls $Calls
            }
        }
        'map' {
            Add-AriaEffectSetValue -Set $Calls -Value ([string]$Expression.transform)
            Add-AriaExpressionEffectCalls -Expression $Expression.sequence -Calls $Calls
        }
        'filter' {
            Add-AriaEffectSetValue -Set $Calls -Value ([string]$Expression.predicate)
            Add-AriaExpressionEffectCalls -Expression $Expression.sequence -Calls $Calls
        }
        'reduce' {
            Add-AriaEffectSetValue -Set $Calls -Value ([string]$Expression.reducer)
            Add-AriaExpressionEffectCalls -Expression $Expression.sequence -Calls $Calls
            Add-AriaExpressionEffectCalls -Expression $Expression.initial -Calls $Calls
        }
        'sequence' {
            foreach ($element in @($Expression.elements)) {
                Add-AriaExpressionEffectCalls -Expression $element -Calls $Calls
            }
        }
        'unary' {
            Add-AriaExpressionEffectCalls -Expression $Expression.operand -Calls $Calls
        }
        'binary' {
            Add-AriaExpressionEffectCalls -Expression $Expression.left -Calls $Calls
            Add-AriaExpressionEffectCalls -Expression $Expression.right -Calls $Calls
        }
    }
}

function Add-AriaSourceStatementEffectFacts {
    param(
        [AllowEmptyCollection()][object[]]$Statements,
        [Parameter(Mandatory=$true)][hashtable]$Calls,
        [Parameter(Mandatory=$true)][hashtable]$Effects,
        [Parameter(Mandatory=$true)][hashtable]$Capabilities
    )

    foreach ($statement in @($Statements)) {
        switch ([string]$statement.op) {
            'emit' {
                Add-AriaEffectSetValue $Effects 'console.emit'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'signal' {
                Add-AriaEffectSetValue $Effects 'console.emit'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'let' { Add-AriaExpressionEffectCalls $statement.expression $Calls }
            'set' { Add-AriaExpressionEffectCalls $statement.expression $Calls }
            'remember' {
                Add-AriaEffectSetValue $Effects 'memory.write'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'recall' { Add-AriaEffectSetValue $Effects 'memory.read' }
            'require' {
                Add-AriaEffectSetValue `
                    -Set $Capabilities `
                    -Value ([string]$statement.capability)
            }
            'assert' { Add-AriaExpressionEffectCalls $statement.expression $Calls }
            'read' {
                Add-AriaEffectSetValue $Effects 'fs.read'
                Add-AriaExpressionEffectCalls $statement.path $Calls
            }
            'write' {
                Add-AriaEffectSetValue $Effects 'fs.write'
                Add-AriaExpressionEffectCalls $statement.path $Calls
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'dispatch' {
                Add-AriaEffectSetValue $Effects 'agent.dispatch'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'connect' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'intent' {
                Add-AriaEffectSetValue $Effects 'console.emit'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'propose' {
                Add-AriaEffectSetValue $Effects 'console.emit'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'consent' {
                Add-AriaEffectSetValue $Effects 'console.emit'
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
            'disconnect' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'if' {
                Add-AriaExpressionEffectCalls $statement.condition $Calls
                Add-AriaSourceStatementEffectFacts `
                    -Statements @($statement.then) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
                Add-AriaSourceStatementEffectFacts `
                    -Statements @($statement.else) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
            }
            'repeat' {
                Add-AriaExpressionEffectCalls $statement.count $Calls
                Add-AriaSourceStatementEffectFacts `
                    -Statements @($statement.body) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
            }
            'return' {
                Add-AriaExpressionEffectCalls $statement.expression $Calls
            }
        }
    }
}

function Add-AriaBytecodeInstructionEffectFacts {
    param(
        [AllowEmptyCollection()][object[]]$Instructions,
        [Parameter(Mandatory=$true)][hashtable]$Calls,
        [Parameter(Mandatory=$true)][hashtable]$Effects,
        [Parameter(Mandatory=$true)][hashtable]$Capabilities
    )

    foreach ($instruction in @($Instructions)) {
        switch ([string]$instruction.op) {
            'EMIT' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'SIGNAL' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'MEM_SET' { Add-AriaEffectSetValue $Effects 'memory.write' }
            'MEM_GET' { Add-AriaEffectSetValue $Effects 'memory.read' }
            'FS_READ' { Add-AriaEffectSetValue $Effects 'fs.read' }
            'FS_WRITE' { Add-AriaEffectSetValue $Effects 'fs.write' }
            'AGENT_DISPATCH' { Add-AriaEffectSetValue $Effects 'agent.dispatch' }
            'CONNECT_OPEN' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'CONNECT_INTENT' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'CONNECT_PROPOSE' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'CONNECT_CONSENT' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'CONNECT_CLOSE' { Add-AriaEffectSetValue $Effects 'console.emit' }
            'REQUIRE_CAP' {
                Add-AriaEffectSetValue `
                    -Set $Capabilities `
                    -Value ([string]$instruction.arg)
            }
            'CALL' {
                Add-AriaEffectSetValue `
                    -Set $Calls `
                    -Value ([string]$instruction.name)
            }
            'MAP' {
                Add-AriaEffectSetValue `
                    -Set $Calls `
                    -Value ([string]$instruction.transform)
            }
            'FILTER' {
                Add-AriaEffectSetValue `
                    -Set $Calls `
                    -Value ([string]$instruction.predicate)
            }
            'REDUCE' {
                Add-AriaEffectSetValue `
                    -Set $Calls `
                    -Value ([string]$instruction.reducer)
            }
            'IF' {
                Add-AriaBytecodeInstructionEffectFacts `
                    -Instructions @($instruction.then) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
                Add-AriaBytecodeInstructionEffectFacts `
                    -Instructions @($instruction.else) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
            }
            'REPEAT' {
                Add-AriaBytecodeInstructionEffectFacts `
                    -Instructions @($instruction.body) `
                    -Calls $Calls `
                    -Effects $Effects `
                    -Capabilities $Capabilities
            }
        }
    }
}

function Test-AriaEffectRecursion {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][hashtable]$Facts
    )

    if (-not $Facts.ContainsKey($Name)) { return $false }

    $stack = New-Object System.Collections.Stack
    foreach ($call in @($Facts[$Name].calls)) { $stack.Push([string]$call) }
    $visited = @{}

    while ($stack.Count -gt 0) {
        $current = [string]$stack.Pop()
        if ($current -eq $Name) { return $true }
        if ($visited.ContainsKey($current)) { continue }
        $visited[$current] = $true
        if (-not $Facts.ContainsKey($current)) { continue }
        foreach ($call in @($Facts[$current].calls)) {
            $stack.Push([string]$call)
        }
    }

    return $false
}

function ConvertTo-AriaEffectSummaryCanonicalBody {
    param([Parameter(Mandatory=$true)]$Summary)

    return [pscustomobject][ordered]@{
        format = [string](Get-AriaEffectProperty $Summary 'format')
        version = [int](Get-AriaEffectProperty $Summary 'version')
        name = [string](Get-AriaEffectProperty $Summary 'name')
        calls = @(Sort-AriaEffectStringsOrdinal @(Get-AriaEffectProperty $Summary 'calls'))
        directEffects = @(
            Sort-AriaEffectStringsOrdinal `
                @(Get-AriaEffectProperty $Summary 'directEffects')
        )
        directCapabilities = @(
            Sort-AriaEffectStringsOrdinal `
                @(Get-AriaEffectProperty $Summary 'directCapabilities')
        )
        transitiveEffects = @(
            Sort-AriaEffectStringsOrdinal `
                @(Get-AriaEffectProperty $Summary 'transitiveEffects')
        )
        transitiveCapabilities = @(
            Sort-AriaEffectStringsOrdinal `
                @(Get-AriaEffectProperty $Summary 'transitiveCapabilities')
        )
        purity = [string](Get-AriaEffectProperty $Summary 'purity')
        recursive = [bool](Get-AriaEffectProperty $Summary 'recursive')
    }
}

function Get-AriaEffectSummaryDigest {
    param([Parameter(Mandatory=$true)]$Summary)

    return 'sha256:' + (
        Get-AriaSha256Text (
            ConvertTo-AriaJson (
                ConvertTo-AriaEffectSummaryCanonicalBody $Summary
            )
        )
    )
}

function ConvertTo-AriaEffectGraphCanonicalBody {
    param([Parameter(Mandatory=$true)]$Graph)

    $values = New-Object System.Collections.Generic.List[object]
    foreach ($summary in @(Get-AriaEffectProperty $Graph 'functions')) {
        $values.Add(
            [pscustomobject][ordered]@{
                body = ConvertTo-AriaEffectSummaryCanonicalBody $summary
                digest = [string](Get-AriaEffectProperty $summary 'digest')
            }
        )
    }

    $sorted = [System.Collections.SortedList]::new(
        [StringComparer]::Ordinal
    )

    foreach ($item in @($values.ToArray())) {
        $sorted.Add([string]$item.body.name,$item)
    }

    return [pscustomobject][ordered]@{
        format = [string](Get-AriaEffectProperty $Graph 'format')
        version = [int](Get-AriaEffectProperty $Graph 'version')
        functions = @($sorted.Values | ForEach-Object { $_ })
    }
}

function Get-AriaEffectGraphDigest {
    param([Parameter(Mandatory=$true)]$Graph)

    return 'sha256:' + (
        Get-AriaSha256Text (
            ConvertTo-AriaJson (
                ConvertTo-AriaEffectGraphCanonicalBody $Graph
            )
        )
    )
}

function New-AriaEffectGraphFromFacts {
    param([AllowEmptyCollection()][object[]]$Facts = @())

    $factsMap = @{}
    foreach ($fact in @($Facts)) {
        $name = [string](Get-AriaEffectProperty $fact 'name')
        if ([string]::IsNullOrWhiteSpace($name)) {
            throw 'Effect fact requires a function name.'
        }
        if ($factsMap.ContainsKey($name)) {
            throw "Duplicate effect fact '$name'."
        }

        $factsMap[$name] = [pscustomobject][ordered]@{
            name = $name
            calls = @(Sort-AriaEffectStringsOrdinal @(Get-AriaEffectProperty $fact 'calls'))
            directEffects = @(
                Sort-AriaEffectStringsOrdinal `
                    @(Get-AriaEffectProperty $fact 'directEffects')
            )
            directCapabilities = @(
                Sort-AriaEffectStringsOrdinal `
                    @(Get-AriaEffectProperty $fact 'directCapabilities')
            )
        }
    }

    [string[]]$names = @($factsMap.Keys | ForEach-Object { [string]$_ })
    [Array]::Sort($names,[StringComparer]::Ordinal)

    $closures = @{}
    foreach ($name in $names) {
        $effectSet = @{}
        $capabilitySet = @{}
        foreach ($effect in @($factsMap[$name].directEffects)) {
            Add-AriaEffectSetValue $effectSet ([string]$effect)
        }
        foreach ($capability in @($factsMap[$name].directCapabilities)) {
            Add-AriaEffectSetValue $capabilitySet ([string]$capability)
        }
        $closures[$name] = [pscustomobject]@{
            effects = $effectSet
            capabilities = $capabilitySet
        }
    }

    $changed = $true
    $pass = 0
    $maxPasses = [Math]::Max(1,($names.Count * 2) + 1)

    while ($changed -and $pass -lt $maxPasses) {
        $changed = $false
        $pass++

        foreach ($name in $names) {
            foreach ($call in @($factsMap[$name].calls)) {
                $callee = [string]$call
                if (-not $closures.ContainsKey($callee)) { continue }

                foreach ($effect in @($closures[$callee].effects.Keys)) {
                    if (-not $closures[$name].effects.ContainsKey([string]$effect)) {
                        $closures[$name].effects[[string]$effect] = $true
                        $changed = $true
                    }
                }

                foreach ($capability in @($closures[$callee].capabilities.Keys)) {
                    if (-not $closures[$name].capabilities.ContainsKey([string]$capability)) {
                        $closures[$name].capabilities[[string]$capability] = $true
                        $changed = $true
                    }
                }
            }
        }
    }

    if ($changed) {
        throw 'Effect closure did not converge within the deterministic bound.'
    }

    $summaries = New-Object System.Collections.Generic.List[object]

    foreach ($name in $names) {
        [string[]]$transitiveEffects = @(
            Sort-AriaEffectStringsOrdinal @($closures[$name].effects.Keys)
        )
        [string[]]$transitiveCapabilities = @(
            Sort-AriaEffectStringsOrdinal @($closures[$name].capabilities.Keys)
        )

        $summary = [pscustomobject][ordered]@{
            format = 'aria.function-effect-summary'
            version = 1
            name = $name
            calls = @($factsMap[$name].calls)
            directEffects = @($factsMap[$name].directEffects)
            directCapabilities = @($factsMap[$name].directCapabilities)
            transitiveEffects = $transitiveEffects
            transitiveCapabilities = $transitiveCapabilities
            purity = $(
                if (
                    $transitiveEffects.Count -eq 0 -and
                    $transitiveCapabilities.Count -eq 0
                ) { 'pure' } else { 'effectful' }
            )
            recursive = [bool](Test-AriaEffectRecursion $name $factsMap)
            digest = ''
        }

        $summary.digest = Get-AriaEffectSummaryDigest $summary
        $summaries.Add($summary)
    }

    $graph = [pscustomobject][ordered]@{
        format = 'aria.effect-graph'
        version = 2
        functions = $summaries.ToArray()
        digest = ''
    }
    $graph.digest = Get-AriaEffectGraphDigest $graph
    return $graph
}

function Get-AriaSourceEffectGraph {
    param(
        [Parameter(Mandatory=$true)]$Model,
        [hashtable]$CapabilityMap = @{}
    )

    $facts = New-Object System.Collections.Generic.List[object]

    $entryFlow = @(
        @($Model.flows) |
            Where-Object { [string]$_.name -eq [string]$Model.entry }
    ) | Select-Object -First 1

    $entryCalls = @{}
    $entryEffects = @{}
    $entryCapabilities = @{}
    if ($null -ne $entryFlow) {
        Add-AriaSourceStatementEffectFacts `
            -Statements @($entryFlow.statements) `
            -Calls $entryCalls `
            -Effects $entryEffects `
            -Capabilities $entryCapabilities
    }

    $facts.Add(
        [pscustomobject][ordered]@{
            name = '$entry'
            calls = @(Sort-AriaEffectStringsOrdinal @($entryCalls.Keys))
            directEffects = @(
                Sort-AriaEffectStringsOrdinal @($entryEffects.Keys)
            )
            directCapabilities = @(
                Sort-AriaEffectStringsOrdinal @($entryCapabilities.Keys)
            )
        }
    )

    foreach ($function in @($Model.functions)) {
        $calls = @{}
        $effects = @{}
        $capabilities = @{}

        Add-AriaSourceStatementEffectFacts `
            -Statements @($function.statements) `
            -Calls $calls `
            -Effects $effects `
            -Capabilities $capabilities

        $facts.Add(
            [pscustomobject][ordered]@{
                name = [string]$function.name
                calls = @(Sort-AriaEffectStringsOrdinal @($calls.Keys))
                directEffects = @(
                    Sort-AriaEffectStringsOrdinal @($effects.Keys)
                )
                directCapabilities = @(
                    Sort-AriaEffectStringsOrdinal @($capabilities.Keys)
                )
            }
        )
    }

    return New-AriaEffectGraphFromFacts -Facts $facts.ToArray()
}

function Get-AriaBytecodeEffectGraph {
    param([Parameter(Mandatory=$true)]$BytecodeModel)

    $facts = New-Object System.Collections.Generic.List[object]

    $entryCalls = @{}
    $entryEffects = @{}
    $entryCapabilities = @{}
    Add-AriaBytecodeInstructionEffectFacts `
        -Instructions @($BytecodeModel.instructions) `
        -Calls $entryCalls `
        -Effects $entryEffects `
        -Capabilities $entryCapabilities

    $facts.Add(
        [pscustomobject][ordered]@{
            name = '$entry'
            calls = @(Sort-AriaEffectStringsOrdinal @($entryCalls.Keys))
            directEffects = @(
                Sort-AriaEffectStringsOrdinal @($entryEffects.Keys)
            )
            directCapabilities = @(
                Sort-AriaEffectStringsOrdinal @($entryCapabilities.Keys)
            )
        }
    )

    foreach ($function in @($BytecodeModel.functions)) {
        $calls = @{}
        $effects = @{}
        $capabilities = @{}

        Add-AriaBytecodeInstructionEffectFacts `
            -Instructions @($function.instructions) `
            -Calls $calls `
            -Effects $effects `
            -Capabilities $capabilities

        $facts.Add(
            [pscustomobject][ordered]@{
                name = [string]$function.name
                calls = @(Sort-AriaEffectStringsOrdinal @($calls.Keys))
                directEffects = @(
                    Sort-AriaEffectStringsOrdinal @($effects.Keys)
                )
                directCapabilities = @(
                    Sort-AriaEffectStringsOrdinal @($capabilities.Keys)
                )
            }
        )
    }

    return New-AriaEffectGraphFromFacts -Facts $facts.ToArray()
}

function Get-AriaEffectSummary {
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)][string]$Name
    )

    $matches = @(
        @(Get-AriaEffectProperty $Graph 'functions') |
            Where-Object {
                [string](Get-AriaEffectProperty $_ 'name') -eq $Name
            }
    )

    if ($matches.Count -ne 1) {
        throw "Expected one effect summary '$Name'; found $($matches.Count)."
    }

    return $matches[0]
}

function Test-AriaEffectGraph {
    param([Parameter(Mandatory=$true)]$Graph)

    $errors = New-Object System.Collections.Generic.List[string]

    if ([string](Get-AriaEffectProperty $Graph 'format') -ne 'aria.effect-graph') {
        $errors.Add('E_EFFECT_GRAPH_FORMAT')
    }
    if ([int](Get-AriaEffectProperty $Graph 'version') -ne 2) {
        $errors.Add('E_EFFECT_GRAPH_VERSION')
    }

    $names = @{}
    $previous = $null

    foreach ($summary in @(Get-AriaEffectProperty $Graph 'functions')) {
        $name = [string](Get-AriaEffectProperty $summary 'name')
        if (
            $name -ne '$entry' -and
            $name -notmatch '^[A-Za-z_][A-Za-z0-9_.]*$'
        ) {
            $errors.Add('E_EFFECT_SUMMARY_NAME')
        }
        if ($names.ContainsKey($name)) {
            $errors.Add('E_EFFECT_SUMMARY_DUPLICATE')
        }
        $names[$name] = $true

        if (
            $null -ne $previous -and
            [string]::CompareOrdinal([string]$previous,$name) -ge 0
        ) {
            $errors.Add('E_EFFECT_GRAPH_ORDER')
        }
        $previous = $name

        if ([string](Get-AriaEffectProperty $summary 'format') -ne 'aria.function-effect-summary') {
            $errors.Add('E_EFFECT_SUMMARY_FORMAT')
        }
        if ([int](Get-AriaEffectProperty $summary 'version') -ne 1) {
            $errors.Add('E_EFFECT_SUMMARY_VERSION')
        }

        $purity = [string](Get-AriaEffectProperty $summary 'purity')
        if ($purity -notin @('pure','effectful')) {
            $errors.Add('E_EFFECT_SUMMARY_PURITY')
        }

        foreach ($propertyName in @(
            'calls',
            'directEffects',
            'directCapabilities',
            'transitiveEffects',
            'transitiveCapabilities'
        )) {
            [string[]]$observed = @(
                @(Get-AriaEffectProperty $summary $propertyName) |
                    ForEach-Object { [string]$_ }
            )
            [string[]]$canonical = @(
                Sort-AriaEffectStringsOrdinal $observed
            )
            if (
                (ConvertTo-AriaJson $observed) -ne
                (ConvertTo-AriaJson $canonical)
            ) {
                $errors.Add('E_EFFECT_SUMMARY_ORDER')
            }
        }

        $effectCount = @(
            Get-AriaEffectProperty $summary 'transitiveEffects'
        ).Count
        $capabilityCount = @(
            Get-AriaEffectProperty $summary 'transitiveCapabilities'
        ).Count
        $expectedPurity = if (
            $effectCount -eq 0 -and
            $capabilityCount -eq 0
        ) { 'pure' } else { 'effectful' }

        if ($purity -ne $expectedPurity) {
            $errors.Add('E_EFFECT_SUMMARY_PURITY_DRIFT')
        }

        try {
            $expectedDigest = Get-AriaEffectSummaryDigest $summary
            if ([string](Get-AriaEffectProperty $summary 'digest') -ne $expectedDigest) {
                $errors.Add('E_EFFECT_SUMMARY_DIGEST')
            }
        }
        catch {
            $errors.Add('E_EFFECT_SUMMARY_DIGEST_CALCULATION')
        }
    }

    foreach ($summary in @(Get-AriaEffectProperty $Graph 'functions')) {
        foreach ($call in @(Get-AriaEffectProperty $summary 'calls')) {
            if (-not $names.ContainsKey([string]$call)) {
                $errors.Add('E_EFFECT_GRAPH_UNKNOWN_CALL')
            }
        }
    }

    try {
        $expectedGraphDigest = Get-AriaEffectGraphDigest $Graph
        if ([string](Get-AriaEffectProperty $Graph 'digest') -ne $expectedGraphDigest) {
            $errors.Add('E_EFFECT_GRAPH_DIGEST')
        }
    }
    catch {
        $errors.Add('E_EFFECT_GRAPH_DIGEST_CALCULATION')
    }

    return [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
    }
}

function Test-AriaEffectGraphEquivalent {
    param(
        [Parameter(Mandatory=$true)]$Left,
        [Parameter(Mandatory=$true)]$Right
    )

    $leftJson = ConvertTo-AriaJson (
        ConvertTo-AriaEffectGraphCanonicalBody $Left
    )
    $rightJson = ConvertTo-AriaJson (
        ConvertTo-AriaEffectGraphCanonicalBody $Right
    )
    return [bool]($leftJson -eq $rightJson)
}

function Format-AriaEffectGraph {
    param([Parameter(Mandatory=$true)]$Graph)

    $validation = Test-AriaEffectGraph $Graph
    if (-not $validation.valid) {
        throw (
            'Cannot format invalid effect graph: ' +
            (@($validation.errors) -join ', ')
        )
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('ARIA EFFECT GRAPH ' + [string]$Graph.digest)

    foreach ($summary in @($Graph.functions)) {
        $effects = if (@($summary.transitiveEffects).Count -eq 0) {
            'none'
        }
        else {
            @($summary.transitiveEffects) -join ','
        }
        $capabilities = if (@($summary.transitiveCapabilities).Count -eq 0) {
            'none'
        }
        else {
            @($summary.transitiveCapabilities) -join ','
        }
        $calls = if (@($summary.calls).Count -eq 0) {
            'none'
        }
        else {
            @($summary.calls) -join ','
        }

        $lines.Add(
            ('{0}  {1}  recursive={2}' -f
                $summary.purity.ToUpperInvariant(),
                $summary.name,
                ([bool]$summary.recursive).ToString().ToLowerInvariant())
        )
        $lines.Add('  calls=' + $calls)
        $lines.Add('  effects=' + $effects)
        $lines.Add('  capabilities=' + $capabilities)
    }

    return $lines -join [Environment]::NewLine
}

Export-ModuleMember -Function `
    Get-AriaEffectProperty, `
    Sort-AriaEffectStringsOrdinal, `
    ConvertTo-AriaEffectSummaryCanonicalBody, `
    Get-AriaEffectSummaryDigest, `
    ConvertTo-AriaEffectGraphCanonicalBody, `
    Get-AriaEffectGraphDigest, `
    New-AriaEffectGraphFromFacts, `
    Get-AriaSourceEffectGraph, `
    Get-AriaBytecodeEffectGraph, `
    Get-AriaEffectSummary, `
    Test-AriaEffectGraph, `
    Test-AriaEffectGraphEquivalent, `
    Format-AriaEffectGraph
