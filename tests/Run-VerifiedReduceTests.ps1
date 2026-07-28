[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$policyPath = Join-Path $root 'aria.policy.json'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aria-verified-reduce-' + [guid]::NewGuid().ToString('N'))

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GlyphMemory.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking

$policy = Get-AriaPolicy -PolicyPath $policyPath
$script:Passed = 0
$script:Failed = 0
$script:Expected = 27

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Equal {
    param($Expected,$Actual,[string]$Message)
    $expectedJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=$Expected})
    $actualJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=$Actual})
    if ($expectedJson -ne $actualJson) { throw "$Message Expected=$Expected Actual=$Actual" }
}
function Test-ReduceCase {
    param([string]$Name,[scriptblock]$Body)
    try {
        & $Body
        $script:Passed++
        Write-Host ("◆  {0}" -f $Name) -ForegroundColor Green
    }
    catch {
        $script:Failed++
        Write-Host ("⬗  {0} · {1}" -f $Name,$_.Exception.Message) -ForegroundColor Magenta
    }
}
function Write-TestSource {
    param([string]$Name,[string]$Source)
    $path = Join-Path $tempRoot $Name
    $text = $Source.Replace("`r`n","`n").Replace("`r","`n")
    if (-not $text.EndsWith("`n")) { $text += "`n" }
    [IO.File]::WriteAllText($path,$text,[Text.UTF8Encoding]::new($false))
    $path
}
function Get-Diagnostics {
    param([string]$Source)
    $parsed = Parse-AriaSource -Source $Source -SourceName '<verified-reduce-diagnostic>'
    $semantic = Test-AriaSemantics -ParseResult $parsed -Policy $policy
    @(Get-AriaErrorDiagnostics -Diagnostics $semantic.diagnostics)
}
function Assert-Diagnostic {
    param([object[]]$Diagnostics,[string]$Code,[string]$Message)
    Assert-True ($Code -in @($Diagnostics.code)) $Message
}
function Copy-JsonValue {
    param($Value)
    $Value | ConvertTo-Json -Depth 100 | ConvertFrom-Json
}

$validSource = @'
aria 0.4.0
module VerifiedReduce version 0.9.0
program VerifiedReduce version 0.9.0
entry Main

function Add(total: Number, value: Number) -> Number {
  ↩ total + value
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3, 4]
  let total: Number = Σ(values, Add, 0)
  halt
}
'@

$subtractSource = $validSource.Replace('VerifiedReduce','VerifiedReduceSubtract').Replace(
    'function Add(total: Number, value: Number) -> Number {' + "`n" + '  ↩ total + value',
    'function Add(total: Number, value: Number) -> Number {' + "`n" + '  ↩ total - value'
).Replace('[1, 2, 3, 4]','[1, 2, 3]').Replace('Σ(values, Add, 0)','Σ(values, Add, 20)')

$emptySource = $validSource.Replace('VerifiedReduce','VerifiedReduceEmpty').Replace('[1, 2, 3, 4]','[]').Replace('Σ(values, Add, 0)','Σ(values, Add, 7)')
$oneSource = $validSource.Replace('VerifiedReduce','VerifiedReduceOne').Replace('[1, 2, 3, 4]','[5]').Replace('Σ(values, Add, 0)','Σ(values, Add, 10)')

$crossTypeSource = @'
aria 0.4.0
module VerifiedReduceCrossType version 0.9.0
program VerifiedReduceCrossType version 0.9.0
entry Main

function Count(total: Number, value: Text) -> Number {
  ↩ total + 1
}

flow Main {
  let values: Sequence<Text> = ["a", "b", "c"]
  let total: Number = Σ(values, Count, 0)
  halt
}
'@

$fractureSource = @'
aria 0.4.0
module VerifiedReduceFracture version 0.9.0
program VerifiedReduceFracture version 0.9.0
entry Main

function Step(total: Number, value: Number) -> Number {
  assert value < 2
  ↩ total + value
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let total: Number = Σ(values, Step, 0)
  halt
}
'@

$compositionSource = @'
aria 0.4.0
module VerifiedAlgorithmPipeline version 0.9.0
program VerifiedAlgorithmPipeline version 0.9.0
entry Main

