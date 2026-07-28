[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$policyPath = Join-Path $root 'aria.policy.json'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aria-verified-filter-' + [guid]::NewGuid().ToString('N'))

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
$script:Expected = 24

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
function Test-FilterCase {
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
    $parsed = Parse-AriaSource -Source $Source -SourceName '<verified-filter-diagnostic>'
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
module VerifiedFilter version 0.8.0
program VerifiedFilter version 0.8.0
entry Main

function Positive(value: Number) -> Bool {
  ↩ value > 0
}

flow Main {
  let values: Sequence<Number> = [-2, 0, 3, 4]
  let selected: Sequence<Number> = ⫰(values, Positive)
  halt
}
'@

$emptySource = @'
aria 0.4.0
module VerifiedFilterEmpty version 0.8.0
program VerifiedFilterEmpty version 0.8.0
entry Main

function Positive(value: Number) -> Bool {
  ↩ value > 0
}

flow Main {
  let values: Sequence<Number> = []
  let selected: Sequence<Number> = ⫰(values, Positive)
  halt
}
'@

$allSource = @'
aria 0.4.0
module VerifiedFilterAll version 0.8.0
program VerifiedFilterAll version 0.8.0
entry Main

function Keep(value: Number) -> Bool {
  ↩ true
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let selected: Sequence<Number> = ⫰(values, Keep)
  halt
}
'@

$noneSource = $allSource.Replace('VerifiedFilterAll','VerifiedFilterNone').Replace('↩ true','↩ false')

$compositionSource = @'
aria 0.4.0
module VerifiedFilterComposition version 0.8.0
program VerifiedFilterComposition version 0.8.0
entry Main

function Double(value: Number) -> Number {
  ↩ value * 2
}

function AboveTwo(value: Number) -> Bool {
  ↩ value > 2
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let selected: Sequence<Number> = ⫰(⨯(values, Double), AboveTwo)
  halt
}
'@

$fractureSource = @'
aria 0.4.0
module VerifiedFilterFracture version 0.8.0
program VerifiedFilterFracture version 0.8.0
entry Main

function BelowTwo(value: Number) -> Bool {
  assert value < 2
  ↩ true
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let selected: Sequence<Number> = ⫰(values, BelowTwo)
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $validPath = Write-TestSource 'verified-filter.aria' $validSource
    $validTwinPath = Write-TestSource 'verified-filter-twin.aria' $validSource
    $emptyPath = Write-TestSource 'verified-filter-empty.aria' $emptySource
    $allPath = Write-TestSource 'verified-filter-all.aria' $allSource
    $nonePath = Write-TestSource 'verified-filter-none.aria' $noneSource
    $compositionPath = Write-TestSource 'verified-filter-composition.aria' $compositionSource
    $fracturePath = Write-TestSource 'verified-filter-fracture.aria' $fractureSource

    $validGate = Invoke-AriaGate -SourcePath $validPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $validTwinGate = Invoke-AriaGate -SourcePath $validTwinPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $emptyGate = Invoke-AriaGate -SourcePath $emptyPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $allGate = Invoke-AriaGate -SourcePath $allPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $noneGate = Invoke-AriaGate -SourcePath $nonePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $compositionGate = Invoke-AriaGate -SourcePath $compositionPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $fractureGate = Invoke-AriaGate -SourcePath $fracturePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet

    Write-Host ''
    Write-Host '⌬  ARIA / VERIFIED FILTER ALPHA.8' -ForegroundColor Cyan
    Write-Host '⧉  verified-filter lattice ×24' -ForegroundColor DarkGray

    Test-FilterCase 'algorithm.filter card is sealed and verified' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        $card = Get-AriaGlyphCard -Id 'algorithm.filter' -Registry $registry
        Assert-Equal 'verified' $card.status 'Filter card status mismatch.'
        Assert-True (Test-AriaGlyphCard $card).valid 'Filter card identity is invalid.'
    }
    Test-FilterCase 'filter glyph forms a dedicated canonical AST node' {
        $parsed = Parse-AriaSource -Source $validSource -SourceName '<filter-ast>'
        $expression = $parsed.model.flows[0].statements[1].expression
        Assert-Equal 'filter' $expression.kind 'Filter AST kind mismatch.'
        Assert-Equal 'Positive' $expression.predicate 'Filter predicate identity mismatch.'
    }
    Test-FilterCase 'filter preserves its input sequence type' {
        $instruction = @($validGate.bytecode.instructions | Where-Object op -eq 'FILTER')[0]
        Assert-Equal 'Sequence<Number>' $instruction.sequenceType 'Filter sequence type mismatch.'
    }
    Test-FilterCase 'unknown filter predicate is rejected' {
        Assert-Diagnostic (Get-Diagnostics ($validSource.Replace('⫰(values, Positive)','⫰(values, Missing)'))) 'ARIA2132' 'Unknown predicate diagnostic missing.'
    }
    Test-FilterCase 'filter predicate must be unary' {
        $source = $validSource.Replace('function Positive(value: Number)', 'function Positive(left: Number, right: Number)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2133' 'Unary predicate diagnostic missing.'
    }
    Test-FilterCase 'filter predicate input must match sequence element type' {
        $source = $validSource.Replace('function Positive(value: Number)', 'function Positive(value: Text)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2134' 'Predicate input diagnostic missing.'
    }
    Test-FilterCase 'filter predicate must return exactly Bool' {
        $source = $validSource.Replace('-> Bool {', '-> Number {').Replace('↩ value > 0', '↩ value')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2135' 'Bool predicate diagnostic missing.'
    }
    Test-FilterCase 'directly effectful predicate is rejected' {
        $source = $validSource.Replace('↩ value > 0', "emit value`n  ↩ value > 0")
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2136' 'Direct purity diagnostic missing.'
    }
    Test-FilterCase 'transitively effectful predicate is rejected' {
        $source = $validSource.Replace(
            'function Positive(value: Number) -> Bool {',
            "function Effectful(value: Number) -> Bool {`n  emit value`n  ↩ true`n}`n`nfunction Positive(value: Number) -> Bool {"
        ).Replace('↩ value > 0', '↩ Effectful(value)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2136' 'Transitive purity diagnostic missing.'
    }
    Test-FilterCase 'compiler emits one explicit FILTER contract' {
        $filters = @($validGate.bytecode.instructions | Where-Object op -eq 'FILTER')
        Assert-Equal 1 $filters.Count 'FILTER instruction count mismatch.'
        Assert-Equal 'Positive' $filters[0].predicate 'FILTER predicate metadata mismatch.'
        Assert-Equal 'Sequence<Number>' $filters[0].sequenceType 'FILTER type metadata mismatch.'
    }
    Test-FilterCase 'effect graph records filter predicate as a call' {
        $entry = Get-AriaEffectSummary -Graph $validGate.bytecode.effectGraph -Name '$entry'
        Assert-True ('Positive' -in @($entry.calls)) 'Entry effect summary omitted filter predicate.'
    }
    Test-FilterCase 'bytecode verifier rejects unknown filter predicate' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.instructions | Where-Object op -eq 'FILTER')[0]).predicate = 'Missing'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'Unknown bytecode predicate was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'unknown predicate') 'Unknown predicate verifier boundary missing.'
    }
    Test-FilterCase 'bytecode verifier independently requires Bool return' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.functions | Where-Object name -eq 'Positive')[0]).returnType = 'Number'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'False predicate return type was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'must return Bool') 'FILTER Bool verifier boundary missing.'
    }
    Test-FilterCase 'bytecode verifier independently rejects false purity' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.functions | Where-Object name -eq 'Positive')[0]).effectSummary.purity = 'effectful'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'False predicate purity was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'not proven pure') 'FILTER purity verifier boundary missing.'
    }
    Test-FilterCase 'runtime filter preserves source order and input immutability' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(3,4) @(Test-AriaSequenceValue $result.variables.selected).values 'Selected values changed order.'
        Assert-Equal @(-2,0,3,4) @(Test-AriaSequenceValue $result.variables.values).values 'Filter mutated its input.'
    }
    Test-FilterCase 'runtime filter admits zero selected values' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $noneGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        $validation = Test-AriaSequenceValue $result.variables.selected
        Assert-Equal 0 @($validation.values).Count 'Zero-cardinality filter mismatch.'
        Assert-Equal 'Sequence<Number>' (Get-AriaCanonicalValueType $result.variables.selected) 'Zero-cardinality type changed.'
    }
    Test-FilterCase 'runtime filter admits all selected values' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $allGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(1,2,3) @(Test-AriaSequenceValue $result.variables.selected).values 'All-cardinality filter mismatch.'
    }
    Test-FilterCase 'empty filter returns typed empty sequence without iteration' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $emptyGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 'Sequence<Number>' (Get-AriaCanonicalValueType $result.variables.selected) 'Empty filter type changed.'
        Assert-Equal 0 @($result.events | Where-Object { $_.kind -eq 'filter' -and $_.state -eq 'iteration' }).Count 'Empty filter invented an iteration.'
    }
    Test-FilterCase 'filter event sequence reports measured counts' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        $states = @($result.events | Where-Object kind -eq 'filter' | ForEach-Object state)
        Assert-Equal @('start','iteration','iteration','iteration','iteration','complete') $states 'Filter event order mismatch.'
        $complete = @($result.events | Where-Object { $_.kind -eq 'filter' -and $_.state -eq 'complete' })[0]
        Assert-Equal 4 $complete.completed 'Completion input count mismatch.'
        Assert-Equal 2 $complete.selectedCount 'Completion selected count mismatch.'
        Assert-True ([int]$complete.durationMs -ge 0) 'Completion duration is not measured.'
    }
    Test-FilterCase 'filter evidence excludes sequence element values' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        foreach ($event in @($result.events | Where-Object kind -eq 'filter')) {
            Assert-True ($null -eq $event.PSObject.Properties['value']) 'Filter evidence exposed an element value.'
            Assert-True ($null -eq $event.PSObject.Properties['values']) 'Filter evidence exposed sequence values.'
            Assert-True ([string]$event.eventDigest -match '^[a-f0-9]{64}$') 'Filter evidence lacks Event Spine identity.'
        }
    }
    Test-FilterCase 'runtime predicate failure emits bounded fracture evidence' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $rejected = $false
        try {
            $null = Invoke-AriaContainer -Container (Read-AriaContainerBytes $fractureGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        }
        catch { $rejected = $true }
        Assert-True $rejected 'Failing predicate completed.'
        $fracture = @(Get-AriaEventBuffer | Where-Object { $_.domain -eq 'algorithm' -and $_.phase -eq 'filter.fracture' })
        Assert-Equal 1 $fracture.Count 'Filter fracture event missing.'
        Assert-Equal 1 $fracture[0].data.completed 'Fracture completed count mismatch.'
        Assert-Equal 1 $fracture[0].data.selectedCount 'Fracture selected count mismatch.'
    }
    Test-FilterCase 'filter compilation and execution are deterministic' {
        Assert-Equal $validGate.buildHash $validTwinGate.buildHash 'Equivalent filter builds diverged.'
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $one = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $two = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validTwinGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(Test-AriaSequenceValue $one.variables.selected).values @(Test-AriaSequenceValue $two.variables.selected).values 'Equivalent filter executions diverged.'
    }
    Test-FilterCase 'filter composes with verified map through explicit boundaries' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $compositionGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(4,6) @(Test-AriaSequenceValue $result.variables.selected).values 'Map/filter composition mismatch.'
        Assert-Equal 1 @($result.events | Where-Object { $_.kind -eq 'map' -and $_.state -eq 'complete' }).Count 'Map boundary missing.'
        Assert-Equal 1 @($result.events | Where-Object { $_.kind -eq 'filter' -and $_.state -eq 'complete' }).Count 'Filter boundary missing.'
    }
    Test-FilterCase 'filter adds computation but no authority' {
        Assert-Equal 40 (Get-AriaOpcodeRegistry).Count 'Algorithm opcode registry count mismatch.'
        Assert-Equal 0 @($validGate.bytecode.capabilities).Count 'Filter introduced a capability.'
        $registry = Read-AriaGlyphCardRegistry -Root $root
        Assert-Equal 'verified' (Get-AriaGlyphCard -Id 'algorithm.map' -Registry $registry).status 'Map regressed.'
        Assert-Equal 'verified' (Get-AriaGlyphCard -Id 'algorithm.reduce' -Registry $registry).status 'Reduce was not admitted.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw "Verified Filter test count diverged. Expected=$script:Expected Observed=$($script:Passed + $script:Failed)"
    }
    Write-Host ("⧉  verified-filter lattice {0}/{1} · {2}" -f $script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'})) -ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
    if ($script:Failed -gt 0) { throw "Verified Filter lattice failed: $script:Failed failure(s)." }
}
finally {
    if (Test-Path -LiteralPath $tempRoot -PathType Container) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
