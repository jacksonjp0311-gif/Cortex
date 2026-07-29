[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$root = Split-Path -Parent $PSScriptRoot

foreach ($module in @(
    'Aria.Common.psm1',
    'Aria.Lexer.psm1',
    'Aria.Parser.psm1',
    'Aria.Semantics.psm1',
    'Aria.Bytecode.psm1',
    'Aria.Gate.psm1',
    'Aria.EventSpine.psm1',
    'Aria.VM.psm1',
    'Aria.GlyphMemory.psm1'
)) {
    Import-Module (Join-Path $root ('src/' + $module)) -Force -DisableNameChecking
}

$policyPath = Join-Path $root 'aria.policy.json'
$policy = Get-AriaPolicy -PolicyPath $policyPath
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aria-homeostasis-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $tempRoot -Force
$examplePath = Join-Path $tempRoot 'constitutional-homeostasis.aria'
$planPath = Join-Path $tempRoot 'constitutional-homeostasis-alpha18.aria'
Write-AriaUtf8NoBom -Path $examplePath -Text (Read-AriaUtf8Text (Join-Path $root 'examples/constitutional-homeostasis.aria'))
Write-AriaUtf8NoBom -Path $planPath -Text (Read-AriaUtf8Text (Join-Path $root 'plans/constitutional-homeostasis-alpha18.aria'))
$script:Passed = 0
$script:Failed = 0
$script:Expected = 12
$script:HomeostasisGate = $null
$script:HomeostasisContainer = $null
$script:HomeostasisResult = $null

function Assert-Homeostasis {
    param([bool]$Value,[string]$Message)
    if (-not $Value) { throw $Message }
}

function Assert-HomeostasisEqual {
    param($Expected,$Actual,[string]$Message)
    if (
        (ConvertTo-AriaJson ([pscustomobject]@{ value = $Expected })) -cne
        (ConvertTo-AriaJson ([pscustomobject]@{ value = $Actual }))
    ) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Test-HomeostasisCase {
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

function Get-HomeostasisGate {
    if ($null -eq $script:HomeostasisGate) {
        $script:HomeostasisGate = Invoke-AriaGate `
            -SourcePath $examplePath `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -Quiet
        $script:HomeostasisContainer = Read-AriaContainerBytes -Bytes $script:HomeostasisGate.bytes
    }
    return $script:HomeostasisGate
}

function Get-HomeostasisResult {
    if ($null -eq $script:HomeostasisResult) {
        $null = Get-HomeostasisGate
        Initialize-AriaEventSpine -WorkspaceRoot $tempRoot -Persist | Out-Null
        $script:HomeostasisResult = Invoke-AriaContainer `
            -Container $script:HomeostasisContainer `
            -PolicyPath $policyPath `
            -WorkspaceRoot $tempRoot `
            -PassThru
    }
    return $script:HomeostasisResult
}

$cardIds = @(
    'memory.balance',
    'governance.constitutional-potential',
    'governance.reversibility-burden',
    'authority.monotonic-descent',
    'recovery.verified-candidate'
)

Test-HomeostasisCase 'constitutional glyph cards are sealed and verified' {
    $registry = Read-AriaGlyphCardRegistry -Root $root
    foreach ($id in $cardIds) {
        $card = Get-AriaGlyphCard -Id $id -Registry $registry
        Assert-Homeostasis ((Test-AriaGlyphCard -Card $card).valid) "Glyph card '$id' is invalid."
        Assert-HomeostasisEqual 'verified' $card.status "Glyph card '$id' is not verified."
    }
}

Test-HomeostasisCase 'constitutional glyphs introduce no capability' {
    $registry = Read-AriaGlyphCardRegistry -Root $root
    foreach ($id in $cardIds) {
        Assert-HomeostasisEqual 0 @((Get-AriaGlyphCard -Id $id -Registry $registry).capabilities).Count "Glyph '$id' introduced authority."
    }
}

Test-HomeostasisCase 'function glyphs lower to their typed function targets' {
    $weave = [string][char]0x22C8
    $potential = [string][char]0x224B
    $burden = [string][char]0x2301
    $authority = [string][char]0x21A7
    $recovery = [string][char]0x21B6
    $cases = [ordered]@{
        ($weave + '(1, 1)') = 'MemoryBalance'
        ($potential + '(0, 0, 0, 0, 0, 0, 0, 0)') = 'ConstitutionalPotential'
        ($burden + '(1)') = 'ReversibilityBurden'
        ($authority + '(1, 2, false)') = 'AuthorityAdmissible'
        ($recovery + '(1, 0, true, true)') = 'RecoveryAdmissible'
    }
    foreach ($source in $cases.Keys) {
        $expression = ConvertFrom-AriaExpression -Text $source -Line 1
        Assert-HomeostasisEqual 'call' $expression.kind "Glyph '$source' did not lower to a call."
        Assert-HomeostasisEqual $cases[$source] $expression.name "Glyph '$source' selected the wrong function."
    }
}

Test-HomeostasisCase 'glyph and textual calls share canonical call arguments' {
    $glyph = ConvertFrom-AriaExpression -Text (([string][char]0x22C8) + '(0.8, 0.6)') -Line 1
    $word = ConvertFrom-AriaExpression -Text 'MemoryBalance(0.8, 0.6)' -Line 1
    Assert-HomeostasisEqual $word.name $glyph.name 'Glyph and textual target names diverged.'
    Assert-HomeostasisEqual @($word.arguments) @($glyph.arguments) 'Glyph and textual arguments diverged.'
}

Test-HomeostasisCase 'constitutional example passes compiler and bytecode gates' {
    $gate = Get-HomeostasisGate
    $verification = Test-AriaBytecodeModel -BytecodeModel $gate.bytecode
    Assert-Homeostasis $verification.valid (@($verification.errors) -join '; ')
}

Test-HomeostasisCase 'constitutional glyphs reuse existing call bytecode' {
    $gate = Get-HomeostasisGate
    Assert-Homeostasis (@($gate.bytecode.instructions.op | Where-Object { $_ -eq 'CALL' }).Count -ge 5) 'Constitutional glyph calls were not explicit CALL instructions.'
    Assert-Homeostasis (@($gate.bytecode.instructions.op | Where-Object { $_ -match 'GLYPH|CONSTITUTION|AUTHORITY_DESCENT|RECOVERY' }).Count -eq 0) 'Constitutional glyphs introduced a privileged opcode.'
}

Test-HomeostasisCase 'context weave balances preservation and adjacency' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis ([math]::Abs(([double]$result.outputs[0]) - 0.6857142857) -lt 0.000001) 'Context weave output changed.'
}

Test-HomeostasisCase 'constitutional potential remains a bounded observation' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis ([math]::Abs(([double]$result.outputs[1]) - 0.0875) -lt 0.000001) 'Potential output changed.'
}

Test-HomeostasisCase 'reversibility burden rises with irreversibility' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis ([double]$result.outputs[2] -gt 0.60) 'Reversibility burden did not rise.'
}

