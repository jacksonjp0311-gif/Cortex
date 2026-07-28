[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    ('aria-sequence-core-' + [guid]::NewGuid().ToString('N'))

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
    $expectedJson = ConvertTo-AriaJson (
        [pscustomobject][ordered]@{ value = $Expected }
    )
    $actualJson = ConvertTo-AriaJson (
        [pscustomobject][ordered]@{ value = $Actual }
    )
    if ($expectedJson -ne $actualJson) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Test-SequenceCase {
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
        Write-Host (
            "⬗  {0} · {1}" -f $Name,$_.Exception.Message
        ) -ForegroundColor Magenta
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
    $parsed = Parse-AriaSource `
        -Source $Source `
        -SourceName '<sequence-diagnostic>'
    $semantic = Test-AriaSemantics `
        -ParseResult $parsed `
        -Policy $policy
    return @(
        Get-AriaErrorDiagnostics `
            -Diagnostics $semantic.diagnostics
    )
}

function Assert-Diagnostic {
    param(
        [object[]]$Diagnostics,
        [string]$Code,
        [string]$Message
    )
    Assert-True ($Code -in @($Diagnostics.code)) $Message
}

$validSource = @'
aria 0.4.0
module SequenceCore version 0.4.0
program SequenceCore version 0.4.0
entry Main

function EchoNumbers(values: Sequence<Number>) -> Sequence<Number> {
  ↩ values
}

flow Main {
  let numbers: Sequence<Number> = [1, 2, 3, 4]
  let empty: Sequence<Text> = []
  let echoed: Sequence<Number> = ▷ EchoNumbers(numbers)
  emit numbers
  emit empty
  emit numbers == echoed
  halt
}
'@

$scalarSource = @'
aria 0.4.0
module ScalarRegression version 0.4.0
program ScalarRegression version 0.4.0
entry Main

function Add(left: Number, right: Number) -> Number {
  ↩ left + right
}

flow Main {
  let result: Number = ▷ Add(20, 22)
  emit result
  halt
}
'@

$memorySource = @'
aria 0.4.0
module SequenceMemory version 0.4.0
program SequenceMemory version 0.4.0
entry Main

memory Vault {
  values: Sequence<Number> = [5, 6, 7]
  empty: Sequence<Text> = []
}

flow Main {
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $validPath = Write-TestSource 'sequence-core.aria' $validSource
    $validTwinPath = Write-TestSource 'sequence-core-twin.aria' $validSource
    $memoryPath = Write-TestSource 'sequence-memory.aria' $memorySource
    $scalarPath = Write-TestSource 'scalar-regression.aria' $scalarSource

    $validGate = Invoke-AriaGate `
        -SourcePath $validPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $validTwinGate = Invoke-AriaGate `
        -SourcePath $validTwinPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $memoryGate = Invoke-AriaGate `
        -SourcePath $memoryPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $scalarGate = Invoke-AriaGate `
        -SourcePath $scalarPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    Write-Host ''
    Write-Host '⌬  ARIA / SEQUENCE CORE' -ForegroundColor Cyan
    Write-Host '⧉  sequence lattice ×15' -ForegroundColor DarkGray

    Test-SequenceCase 'parameterized sequence types parse canonically' {
        $parsed = Parse-AriaSource `
            -Source $validSource `
            -SourceName '<sequence-types>'

        $errors = Get-AriaErrorDiagnostics `
            -Diagnostics $parsed.diagnostics

        Assert-Equal 0 $errors.Count 'Valid sequence source emitted parser errors.'
        Assert-Equal 'Sequence<Number>' `
            $parsed.model.functions[0].parameters[0].type `
            'Sequence parameter type changed.'
        Assert-Equal 'Sequence<Number>' `
            $parsed.model.functions[0].returnType `
            'Sequence return type changed.'
        Assert-Equal 'Sequence<Number>' `
            $parsed.model.flows[0].statements[0].declaredType `
            'Sequence variable type changed.'
    }

    Test-SequenceCase 'homogeneous literal forms canonical sequence AST' {
        $expression = ConvertFrom-AriaExpression `
            -Text '[1, 2, 3, 4]' `
            -Line 1

        Assert-Equal 'sequence' $expression.kind `
            'Sequence literal did not form sequence AST.'
        Assert-Equal 4 @($expression.elements).Count `
            'Sequence element count changed.'
        Assert-Equal @('Number','Number','Number','Number') `
            @($expression.elements.valueType) `
            'Sequence scalar element types changed.'

        $negativeSource = $validSource.Replace(
            '[1, 2, 3, 4]',
            '[-1, 2, 3, 4]'
        )
        $negativePath = Write-TestSource `
            'negative-sequence.aria' `
            $negativeSource
        $negativeGate = Invoke-AriaGate `
            -SourcePath $negativePath `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -Quiet
        $negativeSequence = @(
            $negativeGate.bytecode.constants |
                Where-Object {
                    [string](Get-AriaCanonicalValueType -Value $_) -eq
                        'Sequence<Number>'
                }
        )[0]
        Assert-Equal ([long]-1) ([long]$negativeSequence.values[0]) `
            'Negative numeric sequence literal changed during lowering.'
    }

    Test-SequenceCase 'typed empty sequence is admitted' {
        [object[]]$errors = Get-SourceDiagnostics $validSource
        Assert-Equal 0 $errors.Count `
            'Declared empty sequence was rejected.'
        Assert-Equal 'Sequence<Text>' `
            $validGate.bytecode.instructions[3].type `
            'Typed empty sequence did not preserve its store type.'
    }

    Test-SequenceCase 'untyped empty sequence is rejected' {
        $source = $validSource.Replace(
            'let empty: Sequence<Text> = []',
            'let empty = []'
        )
        [object[]]$errors = Get-SourceDiagnostics $source
        Assert-Diagnostic $errors 'ARIA2115' `
            'Untyped empty-sequence diagnostic is missing.'
    }

    Test-SequenceCase 'mixed element types are rejected' {
        $source = $validSource.Replace(
            '[1, 2, 3, 4]',
            '[1, "two", 3, 4]'
        )
        [object[]]$errors = Get-SourceDiagnostics $source
        Assert-Diagnostic $errors 'ARIA2113' `
            'Mixed-element diagnostic is missing.'
    }

    Test-SequenceCase 'non-literal sequence elements are rejected' {
        $source = $validSource.Replace(
            '[1, 2, 3, 4]',
            '[1, 2 + 3, 4]'
        )
        [object[]]$errors = Get-SourceDiagnostics $source
        Assert-Diagnostic $errors 'ARIA2111' `
            'Non-literal sequence diagnostic is missing.'
    }

    Test-SequenceCase 'sequence element ceiling is enforced' {
        $values = New-Object System.Collections.Generic.List[string]
        for ($index = 0; $index -lt 257; $index++) {
            $values.Add([string]$index)
        }
        $literal = '[' + ($values.ToArray() -join ', ') + ']'
        $source = $validSource.Replace('[1, 2, 3, 4]',$literal)
        [object[]]$errors = Get-SourceDiagnostics $source
        Assert-Diagnostic $errors 'ARIA2110' `
            'Sequence element-limit diagnostic is missing.'
    }

    Test-SequenceCase 'sequence encoded-byte ceiling is enforced' {
        $left = '"' + ('a' * 33000) + '"'
        $right = '"' + ('b' * 33000) + '"'
        $source = $validSource.Replace(
            '[1, 2, 3, 4]',
            ('[' + $left + ', ' + $right + ']')
        ).Replace(
            'Sequence<Number>',
            'Sequence<Text>'
        )
        [object[]]$errors = Get-SourceDiagnostics $source
        Assert-Diagnostic $errors 'ARIA2114' `
            'Sequence byte-limit diagnostic is missing.'
    }

    Test-SequenceCase 'semantic and build identities are deterministic' {
        Assert-Equal $validGate.irHash $validTwinGate.irHash `
            'Equivalent sequence programs produced different semantic IR.'
        Assert-Equal $validGate.buildHash $validTwinGate.buildHash `
            'Equivalent sequence programs produced different build identity.'
    }

    Test-SequenceCase 'sequence uses structured constants without opcode expansion' {
        $opcodes = Get-AriaOpcodeRegistry
        Assert-Equal 40 $opcodes.Count 'Opcode registry changed.'

        $sequences = @(
            $validGate.bytecode.constants |
                Where-Object {
                    (Test-AriaSequenceValue -Value $_).valid
                }
        )

        Assert-Equal 2 $sequences.Count `
            'Sequence constants were not emitted canonically.'

        Assert-Equal 0 @(
            $validGate.bytecode.instructions |
                Where-Object {
                    [string]$_.op -notin @(
                        'PUSH_CONST','STORE','LOAD','CALL',
                        'EMIT','EQ','HALT'
                    )
                }
        ).Count 'Sequence core emitted an unexpected opcode.'
    }

    Test-SequenceCase 'container round-trip preserves sequence values' {
        $container = Read-AriaContainerBytes -Bytes $validGate.bytes
        $verification = Test-AriaBytecodeModel `
            -BytecodeModel $container.bytecode

        Assert-True $verification.valid (
            'Round-tripped bytecode rejected: ' +
            (@($verification.errors) -join '; ')
        )

        $sequence = @(
            $container.bytecode.constants |
                Where-Object {
                    (Test-AriaSequenceValue -Value $_).valid -and
                    [string](Get-AriaCanonicalValueType -Value $_) -eq
                        'Sequence<Number>'
                }
        )[0]

        Assert-Equal @([long]1,[long]2,[long]3,[long]4) `
            @($sequence.values) `
            'Round-tripped sequence values changed.'
    }

    Test-SequenceCase 'runtime renders sequences deterministically' {
        $container = Read-AriaContainerBytes -Bytes $validGate.bytes
        $result = Invoke-AriaContainer `
            -Container $container `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru

        Assert-Equal @('[1,2,3,4]','[]','True') `
            @($result.outputs) `
            'Sequence runtime output changed.'
    }

    Test-SequenceCase 'function boundaries preserve sequence types' {
        $function = @(
            $validGate.bytecode.functions |
                Where-Object { [string]$_.name -eq 'EchoNumbers' }
        )[0]

        Assert-Equal 'Sequence<Number>' `
            $function.parameters[0].type `
            'Sequence function parameter changed.'
        Assert-Equal 'Sequence<Number>' `
            $function.returnType `
            'Sequence function return changed.'

        $calls = @(
            $validGate.bytecode.instructions |
                Where-Object { [string]$_.op -eq 'CALL' }
        )
        Assert-Equal 1 $calls.Count `
            'Sequence function call count changed.'
        Assert-Equal 'Sequence<Number>' `
            $calls[0].returnType `
            'Sequence CALL return contract changed.'
    }

    Test-SequenceCase 'sequence memory defaults survive bytecode projection' {
        $memory = $memoryGate.bytecode.memories[0]
        $valuesValidation = Test-AriaSequenceValue `
            -Value $memory.values.values
        $emptyValidation = Test-AriaSequenceValue `
            -Value $memory.values.empty

        Assert-True $valuesValidation.valid `
            'Sequence memory default was not encoded.'
        Assert-True $emptyValidation.valid `
            'Empty sequence memory default was not encoded.'
        Assert-Equal 'Sequence<Number>' `
            $memory.types.values `
            'Sequence memory type changed.'
        Assert-Equal 'Sequence<Text>' `
            $memory.types.empty `
            'Empty sequence memory type changed.'
    }

    Test-SequenceCase 'map filter and reduce are verified over sequence core' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        foreach ($id in @('algorithm.map','algorithm.filter','algorithm.reduce')) {
            Assert-Equal 'verified' (Get-AriaGlyphCard -Id $id -Registry $registry).status `
                "Algorithm card '$id' was not admitted."
        }

        Assert-Equal 9 @(Get-AriaExecutableGlyphAliases).Count `
            'Sequence core added an executable glyph alias.'

        $container = Read-AriaContainerBytes -Bytes $scalarGate.bytes
        $result = Invoke-AriaContainer `
            -Container $container `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru

        Assert-Equal @('42') @($result.outputs) `
            'Scalar runtime regression failed.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw (
            "Sequence test count diverged. Expected={0} Observed={1}" -f
                $script:Expected,
                ($script:Passed + $script:Failed)
        )
    }

    Write-Host (
        '⧉  sequence lattice {0}/{1} · {2}' -f
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
        throw "Sequence lattice failed: $script:Failed failure(s)."
    }
}
finally {
    Remove-Item `
        -LiteralPath $tempRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
}
