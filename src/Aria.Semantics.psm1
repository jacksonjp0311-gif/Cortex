Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSourceEffectGraph -ErrorAction SilentlyContinue)) {
    Import-Module `
        (Join-Path $PSScriptRoot 'Aria.Effects.psm1') `
        -Force `
        -DisableNameChecking
}
if ($null -eq (Get-Command Get-AriaGlyphCard -ErrorAction SilentlyContinue)) {
    Import-Module `
        (Join-Path $PSScriptRoot 'Aria.GlyphMemory.psm1') `
        -Force `
        -DisableNameChecking
}

function Get-AriaPolicy { param([Parameter(Mandatory=$true)][string]$PolicyPath) return (Read-AriaUtf8Text -Path $PolicyPath | ConvertFrom-Json) }
function Get-AriaPolicyEffect { param([Parameter(Mandatory=$true)]$Policy,[Parameter(Mandatory=$true)][string]$Effect) return ($Policy.effects.PSObject.Properties | Where-Object{$_.Name-eq$Effect}|Select-Object -First 1) }

function Test-AriaPolicyDocument {
    param([Parameter(Mandatory=$true)]$Policy)
    $errors=New-Object System.Collections.Generic.List[string]
    if($null-eq$Policy-or-not($Policy-is[Management.Automation.PSCustomObject])){$errors.Add('Policy document must be a JSON object.');return [pscustomobject]@{valid=$false;errors=$errors.ToArray()}}
    $format=$Policy.PSObject.Properties|Where-Object{$_.Name-eq'format'}|Select-Object -First 1
    $version=$Policy.PSObject.Properties|Where-Object{$_.Name-eq'version'}|Select-Object -First 1
    $default=$Policy.PSObject.Properties|Where-Object{$_.Name-eq'defaultDecision'}|Select-Object -First 1
    $effects=$Policy.PSObject.Properties|Where-Object{$_.Name-eq'effects'}|Select-Object -First 1
    if($null-eq$format-or[string]$format.Value-ne'aria.policy'){$errors.Add("Policy format must be 'aria.policy'.")}
    if($null-eq$version-or-not(Test-AriaSemanticVersion ([string]$version.Value))){$errors.Add('Policy version must be valid Semantic Versioning 2.0.0.')}
    if($null-eq$default-or[string]$default.Value-ne'deny'){$errors.Add("Policy defaultDecision must be 'deny'.")}
    if($null-eq$effects-or$null-eq$effects.Value-or-not($effects.Value-is[Management.Automation.PSCustomObject])){$errors.Add('Policy effects must be a JSON object.');return [pscustomobject]@{valid=$false;errors=$errors.ToArray()}}
    foreach($effectProperty in $effects.Value.PSObject.Properties){
        $name=[string]$effectProperty.Name;$entry=$effectProperty.Value
        if($name-notmatch'^[a-z][a-z0-9.-]*$'){$errors.Add("Policy effect name '$name' is invalid.")}
        if($null-eq$entry-or-not($entry-is[Management.Automation.PSCustomObject])){$errors.Add("Policy effect '$name' must be a JSON object.");continue}
        $allow=$entry.PSObject.Properties|Where-Object{$_.Name-eq'allow'}|Select-Object -First 1
        if($null-eq$allow-or-not($allow.Value-is[bool])){$errors.Add("Policy effect '$name' requires a Boolean allow property.")}
        $max=$entry.PSObject.Properties|Where-Object{$_.Name-eq'maxBytes'}|Select-Object -First 1
        if($null-ne$max-and(-not($max.Value-is[byte]-or$max.Value-is[int16]-or$max.Value-is[int32]-or$max.Value-is[int64])-or[int64]$max.Value-le0)){$errors.Add("Policy effect '$name' maxBytes must be a positive integer.")}
        $roots=$entry.PSObject.Properties|Where-Object{$_.Name-eq'roots'}|Select-Object -First 1
        if($name-in@('fs.read','fs.write')){
            if($null-eq$roots-or$null-eq$roots.Value-or$roots.Value-is[string]-or-not($roots.Value-is[Collections.IEnumerable])){$errors.Add("Policy effect '$name' requires a roots array.");continue}
            $values=@($roots.Value);if($allow-and$allow.Value-is[bool]-and[bool]$allow.Value-and$values.Count-eq0){$errors.Add("Allowed policy effect '$name' requires at least one root.")}
            foreach($value in $values){if(-not($value-is[string])-or[string]::IsNullOrWhiteSpace([string]$value)){$errors.Add("Policy effect '$name' contains a non-string or empty root.");continue};$root=[string]$value;if([IO.Path]::IsPathRooted($root)-or$root-match'(^|[\\/])\.\.([\\/]|$)'){$errors.Add("Policy root '$root' for '$name' must be workspace-relative and cannot contain '..'.")}}
        }
    }
    return [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=$errors.ToArray()}
}