function Double(value: Number) -> Number {
  ↩ value * 2
}

function Positive(value: Number) -> Bool {
  ↩ value > 0
}

function Add(total: Number, value: Number) -> Number {
  ↩ total + value
}

flow Main {
  let values: Sequence<Number> = [-2, -1, 1, 2]
  let total: Number = Σ(⫰(⨯(values, Double), Positive), Add, 0)
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $validPath = Write-TestSource 'verified-reduce.aria' $validSource
    $validTwinPath = Write-TestSource 'verified-reduce-twin.aria' $validSource
    $subtractPath = Write-TestSource 'verified-reduce-subtract.aria' $subtractSource
    $emptyPath = Write-TestSource 'verified-reduce-empty.aria' $emptySource
    $onePath = Write-TestSource 'verified-reduce-one.aria' $oneSource
    $crossTypePath = Write-TestSource 'verified-reduce-cross-type.aria' $crossTypeSource
    $fracturePath = Write-TestSource 'verified-reduce-fracture.aria' $fractureSource
    $compositionPath = Write-TestSource 'verified-algorithm-pipeline.aria' $compositionSource

    $validGate = Invoke-AriaGate -SourcePath $validPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $validTwinGate = Invoke-AriaGate -SourcePath $validTwinPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $subtractGate = Invoke-AriaGate -SourcePath $subtractPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $emptyGate = Invoke-AriaGate -SourcePath $emptyPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $oneGate = Invoke-AriaGate -SourcePath $onePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $crossTypeGate = Invoke-AriaGate -SourcePath $crossTypePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $fractureGate = Invoke-AriaGate -SourcePath $fracturePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $compositionGate = Invoke-AriaGate -SourcePath $compositionPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet

    Write-Host ''
    Write-Host '⌬  ARIA / VERIFIED REDUCE ALPHA.9' -ForegroundColor Cyan
    Write-Host '⧉  verified-reduce lattice ×27' -ForegroundColor DarkGray

    Test-ReduceCase 'algorithm.reduce card is sealed and verified' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        $card = Get-AriaGlyphCard -Id 'algorithm.reduce' -Registry $registry
        Assert-Equal 'verified' $card.status 'Reduce card status mismatch.'
        Assert-True (Test-AriaGlyphCard $card).valid 'Reduce card identity is invalid.'
    }
    Test-ReduceCase 'reduce glyph forms a dedicated canonical AST node' {
        $parsed = Parse-AriaSource -Source $validSource -SourceName '<reduce-ast>'
        $expression = $parsed.model.flows[0].statements[1].expression
        Assert-Equal 'reduce' $expression.kind 'Reduce AST kind mismatch.'
        Assert-Equal 'Add' $expression.reducer 'Reduce reducer identity mismatch.'
        Assert-Equal 'literal' $expression.initial.kind 'Reduce initial expression missing.'
    }
    Test-ReduceCase 'reduce result type follows the initial accumulator' {
        $instruction = @($crossTypeGate.bytecode.instructions | Where-Object op -eq 'REDUCE')[0]
        Assert-Equal 'Number' $instruction.accumulatorType 'Reduce accumulator type mismatch.'
        Assert-Equal 'Sequence<Text>' $instruction.sequenceType 'Reduce sequence type mismatch.'
    }
    Test-ReduceCase 'unknown reducer is rejected' {
        Assert-Diagnostic (Get-Diagnostics ($validSource.Replace('Σ(values, Add, 0)','Σ(values, Missing, 0)'))) 'ARIA2142' 'Unknown reducer diagnostic missing.'
    }
    Test-ReduceCase 'reducer must be binary' {
        $source = $validSource.Replace('function Add(total: Number, value: Number)', 'function Add(total: Number)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2143' 'Binary reducer diagnostic missing.'
    }
    Test-ReduceCase 'reducer accumulator input must match initial type' {
        $source = $validSource.Replace('total: Number, value: Number', 'total: Text, value: Number')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2144' 'Accumulator input diagnostic missing.'
    }
    Test-ReduceCase 'reducer element input must match sequence type' {
        $source = $validSource.Replace('total: Number, value: Number', 'total: Number, value: Text')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2145' 'Element input diagnostic missing.'
    }
    Test-ReduceCase 'reducer return must preserve accumulator type' {
        $source = $validSource.Replace('-> Number {', '-> Bool {').Replace('↩ total + value', '↩ true')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2146' 'Accumulator return diagnostic missing.'
    }
    Test-ReduceCase 'directly effectful reducer is rejected' {
        $source = $validSource.Replace('↩ total + value', "emit value`n  ↩ total + value")
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2147' 'Direct purity diagnostic missing.'
    }
    Test-ReduceCase 'transitively effectful reducer is rejected' {
        $source = $validSource.Replace(
            'function Add(total: Number, value: Number) -> Number {',
            "function Effectful(value: Number) -> Number {`n  emit value`n  ↩ value`n}`n`nfunction Add(total: Number, value: Number) -> Number {"
        ).Replace('↩ total + value', '↩ total + Effectful(value)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2147' 'Transitive purity diagnostic missing.'
    }
    Test-ReduceCase 'compiler emits one explicit REDUCE contract' {
        $reductions = @($validGate.bytecode.instructions | Where-Object op -eq 'REDUCE')
        Assert-Equal 1 $reductions.Count 'REDUCE instruction count mismatch.'
        Assert-Equal 'Add' $reductions[0].reducer 'REDUCE reducer metadata mismatch.'
        Assert-Equal 'Sequence<Number>' $reductions[0].sequenceType 'REDUCE sequence metadata mismatch.'
        Assert-Equal 'Number' $reductions[0].accumulatorType 'REDUCE accumulator metadata mismatch.'
    }
    Test-ReduceCase 'effect graph records reducer as a call' {
        $entry = Get-AriaEffectSummary -Graph $validGate.bytecode.effectGraph -Name '$entry'
        Assert-True ('Add' -in @($entry.calls)) 'Entry effect summary omitted reducer.'
    }
    Test-ReduceCase 'bytecode verifier rejects unknown reducer' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.instructions | Where-Object op -eq 'REDUCE')[0]).reducer = 'Missing'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'Unknown bytecode reducer was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'unknown reducer') 'Unknown reducer verifier boundary missing.'
    }
    Test-ReduceCase 'bytecode verifier rejects reversed reducer parameters' {
        $mutated = Copy-JsonValue $crossTypeGate.bytecode
        $fn = @($mutated.functions | Where-Object name -eq 'Count')[0]
        $first = $fn.parameters[0].type
        $fn.parameters[0].type = $fn.parameters[1].type
        $fn.parameters[1].type = $first
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'Reversed reducer parameters were accepted.'
        Assert-True (($verification.errors -join ' ') -match 'accumulator input') 'Reducer-order verifier boundary missing.'
    }
    Test-ReduceCase 'bytecode verifier rejects accumulator output drift' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.functions | Where-Object name -eq 'Add')[0]).returnType = 'Bool'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'Reducer output drift was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'does not preserve') 'Reducer-output verifier boundary missing.'
    }
    Test-ReduceCase 'bytecode verifier independently rejects false purity' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.functions | Where-Object name -eq 'Add')[0]).effectSummary.purity = 'effectful'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'False reducer purity was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'not proven pure') 'REDUCE purity verifier boundary missing.'
    }
    Test-ReduceCase 'runtime reduce computes a deterministic total' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 10 $result.variables.total 'Reduce total mismatch.'
    }
    Test-ReduceCase 'non-associative reducer proves strict left-fold order' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $subtractGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 14 $result.variables.total 'Reduce did not execute ((20-1)-2)-3.'
    }
    Test-ReduceCase 'empty reduce returns explicit initial without iteration' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $emptyGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 7 $result.variables.total 'Empty reduce did not return its initial value.'
        Assert-Equal 0 @($result.events | Where-Object { $_.kind -eq 'reduce' -and $_.state -eq 'iteration' }).Count 'Empty reduce invented an iteration.'
    }
    Test-ReduceCase 'single-element reduce invokes reducer exactly once' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $oneGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 15 $result.variables.total 'Single-element reduce mismatch.'
        Assert-Equal 1 @($result.events | Where-Object { $_.kind -eq 'reduce' -and $_.state -eq 'iteration' }).Count 'Single reduce iteration mismatch.'
    }
    Test-ReduceCase 'accumulator type may differ from sequence element type' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $crossTypeGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 3 $result.variables.total 'Cross-type accumulator mismatch.'
        Assert-Equal 'Number' (Get-AriaCanonicalValueType $result.variables.total) 'Accumulator type changed.'
    }
    Test-ReduceCase 'reduce event sequence reports completed calls' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        $states = @($result.events | Where-Object kind -eq 'reduce' | ForEach-Object state)
        Assert-Equal @('start','iteration','iteration','iteration','iteration','complete') $states 'Reduce event order mismatch.'
        $complete = @($result.events | Where-Object { $_.kind -eq 'reduce' -and $_.state -eq 'complete' })[0]
        Assert-Equal 4 $complete.completed 'Reduce completed count mismatch.'
        Assert-Equal 4 $complete.inputCount 'Reduce input count mismatch.'
        Assert-True ([int]$complete.durationMs -ge 0) 'Reduce duration is not measured.'
    }
    Test-ReduceCase 'reduce evidence excludes elements and accumulator values' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        foreach ($event in @($result.events | Where-Object kind -eq 'reduce')) {
            foreach ($forbidden in @('value','values','initial','accumulator','element')) {
                Assert-True ($null -eq $event.PSObject.Properties[$forbidden]) "Reduce evidence exposed '$forbidden'."
            }
            Assert-True ([string]$event.eventDigest -match '^[a-f0-9]{64}$') 'Reduce evidence lacks Event Spine identity.'
        }
    }
    Test-ReduceCase 'runtime reducer failure emits bounded fracture evidence' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $rejected = $false
        try {
            $null = Invoke-AriaContainer -Container (Read-AriaContainerBytes $fractureGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        }
        catch { $rejected = $true }
        Assert-True $rejected 'Failing reducer completed.'
        $fracture = @(Get-AriaEventBuffer | Where-Object { $_.domain -eq 'algorithm' -and $_.phase -eq 'reduce.fracture' })
        Assert-Equal 1 $fracture.Count 'Reduce fracture event missing.'
        Assert-Equal 1 $fracture[0].data.completed 'Reduce fracture completed count mismatch.'
    }
    Test-ReduceCase 'reduce compilation and execution are deterministic' {
        Assert-Equal $validGate.buildHash $validTwinGate.buildHash 'Equivalent reduce builds diverged.'
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $one = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $two = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validTwinGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal $one.variables.total $two.variables.total 'Equivalent reduce executions diverged.'
    }
    Test-ReduceCase 'map filter and reduce compose through explicit boundaries' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $compositionGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 6 $result.variables.total 'Map-filter-reduce pipeline mismatch.'
        foreach ($kind in @('map','filter','reduce')) {
            Assert-Equal 1 @($result.events | Where-Object { $_.kind -eq $kind -and $_.state -eq 'complete' }).Count "Pipeline lost $kind completion."
        }
    }
    Test-ReduceCase 'reduce adds computation but no authority' {
        Assert-Equal 40 (Get-AriaOpcodeRegistry).Count 'REDUCE opcode registry count mismatch.'
        Assert-Equal 0 @($validGate.bytecode.capabilities).Count 'Reduce introduced a capability.'
        $registry = Read-AriaGlyphCardRegistry -Root $root
        foreach ($id in @('algorithm.map','algorithm.filter','algorithm.reduce')) {
            Assert-Equal 'verified' (Get-AriaGlyphCard -Id $id -Registry $registry).status "Algorithm '$id' was not admitted."
            Assert-Equal 0 @((Get-AriaGlyphCard -Id $id -Registry $registry).capabilities).Count "Algorithm '$id' introduced authority."
        }
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw "Verified Reduce test count diverged. Expected=$script:Expected Observed=$($script:Passed + $script:Failed)"
    }
    Write-Host ("⧉  verified-reduce lattice {0}/{1} · {2}" -f $script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'})) -ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
    if ($script:Failed -gt 0) { throw "Verified Reduce lattice failed: $script:Failed failure(s)." }
}
finally {
    if (Test-Path -LiteralPath $tempRoot -PathType Container) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
