Set-StrictMode -Version 2.0

if ($null -eq (Get-Command New-AriaCardExecutionEvidence -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.SignalSubset.psm1') -Force -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'Aria.GlyphMemory.psm1') -Force -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'Aria.ExecutionEvidence.psm1') -Force -DisableNameChecking
}

function Get-AriaCapabilityMapFromBytecode { param($Bytecode) $map=@{};foreach($cap in @($Bytecode.capabilities)){$map[[string]$cap.name]=$cap};return $map }
function Assert-AriaRuntimeEffect { param($Policy,[string]$Effect,[string]$Scope='.') $decision=Test-AriaPolicyAllowsEffect $Policy $Effect $Scope;if(-not$decision.allowed){throw "ARIA VM denied effect '$Effect': $($decision.reason)"} }
function Get-AriaRuntimeValueType { param($Value) return (Get-AriaCanonicalValueType -Value $Value) }
function Assert-AriaRuntimeType { param([string]$Expected,$Value,[string]$Context) $actual=Get-AriaRuntimeValueType $Value;if(-not(Test-AriaTypeAssignable $Expected $actual)){throw "ARIA VM type error in ${Context}: expected $Expected, received $actual."} }
function ConvertTo-AriaRuntimeText {
    param($Value)

    if (
        $Value -is [Management.Automation.PSCustomObject] -or
        $Value -is [Collections.IDictionary]
    ) {
        $validation = Test-AriaSequenceValue -Value $Value

        if ($validation.valid) {
            return ConvertTo-AriaJson `
                -Value ([object[]]@($validation.values))
        }
    }

    return [string]$Value
}

function Copy-AriaRuntimeTable { param([hashtable]$Table) $copy=@{};foreach($key in $Table.Keys){$copy[$key]=$Table[$key]};return $copy }
function New-AriaScopeStack { $scopes=New-Object Collections.ArrayList;$null=$scopes.Add(@{});return,$scopes }
function Get-AriaScopedValue { param($Scopes,[string]$Name) for($i=$Scopes.Count-1;$i-ge0;$i--){if($Scopes[$i].ContainsKey($Name)){return [pscustomobject]@{found=$true;value=$Scopes[$i][$Name]}}};return [pscustomobject]@{found=$false;value=$null} }
function Set-AriaScopedValue { param($Scopes,[string]$Name,$Value) for($i=$Scopes.Count-1;$i-ge0;$i--){if($Scopes[$i].ContainsKey($Name)){$Scopes[$i][$Name]=$Value;return}};throw "ARIA VM cannot set undefined variable '$Name'." }
function Add-AriaScope { param($Scopes,[hashtable]$Values=@{}) $null=$Scopes.Add($Values) }
function Remove-AriaScope { param($Scopes) if($Scopes.Count-le1){throw 'ARIA VM cannot remove the root scope.'};$Scopes.RemoveAt($Scopes.Count-1) }
function Pop-AriaRuntime { param($Stack,[string]$Context) if($Stack.Count-eq0){throw "ARIA VM stack underflow at $Context."};return $Stack.Pop() }

function Publish-AriaVmSemanticEvent {
    param(
        $Context,
        [string]$Domain,
        [string]$Phase,
        [string]$State,
        [string]$Energy,
        [string]$Information,
        [string]$Coherence,
        $Data = $null
    )
    if (-not (Get-Command Send-AriaEvent -ErrorAction SilentlyContinue)) { return $null }
    Send-AriaEvent `
        -Domain $Domain `
        -Phase $Phase `
        -State $State `
        -Energy $Energy `
        -Information $Information `
        -Coherence $Coherence `
        -Source 'aria.vm' `
        -Data $Data `
        -Render:(-not [bool]$Context.passThru) `
        -PassThru
}

function Add-AriaVmRuntimeEvent {
    param(
        $Context,
        $LegacyEvent,
        [string]$Domain,
        [string]$Phase,
        [string]$State,
        [string]$Energy,
        [string]$Information,
        [string]$Coherence,
        [switch]$PassThru
    )
    $semantic = Publish-AriaVmSemanticEvent `
        -Context $Context `
        -Domain $Domain `
        -Phase $Phase `
        -State $State `
        -Energy $Energy `
        -Information $Information `
        -Coherence $Coherence `
        -Data $LegacyEvent
    if ($semantic) {
        $LegacyEvent | Add-Member -NotePropertyName eventDigest -NotePropertyValue ([string]$semantic.digest)
        $LegacyEvent | Add-Member -NotePropertyName cueId -NotePropertyValue ([string]$semantic.projection.cue.id)
        $LegacyEvent | Add-Member -NotePropertyName projectionDigest -NotePropertyValue ([string]$semantic.projection.digest)
    }
    $Context.events.Add($LegacyEvent)
    if ($PassThru) { return $semantic }
}

function Add-AriaVmCardExecutionEvidence {
    param(
        $Context,
        [ValidateSet('map','filter','reduce')][string]$Kind,
        [string]$Target,
        [int]$Line,
        [ValidateSet('completed','fractured')][string]$Outcome,
        $Counts,
        $TerminalEvent
    )
    if ($null -eq $TerminalEvent) {
        throw "ARIA VM cannot seal '$Kind' evidence without a terminal Event Spine identity."
    }
    $card = Get-AriaGlyphCard -Id ('algorithm.' + $Kind) -Registry $Context.glyphRegistry
    $evidence = New-AriaCardExecutionEvidence `
        -Card $card `
        -CompilerVersion ([string]$Context.bytecode.compilerVersion) `
        -SourceHash ([string]$Context.bytecode.sourceHash) `
        -IrHash ([string]$Context.bytecode.irHash) `
        -ArtifactHash ([string]$Context.artifactHash) `
        -EffectGraphDigest ([string]$Context.bytecode.effectGraph.digest) `
        -PolicyDigest ([string]$Context.policyDigest) `
        -TerminalEvent $TerminalEvent `
        -Outcome $Outcome `
        -OperationKind $Kind `
        -Target $Target `
        -Line $Line `
        -Counts $Counts
    $verification = Test-AriaCardExecutionEvidence -Evidence $evidence -Registry $Context.glyphRegistry
    if (-not [bool]$verification.valid) {
        throw ('ARIA VM rejected card execution evidence: ' + (@($verification.errors) -join ', '))
    }
    $Context.executionEvidence.Add($evidence)
    $null = Send-AriaEvent `
        -Domain evidence `
        -Phase card.execution `
        -State $(if ($Outcome -eq 'completed') { 'PASS' } else { 'FAIL' }) `
        -Energy sealing `
        -Information ([string]$card.id) `
        -Coherence $(if ($Outcome -eq 'completed') { 'bounded card evidence sealed' } else { 'bounded card fracture evidence sealed' }) `
        -Source 'aria.vm.evidence' `
        -Data ([pscustomobject][ordered]@{
            receiptDigest = [string]$evidence.digest
            cardId = [string]$card.id
            outcome = $Outcome
            terminalEventDigest = [string]$evidence.terminalEvent.digest
            signalSubsetDigest = ('sha256:' + [string]$evidence.signalSubset.digest)
        }) `
        -Render:(-not [bool]$Context.passThru) `
        -PassThru
    $evidence
}

function Invoke-AriaVmFunction {
    param(
        $Context,
        [Parameter(Mandatory=$true)][string]$Name,
        [AllowEmptyCollection()][object[]]$Arguments = @(),
        [int]$CallDepth,
        [int]$Line
    )
    if (-not $Context.functionMap.ContainsKey($Name)) {
        throw "ARIA VM unknown function '$Name'."
    }
    $fn = $Context.functionMap[$Name]
    if ($Arguments.Count -ne @($fn.parameters).Count) {
        throw "ARIA VM function '$Name' expected $(@($fn.parameters).Count) argument(s), received $($Arguments.Count)."
    }
    $fnScopes = New-AriaScopeStack
    for ($index=0;$index-lt$Arguments.Count;$index++) {
        $parameter = $fn.parameters[$index]
        Assert-AriaRuntimeType ([string]$parameter.type) $Arguments[$index] "argument $($index+1) to $Name"
        $fnScopes[0][[string]$parameter.name] = $Arguments[$index]
    }
    $result = Invoke-AriaInstructionSequence @($fn.instructions) $Context $fnScopes @{} ($CallDepth + 1)
    if ($result.control -ne 'return') {
        throw "ARIA function '$Name' terminated without return."
    }
    Assert-AriaRuntimeType ([string]$fn.returnType) $result.value "return from $Name"
    return $result.value
}

function Invoke-AriaVmMap {
    param($Context,$SequenceValue,$Instruction,[int]$CallDepth)
    $validation = Test-AriaSequenceValue -Value $SequenceValue
    if (-not $validation.valid) { throw 'ARIA VM MAP requires a valid sequence value.' }
    $transformName = [string]$Instruction.transform
    if (-not $Context.functionMap.ContainsKey($transformName)) {
        throw "ARIA VM MAP references unknown transform '$transformName'."
    }
    $transform = $Context.functionMap[$transformName]
    $parameters = @($transform.parameters)
    $summary = $transform.PSObject.Properties['effectSummary']
    if ($parameters.Count -ne 1 -or $null -eq $summary -or [string]$summary.Value.purity -ne 'pure') {
        throw "ARIA VM MAP transform '$transformName' is not an admitted unary pure function."
    }
    $declaredInputElement = Get-AriaSequenceElementType -Type ([string]$Instruction.inputType)
    if (
        [string]$parameters[0].type -ne $declaredInputElement -or
        (
            [string]$validation.elementType -ne 'Empty' -and
            [string]$validation.elementType -ne $declaredInputElement
        )
    ) {
        throw "ARIA VM MAP transform '$transformName' does not accept the declared input sequence."
    }

    if (Get-Command Start-AriaEventOperation -ErrorAction SilentlyContinue) {
        $null = Start-AriaEventOperation -Name ('algorithm.map.' + $transformName)
    }
    $batchStarted = $false
    if (Get-Command Start-AriaEventBatch -ErrorAction SilentlyContinue) {
        Start-AriaEventBatch -ChunkSize 32
        $batchStarted = $true
    }
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $iterations = @($validation.values).Count
    $completed = 0
    $resultValues = New-Object System.Collections.Generic.List[object]
    $startRecord = [pscustomobject][ordered]@{kind='map';state='start';transform=$transformName;iterations=$iterations;line=[int]$Instruction.line}
    Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $startRecord -Domain algorithm -Phase map.start -State ACTIVE -Energy execution -Information $transformName -Coherence 'map started'

    try {
        foreach ($value in @($validation.values)) {
            $mapped = Invoke-AriaVmFunction -Context $Context -Name $transformName -Arguments @($value) -CallDepth $CallDepth -Line ([int]$Instruction.line)
            $resultValues.Add($mapped)
            $completed++
            $iterationRecord = [pscustomobject][ordered]@{kind='map';state='iteration';transform=$transformName;iteration=$completed;iterations=$iterations;line=[int]$Instruction.line}
            Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $iterationRecord -Domain algorithm -Phase map.iteration -State INFO -Energy iteration -Information $transformName -Coherence ("iteration {0} complete" -f $completed)
        }
        $result = New-AriaSequenceValue -ElementType ([string]$transform.returnType) -Values $resultValues.ToArray()
        $clock.Stop()
        $completeRecord = [pscustomobject][ordered]@{kind='map';state='complete';transform=$transformName;iteration=$completed;iterations=$iterations;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
        $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $completeRecord -Domain algorithm -Phase map.complete -State PASS -Energy completion -Information $transformName -Coherence 'map contract passed' -PassThru
        $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind map -Target $transformName -Line ([int]$Instruction.line) -Outcome completed -Counts ([pscustomobject][ordered]@{inputCount=$iterations;completedCount=$completed;outputCount=$resultValues.Count}) -TerminalEvent $terminalEvent
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        return $result
    }
    catch {
        $originalError = $_
        $clock.Stop()
        try {
            $fractureRecord = [pscustomobject][ordered]@{kind='map';state='fracture';transform=$transformName;iteration=$completed;iterations=$iterations;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
            $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $fractureRecord -Domain algorithm -Phase map.fracture -State FAIL -Energy interruption -Information $transformName -Coherence 'map transform rejected' -PassThru
            $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind map -Target $transformName -Line ([int]$Instruction.line) -Outcome fractured -Counts ([pscustomobject][ordered]@{inputCount=$iterations;completedCount=$completed;outputCount=$resultValues.Count}) -TerminalEvent $terminalEvent
        }
        catch {
            # Preserve the runtime fracture when evidence publication is unavailable.
        }
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        throw $originalError
    }
}

function Invoke-AriaVmFilter {
    param($Context,$SequenceValue,$Instruction,[int]$CallDepth)
    $validation = Test-AriaSequenceValue -Value $SequenceValue
    if (-not $validation.valid) { throw 'ARIA VM FILTER requires a valid sequence value.' }
    $predicateName = [string]$Instruction.predicate
    if (-not $Context.functionMap.ContainsKey($predicateName)) {
        throw "ARIA VM FILTER references unknown predicate '$predicateName'."
    }
    $predicate = $Context.functionMap[$predicateName]
    $parameters = @($predicate.parameters)
    $summary = $predicate.PSObject.Properties['effectSummary']
    if (
        $parameters.Count -ne 1 -or
        [string]$predicate.returnType -ne 'Bool' -or
        $null -eq $summary -or
        [string]$summary.Value.purity -ne 'pure'
    ) {
        throw "ARIA VM FILTER predicate '$predicateName' is not an admitted unary pure Bool function."
    }
    $declaredElement = Get-AriaSequenceElementType -Type ([string]$Instruction.sequenceType)
    if (
        [string]$parameters[0].type -ne $declaredElement -or
        (
            [string]$validation.elementType -ne 'Empty' -and
            [string]$validation.elementType -ne $declaredElement
        )
    ) {
        throw "ARIA VM FILTER predicate '$predicateName' does not accept the declared input sequence."
    }

    if (Get-Command Start-AriaEventOperation -ErrorAction SilentlyContinue) {
        $null = Start-AriaEventOperation -Name ('algorithm.filter.' + $predicateName)
    }
    $batchStarted = $false
    if (Get-Command Start-AriaEventBatch -ErrorAction SilentlyContinue) {
        Start-AriaEventBatch -ChunkSize 32
        $batchStarted = $true
    }
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $inputCount = @($validation.values).Count
    $completed = 0
    $selected = 0
    $resultValues = New-Object System.Collections.Generic.List[object]
    $startRecord = [pscustomobject][ordered]@{kind='filter';state='start';predicate=$predicateName;inputCount=$inputCount;line=[int]$Instruction.line}
    Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $startRecord -Domain algorithm -Phase filter.start -State ACTIVE -Energy execution -Information $predicateName -Coherence 'filter started'

    try {
        foreach ($value in @($validation.values)) {
            $accepted = Invoke-AriaVmFunction -Context $Context -Name $predicateName -Arguments @($value) -CallDepth $CallDepth -Line ([int]$Instruction.line)
            if ([bool]$accepted) {
                $resultValues.Add($value)
                $selected++
            }
            $completed++
            $iterationRecord = [pscustomobject][ordered]@{kind='filter';state='iteration';predicate=$predicateName;completed=$completed;inputCount=$inputCount;selectedCount=$selected;line=[int]$Instruction.line}
            Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $iterationRecord -Domain algorithm -Phase filter.iteration -State INFO -Energy iteration -Information $predicateName -Coherence ("iteration {0} complete; {1} selected" -f $completed,$selected)
        }
        $result = New-AriaSequenceValue -ElementType $declaredElement -Values $resultValues.ToArray()
        $clock.Stop()
        $completeRecord = [pscustomobject][ordered]@{kind='filter';state='complete';predicate=$predicateName;completed=$completed;inputCount=$inputCount;selectedCount=$selected;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
        $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $completeRecord -Domain algorithm -Phase filter.complete -State PASS -Energy completion -Information $predicateName -Coherence 'filter contract passed' -PassThru
        $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind filter -Target $predicateName -Line ([int]$Instruction.line) -Outcome completed -Counts ([pscustomobject][ordered]@{inputCount=$inputCount;completedCount=$completed;selectedCount=$selected;outputCount=$resultValues.Count}) -TerminalEvent $terminalEvent
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        return $result
    }
    catch {
        $originalError = $_
        $clock.Stop()
        try {
            $fractureRecord = [pscustomobject][ordered]@{kind='filter';state='fracture';predicate=$predicateName;completed=$completed;inputCount=$inputCount;selectedCount=$selected;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
            $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $fractureRecord -Domain algorithm -Phase filter.fracture -State FAIL -Energy interruption -Information $predicateName -Coherence 'filter predicate rejected' -PassThru
            $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind filter -Target $predicateName -Line ([int]$Instruction.line) -Outcome fractured -Counts ([pscustomobject][ordered]@{inputCount=$inputCount;completedCount=$completed;selectedCount=$selected;outputCount=$resultValues.Count}) -TerminalEvent $terminalEvent
        }
        catch {
            # Preserve the runtime fracture when evidence publication is unavailable.
        }
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        throw $originalError
    }
}

function Invoke-AriaVmReduce {
    param($Context,$SequenceValue,$InitialValue,$Instruction,[int]$CallDepth)
    $validation = Test-AriaSequenceValue -Value $SequenceValue
    if (-not $validation.valid) { throw 'ARIA VM REDUCE requires a valid sequence value.' }
    $reducerName = [string]$Instruction.reducer
    if (-not $Context.functionMap.ContainsKey($reducerName)) {
        throw "ARIA VM REDUCE references unknown reducer '$reducerName'."
    }
    $reducer = $Context.functionMap[$reducerName]
    $parameters = @($reducer.parameters)
    $summary = $reducer.PSObject.Properties['effectSummary']
    $accumulatorType = [string]$Instruction.accumulatorType
    $declaredElement = Get-AriaSequenceElementType -Type ([string]$Instruction.sequenceType)
    if (
        $parameters.Count -ne 2 -or
        [string]$reducer.returnType -ne $accumulatorType -or
        $null -eq $summary -or
        [string]$summary.Value.purity -ne 'pure'
    ) {
        throw "ARIA VM REDUCE reducer '$reducerName' is not an admitted binary pure accumulator function."
    }
    if (
        [string]$parameters[0].type -ne $accumulatorType -or
        [string]$parameters[1].type -ne $declaredElement -or
        (
            [string]$validation.elementType -ne 'Empty' -and
            [string]$validation.elementType -ne $declaredElement
        )
    ) {
        throw "ARIA VM REDUCE reducer '$reducerName' does not preserve the declared accumulator and element types."
    }
    Assert-AriaRuntimeType $accumulatorType $InitialValue 'REDUCE initial accumulator'

    if (Get-Command Start-AriaEventOperation -ErrorAction SilentlyContinue) {
        $null = Start-AriaEventOperation -Name ('algorithm.reduce.' + $reducerName)
    }
    $batchStarted = $false
    if (Get-Command Start-AriaEventBatch -ErrorAction SilentlyContinue) {
        Start-AriaEventBatch -ChunkSize 32
        $batchStarted = $true
    }
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $inputCount = @($validation.values).Count
    $completed = 0
    $accumulator = $InitialValue
    $startRecord = [pscustomobject][ordered]@{kind='reduce';state='start';reducer=$reducerName;inputCount=$inputCount;line=[int]$Instruction.line}
    Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $startRecord -Domain algorithm -Phase reduce.start -State ACTIVE -Energy execution -Information $reducerName -Coherence 'reduce started'

    try {
        foreach ($value in @($validation.values)) {
            $accumulator = Invoke-AriaVmFunction -Context $Context -Name $reducerName -Arguments @($accumulator,$value) -CallDepth $CallDepth -Line ([int]$Instruction.line)
            $completed++
            $iterationRecord = [pscustomobject][ordered]@{kind='reduce';state='iteration';reducer=$reducerName;completed=$completed;inputCount=$inputCount;line=[int]$Instruction.line}
            Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $iterationRecord -Domain algorithm -Phase reduce.iteration -State INFO -Energy iteration -Information $reducerName -Coherence ("iteration {0} complete" -f $completed)
        }
        Assert-AriaRuntimeType $accumulatorType $accumulator 'REDUCE result accumulator'
        $clock.Stop()
        $completeRecord = [pscustomobject][ordered]@{kind='reduce';state='complete';reducer=$reducerName;completed=$completed;inputCount=$inputCount;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
        $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $completeRecord -Domain algorithm -Phase reduce.complete -State PASS -Energy completion -Information $reducerName -Coherence 'reduce contract passed' -PassThru
        $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind reduce -Target $reducerName -Line ([int]$Instruction.line) -Outcome completed -Counts ([pscustomobject][ordered]@{inputCount=$inputCount;completedCount=$completed;outputCount=1}) -TerminalEvent $terminalEvent
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        return $accumulator
    }
    catch {
        $originalError = $_
        $clock.Stop()
        try {
            $fractureRecord = [pscustomobject][ordered]@{kind='reduce';state='fracture';reducer=$reducerName;completed=$completed;inputCount=$inputCount;durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);line=[int]$Instruction.line}
            $terminalEvent = Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $fractureRecord -Domain algorithm -Phase reduce.fracture -State FAIL -Energy interruption -Information $reducerName -Coherence 'reduce reducer rejected' -PassThru
            $null = Add-AriaVmCardExecutionEvidence -Context $Context -Kind reduce -Target $reducerName -Line ([int]$Instruction.line) -Outcome fractured -Counts ([pscustomobject][ordered]@{inputCount=$inputCount;completedCount=$completed;outputCount=0}) -TerminalEvent $terminalEvent
        }
        catch {
            # Preserve the runtime fracture when evidence publication is unavailable.
        }
        if ($batchStarted) { Complete-AriaEventBatch; $batchStarted = $false }
        throw $originalError
    }
}

function Resolve-AriaRuntimePathForEffect {
    param([hashtable]$Active,[hashtable]$CapabilityMap,$Policy,[string]$Effect,[string]$WorkspaceRoot,[string]$RequestedPath)
    [string[]]$names=@($Active.Keys|ForEach-Object{[string]$_});[Array]::Sort($names,[StringComparer]::Ordinal);$authorized=New-Object System.Collections.Generic.List[object]
    foreach($name in $names){if(-not$CapabilityMap.ContainsKey($name)){continue};$cap=$CapabilityMap[$name];if([string]$cap.effect-ne$Effect){continue};$decision=Test-AriaPolicyAllowsCapability $Policy $cap;if(-not$decision.allowed){continue};try{$resolved=Resolve-AriaConfinedPath $WorkspaceRoot ([string]$cap.scope) $RequestedPath;$scope=([string]$cap.scope).Replace([char]92,[char]47).TrimEnd([char]47);$authorized.Add([pscustomobject]@{name=$name;score=$scope.Length;path=$resolved})}catch{continue}}
    if($authorized.Count-eq0){throw "ARIA VM has no active '$Effect' capability authorizing path '$RequestedPath'."};$best=$authorized[0];foreach($candidate in $authorized){if($candidate.score-gt$best.score-or($candidate.score-eq$best.score-and[string]::CompareOrdinal([string]$candidate.name,[string]$best.name)-lt0)){$best=$candidate}};return $best
}
function Assert-AriaTextEffectLimit { param($Policy,[string]$Effect,[AllowEmptyString()][string]$Text,[int64]$Default) $limit=Get-AriaPolicyMaxBytes $Policy $Effect $Default;$encoding=New-Object Text.UTF8Encoding($false);if([int64]$encoding.GetByteCount($Text)-gt$limit){throw "ARIA $Effect payload exceeds policy maxBytes ($limit)."} }
function Assert-AriaFileReadLimit { param($Policy,[string]$Path) $item=Get-Item -LiteralPath $Path -Force;if($item.PSIsContainer){throw "ARIA fs.read target is a directory: $Path"};$limit=Get-AriaPolicyMaxBytes $Policy 'fs.read' 4194304;if([int64]$item.Length-gt$limit){throw "ARIA fs.read target exceeds policy maxBytes ($limit): $Path"} }
function Assert-AriaFileWriteLimit { param($Policy,[string]$Text) Assert-AriaTextEffectLimit $Policy 'fs.write' $Text 1048576 }
function Save-AriaMemoryState { param([string]$Path,[hashtable]$Memories,$Policy) $ordered=[ordered]@{};foreach($memoryName in @($Memories.Keys|Sort-Object)){$entries=[ordered]@{};foreach($key in @($Memories[$memoryName].Keys|Sort-Object)){$entries[$key]=$Memories[$memoryName][$key]};$ordered[$memoryName]=[pscustomobject]$entries};$serialized=([pscustomobject]$ordered|ConvertTo-Json -Depth 50)+[Environment]::NewLine;Assert-AriaTextEffectLimit $Policy 'memory.write' $serialized 16777216;$temp=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp';try{Write-AriaUtf8NoBom $temp $serialized;Move-Item -LiteralPath $temp -Destination $Path -Force}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue} }

function Get-AriaConnectionRuntimeState {
    param($Context,[string]$Name)
    if(-not$Context.connectionMap.ContainsKey($Name)){throw "ARIA VM unknown connection '$Name'."}
    if(-not$Context.connectionStates.ContainsKey($Name)){throw "ARIA VM missing connection state '$Name'."}
    return $Context.connectionStates[$Name]
}
function Assert-AriaConnectionPhase {
    param($Context,[string]$Name,[string]$Expected,[int]$Line)
    $state=Get-AriaConnectionRuntimeState $Context $Name
    if([string]$state.phase-ne$Expected){throw "ARIA connection '$Name' expected phase '$Expected', received '$($state.phase)' at source line $Line."}
    return $state
}
function Add-AriaConnectionEvent {
    param($Context,[string]$Name,[string]$State,[int]$Line,[AllowEmptyString()][string]$Text='',$Approved=$null)
    $definition=$Context.connectionMap[$Name]
    $event=[pscustomobject][ordered]@{kind='connection';state=$State;connection=$Name;operator=[string]$definition.operator;agent=[string]$definition.agent;protocol=[string]$definition.protocol;text=$Text;line=$Line}
    if($null-ne$Approved){$event|Add-Member -NotePropertyName approved -NotePropertyValue ([bool]$Approved)}
    $semanticPhase = switch ($State) {
        'open' { 'open' }
        'intent' { 'intent' }
        'proposal' { 'proposal' }
        'consent' { 'consent' }
        default { 'closure' }
    }
    $semanticState = if ($State -eq 'consent' -and $null -ne $Approved -and -not [bool]$Approved) {
        'REJECT'
    }
    elseif ($State -eq 'open') { 'ACTIVE' }
    elseif ($State -in @('intent','proposal')) { 'INFO' }
    else { 'PASS' }
    Add-AriaVmRuntimeEvent `
        -Context $Context `
        -LegacyEvent $event `
        -Domain connection `
        -Phase $semanticPhase `
        -State $semanticState `
        -Energy lifecycle `
        -Information $Name `
        -Coherence $(if ($semanticState -eq 'REJECT') { 'consent withheld' } elseif ($State -eq 'closed') { 'connection closed' } else { "$State recorded" })
}

function Invoke-AriaBinaryRuntime {
    param([string]$Opcode, $Left, $Right, [int]$Line)

    switch ($Opcode) {
        'ADD' {
            if ($Left -is [string] -and $Right -is [string]) { return ([string]$Left + [string]$Right) }
            Assert-AriaRuntimeType 'Number' $Left "ADD line $Line"
            Assert-AriaRuntimeType 'Number' $Right "ADD line $Line"
            return ($Left + $Right)
        }
        'SUB' { Assert-AriaRuntimeType 'Number' $Left "SUB line $Line"; Assert-AriaRuntimeType 'Number' $Right "SUB line $Line"; return ($Left - $Right) }
        'MUL' { Assert-AriaRuntimeType 'Number' $Left "MUL line $Line"; Assert-AriaRuntimeType 'Number' $Right "MUL line $Line"; return ($Left * $Right) }
        'DIV' {
            Assert-AriaRuntimeType 'Number' $Left "DIV line $Line"
            Assert-AriaRuntimeType 'Number' $Right "DIV line $Line"
            if ([double]$Right -eq 0) { throw "ARIA division by zero at source line $Line." }
            return ([double]$Left / [double]$Right)
        }
        'EQ' { $leftValue=ConvertTo-AriaCanonicalValueProjection $Left;$rightValue=ConvertTo-AriaCanonicalValueProjection $Right;return ((ConvertTo-AriaJson ([pscustomobject]@{ v = $leftValue })) -eq (ConvertTo-AriaJson ([pscustomobject]@{ v = $rightValue }))) }
        'NE' { $leftValue=ConvertTo-AriaCanonicalValueProjection $Left;$rightValue=ConvertTo-AriaCanonicalValueProjection $Right;return ((ConvertTo-AriaJson ([pscustomobject]@{ v = $leftValue })) -ne (ConvertTo-AriaJson ([pscustomobject]@{ v = $rightValue }))) }
        'LT' { Assert-AriaRuntimeType 'Number' $Left "LT line $Line"; Assert-AriaRuntimeType 'Number' $Right "LT line $Line"; return ([double]$Left -lt [double]$Right) }
        'LE' { Assert-AriaRuntimeType 'Number' $Left "LE line $Line"; Assert-AriaRuntimeType 'Number' $Right "LE line $Line"; return ([double]$Left -le [double]$Right) }
        'GT' { Assert-AriaRuntimeType 'Number' $Left "GT line $Line"; Assert-AriaRuntimeType 'Number' $Right "GT line $Line"; return ([double]$Left -gt [double]$Right) }
        'GE' { Assert-AriaRuntimeType 'Number' $Left "GE line $Line"; Assert-AriaRuntimeType 'Number' $Right "GE line $Line"; return ([double]$Left -ge [double]$Right) }
        'AND' { Assert-AriaRuntimeType 'Bool' $Left "AND line $Line"; Assert-AriaRuntimeType 'Bool' $Right "AND line $Line"; return ([bool]$Left -and [bool]$Right) }
        'OR' { Assert-AriaRuntimeType 'Bool' $Left "OR line $Line"; Assert-AriaRuntimeType 'Bool' $Right "OR line $Line"; return ([bool]$Left -or [bool]$Right) }
        default { throw "ARIA VM unknown binary opcode '$Opcode'." }
    }
}

function Invoke-AriaInstructionSequence {
    param([object[]]$Instructions,$Context,$Scopes,[hashtable]$ActiveCapabilities,[int]$CallDepth=0)
    if($CallDepth-gt64){throw 'ARIA VM call depth exceeded 64.'};$stack=New-Object Collections.Stack
    for($ip=0;$ip-lt$Instructions.Count;$ip++){
        $ins=$Instructions[$ip];$op=[string]$ins.op
        switch($op){
            'PUSH_CONST'{$stack.Push($Context.bytecode.constants[[int]$ins.arg])}
            'LOAD'{$result=Get-AriaScopedValue $Scopes ([string]$ins.arg);if(-not$result.found){throw "ARIA VM unknown variable '$($ins.arg)' at source line $($ins.line)."};$stack.Push($result.value)}
            'STORE'{$value=Pop-AriaRuntime $stack "STORE line $($ins.line)";Assert-AriaRuntimeType ([string]$ins.type) $value "variable $($ins.arg)";$Scopes[$Scopes.Count-1][[string]$ins.arg]=$value}
            'SET'{$value=Pop-AriaRuntime $stack "SET line $($ins.line)";Set-AriaScopedValue $Scopes ([string]$ins.arg) $value}
            {$_-in@('ADD','SUB','MUL','DIV','EQ','NE','LT','LE','GT','GE','AND','OR')}{$right=Pop-AriaRuntime $stack "$op line $($ins.line)";$left=Pop-AriaRuntime $stack "$op line $($ins.line)";$stack.Push((Invoke-AriaBinaryRuntime $op $left $right ([int]$ins.line)))}
            'NOT'{$value=Pop-AriaRuntime $stack "NOT line $($ins.line)";Assert-AriaRuntimeType 'Bool' $value "NOT line $($ins.line)";$stack.Push(-not[bool]$value)}
            'NEG'{$value=Pop-AriaRuntime $stack "NEG line $($ins.line)";Assert-AriaRuntimeType 'Number' $value "NEG line $($ins.line)";$stack.Push(-$value)}
            'EMIT'{
                Assert-AriaRuntimeEffect $Context.policy 'console.emit'
                $value=Pop-AriaRuntime $stack "EMIT line $($ins.line)"
                $text=ConvertTo-AriaRuntimeText $value
                Assert-AriaTextEffectLimit $Context.policy 'console.emit' $text 262144
                $Context.outputs.Add($text)
                $null = Publish-AriaVmSemanticEvent -Context $Context -Domain vm -Phase output -State INFO -Energy transmission -Information $text -Coherence 'output emitted' -Data ([pscustomobject][ordered]@{kind='output';line=[int]$ins.line})
                if(-not$Context.passThru){if(Get-Command Write-AriaStream -ErrorAction SilentlyContinue){Write-AriaStream $text}else{Write-Host "∿ $text"}}
            }
            'SIGNAL'{
                Assert-AriaRuntimeEffect $Context.policy 'console.emit'
                $value=Pop-AriaRuntime $stack "SIGNAL line $($ins.line)"
                $text=ConvertTo-AriaRuntimeText $value
                Assert-AriaTextEffectLimit $Context.policy 'console.emit' $text 262144
                $state=[string]$ins.state
                $legacy=[pscustomobject][ordered]@{kind='signal';state=$state;text=$text;line=[int]$ins.line}
                Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $legacy -Domain vm -Phase signal -State INFO -Energy execution -Information $text -Coherence "declared $state signal observed"
            }
            'MEM_SET'{Assert-AriaRuntimeEffect $Context.policy 'memory.write';$value=Pop-AriaRuntime $stack "MEM_SET line $($ins.line)";$expected=[string]$Context.memoryTypes[[string]$ins.memory][[string]$ins.key];Assert-AriaRuntimeType $expected $value "memory $($ins.memory).$($ins.key)";$Context.memories[[string]$ins.memory][[string]$ins.key]=$value;$Context.memoryDirty=$true}
            'MEM_GET'{Assert-AriaRuntimeEffect $Context.policy 'memory.read';if(-not$Context.memories.ContainsKey([string]$ins.memory)-or-not$Context.memories[[string]$ins.memory].ContainsKey([string]$ins.key)){throw "ARIA VM missing memory '$($ins.memory).$($ins.key)'."};$stack.Push($Context.memories[[string]$ins.memory][[string]$ins.key])}
            'REQUIRE_CAP'{$name=[string]$ins.arg;if(-not$Context.capabilityMap.ContainsKey($name)){throw "ARIA VM unknown capability '$name'."};$decision=Test-AriaPolicyAllowsCapability $Context.policy $Context.capabilityMap[$name];if(-not$decision.allowed){throw "ARIA VM denied capability '$name': $($decision.reason)"};$ActiveCapabilities[$name]=$true}
            'ASSERT_TRUE'{$value=Pop-AriaRuntime $stack "ASSERT_TRUE line $($ins.line)";Assert-AriaRuntimeType 'Bool' $value "assert line $($ins.line)";if(-not[bool]$value){throw "ARIA assertion failed at source line $($ins.line)."}}
            'FS_READ'{$path=[string](Pop-AriaRuntime $stack "FS_READ line $($ins.line)");$auth=Resolve-AriaRuntimePathForEffect $ActiveCapabilities $Context.capabilityMap $Context.policy 'fs.read' $Context.workspaceRoot $path;Assert-AriaFileReadLimit $Context.policy $auth.path;$Scopes[$Scopes.Count-1][[string]$ins.arg]=Read-AriaUtf8Text $auth.path}
            'FS_WRITE'{$value=[string](Pop-AriaRuntime $stack "FS_WRITE line $($ins.line)");$path=[string](Pop-AriaRuntime $stack "FS_WRITE line $($ins.line)");$auth=Resolve-AriaRuntimePathForEffect $ActiveCapabilities $Context.capabilityMap $Context.policy 'fs.write' $Context.workspaceRoot $path;Assert-AriaFileWriteLimit $Context.policy $value;Write-AriaUtf8NoBom $auth.path $value}
            'AGENT_DISPATCH'{
                Assert-AriaRuntimeEffect $Context.policy 'agent.dispatch'
                $agent=[string]$ins.agent
                if(-not$Context.agentMap.ContainsKey($agent)){throw "ARIA VM unknown agent '$agent'."}
                $task=[string](Pop-AriaRuntime $stack "AGENT_DISPATCH line $($ins.line)")
                $legacy=[pscustomobject][ordered]@{kind='agent';state='pulse';agent=$agent;text=$task;line=[int]$ins.line}
                Add-AriaVmRuntimeEvent -Context $Context -LegacyEvent $legacy -Domain agent -Phase dispatch -State ACTIVE -Energy delegation -Information $agent -Coherence 'task dispatched'
            }
            'CONNECT_OPEN'{Assert-AriaRuntimeEffect $Context.policy 'console.emit';$name=[string]$ins.connection;$state=Assert-AriaConnectionPhase $Context $name 'closed' ([int]$ins.line);$state.phase='open';$state.approved=$null;$definition=$Context.connectionMap[$name];Add-AriaConnectionEvent $Context $name 'open' ([int]$ins.line)}
            'CONNECT_INTENT'{Assert-AriaRuntimeEffect $Context.policy 'console.emit';$name=[string]$ins.connection;$state=Assert-AriaConnectionPhase $Context $name 'open' ([int]$ins.line);$value=Pop-AriaRuntime $stack "CONNECT_INTENT line $($ins.line)";Assert-AriaRuntimeType 'Text' $value "connection intent line $($ins.line)";$text=[string]$value;$state.phase='intent';Add-AriaConnectionEvent $Context $name 'intent' ([int]$ins.line) $text}
            'CONNECT_PROPOSE'{Assert-AriaRuntimeEffect $Context.policy 'console.emit';$name=[string]$ins.connection;$state=Assert-AriaConnectionPhase $Context $name 'intent' ([int]$ins.line);$value=Pop-AriaRuntime $stack "CONNECT_PROPOSE line $($ins.line)";Assert-AriaRuntimeType 'Text' $value "connection proposal line $($ins.line)";$text=[string]$value;$state.phase='proposal';Add-AriaConnectionEvent $Context $name 'proposal' ([int]$ins.line) $text}
            'CONNECT_CONSENT'{Assert-AriaRuntimeEffect $Context.policy 'console.emit';$name=[string]$ins.connection;$state=Assert-AriaConnectionPhase $Context $name 'proposal' ([int]$ins.line);$value=Pop-AriaRuntime $stack "CONNECT_CONSENT line $($ins.line)";Assert-AriaRuntimeType 'Bool' $value "connection consent line $($ins.line)";$approved=[bool]$value;$state.phase='consent';$state.approved=$approved;Add-AriaConnectionEvent $Context $name 'consent' ([int]$ins.line) '' $approved}
            'CONNECT_CLOSE'{Assert-AriaRuntimeEffect $Context.policy 'console.emit';$name=[string]$ins.connection;$state=Assert-AriaConnectionPhase $Context $name 'consent' ([int]$ins.line);$approved=[bool]$state.approved;$state.phase='closed';Add-AriaConnectionEvent $Context $name 'closed' ([int]$ins.line) '' $approved}
            'CALL'{$name=[string]$ins.name;$argCount=[int]$ins.argCount;if($argCount-eq0){[object[]]$args=@()}else{[object[]]$args=New-Object object[] $argCount};for($a=$args.Length-1;$a-ge0;$a--){$args[$a]=Pop-AriaRuntime $stack "CALL $name line $($ins.line)"};$stack.Push((Invoke-AriaVmFunction -Context $Context -Name $name -Arguments $args -CallDepth $CallDepth -Line ([int]$ins.line)))}
            'MAP'{$sequenceValue=Pop-AriaRuntime $stack "MAP line $($ins.line)";$stack.Push((Invoke-AriaVmMap -Context $Context -SequenceValue $sequenceValue -Instruction $ins -CallDepth $CallDepth))}
            'FILTER'{$sequenceValue=Pop-AriaRuntime $stack "FILTER line $($ins.line)";$stack.Push((Invoke-AriaVmFilter -Context $Context -SequenceValue $sequenceValue -Instruction $ins -CallDepth $CallDepth))}
            'REDUCE'{$initialValue=Pop-AriaRuntime $stack "REDUCE initial line $($ins.line)";$sequenceValue=Pop-AriaRuntime $stack "REDUCE sequence line $($ins.line)";$stack.Push((Invoke-AriaVmReduce -Context $Context -SequenceValue $sequenceValue -InitialValue $initialValue -Instruction $ins -CallDepth $CallDepth))}
            'IF'{$condition=Pop-AriaRuntime $stack "IF line $($ins.line)";Assert-AriaRuntimeType 'Bool' $condition "if line $($ins.line)";Add-AriaScope $Scopes;try{$branch=if([bool]$condition){@($ins.then)}else{@($ins.else)};$result=Invoke-AriaInstructionSequence $branch $Context $Scopes (Copy-AriaRuntimeTable $ActiveCapabilities) $CallDepth}finally{Remove-AriaScope $Scopes};if($result.control-ne'normal'){return $result}}
            'REPEAT'{$raw=Pop-AriaRuntime $stack "REPEAT line $($ins.line)";Assert-AriaRuntimeType 'Number' $raw "repeat line $($ins.line)";$count=[double]$raw;if($count-lt0-or$count-gt[int]$ins.max-or[math]::Floor($count)-ne$count){throw "ARIA repeat count must be an integer from 0 through $($ins.max) at source line $($ins.line)."};for($iteration=0;$iteration-lt[int]$count;$iteration++){Add-AriaScope $Scopes @{([string]$ins.iterator)=[long]$iteration};try{$result=Invoke-AriaInstructionSequence @($ins.body) $Context $Scopes (Copy-AriaRuntimeTable $ActiveCapabilities) $CallDepth}finally{Remove-AriaScope $Scopes};if($result.control-ne'normal'){return $result}}}
            'RETURN'{$value=if([bool]$ins.hasValue){Pop-AriaRuntime $stack "RETURN line $($ins.line)"}else{$null};if($stack.Count-ne0){throw "ARIA VM function return left $($stack.Count) operand(s) on the stack."};return [pscustomobject]@{control='return';value=$value}}
            'HALT'{if($stack.Count-ne0){throw "ARIA VM halt left $($stack.Count) operand(s) on the stack."};return [pscustomobject]@{control='halt';value=$null}}
            default{throw "ARIA VM unknown opcode '$op' at instruction $ip."}
        }
    }
    if($stack.Count-ne0){throw "ARIA VM sequence terminated with a non-empty operand stack ($($stack.Count))."};return [pscustomobject]@{control='normal';value=$null}
}

function Invoke-AriaContainer {
    param($Container,[string]$PolicyPath,[string]$WorkspaceRoot=(Get-AriaRepositoryRoot),[switch]$PassThru)
    if(-not(Test-Path -LiteralPath $WorkspaceRoot -PathType Container)){throw "ARIA VM workspace does not exist: $WorkspaceRoot"};$WorkspaceRoot=[IO.Path]::GetFullPath((Resolve-Path -LiteralPath $WorkspaceRoot).Path);$bytecode=$Container.bytecode;$verification=Test-AriaBytecodeModel $bytecode;if(-not$verification.valid){throw('ARIA VM rejected unverified bytecode: '+($verification.errors-join'; '))};$policy=Get-AriaPolicy $PolicyPath;$validation=Test-AriaPolicyDocument $policy;if(-not$validation.valid){throw('ARIA VM requires a valid deny-by-default policy: '+($validation.errors-join'; '))}
    $capabilityMap=Get-AriaCapabilityMapFromBytecode $bytecode;$agentMap=@{};foreach($agent in @($bytecode.agents)){$agentMap[[string]$agent.name]=$agent};$connectionMap=@{};$connectionStates=@{};foreach($connection in @($bytecode.connections)){$name=[string]$connection.name;$connectionMap[$name]=$connection;$connectionStates[$name]=[pscustomobject]@{phase='closed';approved=$null}};$functionMap=@{};foreach($fn in @($bytecode.functions)){$functionMap[[string]$fn.name]=$fn};$outputs=New-Object System.Collections.Generic.List[string];$events=New-Object System.Collections.Generic.List[object];$memories=@{};$memoryTypes=@{}
    foreach($memory in @($bytecode.memories)){$memories[[string]$memory.name]=ConvertTo-AriaHashtable $memory.values;$types=@{};foreach($property in $memory.types.PSObject.Properties){$types[$property.Name]=[string]$property.Value};$memoryTypes[[string]$memory.name]=$types}
    $stateRelative='.aria/state/'+$bytecode.programName+'.memory.json';$statePath=Resolve-AriaConfinedPath $WorkspaceRoot '.' $stateRelative;$stateRoot=Split-Path -Parent $statePath
    if(Test-Path -LiteralPath $statePath){$info=Get-Item -LiteralPath $statePath -Force;$limit=Get-AriaPolicyMaxBytes $policy 'memory.read' 16777216;if([int64]$info.Length-gt$limit){throw "ARIA memory state exceeds policy maxBytes ($limit): $statePath"};$persisted=ConvertTo-AriaHashtable (Read-AriaUtf8Text $statePath|ConvertFrom-Json);foreach($memoryName in $persisted.Keys){if(-not$memories.ContainsKey($memoryName)){throw "ARIA persisted state contains undeclared memory '$memoryName'."};foreach($key in $persisted[$memoryName].Keys){if(-not$memoryTypes[$memoryName].ContainsKey($key)){throw "ARIA persisted state contains undeclared memory key '$memoryName.$key'."};Assert-AriaRuntimeType ([string]$memoryTypes[$memoryName][$key]) $persisted[$memoryName][$key] "persisted memory $memoryName.$key";$memories[$memoryName][$key]=$persisted[$memoryName][$key]}}}
    $artifactHashProperty=$Container.PSObject.Properties['artifactHash'];if($null-eq$artifactHashProperty-or[string]::IsNullOrWhiteSpace([string]$artifactHashProperty.Value)){throw 'ARIA VM requires an exact artifact identity for execution evidence.'};$executionEvidence=New-Object System.Collections.Generic.List[object];$glyphRegistry=Read-AriaGlyphCardRegistry;$policyDigest=Get-AriaSha256File -Path (Resolve-Path -LiteralPath $PolicyPath).Path
    $context=[pscustomobject]@{bytecode=$bytecode;artifactHash=[string]$artifactHashProperty.Value;policy=$policy;policyDigest=$policyDigest;glyphRegistry=$glyphRegistry;executionEvidence=$executionEvidence;workspaceRoot=$WorkspaceRoot;capabilityMap=$capabilityMap;agentMap=$agentMap;connectionMap=$connectionMap;connectionStates=$connectionStates;functionMap=$functionMap;outputs=$outputs;events=$events;memories=$memories;memoryTypes=$memoryTypes;memoryDirty=$false;passThru=[bool]$PassThru}
    $scopes=New-AriaScopeStack;$result=Invoke-AriaInstructionSequence @($bytecode.instructions) $context $scopes @{} 0;if($result.control-ne'halt'){throw 'ARIA entry flow terminated without HALT.'}
    foreach($name in @($connectionStates.Keys)){if([string]$connectionStates[$name].phase-ne'closed'){throw "ARIA connection '$name' terminated in phase '$($connectionStates[$name].phase)' instead of closed."}}
    if($context.memoryDirty){if(-not(Test-Path -LiteralPath $stateRoot)){New-Item -ItemType Directory -Path $stateRoot -Force|Out-Null};Save-AriaMemoryState $statePath $memories $policy}
    return [pscustomobject][ordered]@{programName=$bytecode.programName;outputs=$outputs.ToArray();events=$events.ToArray();executionEvidence=$executionEvidence.ToArray();variables=$scopes[0];memories=$memories;connections=$connectionStates;graphs=$bytecode.graphs;effectGraph=$bytecode.effectGraph;statePath=$statePath;memoryPersisted=$context.memoryDirty}
}
function Invoke-AriaArtifact { param([string]$Path,[string]$PolicyPath,[string]$WorkspaceRoot=(Get-AriaRepositoryRoot),[switch]$PassThru) return(Invoke-AriaContainer (Read-AriaContainer $Path) $PolicyPath $WorkspaceRoot -PassThru:$PassThru) }
Export-ModuleMember -Function Invoke-AriaContainer,Invoke-AriaArtifact