function Get-AriaPolicyMaxBytes { param($Policy,[string]$Effect,[int64]$Default=4194304) $prop=Get-AriaPolicyEffect $Policy $Effect;if($null-eq$prop){return $Default};$max=$prop.Value.PSObject.Properties|Where-Object{$_.Name-eq'maxBytes'}|Select-Object -First 1;if($null-eq$max){return $Default};return [int64]$max.Value }
function Test-AriaPolicyAllowsCapability {
    param($Policy,$Capability)
    $effect=[string]$Capability.effect;$prop=Get-AriaPolicyEffect $Policy $effect
    if($null-eq$prop){return [pscustomobject]@{allowed=$false;reason="Policy does not define effect '$effect'."}}
    $allow=$prop.Value.PSObject.Properties|Where-Object{$_.Name-eq'allow'}|Select-Object -First 1
    if($null-eq$allow-or-not($allow.Value-is[bool])){return [pscustomobject]@{allowed=$false;reason="Policy effect '$effect' has a malformed allow property."}}
    if(-not[bool]$allow.Value){return [pscustomobject]@{allowed=$false;reason="Policy denies effect '$effect'."}}
    if($effect-in@('fs.read','fs.write')){
        $roots=@($prop.Value.roots);if($roots.Count-eq0){return [pscustomobject]@{allowed=$false;reason="Policy defines no roots for '$effect'."}}
        $scope=([string]$Capability.scope).Replace([char]92,[char]47).TrimEnd([char]47);if(-not$scope){$scope='.'};$ok=$false
        foreach($value in $roots){$root=([string]$value).Replace([char]92,[char]47).TrimEnd([char]47);if(-not$root){$root='.'};$comparison=if([Environment]::OSVersion.Platform-eq[PlatformID]::Win32NT){[StringComparison]::OrdinalIgnoreCase}else{[StringComparison]::Ordinal};if($root-eq'.'-or[string]::Equals($scope,$root,$comparison)-or$scope.StartsWith(($root+'/'),$comparison)){$ok=$true}}
        if(-not$ok){return [pscustomobject]@{allowed=$false;reason="Capability scope '$($Capability.scope)' is outside policy roots."}}
    }
    return [pscustomobject]@{allowed=$true;reason='allowed'}
}
function Test-AriaPolicyAllowsEffect { param($Policy,[string]$Effect,[string]$Scope='.') return (Test-AriaPolicyAllowsCapability $Policy ([pscustomobject]@{effect=$Effect;scope=$Scope})) }
function Get-AriaGlyphRegistry { $path=Join-Path (Get-AriaRepositoryRoot) 'grammar/glyphs.json';$doc=Read-AriaUtf8Text $path|ConvertFrom-Json;if([string]$doc.format-ne'aria.glyph-registry'){throw 'ARIA glyph registry has an invalid format.'};$registry=[ordered]@{};$symbols=@{};foreach($glyph in @($doc.glyphs)){$id=[string]$glyph.id;$symbol=[string]$glyph.symbol;if([string]::IsNullOrWhiteSpace($id)-or[string]::IsNullOrWhiteSpace($symbol)){throw 'ARIA glyph registry contains an empty id or symbol.'};if($registry.Contains($id)){throw "ARIA glyph registry contains duplicate id '$id'."};if($symbols.ContainsKey($symbol)){throw "ARIA glyph registry contains duplicate symbol '$symbol'."};$registry[$id]=$symbol;$symbols[$symbol]=$true};return $registry }

