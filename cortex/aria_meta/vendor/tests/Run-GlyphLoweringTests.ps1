[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    ('aria-glyph-lowering-' + [guid]::NewGuid().ToString('N'))

Import-Module `
    (Join-Path $root 'src/Aria.Common.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.Lexer.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.Parser.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.Semantics.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.Bytecode.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.Gate.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.VM.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.GlyphMemory.psm1') `
    -Force `
    -DisableNameChecking

$policyPath = Join-Path $root 'aria.policy.json'
$policy = Get-AriaPolicy -PolicyPath $policyPath

$script:Passed = 0
$script:Failed = 0
$script:Expected = 12

function Assert-True {
    param([bool]$Condition,[string]$Message)

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Equal {
    param($Expected,$Actual,[string]$Message)

    $expectedJson = ConvertTo-AriaJson `
        ([pscustomobject][ordered]@{ value = $Expected })

    $actualJson = ConvertTo-AriaJson `
        ([pscustomobject][ordered]@{ value = $Actual })

    if ($expectedJson -ne $actualJson) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Test-GlyphLoweringCase {
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
            "⬗  {0} · {1}" -f
                $Name,
                $_.Exception.Message
        ) -ForegroundColor Magenta
    }
}

function Write-TestSource {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Source
    )

    $path = Join-Path $tempRoot $Name
    $encoding = New-Object Text.UTF8Encoding($false)
    $canonical = $Source.Replace("`r`n","`n").Replace("`r","`n")

    if (-not $canonical.EndsWith("`n")) {
        $canonical += "`n"
    }

    [IO.File]::WriteAllText($path, $canonical, $encoding)
    return $path
}

