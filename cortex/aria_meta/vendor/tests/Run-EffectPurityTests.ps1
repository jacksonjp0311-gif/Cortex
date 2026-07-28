[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    ('aria-effect-purity-' + [guid]::NewGuid().ToString('N'))

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
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
$script:Expected = 18

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param($Expected,$Actual,[string]$Message)
    $expectedJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{ value=$Expected })
    $actualJson = ConvertTo-AriaJson ([pscustomobject][ordered]@{ value=$Actual })
    if ($expectedJson -ne $actualJson) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Assert-Contains {
    param([object[]]$Values,[string]$Pattern,[string]$Message)
    $joined = @($Values | ForEach-Object { [string]$_ }) -join "`n"
    if ($joined -notmatch [regex]::Escape($Pattern)) {
        throw "$Message Observed=$joined"
    }
}

function Test-EffectCase {
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

$source = @'
aria 0.4.0
module EffectPurity version 0.5.0
program EffectPurity version 0.5.0
entry Main

capability RepoRead {
  effect = "fs.read"
  scope = "."
}

function Increment(value: Number) -> Number {
  ↩ value + 1
}

function Double(value: Number) -> Number {
  ↩ Increment(value) * 2
}

function Speak(value: Number) -> Number {
  emit value
  ↩ value
}

function SpeakThrough(value: Number) -> Number {
  ↩ Speak(value)
}

function ReadText(path: Text) -> Text {
  require RepoRead
  read path -> content
  ↩ content
}

function ReadThrough(path: Text) -> Text {
  ↩ ReadText(path)
}

function Ordered(path: Text, value: Number) -> Number {
  let content: Text = ReadText(path)
  let spoken: Number = Speak(value)
  ↩ Increment(spoken)
}

function CycleA(value: Number) -> Number {
  ↩ CycleB(value)
}

function CycleB(value: Number) -> Number {
  emit value
  ↩ CycleA(value)
}

flow Main {
  let result: Number = Double(20)
  emit result
  halt
}
'@

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    $sourcePath = Write-TestSource 'effect-purity.aria' $source
    $twinPath = Write-TestSource 'effect-purity-twin.aria' $source

    $gate = Invoke-AriaGate `
        -SourcePath $sourcePath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $twinGate = Invoke-AriaGate `
        -SourcePath $twinPath `
        -PolicyPath $policyPath `
        -WorkspaceRoot $tempRoot `
        -Quiet

    $graph = $gate.effectGraph

    Write-Host ''
    Write-Host '⌬  ARIA / EFFECT GRAPH & PURITY CORE' -ForegroundColor Cyan
    Write-Host '⧉  effect lattice ×18' -ForegroundColor DarkGray

    Test-EffectCase 'effect graph is sealed and valid' {
        $validation = Test-AriaEffectGraph $graph
        Assert-True $validation.valid (
            'Effect graph rejected: ' + (@($validation.errors) -join ', ')
        )
        Assert-True ([string]$graph.digest -match '^sha256:[a-f0-9]{64}$') `
            'Effect graph digest is malformed.'
    }

    Test-EffectCase 'direct pure function inference is exact' {
        $summary = Get-AriaEffectSummary $graph 'Increment'
        Assert-Equal 'pure' $summary.purity 'Increment purity changed.'
        Assert-Equal 0 @($summary.directEffects).Count 'Pure function gained an effect.'
        Assert-Equal 0 @($summary.directCapabilities).Count 'Pure function gained a capability.'
    }

    Test-EffectCase 'direct effect inference is exact' {
        $summary = Get-AriaEffectSummary $graph 'Speak'
        Assert-Equal 'effectful' $summary.purity 'Speak purity changed.'
        Assert-Equal @('console.emit') @($summary.directEffects) `
            'Direct console effect changed.'
    }

    Test-EffectCase 'transitive effect closure follows calls' {
        $summary = Get-AriaEffectSummary $graph 'SpeakThrough'
        Assert-Equal 0 @($summary.directEffects).Count `
            'Wrapper gained a direct effect.'
        Assert-Equal @('console.emit') @($summary.transitiveEffects) `
            'Transitive console effect was not propagated.'
        Assert-Equal 'effectful' $summary.purity `
            'Effectful call chain was marked pure.'
    }

    Test-EffectCase 'direct capability requirements are recorded' {
        $summary = Get-AriaEffectSummary $graph 'ReadText'
        Assert-Equal @('RepoRead') @($summary.directCapabilities) `
            'Direct capability summary changed.'
        Assert-Equal @('fs.read') @($summary.directEffects) `
            'Direct fs.read effect changed.'
    }

    Test-EffectCase 'transitive capability closure follows calls' {
        $summary = Get-AriaEffectSummary $graph 'ReadThrough'
        Assert-Equal 0 @($summary.directCapabilities).Count `
            'Wrapper gained a direct capability.'
        Assert-Equal @('RepoRead') @($summary.transitiveCapabilities) `
            'Transitive capability was not propagated.'
        Assert-Equal @('fs.read') @($summary.transitiveEffects) `
            'Transitive fs.read effect was not propagated.'
    }

    Test-EffectCase 'pure call chains remain provably pure' {
        $summary = Get-AriaEffectSummary $graph 'Double'
        Assert-Equal @('Increment') @($summary.calls) `
            'Pure call edge changed.'
        Assert-Equal 'pure' $summary.purity `
            'Pure call chain was marked effectful.'
    }

    Test-EffectCase 'multi-edge effect closure is interconnected' {
        $summary = Get-AriaEffectSummary $graph 'Ordered'
        Assert-Equal @('Increment','ReadText','Speak') @($summary.calls) `
            'Call graph order or edges changed.'
        Assert-Equal @('console.emit','fs.read') @($summary.transitiveEffects) `
            'Combined effect closure changed.'
        Assert-Equal @('RepoRead') @($summary.transitiveCapabilities) `
            'Combined capability closure changed.'
    }

    Test-EffectCase 'call graph and digests are deterministic' {
        Assert-Equal $graph.digest $twinGate.effectGraph.digest `
            'Equivalent sources produced different effect graph identity.'
        Assert-Equal @($graph.functions.name) @($twinGate.effectGraph.functions.name) `
            'Equivalent sources produced different function order.'
    }

    Test-EffectCase 'recursive cycles converge with effect propagation' {
        $left = Get-AriaEffectSummary $graph 'CycleA'
        $right = Get-AriaEffectSummary $graph 'CycleB'
        Assert-True ([bool]$left.recursive) 'CycleA was not marked recursive.'
        Assert-True ([bool]$right.recursive) 'CycleB was not marked recursive.'
        Assert-Equal @('console.emit') @($left.transitiveEffects) `
            'Cycle effect did not reach CycleA.'
        Assert-Equal @('console.emit') @($right.transitiveEffects) `
            'Cycle effect did not remain on CycleB.'
    }

    Test-EffectCase 'source and bytecode effect graphs are equal' {
        $derived = Get-AriaBytecodeEffectGraph $gate.bytecode
        Assert-True (Test-AriaEffectGraphEquivalent $graph $derived) `
            'Source and bytecode effect graphs diverged.'
    }

    Test-EffectCase 'function summaries project into executable metadata' {
        foreach ($function in @($gate.bytecode.functions)) {
            $expected = Get-AriaEffectSummary $graph ([string]$function.name)
            Assert-Equal `
                (ConvertTo-AriaEffectSummaryCanonicalBody $expected) `
                (ConvertTo-AriaEffectSummaryCanonicalBody $function.effectSummary) `
                "Function '$($function.name)' effect projection changed."
        }
    }

    Test-EffectCase 'verifier rejects a coherently resealed false graph' {
        $tampered = (ConvertTo-AriaJson $gate.bytecode) | ConvertFrom-Json
        $summary = Get-AriaEffectSummary $tampered.effectGraph 'Increment'
        $summary.directEffects = @('console.emit')
        $summary.transitiveEffects = @('console.emit')
        $summary.purity = 'effectful'
        $summary.digest = Get-AriaEffectSummaryDigest $summary
        $tampered.effectGraph.digest = Get-AriaEffectGraphDigest $tampered.effectGraph
        $verification = Test-AriaBytecodeModel $tampered
        Assert-True (-not $verification.valid) `
            'Verifier accepted a false but resealed effect graph.'
        Assert-Contains @($verification.errors) `
            'Effect graph does not match executable instructions.' `
            'Independent derivation error is missing.'
    }

    Test-EffectCase 'verifier rejects per-function summary drift' {
        $tampered = (ConvertTo-AriaJson $gate.bytecode) | ConvertFrom-Json
        $target = @(
            $tampered.functions |
                Where-Object { [string]$_.name -eq 'Double' }
        )[0]
        $target.effectSummary.purity = 'effectful'
        $verification = Test-AriaBytecodeModel $tampered
        Assert-True (-not $verification.valid) `
            'Verifier accepted function-summary drift.'
        Assert-Contains @($verification.errors) `
            "Function 'Double' effect summary does not match the effect graph." `
            'Function-summary parity error is missing.'
    }

    Test-EffectCase 'VM admits and exposes only verified effect metadata' {
        $container = Read-AriaContainerBytes -Bytes $gate.bytes
        $result = Invoke-AriaContainer `
            -Container $container `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru
        Assert-Equal @('42') @($result.outputs) 'Runtime output changed.'
        Assert-Equal $graph.digest $result.effectGraph.digest `
            'VM did not expose the admitted effect graph.'
    }

    Test-EffectCase 'effect graph formatter presents bounded operator evidence' {
        $formatted = Format-AriaEffectGraph $graph
        Assert-True ($formatted -match 'PURE  Increment') `
            'Pure function is missing from effect view.'
        Assert-True ($formatted -match 'EFFECTFUL  ReadThrough') `
            'Effectful function is missing from effect view.'
        Assert-True ($formatted -match 'capabilities=RepoRead') `
            'Capability evidence is missing from effect view.'
    }

    Test-EffectCase 'algorithm cards consume purity proof at bounded stages' {
        $registry = Read-AriaGlyphCardRegistry -Root $root
        foreach ($id in @('algorithm.map','algorithm.filter','algorithm.reduce')) {
            $card = Get-AriaGlyphCard -Id $id -Registry $registry
            Assert-Equal 'verified' $card.status `
                "Algorithm card '$id' has the wrong admission stage."
            Assert-True (
                @($card.tests | Where-Object { [string]$_ -match 'effect graph' }).Count -ge 1
            ) "Algorithm card '$id' does not reference effect-graph proof."
        }
    }

    Test-EffectCase 'effect core expands neither opcode nor policy authority' {
        Assert-Equal 40 (Get-AriaOpcodeRegistry).Count `
            'Effect core changed the opcode registry.'
        Assert-Equal @(
            'agent.dispatch','console.emit','fs.read','fs.write',
            'graph.inspect','memory.read','memory.write','network.connect',
            'process.exec'
        ) @($policy.effects.PSObject.Properties.Name | Sort-Object) `
            'Effect core changed policy effect authority.'

        $sequenceSource = @'
aria 0.4.0
module EffectSequenceRegression version 0.5.0
program EffectSequenceRegression version 0.5.0
entry Main

function Echo(values: Sequence<Number>) -> Sequence<Number> {
  ↩ values
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3]
  let echoed: Sequence<Number> = values ≫ Echo
  emit values == echoed
  halt
}
'@
        $sequencePath = Write-TestSource 'effect-sequence-regression.aria' $sequenceSource
        $sequenceGate = Invoke-AriaGate `
            -SourcePath $sequencePath `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -Quiet
        $echo = Get-AriaEffectSummary $sequenceGate.effectGraph 'Echo'
        Assert-Equal 'pure' $echo.purity `
            'Sequence/composition regression changed purity.'
    }

    if (($script:Passed + $script:Failed) -ne $script:Expected) {
        throw (
            'Effect test count diverged. Expected={0} Observed={1}' -f
                $script:Expected,
                ($script:Passed + $script:Failed)
        )
    }

    Write-Host (
        '⧉  effect lattice {0}/{1} · {2}' -f
            $script:Passed,
            $script:Expected,
            $(if ($script:Failed -eq 0) { 'coherent' } else { "$($script:Failed) fracture(s)" })
    ) -ForegroundColor $(if ($script:Failed -eq 0) { 'Green' } else { 'Magenta' })

    if ($script:Failed -gt 0) {
        throw "Effect lattice failed: $script:Failed failure(s)."
    }
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
