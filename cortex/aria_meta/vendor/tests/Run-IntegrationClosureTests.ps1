[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Intent.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.IntentVerifier.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GlyphMemory.psm1') -Force -DisableNameChecking

$policyPath = Join-Path $root 'aria.policy.json'
$script:Passed = 0
$script:Failed = 0
$script:Expected = 6

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

function Test-ClosureCase {
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

$helloGate = Invoke-AriaGate `
    -SourcePath (Join-Path $root 'examples/hello.aria') `
    -PolicyPath $policyPath `
    -WorkspaceRoot $root `
    -Quiet

$effectGate = Invoke-AriaGate `
    -SourcePath (Join-Path $root 'examples/effect-purity.aria') `
    -PolicyPath $policyPath `
    -WorkspaceRoot $root `
    -Quiet

Write-Host ''
Write-Host '⌬  ARIA / INTEGRATION CLOSURE ALPHA.5.1' -ForegroundColor Cyan
Write-Host '⧉  integration lattice ×6' -ForegroundColor DarkGray

Test-ClosureCase 'entry flow effects are complete and explicit' {
    Assert-Equal 2 $helloGate.effectGraph.version `
        'Whole-program effect graph version changed.'
    $entry = Get-AriaEffectSummary $helloGate.effectGraph '$entry'
    Assert-Equal 'effectful' $entry.purity 'Hello entry purity changed.'
    Assert-Equal @('console.emit','memory.read','memory.write') `
        @($entry.directEffects) 'Entry effects are incomplete.'
}

Test-ClosureCase 'entry calls participate in transitive closure' {
    $entry = Get-AriaEffectSummary $effectGate.effectGraph '$entry'
    Assert-Equal @('Double','Increment') @($entry.calls) `
        'Entry call topology changed.'
    Assert-Equal @('console.emit') @($entry.transitiveEffects) `
        'Entry transitive effects changed.'
}

Test-ClosureCase 'verifier rejects a false resealed entry summary' {
    $tampered = (ConvertTo-AriaJson $helloGate.bytecode) | ConvertFrom-Json
    $entry = Get-AriaEffectSummary $tampered.effectGraph '$entry'
    $entry.directEffects = @('console.emit')
    $entry.transitiveEffects = @('console.emit')
    $entry.digest = Get-AriaEffectSummaryDigest $entry
    $tampered.effectGraph.digest = Get-AriaEffectGraphDigest $tampered.effectGraph
    $verification = Test-AriaBytecodeModel $tampered
    Assert-True (-not[bool]$verification.valid) `
        'Verifier accepted a false whole-program effect graph.'
    Assert-True (
        (@($verification.errors) -join "`n") -match
        'Effect graph does not match executable instructions'
    ) 'Entry-effect mismatch diagnostic is missing.'
}

Test-ClosureCase 'intent program summary derives from admitted artifact' {
    $summary = New-AriaIntentProgramSummaryFromArtifact `
        -ArtifactBytes $helloGate.bytes
    $validation = Test-AriaIntentProgramSummary $summary
    Assert-True ([bool]$validation.valid) `
        'Artifact-derived intent summary was rejected.'
    Assert-Equal "sha256:$(Get-AriaSha256Bytes -Bytes $helloGate.bytes)" `
        $summary.artifactId 'Intent summary artifact binding changed.'
    Assert-Equal $helloGate.effectGraph.digest $summary.effectGraphId `
        'Intent summary effect binding changed.'
    Assert-Equal @('console.emit','memory.read','memory.write') `
        @($summary.requestedEffects) 'Intent summary effects were self-reported.'
}

Test-ClosureCase 'intent derivation rejects corrupt artifact bytes' {
    [byte[]]$corrupt = $helloGate.bytes.Clone()
    $corrupt[$corrupt.Length - 1] = $corrupt[$corrupt.Length - 1] -bxor 1
    $rejected = $false
    try {
        $null = New-AriaIntentProgramSummaryFromArtifact `
            -ArtifactBytes $corrupt
    }
    catch { $rejected = $true }
    Assert-True $rejected 'Corrupt artifact produced an intent summary.'
}

Test-ClosureCase 'integration closure remains authority-stable after reduce' {
    Assert-Equal 40 (Get-AriaOpcodeRegistry).Count `
        'Verified algorithm opcodes are missing.'
    $registry = Read-AriaGlyphCardRegistry -Root $root
    foreach ($id in @('algorithm.map','algorithm.filter','algorithm.reduce')) {
        $card = Get-AriaGlyphCard -Id $id -Registry $registry
        Assert-Equal 'verified' $card.status "Algorithm '$id' was not admitted."
        Assert-Equal 0 @($card.capabilities).Count "Algorithm '$id' introduced authority."
    }
}

if (($script:Passed + $script:Failed) -ne $script:Expected) {
    throw (
        'Integration test count diverged. Expected={0} Observed={1}' -f
            $script:Expected,
            ($script:Passed + $script:Failed)
    )
}

Write-Host (
    '⧉  integration lattice {0}/{1} · {2}' -f
        $script:Passed,
        $script:Expected,
        $(if ($script:Failed -eq 0) { 'coherent' } else { "$($script:Failed) fracture(s)" })
) -ForegroundColor $(if ($script:Failed -eq 0) { 'Green' } else { 'Magenta' })

if ($script:Failed -gt 0) {
    throw "Integration lattice failed: $script:Failed failure(s)."
}
