[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$policyPath = Join-Path $root 'aria.policy.json'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aria-verified-map-' + [guid]::NewGuid().ToString('N'))

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
$script:Expected = 22

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
function Test-MapCase {
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
    $parsed = Parse-AriaSource -Source $Source -SourceName '<verified-map-diagnostic>'
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
module VerifiedMap version 0.7.0
program VerifiedMap version 0.7.0
entry Main

function Double(value: Number) -> Number {
  ↩ value * 2
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3, 4]
  let mapped: Sequence<Number> = ⨯(values, Double)
  halt
}
'@

$boolSource = @'
aria 0.4.0
module VerifiedMapBool version 0.7.0
program VerifiedMapBool version 0.7.0
entry Main

function Positive(value: Number) -> Bool {
  ↩ value > 0
}

flow Main {
  let values: Sequence<Number> = [-1, 0, 2]
  let mapped: Sequence<Bool> = ⨯(values, Positive)
  halt
}
'@

$emptySource = @'
aria 0.4.0
module VerifiedMapEmpty version 0.7.0
program VerifiedMapEmpty version 0.7.0
entry Main

function Double(value: Number) -> Number {
  ↩ value * 2
}

flow Main {
  let values: Sequence<Number> = []
  let mapped: Sequence<Number> = ⨯(values, Double)
  halt
}
'@

$nestedSource = @'
aria 0.4.0
module VerifiedMapNested version 0.7.0
program VerifiedMapNested version 0.7.0
entry Main

function Double(value: Number) -> Number {
  ↩ value * 2
}

flow Main {
  let values: Sequence<Number> = [1, 2]
  let mapped: Sequence<Number> = ⨯(⨯(values, Double), Double)
  halt
}
'@

$fractureSource = @'
aria 0.4.0
module VerifiedMapFracture version 0.7.0
program VerifiedMapFracture version 0.7.0
entry Main

function BelowTwo(value: Number) -> Number {
  assert value < 2
  ↩ value
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let mapped: Sequence<Number> = ⨯(values, BelowTwo)
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $validPath = Write-TestSource 'verified-map.aria' $validSource
    $validTwinPath = Write-TestSource 'verified-map-twin.aria' $validSource
    $boolPath = Write-TestSource 'verified-map-bool.aria' $boolSource
    $emptyPath = Write-TestSource 'verified-map-empty.aria' $emptySource
    $nestedPath = Write-TestSource 'verified-map-nested.aria' $nestedSource
    $fracturePath = Write-TestSource 'verified-map-fracture.aria' $fractureSource

    $validGate = Invoke-AriaGate -SourcePath $validPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $validTwinGate = Invoke-AriaGate -SourcePath $validTwinPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $boolGate = Invoke-AriaGate -SourcePath $boolPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $emptyGate = Invoke-AriaGate -SourcePath $emptyPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $nestedGate = Invoke-AriaGate -SourcePath $nestedPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    $fractureGate = Invoke-AriaGate -SourcePath $fracturePath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet

    Write-Host ''
    Write-Host '⌬  ARIA / VERIFIED MAP ALPHA.7' -ForegroundColor Cyan
    Write-Host '⧉  verified-map lattice ×22' -ForegroundColor DarkGray

    Test-MapCase 'algorithm.map card is sealed and verified' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        $card = Get-AriaGlyphCard -Id 'algorithm.map' -Registry $registry
        Assert-Equal 'verified' $card.status 'Map card status mismatch.'
        Assert-True (Test-AriaGlyphCard $card).valid 'Map card identity is invalid.'
    }
    Test-MapCase 'map glyph forms a dedicated canonical AST node' {
        $parsed = Parse-AriaSource -Source $validSource -SourceName '<map-ast>'
        $expression = $parsed.model.flows[0].statements[1].expression
        Assert-Equal 'map' $expression.kind 'Map AST kind mismatch.'
        Assert-Equal 'Double' $expression.transform 'Map transform identity mismatch.'
    }
    Test-MapCase 'map infers output sequence from transform return type' {
        $instruction = @($validGate.bytecode.instructions | Where-Object op -eq 'MAP')[0]
        Assert-Equal 'Sequence<Number>' $instruction.outputType 'Map output type mismatch.'
    }
    Test-MapCase 'unknown map transform is rejected' {
        Assert-Diagnostic (Get-Diagnostics ($validSource.Replace('⨯(values, Double)','⨯(values, Missing)'))) 'ARIA2122' 'Unknown transform diagnostic missing.'
    }
    Test-MapCase 'map transform must be unary' {
        $source = $validSource.Replace('function Double(value: Number)', 'function Double(left: Number, right: Number)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2123' 'Unary transform diagnostic missing.'
    }
    Test-MapCase 'map transform input must match sequence element type' {
        $source = $validSource.Replace('function Double(value: Number)', 'function Double(value: Text)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2124' 'Transform input diagnostic missing.'
    }
    Test-MapCase 'map transform output must remain scalar' {
        $source = $validSource.Replace('-> Number {', '-> Sequence<Number> {').Replace('↩ value * 2', '↩ [1, 2]')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2125' 'Scalar output diagnostic missing.'
    }
    Test-MapCase 'directly effectful transform is rejected' {
        $source = $validSource.Replace('↩ value * 2', "emit value`n  ↩ value * 2")
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2126' 'Direct purity diagnostic missing.'
    }
    Test-MapCase 'transitively effectful transform is rejected' {
        $source = $validSource.Replace(
            'function Double(value: Number) -> Number {',
            "function Effectful(value: Number) -> Number {`n  emit value`n  ↩ value`n}`n`nfunction Double(value: Number) -> Number {"
        ).Replace('↩ value * 2', '↩ Effectful(value)')
        Assert-Diagnostic (Get-Diagnostics $source) 'ARIA2126' 'Transitive purity diagnostic missing.'
    }
    Test-MapCase 'compiler emits one explicit MAP contract' {
        $maps = @($validGate.bytecode.instructions | Where-Object op -eq 'MAP')
        Assert-Equal 1 $maps.Count 'MAP instruction count mismatch.'
        Assert-Equal 'Double' $maps[0].transform 'MAP transform metadata mismatch.'
        Assert-Equal 'Sequence<Number>' $maps[0].inputType 'MAP input metadata mismatch.'
    }
    Test-MapCase 'effect graph records map transform as a call' {
        $entry = Get-AriaEffectSummary -Graph $validGate.bytecode.effectGraph -Name '$entry'
        Assert-True ('Double' -in @($entry.calls)) 'Entry effect summary omitted map transform.'
    }
    Test-MapCase 'bytecode verifier rejects unknown map transform' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.instructions | Where-Object op -eq 'MAP')[0]).transform = 'Missing'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'Unknown bytecode transform was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'unknown transform') 'Unknown transform verifier boundary missing.'
    }
    Test-MapCase 'bytecode verifier independently rejects false purity' {
        $mutated = Copy-JsonValue $validGate.bytecode
        (@($mutated.functions | Where-Object name -eq 'Double')[0]).effectSummary.purity = 'effectful'
        $verification = Test-AriaBytecodeModel $mutated
        Assert-True (-not $verification.valid) 'False transform purity was accepted.'
        Assert-True (($verification.errors -join ' ') -match 'not proven pure') 'MAP purity verifier boundary missing.'
    }
    Test-MapCase 'runtime map preserves order and cardinality' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        $validation = Test-AriaSequenceValue $result.variables.mapped
        Assert-Equal @(2,4,6,8) @($validation.values) 'Mapped values changed order or length.'
    }
    Test-MapCase 'runtime map preserves exact output element type' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $boolGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 'Sequence<Bool>' (Get-AriaCanonicalValueType $result.variables.mapped) 'Map output element type changed.'
        Assert-Equal @($false,$false,$true) @(Test-AriaSequenceValue $result.variables.mapped).values 'Boolean map output mismatch.'
    }
    Test-MapCase 'empty map returns typed empty sequence without iteration' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $emptyGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal 'Sequence<Number>' (Get-AriaCanonicalValueType $result.variables.mapped) 'Empty map type changed.'
        Assert-Equal 0 @($result.events | Where-Object state -eq 'iteration').Count 'Empty map invented an iteration.'
    }
    Test-MapCase 'map event sequence matches completed iterations' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        $states = @($result.events | Where-Object kind -eq 'map' | ForEach-Object state)
        Assert-Equal @('start','iteration','iteration','iteration','iteration','complete') $states 'Map event order mismatch.'
        $complete = @($result.events | Where-Object { $_.kind -eq 'map' -and $_.state -eq 'complete' })[0]
        Assert-Equal 4 $complete.iterations 'Completion iteration count mismatch.'
        Assert-True ([int]$complete.durationMs -ge 0) 'Completion duration is not measured.'
    }
    Test-MapCase 'map evidence excludes element values' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        foreach ($event in @($result.events | Where-Object kind -eq 'map')) {
            Assert-True ($null -eq $event.PSObject.Properties['value']) 'Map evidence exposed an element value.'
            Assert-True ($null -eq $event.PSObject.Properties['values']) 'Map evidence exposed sequence values.'
            Assert-True ([string]$event.eventDigest -match '^[a-f0-9]{64}$') 'Map evidence lacks Event Spine identity.'
        }
    }
    Test-MapCase 'runtime transform failure emits bounded fracture evidence' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $rejected = $false
        try {
            $null = Invoke-AriaContainer -Container (Read-AriaContainerBytes $fractureGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        }
        catch { $rejected = $true }
        Assert-True $rejected 'Failing transform completed.'
        $fracture = @(Get-AriaEventBuffer | Where-Object { $_.domain -eq 'algorithm' -and $_.phase -eq 'map.fracture' })
        Assert-Equal 1 $fracture.Count 'Map fracture event missing.'
        Assert-Equal 1 $fracture[0].data.iteration 'Fracture completed-iteration count mismatch.'
    }
    Test-MapCase 'map compilation and execution are deterministic' {
        Assert-Equal $validGate.buildHash $validTwinGate.buildHash 'Equivalent map builds diverged.'
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $one = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $two = Invoke-AriaContainer -Container (Read-AriaContainerBytes $validTwinGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(Test-AriaSequenceValue $one.variables.mapped).values @(Test-AriaSequenceValue $two.variables.mapped).values 'Equivalent map executions diverged.'
    }
    Test-MapCase 'nested maps retain explicit operation boundaries' {
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot | Out-Null
        $result = Invoke-AriaContainer -Container (Read-AriaContainerBytes $nestedGate.bytes) -PolicyPath $policyPath -WorkspaceRoot $tempRoot -PassThru
        Assert-Equal @(4,8) @(Test-AriaSequenceValue $result.variables.mapped).values 'Nested map output mismatch.'
        Assert-Equal 2 @($result.events | Where-Object { $_.kind -eq 'map' -and $_.state -eq 'start' }).Count 'Nested maps lost operation starts.'
    }
    Test-MapCase 'map adds computation but no authority' {
        Assert-Equal 40 (Get-AriaOpcodeRegistry).Count 'Algorithm opcode registry count mismatch.'
        Assert-Equal 0 @($validGate.bytecode.capabilities).Count 'Map introduced a capability.'
        $registry = Read-AriaGlyphCardRegistry -Root $root
        Assert-Equal 'verified' (Get-AriaGlyphCard -Id 'algorithm.filter' -Registry $registry).status 'Filter was not admitted.'
        Assert-Equal 'verified' (Get-AriaGlyphCard -Id 'algorithm.reduce' -Registry $registry).status 'Reduce was not admitted.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw "Verified Map test count diverged. Expected=$script:Expected Observed=$($script:Passed + $script:Failed)"
    }
    Write-Host ("⧉  verified-map lattice {0}/{1} · {2}" -f $script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'})) -ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
    if ($script:Failed -gt 0) { throw "Verified Map lattice failed: $script:Failed failure(s)." }
}
finally {
    if (Test-Path -LiteralPath $tempRoot -PathType Container) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
