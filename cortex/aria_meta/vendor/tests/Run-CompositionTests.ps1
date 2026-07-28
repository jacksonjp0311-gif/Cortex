[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    ('aria-composition-' + [guid]::NewGuid().ToString('N'))

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GlyphMemory.psm1') -Force -DisableNameChecking

$policyPath = Join-Path $root 'aria.policy.json'
$policy = Get-AriaPolicy -PolicyPath $policyPath

$script:Passed = 0
$script:Failed = 0
$script:Expected = 15

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param($Expected,$Actual,[string]$Message)
    $expectedJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{ value = $Expected })
    $actualJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{ value = $Actual })
    if ($expectedJson -ne $actualJson) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Test-CompositionCase {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )
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
    $encoding = New-Object Text.UTF8Encoding($false)
    $canonical = $Source.Replace("`r`n","`n").Replace("`r","`n")
    if (-not $canonical.EndsWith("`n")) { $canonical += "`n" }
    [IO.File]::WriteAllText($path,$canonical,$encoding)
    return $path
}

function Get-SourceDiagnostics {
    param([string]$Source)
    $parsed = Parse-AriaSource -Source $Source -SourceName '<composition-diagnostic>'
    $semantic = Test-AriaSemantics -ParseResult $parsed -Policy $policy
    return (Get-AriaErrorDiagnostics -Diagnostics $semantic.diagnostics)
}

function Get-DiagnosticIdentity {
    param([object[]]$Diagnostics)
    return @(
        @($Diagnostics) |
            ForEach-Object {
                "{0}|{1}|{2}" -f $_.code,$_.line,$_.message
            }
    )
}

function Assert-ExpressionRejected {
    param([string]$Expression)
    $rejected = $false
    try {
        $null = ConvertFrom-AriaExpression -Text $Expression -Line 1
    }
    catch {
        $rejected = $true
    }
    Assert-True $rejected "Malformed composition was accepted: $Expression"
}

$glyphSource = @'
aria 0.4.0
module TypedComposition version 0.3.0
program TypedComposition version 0.3.0
entry Main

function Increment(value: Number) -> Number {
  ↩ value + 1
}

function Double(value: Number) -> Number {
  ↩ value * 2
}

function Square(value: Number) -> Number {
  ↩ value * value
}

function Add(left: Number, right: Number) -> Number {
  ↩ left + right
}

function IdentityText(value: Text) -> Text {
  ↩ value
}

flow Main {
  let result: Number = 10 ≫ Increment ≫ Double ≫ Square
  emit result
  halt
}
'@

$textSource = @'
aria 0.4.0
module TypedComposition version 0.3.0
program TypedComposition version 0.3.0
entry Main

function Increment(value: Number) -> Number {
  return value + 1
}

function Double(value: Number) -> Number {
  return value * 2
}

function Square(value: Number) -> Number {
  return value * value
}

function Add(left: Number, right: Number) -> Number {
  return left + right
}

function IdentityText(value: Text) -> Text {
  return value
}