function Get-SourceDiagnostics {
    param([Parameter(Mandatory=$true)][string]$Source)

    $parsed = Parse-AriaSource `
        -Source $Source `
        -SourceName '<glyph-lowering-diagnostic>'

    $semantic = Test-AriaSemantics `
        -ParseResult $parsed `
        -Policy $policy

    return @(
        Get-AriaErrorDiagnostics `
            -Diagnostics $semantic.diagnostics
    )
}

function Get-DiagnosticIdentity {
    param([object[]]$Diagnostics)

    return @(
        $Diagnostics |
            ForEach-Object {
                "{0}|{1}|{2}" -f
                    $_.code,
                    $_.line,
                    $_.message
            }
    )
}

$glyphSource = @'
aria 0.4.0
module GlyphFunctions version 0.1.0
program GlyphFunctions version 0.1.0
entry Main

function Add(left: Number, right: Number) -> Number {
  ↩ left + right
}

function Double(value: Number) -> Number {
  ↩ value * 2
}

flow Main {
  let total: Number = ▷ Add(20, 22)
  let nested: Number = ▷ Double(▷ Add(10, 11))
  emit total
  emit nested
  halt
}
'@

$textSource = @'
aria 0.4.0
module GlyphFunctions version 0.1.0
program GlyphFunctions version 0.1.0
entry Main

function Add(left: Number, right: Number) -> Number {
  return left + right
}

function Double(value: Number) -> Number {
  return value * 2
}

flow Main {
  let total: Number = Add(20, 22)
  let nested: Number = Double(Add(10, 11))
  emit total
  emit nested
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $glyphPath = Write-TestSource `
        -Name 'glyph-functions.aria' `
        -Source $glyphSource

    $textPath = Write-TestSource `
        -Name 'text-functions.aria' `
        -Source $textSource

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
    Write-Host '⌬  ARIA / GLYPH LOWERING' -ForegroundColor Cyan
    Write-Host '⧉  glyph-lowering lattice ×12' -ForegroundColor DarkGray

    Test-GlyphLoweringCase 'alias registry aligns with verified cards' {
        $aliases = @(Get-AriaExecutableGlyphAliases)
        Assert-Equal 9 $aliases.Count 'Executable alias count mismatch.'

        $invokeAlias = @(
            $aliases |
                Where-Object { [string]$_.glyph -eq '▷' }
        )

        $returnAlias = @(
            $aliases |
                Where-Object { [string]$_.glyph -eq '↩' }
        )

        Assert-Equal 1 $invokeAlias.Count 'Invoke alias is missing.'
        Assert-Equal 1 $returnAlias.Count 'Return alias is missing.'
        Assert-Equal 'call' $invokeAlias[0].keyword 'Invoke alias target mismatch.'
        Assert-Equal 'return' $returnAlias[0].keyword 'Return alias target mismatch.'

        $registry = Read-AriaGlyphCardRegistry -Root $root
        $invokeCard = Get-AriaGlyphCard `
            -Id 'function.invoke' `
            -Registry $registry

        $returnCard = Get-AriaGlyphCard `
            -Id 'function.return' `
            -Registry $registry

        Assert-Equal $invokeCard.symbol $invokeAlias[0].glyph `
            'Invoke alias diverged from its semantic card.'

        Assert-Equal $returnCard.symbol $returnAlias[0].glyph `
            'Return alias diverged from its semantic card.'
    }

    Test-GlyphLoweringCase 'invoke glyph lowers to canonical call AST' {
        $expression = ConvertFrom-AriaExpression `
            -Text '▷ Add(1, 2)' `
            -Line 1

        Assert-Equal 'call' $expression.kind 'Invoke glyph did not lower to call.'
        Assert-Equal 'Add' $expression.name 'Invoke target mismatch.'
        Assert-Equal 2 @($expression.arguments).Count 'Invoke argument count mismatch.'

        Assert-True (
            $null -eq $expression.PSObject.Properties['surface']
        ) 'Canonical call AST retained a glyph-only surface property.'
    }

    Test-GlyphLoweringCase 'invoke glyph supports adjacency and nesting' {
        $adjacent = ConvertFrom-AriaExpression `
            -Text '▷Add(1, 2)' `
            -Line 1

        $nested = ConvertFrom-AriaExpression `
            -Text '▷ Double(▷Add(10, 11))' `
            -Line 1

        Assert-Equal 'call' $adjacent.kind 'Adjacent invoke glyph was rejected.'
        Assert-Equal 'Double' $nested.name 'Outer nested call target mismatch.'
        Assert-Equal 'call' $nested.arguments[0].kind `
            'Nested invoke glyph did not lower recursively.'
        Assert-Equal 'Add' $nested.arguments[0].name `
            'Nested invoke target mismatch.'
    }

    Test-GlyphLoweringCase 'return glyph lowers to canonical return statement' {
        $parsed = Parse-AriaSource `
            -Source $glyphSource `
            -SourceName '<glyph-return>'

        $errors = Get-AriaErrorDiagnostics `
            -Diagnostics $parsed.diagnostics

        if ($errors.Count -ne 0) {
            throw (
                'Glyph return emitted parser errors: ' +
                (@(
                    $errors |
                        ForEach-Object {
                            "{0}@{1}:{2}" -f
                                $_.code,
                                $_.line,
                                $_.message
                        }
                ) -join '; ')
            )
        }

        $returns = @(
            $parsed.model.functions |
                ForEach-Object { @($_.statements) } |
                Where-Object { [string]$_.op -eq 'return' }
        )

        Assert-Equal 2 $returns.Count 'Glyph return statement count mismatch.'

        foreach ($statement in $returns) {
            Assert-True (
                $null -eq $statement.PSObject.Properties['surface']
            ) 'Canonical return AST retained a glyph-only surface property.'
        }
    }

    Test-GlyphLoweringCase 'glyph and textual source share semantic IR' {
        Assert-Equal $textGate.irHash $glyphGate.irHash `
            'Glyph and textual semantic IR hashes differ.'
    }

    Test-GlyphLoweringCase 'glyph and textual executable bytecode are equal' {
        $textProjection = [pscustomobject][ordered]@{
            constants = $textGate.bytecode.constants
            functions = $textGate.bytecode.functions
            instructions = $textGate.bytecode.instructions
        }

        $glyphProjection = [pscustomobject][ordered]@{
            constants = $glyphGate.bytecode.constants
            functions = $glyphGate.bytecode.functions
            instructions = $glyphGate.bytecode.instructions
        }

        Assert-Equal $textProjection $glyphProjection `
            'Executable bytecode projection differs.'
    }

    Test-GlyphLoweringCase 'source provenance remains distinct' {
        Assert-True (
            $textGate.sourceHash -ne $glyphGate.sourceHash
        ) 'Different source surfaces collapsed to one source hash.'

        Assert-True (
            $textGate.buildHash -ne $glyphGate.buildHash
        ) 'Provenance-bearing containers unexpectedly share a build hash.'
    }

    Test-GlyphLoweringCase 'lowering introduces no new opcode' {
        $opcodes = Get-AriaOpcodeRegistry
        Assert-Equal 40 $opcodes.Count 'Opcode registry changed during lowering.'

        $generated = @(
            @($glyphGate.bytecode.instructions.op) +
            @(
                $glyphGate.bytecode.functions |
                    ForEach-Object {
                        @($_.instructions.op)
                    }
            )
        )

        Assert-True ('CALL' -in $generated) 'CALL was not generated.'
        Assert-True ('RETURN' -in $generated) 'RETURN was not generated.'
    }

    Test-GlyphLoweringCase 'glyph program executes expected values' {
        $container = Read-AriaContainerBytes -Bytes $glyphGate.bytes
        $result = Invoke-AriaContainer `
            -Container $container `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru

        Assert-Equal @('42','42') @($result.outputs) `
            'Glyph runtime output mismatch.'
    }

    Test-GlyphLoweringCase 'glyph and textual runtime behavior are equal' {
        $glyphContainer = Read-AriaContainerBytes -Bytes $glyphGate.bytes
        $textContainer = Read-AriaContainerBytes -Bytes $textGate.bytes

        $glyphResult = Invoke-AriaContainer `
            -Container $glyphContainer `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru

        $textResult = Invoke-AriaContainer `
            -Container $textContainer `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru

        Assert-Equal @($textResult.outputs) @($glyphResult.outputs) `
            'Runtime outputs differ by source surface.'
    }

    Test-GlyphLoweringCase 'unknown function diagnostics preserve parity' {
        $glyphUnknown = $glyphSource.Replace(
            '▷ Add(20, 22)',
            '▷ Missing(20, 22)'
        )

        $textUnknown = $textSource.Replace(
            'Add(20, 22)',
            'Missing(20, 22)'
        )

        $glyphErrors = Get-SourceDiagnostics -Source $glyphUnknown
        $textErrors = Get-SourceDiagnostics -Source $textUnknown

        Assert-Equal `
            (Get-DiagnosticIdentity $textErrors) `
            (Get-DiagnosticIdentity $glyphErrors) `
            'Unknown-function diagnostics differ.'

        Assert-True (
            'ARIA2061' -in @($glyphErrors.code)
        ) 'Unknown function diagnostic code is missing.'
    }

    Test-GlyphLoweringCase 'type and return authority diagnostics preserve parity' {
        $glyphType = $glyphSource.Replace(
            '▷ Add(20, 22)',
            '▷ Add("twenty", 22)'
        )

        $textType = $textSource.Replace(
            'Add(20, 22)',
            'Add("twenty", 22)'
        )

        Assert-Equal `
            (Get-DiagnosticIdentity (Get-SourceDiagnostics $textType)) `
            (Get-DiagnosticIdentity (Get-SourceDiagnostics $glyphType)) `
            'Argument-type diagnostics differ.'

        $glyphReturn = @'
aria 0.4.0
program ReturnAuthority version 0.1.0
entry Main

flow Main {
  ↩ 1
}
'@

        $textReturn = @'
aria 0.4.0
program ReturnAuthority version 0.1.0
entry Main

flow Main {
  return 1
}
'@

        $glyphReturnErrors = Get-SourceDiagnostics $glyphReturn
        $textReturnErrors = Get-SourceDiagnostics $textReturn

        Assert-Equal `
            (Get-DiagnosticIdentity $textReturnErrors) `
            (Get-DiagnosticIdentity $glyphReturnErrors) `
            'Return-scope diagnostics differ.'

        Assert-True (
            'ARIA2087' -in @($glyphReturnErrors.code)
        ) 'Return authority diagnostic code is missing.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw (
            "Glyph-lowering test count diverged. Expected={0} Observed={1}" -f
                $script:Expected,
                ($script:Passed + $script:Failed)
        )
    }

    Write-Host (
        '⧉  glyph-lowering lattice {0}/{1} · {2}' -f
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
        throw "Glyph-lowering lattice failed: $script:Failed failure(s)."
    }
}
finally {
    Remove-Item `
        -LiteralPath $tempRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
}