function Test-AriaTypeAssignable {
    param([string]$Expected,[string]$Actual)

    if (
        $Expected -eq 'Any' -or
        $Actual -eq 'Any' -or
        $Expected -eq $Actual
    ) {
        return $true
    }

    if (
        $Actual -eq 'Sequence<Empty>' -and
        (Test-AriaSequenceTypeName -Type $Expected) -and
        $Expected -ne 'Sequence<Empty>'
    ) {
        return $true
    }

    return $false
}
function Copy-AriaTable { param([hashtable]$Table) $copy=@{};foreach($key in $Table.Keys){$copy[$key]=$Table[$key]};return $copy }
function Get-AriaScopedType { param([object[]]$Scopes,[string]$Name) for($i=$Scopes.Count-1;$i-ge0;$i--){if($Scopes[$i].ContainsKey($Name)){return [string]$Scopes[$i][$Name]}};return $null }
function Add-AriaTypeDiagnostic { param($Diagnostics,[string]$Code,[string]$Message,[int]$Line) $Diagnostics.Add((New-AriaDiagnostic error $Code $Message $Line)) }
function Add-AriaDeniedEffectDiagnostic { param($Policy,[string]$Effect,[int]$Line,$Diagnostics) $decision=Test-AriaPolicyAllowsEffect $Policy $Effect;if(-not$decision.allowed){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2009' "Required effect '$Effect' rejected: $($decision.reason)" $Line} }

function Get-AriaExpressionType {
    param($Expression,[object[]]$Scopes,[hashtable]$Functions,$Diagnostics,[int]$Line)
    if($null-eq$Expression){return 'Null'}
    $type='Any'
    switch($Expression.kind){
        'literal'{$type=[string]$Expression.valueType}
        'sequence'{
            $limits = Get-AriaSequenceLimits
            [object[]]$elements = @($Expression.elements)

            if ($elements.Count -gt $limits.maxElements) {
                Add-AriaTypeDiagnostic `
                    $Diagnostics `
                    'ARIA2110' `
                    "Sequence literal exceeds $($limits.maxElements) elements." `
                    $Line
            }

            if ($elements.Count -eq 0) {
                $elementType = 'Empty'
                $type = 'Sequence<Empty>'
            }
            else {
                $elementTypes = New-Object System.Collections.Generic.List[string]
                $values = New-Object System.Collections.Generic.List[object]
                $allLiteral = $true

                foreach ($element in $elements) {
                    $elementTypes.Add(
                        (Get-AriaExpressionType `
                            $element `
                            $Scopes `
                            $Functions `
                            $Diagnostics `
                            $Line)
                    )

                    if ([string]$element.kind -eq 'literal') {
                        $values.Add($element.value)
                    }
                    elseif (
                        [string]$element.kind -eq 'unary' -and
                        [string]$element.operator -eq 'neg' -and
                        [string]$element.operand.kind -eq 'literal' -and
                        [string]$element.operand.valueType -eq 'Number'
                    ) {
                        $values.Add((-1 * $element.operand.value))
                    }
                    else {
                        $allLiteral = $false
                    }
                }

                if (-not $allLiteral) {
                    Add-AriaTypeDiagnostic `
                        $Diagnostics `
                        'ARIA2111' `
                        'Sequence elements must be scalar literals in alpha.4.' `
                        $Line
                }

                $elementType = [string]$elementTypes[0]

                if ($elementType -notin @('Text','Number','Bool','Null')) {
                    Add-AriaTypeDiagnostic `
                        $Diagnostics `
                        'ARIA2112' `
                        "Sequence element type '$elementType' is not an alpha.4 scalar." `
                        $Line
                    $type = 'Any'
                }
                else {
                    $heterogeneous = $false

                    foreach ($candidate in $elementTypes) {
                        if ([string]$candidate -ne $elementType) {
                            $heterogeneous = $true
                        }
                    }

                    if ($heterogeneous) {
                        Add-AriaTypeDiagnostic `
                            $Diagnostics `
                            'ARIA2113' `
                            'Sequence literal elements must have one exact type.' `
                            $Line
                        $type = 'Any'
                    }
                    else {
                        $type = 'Sequence<' + $elementType + '>'

                        if ($allLiteral) {
                            try {
                                $null = New-AriaSequenceValue `
                                    -ElementType $elementType `
                                    -Values $values.ToArray()
                            }
                            catch {
                                Add-AriaTypeDiagnostic `
                                    $Diagnostics `
                                    'ARIA2114' `
                                    $_.Exception.Message `
                                    $Line
                            }
                        }
                    }
                }
            }

            $Expression |
                Add-Member `
                    -NotePropertyName elementType `
                    -NotePropertyValue $elementType `
                    -Force
        }
        'identifier'{$found=Get-AriaScopedType $Scopes ([string]$Expression.value);if($null-eq$found){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2060' "Unknown variable '$($Expression.value)'." $Line;$type='Any'}else{$type=$found}}
        'call'{
            $name=[string]$Expression.name
            if(-not$Functions.ContainsKey($name)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2061' "Unknown function '$name'." $Line;$type='Any'}else{$fn=$Functions[$name];$args=@($Expression.arguments);if($args.Count-ne$fn.parameters.Count){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2062' "Function '$name' expects $($fn.parameters.Count) argument(s), received $($args.Count)." $Line};for($i=0;$i-lt$args.Count;$i++){$actual=Get-AriaExpressionType $args[$i] $Scopes $Functions $Diagnostics $Line;if($i-lt$fn.parameters.Count-and-not(Test-AriaTypeAssignable ([string]$fn.parameters[$i].type) $actual)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2063' "Argument $($i+1) to '$name' expects $($fn.parameters[$i].type), received $actual." $Line}};$type=[string]$fn.returnType}
        }
        'map' {
            $sequenceType = Get-AriaExpressionType $Expression.sequence $Scopes $Functions $Diagnostics $Line
            $transformName = [string]$Expression.transform
            $elementType = Get-AriaSequenceElementType -Type $sequenceType

            try {
                $mapCard = Get-AriaGlyphCard -Id 'algorithm.map'
                if ([string]$mapCard.status -ne 'verified') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2120' 'The algorithm.map glyph card is not verified.' $Line
                }
            }
            catch {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2120' 'The algorithm.map glyph card is unavailable or invalid.' $Line
            }

            if (-not (Test-AriaDeclaredTypeName -Type $sequenceType) -or -not $elementType) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2121' "Map requires Sequence<T>, received $sequenceType." $Line
                $type = 'Any'
            }
            elseif (-not $Functions.ContainsKey($transformName)) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2122' "Map references unknown transform '$transformName'." $Line
                $type = 'Any'
            }
            else {
                $transform = $Functions[$transformName]
                $parameters = @($transform.parameters)
                if ($parameters.Count -ne 1) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2123' "Map transform '$transformName' must have exactly one parameter." $Line
                }
                elseif ([string]$parameters[0].type -ne $elementType) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2124' "Map transform '$transformName' expects $($parameters[0].type), sequence provides $elementType." $Line
                }

                $returnType = [string]$transform.returnType
                if ($returnType -notin @('Text','Number','Bool','Null')) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2125' "Map transform '$transformName' must return an established scalar type, received $returnType." $Line
                    $type = 'Any'
                }
                else {
                    $type = 'Sequence<' + $returnType + '>'
                }

                $summary = $transform.PSObject.Properties['effectSummary']
                if ($null -eq $summary -or [string]$summary.Value.purity -ne 'pure') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2126' "Map transform '$transformName' must have a verified pure effect summary." $Line
                }
            }
        }
        'filter' {
            $sequenceType = Get-AriaExpressionType $Expression.sequence $Scopes $Functions $Diagnostics $Line
            $predicateName = [string]$Expression.predicate
            $elementType = Get-AriaSequenceElementType -Type $sequenceType

            try {
                $filterCard = Get-AriaGlyphCard -Id 'algorithm.filter'
                if ([string]$filterCard.status -ne 'verified') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2130' 'The algorithm.filter glyph card is not verified.' $Line
                }
            }
            catch {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2130' 'The algorithm.filter glyph card is unavailable or invalid.' $Line
            }

            if (-not (Test-AriaDeclaredTypeName -Type $sequenceType) -or -not $elementType) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2131' "Filter requires Sequence<T>, received $sequenceType." $Line
                $type = 'Any'
            }
            elseif (-not $Functions.ContainsKey($predicateName)) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2132' "Filter references unknown predicate '$predicateName'." $Line
                $type = 'Any'
            }
            else {
                $predicate = $Functions[$predicateName]
                $parameters = @($predicate.parameters)
                if ($parameters.Count -ne 1) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2133' "Filter predicate '$predicateName' must have exactly one parameter." $Line
                }
                elseif ([string]$parameters[0].type -ne $elementType) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2134' "Filter predicate '$predicateName' expects $($parameters[0].type), sequence provides $elementType." $Line
                }

                if ([string]$predicate.returnType -ne 'Bool') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2135' "Filter predicate '$predicateName' must return Bool, received $($predicate.returnType)." $Line
                }

                $summary = $predicate.PSObject.Properties['effectSummary']
                if ($null -eq $summary -or [string]$summary.Value.purity -ne 'pure') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2136' "Filter predicate '$predicateName' must have a verified pure effect summary." $Line
                }
                $type = $sequenceType
            }
        }
        'reduce' {
            $sequenceType = Get-AriaExpressionType $Expression.sequence $Scopes $Functions $Diagnostics $Line
            $accumulatorType = Get-AriaExpressionType $Expression.initial $Scopes $Functions $Diagnostics $Line
            $reducerName = [string]$Expression.reducer
            $elementType = Get-AriaSequenceElementType -Type $sequenceType

            try {
                $reduceCard = Get-AriaGlyphCard -Id 'algorithm.reduce'
                if ([string]$reduceCard.status -ne 'verified') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2140' 'The algorithm.reduce glyph card is not verified.' $Line
                }
            }
            catch {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2140' 'The algorithm.reduce glyph card is unavailable or invalid.' $Line
            }

            if (-not (Test-AriaDeclaredTypeName -Type $sequenceType) -or -not $elementType) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2141' "Reduce requires Sequence<T>, received $sequenceType." $Line
                $type = 'Any'
            }
            elseif (-not $Functions.ContainsKey($reducerName)) {
                Add-AriaTypeDiagnostic $Diagnostics 'ARIA2142' "Reduce references unknown reducer '$reducerName'." $Line
                $type = 'Any'
            }
            else {
                $reducer = $Functions[$reducerName]
                $parameters = @($reducer.parameters)
                if ($parameters.Count -ne 2) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2143' "Reduce reducer '$reducerName' must have exactly two parameters." $Line
                }
                else {
                    if ([string]$parameters[0].type -ne $accumulatorType) {
                        Add-AriaTypeDiagnostic $Diagnostics 'ARIA2144' "Reduce reducer '$reducerName' accumulator parameter expects $($parameters[0].type), initial value provides $accumulatorType." $Line
                    }
                    if ([string]$parameters[1].type -ne $elementType) {
                        Add-AriaTypeDiagnostic $Diagnostics 'ARIA2145' "Reduce reducer '$reducerName' element parameter expects $($parameters[1].type), sequence provides $elementType." $Line
                    }
                }

                if ([string]$reducer.returnType -ne $accumulatorType) {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2146' "Reduce reducer '$reducerName' must return accumulator type $accumulatorType, received $($reducer.returnType)." $Line
                }

                $summary = $reducer.PSObject.Properties['effectSummary']
                if ($null -eq $summary -or [string]$summary.Value.purity -ne 'pure') {
                    Add-AriaTypeDiagnostic $Diagnostics 'ARIA2147' "Reduce reducer '$reducerName' must have a verified pure effect summary." $Line
                }
                $type = $accumulatorType
            }
        }
        'unary'{$operand=Get-AriaExpressionType $Expression.operand $Scopes $Functions $Diagnostics $Line;if($Expression.operator-eq'not'){if(-not(Test-AriaTypeAssignable 'Bool' $operand)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2064' "Operator 'not' requires Bool, received $operand." $Line};$type='Bool'}else{if(-not(Test-AriaTypeAssignable 'Number' $operand)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2065' "Unary '-' requires Number, received $operand." $Line};$type='Number'}}
        'binary'{
            $left=Get-AriaExpressionType $Expression.left $Scopes $Functions $Diagnostics $Line;$right=Get-AriaExpressionType $Expression.right $Scopes $Functions $Diagnostics $Line;$op=[string]$Expression.operator
            switch($op){
                '+'{if($left-eq'Text'-and$right-eq'Text'){$type='Text'}elseif((Test-AriaTypeAssignable 'Number' $left)-and(Test-AriaTypeAssignable 'Number' $right)){$type='Number'}else{Add-AriaTypeDiagnostic $Diagnostics 'ARIA2066' "Operator '+' requires Number+Number or Text+Text, received $left+$right." $Line;$type='Any'}}
                {$_-in@('-','*','/')} {if(-not((Test-AriaTypeAssignable 'Number' $left)-and(Test-AriaTypeAssignable 'Number' $right))){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2067' "Operator '$op' requires Number operands, received $left and $right." $Line};$type='Number'}
                {$_-in@('<','<=','>','>=')} {if(-not((Test-AriaTypeAssignable 'Number' $left)-and(Test-AriaTypeAssignable 'Number' $right))){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2068' "Operator '$op' requires Number operands, received $left and $right." $Line};$type='Bool'}
                {$_-in@('==','!=')} {if(-not((Test-AriaTypeAssignable $left $right)-or(Test-AriaTypeAssignable $right $left))){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2069' "Operator '$op' compares incompatible types $left and $right." $Line};$type='Bool'}
                {$_-in@('and','or')} {if(-not((Test-AriaTypeAssignable 'Bool' $left)-and(Test-AriaTypeAssignable 'Bool' $right))){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2070' "Operator '$op' requires Bool operands, received $left and $right." $Line};$type='Bool'}
            }
        }
        default{Add-AriaTypeDiagnostic $Diagnostics 'ARIA2071' "Unknown expression kind '$($Expression.kind)'." $Line;$type='Any'}
    }
    $Expression | Add-Member -NotePropertyName inferredType -NotePropertyValue $type -Force
    return $type
}

function Test-AriaStatementsAlwaysReturn {
    param([object[]]$Statements)
    foreach($statement in $Statements){if($statement.op-eq'return'){return $true};if($statement.op-eq'if'-and(Test-AriaStatementsAlwaysReturn @($statement.then))-and(Test-AriaStatementsAlwaysReturn @($statement.else))){return $true}}
    return $false
}

function Test-AriaStatementSequence {
    param([object[]]$Statements,[object[]]$Scopes,[hashtable]$Functions,[hashtable]$Memories,[hashtable]$Capabilities,[hashtable]$Agents,[hashtable]$Connections,$Policy,$Diagnostics,[string]$ReturnType,[bool]$IsFunction,[hashtable]$ActiveCapabilities)
    foreach($statement in $Statements){
        switch($statement.op){
            'emit'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;$null=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line}
            'signal'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;$null=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line}
            'let'{
                $actual = Get-AriaExpressionType `
                    $statement.expression `
                    $Scopes `
                    $Functions `
                    $Diagnostics `
                    $statement.line

                $expected = if ($statement.declaredType) {
                    [string]$statement.declaredType
                }
                else {
                    $actual
                }

                if (
                    $actual -eq 'Sequence<Empty>' -and
                    -not $statement.declaredType
                ) {
                    Add-AriaTypeDiagnostic `
                        $Diagnostics `
                        'ARIA2115' `
                        'An empty sequence requires an explicit Sequence<T> type.' `
                        $statement.line
                }
                elseif (
                    $Scopes[$Scopes.Count-1].ContainsKey($statement.name) -or
                    $null -ne (Get-AriaScopedType $Scopes $statement.name)
                ) {
                    Add-AriaTypeDiagnostic `
                        $Diagnostics `
                        'ARIA2072' `
                        "Variable '$($statement.name)' is already defined." `
                        $statement.line
                }
                elseif (-not (Test-AriaTypeAssignable $expected $actual)) {
                    Add-AriaTypeDiagnostic `
                        $Diagnostics `
                        'ARIA2073' `
                        "Variable '$($statement.name)' expects $expected, received $actual." `
                        $statement.line
                }
                else {
                    $Scopes[$Scopes.Count-1][$statement.name] = $expected
                    $statement |
                        Add-Member `
                            -NotePropertyName inferredType `
                            -NotePropertyValue $expected `
                            -Force
                }
            }
            'set'{$expected=Get-AriaScopedType $Scopes $statement.name;$actual=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if($null-eq$expected){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2074' "Cannot set undefined variable '$($statement.name)'." $statement.line}elseif(-not(Test-AriaTypeAssignable $expected $actual)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2075' "Variable '$($statement.name)' expects $expected, received $actual." $statement.line}}
            'remember'{Add-AriaDeniedEffectDiagnostic $Policy 'memory.write' $statement.line $Diagnostics;if(-not$Memories.ContainsKey($statement.memory)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2041' "Unknown memory '$($statement.memory)'." $statement.line}elseif(-not$Memories[$statement.memory].ContainsKey($statement.key)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2046' "Unknown memory key '$($statement.memory).$($statement.key)'." $statement.line}else{$actual=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;$expected=[string]$Memories[$statement.memory][$statement.key];if(-not(Test-AriaTypeAssignable $expected $actual)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2076' "Memory '$($statement.memory).$($statement.key)' expects $expected, received $actual." $statement.line}}}
            'recall'{Add-AriaDeniedEffectDiagnostic $Policy 'memory.read' $statement.line $Diagnostics;if(-not$Memories.ContainsKey($statement.memory)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2042' "Unknown memory '$($statement.memory)'." $statement.line}elseif(-not$Memories[$statement.memory].ContainsKey($statement.key)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2047' "Unknown memory key '$($statement.memory).$($statement.key)'." $statement.line}else{$actual=[string]$Memories[$statement.memory][$statement.key];$expected=if($statement.declaredType){[string]$statement.declaredType}else{$actual};if(-not(Test-AriaTypeAssignable $expected $actual)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2077' "Recall target '$($statement.name)' expects $expected, memory provides $actual." $statement.line}else{$Scopes[$Scopes.Count-1][$statement.name]=$expected;$statement | Add-Member -NotePropertyName inferredType -NotePropertyValue $expected -Force}}}
            'require'{if(-not$Capabilities.ContainsKey($statement.capability)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2043' "Unknown capability '$($statement.capability)'." $statement.line}else{$ActiveCapabilities[$statement.capability]=$true}}
            'assert'{$type=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Bool' $type)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2078' "assert requires Bool, received $type." $statement.line}}
            'read'{$pathType=Get-AriaExpressionType $statement.path $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Text' $pathType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2079' "read path requires Text, received $pathType." $statement.line};$has=$false;foreach($name in $ActiveCapabilities.Keys){if($Capabilities[$name].effect-eq'fs.read'){$has=$true}};if(-not$has){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2044' 'read requires an active fs.read capability.' $statement.line};$Scopes[$Scopes.Count-1][$statement.name]='Text';$statement | Add-Member -NotePropertyName inferredType -NotePropertyValue 'Text' -Force}
            'write'{$pathType=Get-AriaExpressionType $statement.path $Scopes $Functions $Diagnostics $statement.line;$valueType=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Text' $pathType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2080' "write path requires Text, received $pathType." $statement.line};if(-not(Test-AriaTypeAssignable 'Text' $valueType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2081' "write value requires Text, received $valueType." $statement.line};$has=$false;foreach($name in $ActiveCapabilities.Keys){if($Capabilities[$name].effect-eq'fs.write'){$has=$true}};if(-not$has){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2045' 'write requires an active fs.write capability.' $statement.line}}
            'dispatch'{Add-AriaDeniedEffectDiagnostic $Policy 'agent.dispatch' $statement.line $Diagnostics;if(-not$Agents.ContainsKey($statement.agent)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2082' "Unknown agent '$($statement.agent)'." $statement.line};$taskType=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Text' $taskType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2083' "dispatch task requires Text, received $taskType." $statement.line}}
            'connect'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;if(-not$Connections.ContainsKey($statement.connection)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2104' "Unknown connection '$($statement.connection)'." $statement.line}}
            'intent'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;if(-not$Connections.ContainsKey($statement.connection)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2104' "Unknown connection '$($statement.connection)'." $statement.line};$intentType=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Text' $intentType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2105' "connection intent requires Text, received $intentType." $statement.line}}
            'propose'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;if(-not$Connections.ContainsKey($statement.connection)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2104' "Unknown connection '$($statement.connection)'." $statement.line};$proposalType=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Text' $proposalType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2106' "connection proposal requires Text, received $proposalType." $statement.line}}
            'consent'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;if(-not$Connections.ContainsKey($statement.connection)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2104' "Unknown connection '$($statement.connection)'." $statement.line};$consentType=Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Bool' $consentType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2107' "connection consent requires Bool, received $consentType." $statement.line}}
            'disconnect'{Add-AriaDeniedEffectDiagnostic $Policy 'console.emit' $statement.line $Diagnostics;if(-not$Connections.ContainsKey($statement.connection)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2104' "Unknown connection '$($statement.connection)'." $statement.line}}
            'if'{$conditionType=Get-AriaExpressionType $statement.condition $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Bool' $conditionType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2084' "if condition requires Bool, received $conditionType." $statement.line};$thenScopes = @($Scopes) + @(@{});$elseScopes = @($Scopes) + @(@{});Test-AriaStatementSequence @($statement.then) $thenScopes $Functions $Memories $Capabilities $Agents $Connections $Policy $Diagnostics $ReturnType $IsFunction (Copy-AriaTable $ActiveCapabilities);Test-AriaStatementSequence @($statement.else) $elseScopes $Functions $Memories $Capabilities $Agents $Connections $Policy $Diagnostics $ReturnType $IsFunction (Copy-AriaTable $ActiveCapabilities)}
            'repeat'{$countType=Get-AriaExpressionType $statement.count $Scopes $Functions $Diagnostics $statement.line;if(-not(Test-AriaTypeAssignable 'Number' $countType)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2085' "repeat count requires Number, received $countType." $statement.line};if($statement.count.kind-eq'literal'-and([double]$statement.count.value-lt0-or[double]$statement.count.value-gt10000-or[math]::Floor([double]$statement.count.value)-ne[double]$statement.count.value)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2086' 'repeat literal count must be an integer from 0 through 10000.' $statement.line};$loopScope = @{};$loopScope[[string]$statement.iterator] = 'Number';$loopScopes = @($Scopes) + @($loopScope);Test-AriaStatementSequence @($statement.body) $loopScopes $Functions $Memories $Capabilities $Agents $Connections $Policy $Diagnostics $ReturnType $IsFunction (Copy-AriaTable $ActiveCapabilities)}
            'return'{if(-not$IsFunction){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2087' 'return is valid only inside a function.' $statement.line}else{$actual=if($null-eq$statement.expression){'Null'}else{Get-AriaExpressionType $statement.expression $Scopes $Functions $Diagnostics $statement.line};if(-not(Test-AriaTypeAssignable $ReturnType $actual)){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2088' "Function return expects $ReturnType, received $actual." $statement.line}}}
            'halt'{if($IsFunction){Add-AriaTypeDiagnostic $Diagnostics 'ARIA2089' 'halt is not valid inside a function; use return.' $statement.line}}
        }
    }
}

function Test-AriaSemantics {
    param($ParseResult,$Policy)
    $diagnostics=New-Object System.Collections.Generic.List[object];foreach($d in $ParseResult.diagnostics){$diagnostics.Add($d)};$model=$ParseResult.model
    if($null-ne$model.specVersion-and-not(Test-AriaSemanticVersion $model.specVersion)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2001' "Invalid language version '$($model.specVersion)'." 0}
    if($null-ne$model.programVersion-and-not(Test-AriaSemanticVersion $model.programVersion)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2002' "Invalid program version '$($model.programVersion)'." 0}
    if($null-ne$model.moduleVersion-and-not(Test-AriaSemanticVersion $model.moduleVersion)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2003' "Invalid module version '$($model.moduleVersion)'." 0}

    $memories=@{};foreach($memory in $model.memories){if($memories.ContainsKey($memory.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2004' "Duplicate memory '$($memory.name)'." $memory.line;continue};$fields=@{};foreach($entry in $memory.values){if($fields.ContainsKey($entry.key)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2005' "Duplicate memory key '$($memory.name).$($entry.key)'." $entry.line;continue};if($entry.expression.kind-notin@('literal','sequence')){Add-AriaTypeDiagnostic $diagnostics 'ARIA2006' 'Memory defaults must be scalar or sequence literals.' $entry.line;$actual='Any'}else{$actual=Get-AriaExpressionType $entry.expression @(@{}) @{} $diagnostics $entry.line};$expected=if($entry.declaredType){[string]$entry.declaredType}else{$actual};if($actual-eq'Sequence<Empty>'-and-not$entry.declaredType){Add-AriaTypeDiagnostic $diagnostics 'ARIA2115' 'An empty sequence requires an explicit Sequence<T> type.' $entry.line;$expected='Any'};if(-not(Test-AriaTypeAssignable $expected $actual)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2007' "Memory '$($memory.name).$($entry.key)' expects $expected, received $actual." $entry.line};$entry | Add-Member -NotePropertyName inferredType -NotePropertyValue $expected -Force;$fields[$entry.key]=$expected};$memories[$memory.name]=$fields}
    $capabilities=@{};foreach($cap in $model.capabilities){if($capabilities.ContainsKey($cap.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2010' "Duplicate capability '$($cap.name)'." $cap.line;continue};$capabilities[$cap.name]=$cap;if(-not($cap.effect-is[string])-or-not($cap.scope-is[string])){Add-AriaTypeDiagnostic $diagnostics 'ARIA2011' "Capability '$($cap.name)' requires string effect and scope properties." $cap.line;continue};if([IO.Path]::IsPathRooted([string]$cap.scope)-or[string]$cap.scope-match'(^|[\\/])\.\.([\\/]|$)'){Add-AriaTypeDiagnostic $diagnostics 'ARIA2013' "Capability '$($cap.name)' scope must be repository-relative and cannot contain '..'." $cap.line;continue};$decision=Test-AriaPolicyAllowsCapability $Policy $cap;if(-not$decision.allowed){Add-AriaTypeDiagnostic $diagnostics 'ARIA2012' "Capability '$($cap.name)' rejected: $($decision.reason)" $cap.line}}
    $agents=@{};foreach($agent in $model.agents){if($agents.ContainsKey($agent.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2020' "Duplicate agent '$($agent.name)'." $agent.line}else{$agents[$agent.name]=$agent};foreach($grant in $agent.grants){if(-not$capabilities.ContainsKey($grant.capability)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2021' "Agent '$($agent.name)' grants unknown capability '$($grant.capability)'." $grant.line}}}
    $connections=@{};foreach($connection in @($model.connections)){if($connections.ContainsKey($connection.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2100' "Duplicate connection '$($connection.name)'." $connection.line;continue};$connections[$connection.name]=$connection;if([string]::IsNullOrWhiteSpace([string]$connection.operator)-or[string]::IsNullOrWhiteSpace([string]$connection.agent)-or[string]::IsNullOrWhiteSpace([string]$connection.protocol)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2101' "Connection '$($connection.name)' requires operator, agent, and protocol Text properties." $connection.line;continue};if(-not$agents.ContainsKey([string]$connection.agent)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2102' "Connection '$($connection.name)' references unknown agent '$($connection.agent)'." $connection.line};if([string]$connection.protocol-ne'intent-proposal-consent'){Add-AriaTypeDiagnostic $diagnostics 'ARIA2103' "Connection '$($connection.name)' protocol must be 'intent-proposal-consent'." $connection.line}}
    $glyphs=Get-AriaGlyphRegistry;$graphs=@{};foreach($graph in $model.graphs){if($graphs.ContainsKey($graph.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2029' "Duplicate graph '$($graph.name)'." $graph.line;continue};$graphs[$graph.name]=$graph;$nodes=@{};foreach($node in $graph.nodes){if($nodes.ContainsKey($node.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2030' "Duplicate graph node '$($node.name)' in '$($graph.name)'." $node.line}else{$nodes[$node.name]=$node};$expected=$glyphs[[string]$node.nodeKind];if([string]$node.glyph-ne$expected){Add-AriaTypeDiagnostic $diagnostics 'ARIA2033' "Glyph for node kind '$($node.nodeKind)' must be '$expected'." $node.line}};foreach($link in $graph.links){if(-not$nodes.ContainsKey($link.source)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2031' "Unknown graph source '$($link.source)'." $link.line};if(-not$nodes.ContainsKey($link.target)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2032' "Unknown graph target '$($link.target)'." $link.line}}}
    $functions=@{};foreach($fn in $model.functions){if($functions.ContainsKey($fn.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2090' "Duplicate function '$($fn.name)'." $fn.line}else{$functions[$fn.name]=$fn};$params=@{};foreach($p in $fn.parameters){if($params.ContainsKey($p.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2091' "Duplicate parameter '$($p.name)' in function '$($fn.name)'." $p.line}else{$params[$p.name]=$p.type}}}
    $effectGraph = Get-AriaSourceEffectGraph -Model $model -CapabilityMap $capabilities
    foreach($fn in @($model.functions)){$fn|Add-Member -NotePropertyName effectSummary -NotePropertyValue (Get-AriaEffectSummary -Graph $effectGraph -Name ([string]$fn.name)) -Force}
    foreach($fn in $model.functions){$scope=@{};foreach($p in $fn.parameters){$scope[$p.name]=$p.type};Test-AriaStatementSequence @($fn.statements) @($scope) $functions $memories $capabilities $agents $connections $Policy $diagnostics ([string]$fn.returnType) $true @{};if($fn.returnType-ne'Null'-and-not(Test-AriaStatementsAlwaysReturn @($fn.statements))){Add-AriaTypeDiagnostic $diagnostics 'ARIA2092' "Function '$($fn.name)' does not return on every visible path." $fn.line}}
    $flows=@{};foreach($flow in $model.flows){if($flows.ContainsKey($flow.name)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2040' "Duplicate flow '$($flow.name)'." $flow.line;continue};$flows[$flow.name]=$flow;Test-AriaStatementSequence @($flow.statements) @(@{}) $functions $memories $capabilities $agents $connections $Policy $diagnostics 'Null' $false @{}}
    if($null-ne$model.entry-and-not$flows.ContainsKey($model.entry)){Add-AriaTypeDiagnostic $diagnostics 'ARIA2050' "Entry flow '$($model.entry)' does not exist." 0}
    return [pscustomobject][ordered]@{model=$model;diagnostics=$diagnostics.ToArray();capabilityMap=$capabilities;functionMap=$functions;memoryTypes=$memories;connectionMap=$connections;effectGraph=$effectGraph}
}

Export-ModuleMember -Function Get-AriaPolicy,Get-AriaPolicyEffect,Test-AriaPolicyDocument,Get-AriaPolicyMaxBytes,Test-AriaPolicyAllowsCapability,Test-AriaPolicyAllowsEffect,Get-AriaGlyphRegistry,Test-AriaTypeAssignable,Test-AriaSemantics