flow Main {
  let result: Number = Square(Double(Increment(10)))
  emit result
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $glyphPath = Write-TestSource 'typed-composition-glyph.aria' $glyphSource
    $textPath = Write-TestSource 'typed-composition-text.aria' $textSource

    $glyphGate = Invoke-AriaGate `
        -SourcePath $glyphPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $textGate = Invoke-AriaGate `
        -SourcePath $textPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    Write-Host ''
    Write-Host '⌬  ARIA / TYPED COMPOSITION' -ForegroundColor Cyan
    Write-Host '⧉  composition lattice ×15' -ForegroundColor DarkGray

    Test-CompositionCase 'pipe card and executable alias are verified' {
        $aliases = @(Get-AriaExecutableGlyphAliases)
        Assert-Equal 9 $aliases.Count 'Executable glyph alias count mismatch.'

        $pipeAliases = @($aliases | Where-Object { [string]$_.glyph -eq '≫' })
        Assert-Equal 1 $pipeAliases.Count 'Pipe alias is missing.'
        Assert-Equal 'pipe' $pipeAliases[0].keyword 'Pipe alias target mismatch.'

        $registry = Read-AriaGlyphCardRegistry -Root $root
        $card = Get-AriaGlyphCard -Id 'composition.pipe' -Registry $registry

        Assert-Equal 'verified' $card.status 'Pipe card was not verified.'
        Assert-Equal $card.symbol $pipeAliases[0].glyph 'Pipe alias diverged from card.'
        Assert-Equal 'nested-call' $card.lowering.target 'Pipe lowering target changed.'
    }

    Test-CompositionCase 'pipe lowers left-to-right into nested calls' {
        $expression = ConvertFrom-AriaExpression `
            -Text '10 ≫ Increment ≫ Double ≫ Square' `
            -Line 1

        Assert-Equal 'call' $expression.kind 'Outer pipe did not lower to a call.'
        Assert-Equal 'Square' $expression.name 'Final stage is not outermost.'
        Assert-Equal 'Double' $expression.arguments[0].name 'Middle stage order changed.'
        Assert-Equal 'Increment' $expression.arguments[0].arguments[0].name `
            'First stage order changed.'
        Assert-Equal 10 `
            $expression.arguments[0].arguments[0].arguments[0].value `
            'Initial value changed during lowering.'
    }

    Test-CompositionCase 'pipe precedence follows complete left expression' {
        $expression = ConvertFrom-AriaExpression `
            -Text '1 + 2 ≫ Double' `
            -Line 1

        Assert-Equal 'call' $expression.kind 'Pipe did not produce a call.'
        Assert-Equal 'Double' $expression.name 'Pipe target mismatch.'
        Assert-Equal 'binary' $expression.arguments[0].kind `
            'Additive expression was not completed before piping.'
        Assert-Equal '+' $expression.arguments[0].operator `
            'Additive operator changed before piping.'
    }

    Test-CompositionCase 'invoke glyph composes through pipe' {
        $expression = ConvertFrom-AriaExpression `
            -Text '▷ Add(20, 1) ≫ Double' `
            -Line 1

        Assert-Equal 'Double' $expression.name 'Outer composed function mismatch.'
        Assert-Equal 'call' $expression.arguments[0].kind `
            'Invoke glyph was not preserved as canonical call.'
        Assert-Equal 'Add' $expression.arguments[0].name `
            'Invoke target changed inside composition.'
    }

    Test-CompositionCase 'glyph and textual forms share semantic IR' {
        Assert-Equal $textGate.irHash $glyphGate.irHash `
            'Composition and nested calls produced different IR.'
    }

    Test-CompositionCase 'glyph and textual executable bytecode are equal' {
        $glyphProjection = [pscustomobject][ordered]@{
            constants = $glyphGate.bytecode.constants
            functions = $glyphGate.bytecode.functions
            instructions = $glyphGate.bytecode.instructions
        }
        $textProjection = [pscustomobject][ordered]@{
            constants = $textGate.bytecode.constants
            functions = $textGate.bytecode.functions
            instructions = $textGate.bytecode.instructions
        }
        Assert-Equal $textProjection $glyphProjection `
            'Composition executable bytecode differs from nested calls.'
    }

    Test-CompositionCase 'CALL ordering preserves source stage order' {
        $calls = @(
            $glyphGate.bytecode.instructions |
                Where-Object { [string]$_.op -eq 'CALL' } |
                ForEach-Object { [string]$_.name }
        )
        Assert-Equal @('Increment','Double','Square') $calls `
            'CALL ordering does not match left-to-right stages.'
    }

    Test-CompositionCase 'source provenance remains distinct' {
        Assert-True ($glyphGate.sourceHash -ne $textGate.sourceHash) `
            'Distinct source surfaces collapsed to one source hash.'
        Assert-True ($glyphGate.buildHash -ne $textGate.buildHash) `
            'Provenance-bearing containers unexpectedly match.'
    }

    Test-CompositionCase 'composition executes the expected result' {
        $container = Read-AriaContainerBytes -Bytes $glyphGate.bytes
        $result = Invoke-AriaContainer `
            -Container $container `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru
        Assert-Equal @('484') @($result.outputs) `
            'Composition runtime result mismatch.'
    }

    Test-CompositionCase 'unknown stage diagnostics preserve parity' {
        $glyph = $glyphSource.Replace(
            '10 ≫ Increment ≫ Double ≫ Square',
            '10 ≫ Missing ≫ Double ≫ Square'
        )
        $text = $textSource.Replace(
            'Square(Double(Increment(10)))',
            'Square(Double(Missing(10)))'
        )
        $glyphErrors = Get-SourceDiagnostics $glyph
        $textErrors = Get-SourceDiagnostics $text
        Assert-Equal `
            (Get-DiagnosticIdentity $textErrors) `
            (Get-DiagnosticIdentity $glyphErrors) `
            'Unknown-stage diagnostics differ.'
        Assert-True ('ARIA2061' -in @($glyphErrors.code)) `
            'Unknown-stage diagnostic code is missing.'
    }

    Test-CompositionCase 'type continuity diagnostics preserve parity' {
        $glyph = $glyphSource.Replace(
            '10 ≫ Increment ≫ Double ≫ Square',
            '10 ≫ IdentityText ≫ Double'
        )
        $text = $textSource.Replace(
            'Square(Double(Increment(10)))',
            'Double(IdentityText(10))'
        )
        $glyphErrors = Get-SourceDiagnostics $glyph
        $textErrors = Get-SourceDiagnostics $text
        Assert-Equal `
            (Get-DiagnosticIdentity $textErrors) `
            (Get-DiagnosticIdentity $glyphErrors) `
            'Composition type diagnostics differ.'
        Assert-True ('ARIA2063' -in @($glyphErrors.code)) `
            'Composition type-continuity diagnostic is missing.'
    }

    Test-CompositionCase 'stage arity diagnostics preserve parity' {
        $glyph = $glyphSource.Replace(
            '10 ≫ Increment ≫ Double ≫ Square',
            '10 ≫ Add'
        )
        $text = $textSource.Replace(
            'Square(Double(Increment(10)))',
            'Add(10)'
        )
        $glyphErrors = Get-SourceDiagnostics $glyph
        $textErrors = Get-SourceDiagnostics $text
        Assert-Equal `
            (Get-DiagnosticIdentity $textErrors) `
            (Get-DiagnosticIdentity $glyphErrors) `
            'Composition arity diagnostics differ.'
        Assert-True ('ARIA2062' -in @($glyphErrors.code)) `
            'Composition arity diagnostic is missing.'
    }

    Test-CompositionCase 'malformed pipes are rejected deterministically' {
        Assert-ExpressionRejected '10 ≫'
        Assert-ExpressionRejected '10 ≫ Increment()'
        Assert-ExpressionRejected '10 ≫ ▷ Increment(1)'
    }

    Test-CompositionCase 'composition adds no opcode or capability' {
        $opcodes = Get-AriaOpcodeRegistry
        Assert-Equal 40 $opcodes.Count 'Opcode registry changed.'
        Assert-Equal 0 @($glyphGate.bytecode.capabilities).Count `
            'Composition introduced a capability.'
        Assert-Equal 0 @($glyphGate.bytecode.instructions |
            Where-Object { [string]$_.op -notin @(
                'PUSH_CONST','LOAD','STORE','CALL','EMIT','HALT'
            )
        }).Count 'Composition emitted an unexpected top-level opcode.'
    }

    Test-CompositionCase 'verified pipe remains active beside bounded map' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        $pipe = Get-AriaGlyphCard -Id 'composition.pipe' -Registry $registry
        $map = Get-AriaGlyphCard -Id 'algorithm.map' -Registry $registry
        $context = 'sha256:' + (Get-AriaSha256Text 'typed-composition-alpha3')

        $activation = New-AriaGlyphActivation `
            -Card $pipe `
            -ContextDigest $context `
            -TestsPassed 15 `
            -TestsFailed 0 `
            -Source 'tests'

        Assert-True (Test-AriaGlyphActivation $activation).valid `
            'Verified pipe activation was rejected.'
        Assert-Equal 'verified' $map.status `
            'Verified map card is not visible beside composition.'
        $mapActivation = New-AriaGlyphActivation `
            -Card $map `
            -ContextDigest $context `
            -TestsPassed 15 `
            -TestsFailed 0 `
            -Source 'tests'
        Assert-True (Test-AriaGlyphActivation $mapActivation).valid `
            'Verified map activation was rejected.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw (
            "Composition test count diverged. Expected={0} Observed={1}" -f
                $script:Expected,
                ($script:Passed + $script:Failed)
        )
    }

    Write-Host (
        '⧉  composition lattice {0}/{1} · {2}' -f
            $script:Passed,
            $script:Expected,
            $(if ($script:Failed -eq 0) {
                'coherent'
            }
            else {
                "$($script:Failed) fracture(s)"
            })
    ) -ForegroundColor $(if ($script:Failed -eq 0) {
        'Green'
    }
    else {
        'Magenta'
    })

    if ($script:Failed -gt 0) {
        throw "Composition lattice failed: $script:Failed failure(s)."
    }
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