Test-HomeostasisCase 'authority descent rejects ungranted growth' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis (-not [Convert]::ToBoolean($result.outputs[3])) 'Ungranted authority growth was admitted.'
}

Test-HomeostasisCase 'authority descent admits externally verified growth' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis ([Convert]::ToBoolean($result.outputs[4])) 'Verified authority growth was rejected.'
}

Test-HomeostasisCase 'verified recovery requires descent integrity and resolution' {
    $result = Get-HomeostasisResult
    Assert-Homeostasis ([Convert]::ToBoolean($result.outputs[5])) 'Valid recovery candidate was rejected.'
    $plan = Invoke-AriaGate -SourcePath $planPath -PolicyPath $policyPath -WorkspaceRoot $tempRoot -Quiet
    Assert-Homeostasis ((Test-AriaBytecodeModel -BytecodeModel $plan.bytecode).valid) 'Constitutional evolution plan failed bytecode verification.'
}

Write-Host (
    "⧉  constitutional-homeostasis lattice {0}/{1} · {2}" -f
    $script:Passed,
    $script:Expected,
    $(if ($script:Failed) { 'fractured' } else { 'coherent' })
) -ForegroundColor $(if ($script:Failed) { 'Magenta' } else { 'Green' })

$null = Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue

if ($script:Passed + $script:Failed -ne $script:Expected) {
    throw 'Constitutional homeostasis test count diverged.'
}
if ($script:Failed) {
    throw "Constitutional homeostasis lattice failed: $script:Failed failure(s)."
}
