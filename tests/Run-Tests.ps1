[CmdletBinding()]
param(
    [switch]$VerboseOutput,

    [ValidateSet(
        'all',
        'syntax',
        'authority',
        'artifact',
        'state',
        'evolution',
        'transmission'
    )]
    [string]$Lane = 'all'
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tempRoot = [System.IO.Path]::GetTempPath()
if ([string]::IsNullOrWhiteSpace($tempRoot)) {
    throw 'ARIA could not resolve the platform temporary directory.'
}

Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Etherflow.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Transmission.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SignalSubset.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gitflow.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking

$lanePath = Join-Path $PSScriptRoot 'conformance-lanes.json'

if (-not (Test-Path -LiteralPath $lanePath -PathType Leaf)) {
    throw "ARIA conformance lane registry is missing: $lanePath"
}

$laneDocument = Get-Content `
    -LiteralPath $lanePath `
    -Encoding UTF8 `
    -Raw |
    ConvertFrom-Json

if ([string]$laneDocument.schema -ne 'aria.conformance-lanes') {
    throw 'ARIA conformance lane registry has an invalid schema identity.'
}

if ([int]$laneDocument.version -ne 1) {
    throw 'ARIA conformance lane registry has an unsupported version.'
}

$validLanes = @(
    'syntax'
    'authority'
    'artifact'
    'state'
    'evolution'
    'transmission'
)

$laneRecords = @($laneDocument.tests)

if ($laneRecords.Count -ne 202) {
    throw "ARIA conformance lane registry expected 202 tests but found $($laneRecords.Count)."
}

$script:LaneByName = @{}

foreach ($record in $laneRecords) {
    $name = [string]$record.name
    $recordLane = [string]$record.lane

    if ([string]::IsNullOrWhiteSpace($name)) {
        throw 'ARIA conformance lane registry contains an unnamed test.'
    }

    if ($script:LaneByName.ContainsKey($name)) {
        throw "ARIA conformance lane registry contains duplicate test identity: $name"
    }

    if ($recordLane -notin $validLanes) {
        throw "ARIA conformance test '$name' has invalid lane '$recordLane'."
    }

    $script:LaneByName[$name] = $recordLane
}

$expectedTests = if ($Lane -eq 'all') {
    $laneRecords.Count
}
else {
    @(
        $laneRecords |
            Where-Object {
                [string]$_.lane -eq $Lane
            }
    ).Count
}

if ($expectedTests -le 0) {
    throw "ARIA conformance lane '$Lane' contains no tests."
}

$script:ObservedTests = 0
$script:Passed = 0
$script:Failed = 0
$script:SuiteClock = [Diagnostics.Stopwatch]::StartNew()

$subtitle = if ($Lane -eq 'all') {
    'compiler · verifier · policy · memory · virtual machine'
}
else {
    "directional verifier lane · $Lane"
}

$enumeratorName = if ($Lane -eq 'all') {
    'conformance lattice'
}
else {
    "$Lane lane"
}

Write-AriaBanner `
    -Title 'ARIA / CONFORMANCE' `
    -Subtitle $subtitle

Start-AriaEnumerator `
    -Name $enumeratorName `
    -Expected $expectedTests `
    -Domain 'conformance'

function Test-Case {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )

    if (-not $script:LaneByName.ContainsKey($Name)) {
        throw "ARIA test is absent from the conformance lane registry: $Name"
    }

    $testLane = [string]$script:LaneByName[$Name]

    if ($Lane -ne 'all' -and $testLane -ne $Lane) {
        return
    }

    $script:ObservedTests++
    $clock = [Diagnostics.Stopwatch]::StartNew()

    try {
        & $Body
        $clock.Stop()

        Add-AriaEnumerationItem `
            -Name $Name `
            -State Pass `
            -Duration $clock.Elapsed

        $script:Passed++
    }
    catch {
        $clock.Stop()

        Add-AriaEnumerationItem `
            -Name $Name `
            -State Fail `
            -Detail $_.Exception.Message `
            -Duration $clock.Elapsed

        if ($VerboseOutput) {
            Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
        }

        $script:Failed++
    }
}
function Assert-True { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
function Assert-Equal { param($Expected, $Actual, [string]$Message) if ((ConvertTo-AriaJson -Value ([pscustomobject][ordered]@{v=$Expected})) -ne (ConvertTo-AriaJson -Value ([pscustomobject][ordered]@{v=$Actual}))) { throw "$Message Expected=$Expected Actual=$Actual" } }

$policy = Join-Path $root 'aria.policy.json'
$hello = Join-Path $root 'examples/hello.aria'
$denied = Join-Path $root 'examples/denied-write.aria'


Import-Module (Join-Path $root 'src/Aria.GraphCore.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.TypedCore.psm1') -Force -DisableNameChecking

Import-Module (Join-Path $root 'src/Aria.GraphReplay.psm1') -Force -DisableNameChecking

Import-Module (Join-Path $root 'src/Aria.CapabilityAuthority.psm1') -Force -DisableNameChecking

Import-Module (Join-Path $root 'src/Aria.GovernedEvolution.psm1') -Force -DisableNameChecking

Import-Module (Join-Path $root 'src/Aria.EvolutionPlanning.psm1') -Force -DisableNameChecking

Import-Module (Join-Path $root 'src/Aria.SourceCore.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Intent.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.IntentVerifier.psm1') -Force -DisableNameChecking

Test-Case 'opcode registry is machine-readable and complete' {
    $registry = Get-AriaOpcodeRegistry
    Assert-Equal 40 $registry.Count 'Opcode registry size mismatch.'
    Assert-Equal 1 $registry['EMIT'].pops 'EMIT stack contract mismatch.'
}

Test-Case 'glyph registry is machine-readable and unique' {
    $registry = Get-AriaGlyphRegistry
    Assert-Equal '⟁' $registry['agent'] 'Agent glyph mismatch.'
    Assert-Equal 10 $registry.Count 'Glyph registry size mismatch.'
}

Test-Case 'parser recognizes program and glyph graph' {
    $parsed = Parse-AriaSource -Source (Get-AriaSourceText -Path $hello) -SourceName $hello
    Assert-Equal 'HelloARIA' $parsed.model.programName 'Program name mismatch.'
    Assert-Equal 4 $parsed.model.graphs[0].nodes.Count 'Graph node count mismatch.'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $parsed.diagnostics).Count 'Parser emitted errors.'

    # aria.executable-glyph-parity/0.1
    $aliases = @(Get-AriaExecutableGlyphAliases)

    Assert-Equal 9 $aliases.Count `
        'Executable glyph alias registry size mismatch.'

    $uniqueGlyphs = @(
        $aliases.glyph |
            Sort-Object -Unique
    )

    Assert-Equal 9 $uniqueGlyphs.Count `
        'Executable glyph aliases are not unique.'

    $glyphSource = @"
aria 0.4.0
module GlyphConnection version 0.1.0
program GlyphConnection version 0.1.0
entry Main

agent Architect {
}

connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}

∿ Main {
  ↔ HumanAI
  🜁 HumanAI ← "inspect"
  🜂 HumanAI ← "change"
  ⛨ HumanAI ← true
  ◆ HumanAI
}
"@

    $textSource = @"
aria 0.4.0
module GlyphConnection version 0.1.0
program GlyphConnection version 0.1.0
entry Main

agent Architect {
}

connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}

flow Main {
  connect HumanAI
  intent HumanAI <- "inspect"
  propose HumanAI <- "change"
  consent HumanAI <- true
  disconnect HumanAI
}
"@

    $glyphParsed = Parse-AriaSource `
        -Source $glyphSource `
        -SourceName '<glyph-connection>'

    $textParsed = Parse-AriaSource `
        -Source $textSource `
        -SourceName '<text-connection>'

    Assert-Equal 0 `
        (Get-AriaErrorDiagnostics `
            -Diagnostics $glyphParsed.diagnostics).Count `
        'Glyphic connection source emitted parser errors.'

    Assert-Equal 0 `
        (Get-AriaErrorDiagnostics `
            -Diagnostics $textParsed.diagnostics).Count `
        'Textual connection source emitted parser errors.'

    $glyphStatements = @(
        $glyphParsed.model.flows[0].statements
    )

    $textStatements = @(
        $textParsed.model.flows[0].statements
    )

    Assert-Equal `
        'connect,intent,propose,consent,disconnect' `
        (@($glyphStatements.op) -join ',') `
        'Glyphic connection operations did not lower canonically.'

    Assert-Equal `
        (@($textStatements.op) -join ',') `
        (@($glyphStatements.op) -join ',') `
        'Glyphic and textual operation sequences differ.'

    for (
        $statementIndex = 0;
        $statementIndex -lt $glyphStatements.Count;
        $statementIndex++
    ) {
        Assert-Equal `
            ([string]$textStatements[$statementIndex].connection) `
            ([string]$glyphStatements[$statementIndex].connection) `
            "Connection identity differs at statement $statementIndex."

        if (
            $null -ne
            $glyphStatements[$statementIndex].PSObject.Properties[
                'expression'
            ]
        ) {
            Assert-Equal `
                ([string]$textStatements[$statementIndex].expression.kind) `
                ([string]$glyphStatements[$statementIndex].expression.kind) `
                "Expression kind differs at statement $statementIndex."

            Assert-Equal `
                $textStatements[$statementIndex].expression.value `
                $glyphStatements[$statementIndex].expression.value `
                "Expression value differs at statement $statementIndex."
        }
    }
}

Test-Case 'compiler output is deterministic' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $one = Get-AriaSha256Bytes -Bytes $gate.bytes
    $two = Get-AriaSha256Bytes -Bytes (ConvertTo-AriaContainerBytes -BytecodeModel $gate.bytecode)
    Assert-Equal $one $two 'Container hashes differ.'
}

Test-Case 'container round-trip verifies digest' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    Assert-Equal 'HelloARIA' $container.bytecode.programName 'Round-trip program mismatch.'
}

Test-Case 'VM executes output and memory' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    $result = Invoke-AriaContainer -Container $container -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-Equal 'ARIA is online.' $result.outputs[0] 'First output mismatch.'
    Assert-Equal 'active' $result.outputs[1] 'Memory output mismatch.'
}


Test-Case 'bytecode verifier accepts compiler output' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $verification = Test-AriaBytecodeModel -BytecodeModel $gate.bytecode
    Assert-True $verification.valid ('Verifier rejected compiler output: ' + ($verification.errors -join '; '))
    Assert-True ($verification.maxStack -ge 1) 'Verifier did not calculate stack depth.'
}

Test-Case 'bytecode verifier rejects stack underflow' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $malicious = $gate.bytecode | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $malicious.instructions = @(
        [pscustomobject][ordered]@{ op = 'EMIT'; line = 1 },
        [pscustomobject][ordered]@{ op = 'HALT'; line = 2 }
    )
    $verification = Test-AriaBytecodeModel -BytecodeModel $malicious
    Assert-True (-not $verification.valid) 'Stack-underflow bytecode unexpectedly passed verification.'
}

Test-Case 'container corruption is detected' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    [byte[]]$corrupt = $gate.bytes.Clone()
    $corrupt[$corrupt.Length - 1] = $corrupt[$corrupt.Length - 1] -bxor 1
    $rejected = $false
    try { $null = Read-AriaContainerBytes -Bytes $corrupt }
    catch { $rejected = $true }
    Assert-True $rejected 'Corrupted container unexpectedly passed verification.'
}

Test-Case 'locked spec rejects incompatible source' {
    $temp = Join-Path $tempRoot ('aria-spec-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 9.9.9
program Future version 0.1.0
entry Main
flow Main {
  emit "future"
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Incompatible language spec unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'default policy rejects filesystem writes' {
    $rejected = $false
    try { $null = Invoke-AriaGate -SourcePath $denied -PolicyPath $policy -WorkspaceRoot $root -Quiet }
    catch { $rejected = $true }
    Assert-True $rejected 'Denied write program unexpectedly passed.'
}

Test-Case 'path confinement rejects traversal' {
    $rejected = $false
    try { $null = Resolve-AriaConfinedPath -WorkspaceRoot $root -Scope '.' -RequestedPath '../outside.txt' }
    catch { $rejected = $true }
    Assert-True $rejected 'Traversal path unexpectedly passed.'
}


Test-Case 'repository manifest verifies' {
    $manifest = Test-AriaManifest -Root $root
    Assert-True $manifest.valid ("Manifest verification failed: $($manifest.message)")

    $identity = Test-AriaManifestByteIdentity -Root $root

    Assert-True `
        $identity.valid `
        ("Repository byte identity failed: $($identity.message)")

    $identityRoot = Join-Path `
        $tempRoot `
        ('aria-manifest-identity-' + [guid]::NewGuid().ToString('N'))

    $null = New-Item `
        -ItemType Directory `
        -Path $identityRoot `
        -Force

    try {
        & git -C $identityRoot init --quiet

        if ($LASTEXITCODE -ne 0) {
            throw 'Could not initialize byte-identity test repository.'
        }

        & git -C $identityRoot config core.autocrlf false

        if ($LASTEXITCODE -ne 0) {
            throw 'Could not configure byte-identity test repository.'
        }

        Write-AriaUtf8NoBom `
            -Path (Join-Path $identityRoot '.gitattributes') `
            -Text "*.txt text eol=lf`n"

        Write-AriaUtf8NoBom `
            -Path (Join-Path $identityRoot 'sample.txt') `
            -Text "alpha`r`nbeta`r`n"

        $fractured = Test-AriaManifestByteIdentity `
            -Root $identityRoot

        Assert-True `
            (-not $fractured.valid) `
            'Git-normalized working bytes unexpectedly passed.'

        Assert-True `
            ($fractured.message -match 'git-normalized:sample\.txt') `
            ("Unexpected byte-identity diagnostic: $($fractured.message)")

        Write-AriaUtf8NoBom `
            -Path (Join-Path $identityRoot 'sample.txt') `
            -Text "alpha`nbeta`n"

        $canonical = Test-AriaManifestByteIdentity `
            -Root $identityRoot

        Assert-True `
            $canonical.valid `
            ("Canonical Git bytes were rejected: $($canonical.message)")
    }
    finally {
        Remove-Item `
            -LiteralPath $identityRoot `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }

    # manifest native stdin remains BOM-free under hostile OutputEncoding
    $savedManifestOutputEncoding = $global:OutputEncoding

    try {
        $global:OutputEncoding = New-Object System.Text.UTF8Encoding($true)
        $hostileEncodingIdentity = Test-AriaManifestByteIdentity -Root $root
    }
    finally {
        $global:OutputEncoding = $savedManifestOutputEncoding
    }

    if (-not [bool]$hostileEncodingIdentity.applicable) {
        throw 'Manifest byte identity unexpectedly became inapplicable under hostile OutputEncoding.'
    }

    if (-not [bool]$hostileEncodingIdentity.valid) {
        throw (
            'Manifest native stdin acquired encoding-dependent bytes: ' +
            [string]$hostileEncodingIdentity.message
        )
    }

    if ([int]$hostileEncodingIdentity.checked -le 0) {
        throw 'Manifest native stdin regression did not evaluate any paths.'
    }
}


Test-Case 'strict repository manifest gate accepts tracked tree' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet -StrictRepository
    Assert-Equal 'HelloARIA' $gate.bytecode.programName 'Strict gate program mismatch.'
}

Test-Case 'VM rejects structurally invalid but checksummed bytecode' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $mutated = Read-AriaContainerBytes -Bytes $gate.bytes
    $mutated.bytecode.instructions[0].op = 'UNKNOWN_OPCODE'
    $repacked = Read-AriaContainerBytes -Bytes (ConvertTo-AriaContainerBytes -BytecodeModel $mutated.bytecode)
    $rejected = $false
    try { $null = Invoke-AriaContainer -Container $repacked -PolicyPath $policy -WorkspaceRoot $root -PassThru }
    catch { $rejected = $true }
    Assert-True $rejected 'VM executed invalid bytecode with a valid container digest.'
}

Test-Case 'container rejects header length mismatch' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $tampered = New-Object byte[] $gate.bytes.Length
    [Array]::Copy($gate.bytes, $tampered, $gate.bytes.Length)
    $tampered[12] = [byte]($tampered[12] -bxor 1)
    $rejected = $false
    try { $null = Read-AriaContainerBytes -Bytes $tampered }
    catch { $rejected = $true }
    Assert-True $rejected 'Container with a mismatched payload length unexpectedly passed.'
}


Test-Case 'custom workspace receives build and memory state' {
    $workspace = Join-Path $tempRoot ('aria-workspace-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path $workspace -Force | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        Assert-True ($compiled.artifactPath.StartsWith([System.IO.Path]::GetFullPath($workspace), [System.StringComparison]::OrdinalIgnoreCase)) 'Artifact was not rooted in the selected workspace.'
        $container = Read-AriaContainer -Path $compiled.artifactPath
        $result = Invoke-AriaContainer -Container $container -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        Assert-True (Test-Path -LiteralPath $result.statePath) 'Memory state was not written to the selected workspace.'
    }
    finally { Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue }
}

Test-Case 'glyph mismatch is rejected semantically' {
    $temp = Join-Path $tempRoot ('aria-glyph-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program WrongGlyph version 0.1.0
entry Main
graph Invalid {
  node ◉ agent architect
}
flow Main {
  halt
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Mismatched glyph and node kind unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'runtime rechecks capability policy' {
    $workspace = Join-Path $tempRoot ('aria-runtime-policy-' + [guid]::NewGuid().ToString('N'))
    $denyPolicy = Join-Path $workspace 'deny.policy.json'
    try {
        New-Item -ItemType Directory -Path $workspace -Force | Out-Null
        Write-AriaUtf8NoBom -Path (Join-Path $workspace 'README.md') -Text "runtime policy fixture`n"
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/read-repository.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $policyDocument = Get-AriaPolicy -PolicyPath $policy
        $policyDocument.effects.'fs.read'.allow = $false
        Write-AriaUtf8NoBom -Path $denyPolicy -Text (($policyDocument | ConvertTo-Json -Depth 20) + "`n")
        $rejected = $false
        try { $null = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $denyPolicy -WorkspaceRoot $workspace -PassThru }
        catch { $rejected = $true }
        Assert-True $rejected 'Runtime executed a capability denied by the execution-time policy.'
    }
    finally { Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue }
}

Test-Case 'read-only execution does not persist memory state' {
    $workspace = Join-Path $tempRoot ('aria-readonly-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path $workspace -Force | Out-Null
        Write-AriaUtf8NoBom -Path (Join-Path $workspace 'README.md') -Text "read-only fixture`n"
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/read-repository.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru
        Assert-Equal 'read-only fixture' ([string]$result.outputs[0]).Trim() 'Repository read output mismatch.'
        Assert-True (-not $result.memoryPersisted) 'Read-only program reported memory persistence.'
        Assert-True (-not (Test-Path -LiteralPath $result.statePath)) 'Read-only program created a memory state file.'
    }
    finally { Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue }
}


Test-Case 'parser recognizes structured signals' {
    $source = @'
aria 0.4.0
program SignalProbe version 0.1.0
entry Main
flow Main {
  signal pulse "compiler awake"
  signal pass "compiler ready"
}
'@
    $parsed = Parse-AriaSource -Source $source -SourceName '<signal-probe>'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $parsed.diagnostics).Count 'Signal parser emitted errors.'
    Assert-Equal 'signal' $parsed.model.flows[0].statements[0].op 'Signal opcode was not parsed.'
    Assert-Equal 'pulse' $parsed.model.flows[0].statements[0].state 'Signal state mismatch.'
}

Test-Case 'VM emits structured traceflow events' {
    $gate = Invoke-AriaGate -SourcePath $hello -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    $result = Invoke-AriaContainer -Container $container -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-True ($result.events.Count -ge 2) 'Traceflow events were not produced.'
    Assert-Equal 'pulse' $result.events[0].state 'First traceflow state mismatch.'
    Assert-Equal 'language core' $result.events[0].text 'First traceflow text mismatch.'
}

Test-Case 'canonical JSON is stable and preserves glyphs' {
    $value = [pscustomobject][ordered]@{
        z = 1
        glyph = '⟁'
        nested = [pscustomobject][ordered]@{ enabled = $true; empty = $null }
    }
    $json = ConvertTo-AriaJson -Value $value
    Assert-Equal '{"z":1,"glyph":"⟁","nested":{"enabled":true,"empty":null}}' $json 'Canonical JSON mismatch.'
    $roundTrip = $json | ConvertFrom-Json
    Assert-Equal '⟁' $roundTrip.glyph 'Canonical JSON glyph round-trip failed.'
}



Test-Case 'parser recognizes module functions and typed expressions' {
    $source = Get-AriaSourceText -Path (Join-Path $root 'examples/functions.aria')
    $parsed = Parse-AriaSource -Source $source -SourceName '<functions>'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $parsed.diagnostics).Count 'Typed parser emitted errors.'
    Assert-Equal 'Arithmetic' $parsed.model.moduleName 'Module name mismatch.'
    Assert-Equal 2 $parsed.model.functions.Count 'Function count mismatch.'
    Assert-Equal 'call' $parsed.model.flows[0].statements[0].expression.kind 'Function call expression was not parsed.'
}

Test-Case 'functions execute with typed returns' {
    $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/functions.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-Equal '5' $result.outputs[0] 'Function result output mismatch.'
    Assert-Equal 'high' $result.outputs[1] 'Conditional function output mismatch.'
}

Test-Case 'bounded repeat and lexical set execute' {
    $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/control-flow.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-Equal '6' $result.outputs[0] 'Repeat accumulation mismatch.'
    Assert-Equal 'pass' $result.events[0].state 'Conditional trace state mismatch.'
}

Test-Case 'agent dispatch emits deterministic event' {
    $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/agent-dispatch.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-Equal 'agent' $result.events[0].kind 'Agent event kind mismatch.'
    Assert-Equal 'Architect' $result.events[0].agent 'Agent dispatch target mismatch.'
    Assert-Equal 'analyze repository graph' $result.events[0].text 'Agent dispatch task mismatch.'
}

Test-Case 'typed binding rejects incompatible value' {
    $temp = Join-Path $tempRoot ('aria-type-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program WrongType version 0.1.0
entry Main
flow Main {
  let count: Number = "three"
  halt
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Incompatible typed binding unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'repeat rejects unsafe literal bound' {
    $temp = Join-Path $tempRoot ('aria-repeat-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program UnsafeLoop version 0.1.0
entry Main
flow Main {
  repeat 10001 as index {
    emit index
  }
  halt
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Unsafe repeat bound unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'module identity survives bytecode container' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/functions.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    Assert-Equal 'Arithmetic' $container.bytecode.moduleName 'Module name did not survive compilation.'
    Assert-Equal '0.1.0' $container.bytecode.moduleVersion 'Module version did not survive compilation.'
}

Test-Case 'persisted memory type is revalidated' {
    $workspace = Join-Path $tempRoot ('aria-memory-type-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path (Join-Path $workspace '.aria/state') -Force | Out-Null
        $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/coreflow.aria') -PolicyPath $policy -WorkspaceRoot $workspace -Quiet
        Write-AriaUtf8NoBom -Path (Join-Path $workspace '.aria/state/CoreflowDemo.memory.json') -Text '{"Runtime":{"cycles":"wrong","status":"ready"}}'
        $rejected = $false
        try { $null = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $workspace -PassThru }
        catch { $rejected = $true }
        Assert-True $rejected 'Invalid persisted memory type unexpectedly executed.'
    }
    finally { Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue }
}



Test-Case 'bytecode verifier rejects arithmetic type confusion' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/functions.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $mutated = $gate.bytecode | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $mutated.instructions = @(
        [pscustomobject][ordered]@{ op = 'PUSH_CONST'; arg = 0; type = 'Text'; line = 1 },
        [pscustomobject][ordered]@{ op = 'PUSH_CONST'; arg = 1; type = 'Number'; line = 1 },
        [pscustomobject][ordered]@{ op = 'ADD'; line = 1 },
        [pscustomobject][ordered]@{ op = 'EMIT'; line = 1 },
        [pscustomobject][ordered]@{ op = 'HALT'; line = 2 }
    )
    $mutated.constants = @('text', 1)
    $verification = Test-AriaBytecodeModel -BytecodeModel $mutated
    Assert-True (-not $verification.valid) 'Mixed Text+Number ADD unexpectedly passed verification.'
}

Test-Case 'bytecode verifier rejects non-text agent task' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/agent-dispatch.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $mutated = $gate.bytecode | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $mutated.constants = @(42)
    $mutated.instructions = @(
        [pscustomobject][ordered]@{ op = 'PUSH_CONST'; arg = 0; type = 'Number'; line = 1 },
        [pscustomobject][ordered]@{ op = 'AGENT_DISPATCH'; agent = 'Architect'; line = 1 },
        [pscustomobject][ordered]@{ op = 'HALT'; line = 2 }
    )
    $verification = Test-AriaBytecodeModel -BytecodeModel $mutated
    Assert-True (-not $verification.valid) 'Numeric agent task unexpectedly passed verification.'
}

Test-Case 'Null-returning function remains a typed expression' {
    $temp = Join-Path $tempRoot ('aria-null-call-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
module NullCalls version 0.1.0
program NullCall version 0.1.0
entry Main
function Nothing() -> Null {
  return
}
flow Main {
  let result: Null = Nothing()
  assert result == null
  halt
}
'@
        $compiled = Invoke-AriaCompile -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
        Assert-True ($null -eq $result.variables.result) 'Null function result was not retained as a typed value.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}


Test-Case 'parser recognizes connection ontology and lifecycle' {
    $source = Get-AriaSourceText -Path (Join-Path $root 'examples/connection.aria')
    $parsed = Parse-AriaSource -Source $source -SourceName '<connection>'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $parsed.diagnostics).Count 'Connection parser emitted errors.'
    Assert-Equal 1 $parsed.model.connections.Count 'Connection declaration count mismatch.'
    Assert-Equal 'HumanAI' $parsed.model.connections[0].name 'Connection name mismatch.'
    Assert-Equal 'connect' $parsed.model.flows[0].statements[0].op 'Connection open statement mismatch.'
    Assert-Equal 'consent' $parsed.model.flows[0].statements[3].op 'Connection consent statement mismatch.'
}

Test-Case 'connection ontology survives bytecode container' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/connection.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $container = Read-AriaContainerBytes -Bytes $gate.bytes
    Assert-Equal 1 $container.bytecode.connections.Count 'Connection declaration did not survive compilation.'
    Assert-Equal 'intent-proposal-consent' $container.bytecode.connections[0].protocol 'Connection protocol mismatch.'
}

Test-Case 'VM emits deterministic connection lifecycle' {
    $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/connection.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
    $events = @($result.events | Where-Object { $_.kind -eq 'connection' })
    Assert-Equal 5 $events.Count 'Connection event count mismatch.'
    Assert-Equal 'open' $events[0].state 'Connection open event mismatch.'
    Assert-Equal 'intent' $events[1].state 'Connection intent event mismatch.'
    Assert-Equal 'proposal' $events[2].state 'Connection proposal event mismatch.'
    Assert-Equal $true $events[3].approved 'Connection consent was not recorded.'
    Assert-Equal 'closed' $events[4].state 'Connection close event mismatch.'
}

Test-Case 'withheld consent closes without authority' {
    $temp = Join-Path $tempRoot ('aria-consent-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program WithheldConsent version 0.1.0
entry Main
agent Architect {
}
connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}
flow Main {
  connect HumanAI
  intent HumanAI <- "inspect"
  propose HumanAI <- "change"
  consent HumanAI <- false
  disconnect HumanAI
  halt
}
'@
        $compiled = Invoke-AriaCompile -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet
        $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
        $consent = @($result.events | Where-Object { $_.kind -eq 'connection' -and $_.state -eq 'consent' })[0]
        Assert-Equal $false $consent.approved 'Withheld consent was not preserved.'
        Assert-Equal 'closed' $result.connections['HumanAI'].phase 'Withheld connection did not close safely.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'semantics rejects unknown connection' {
    $temp = Join-Path $tempRoot ('aria-unknown-connection-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program UnknownConnection version 0.1.0
entry Main
flow Main {
  connect Missing
  halt
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Unknown connection unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'connection rejects unknown agent identity' {
    $temp = Join-Path $tempRoot ('aria-unknown-agent-connection-' + [guid]::NewGuid().ToString('N') + '.aria')
    try {
        Write-AriaUtf8NoBom -Path $temp -Text @'
aria 0.4.0
program UnknownConnectionAgent version 0.1.0
entry Main
connection HumanAI {
  operator = "human"
  agent = "Missing"
  protocol = "intent-proposal-consent"
}
flow Main {
  halt
}
'@
        $rejected = $false
        try { $null = Invoke-AriaGate -SourcePath $temp -PolicyPath $policy -WorkspaceRoot $root -Quiet }
        catch { $rejected = $true }
        Assert-True $rejected 'Connection with unknown agent unexpectedly passed.'
    }
    finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Test-Case 'bytecode verifier rejects non-text connection intent' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/connection.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $mutated = $gate.bytecode | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $mutated.constants = @(42)
    $mutated.instructions = @(
        [pscustomobject][ordered]@{ op = 'PUSH_CONST'; arg = 0; type = 'Number'; line = 1 },
        [pscustomobject][ordered]@{ op = 'CONNECT_INTENT'; connection = 'HumanAI'; line = 1 },
        [pscustomobject][ordered]@{ op = 'HALT'; line = 2 }
    )
    $verification = Test-AriaBytecodeModel -BytecodeModel $mutated
    Assert-True (-not $verification.valid) 'Numeric connection intent unexpectedly passed verification.'
}

Test-Case 'VM rejects connection message before open' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/connection.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $mutated = $gate.bytecode | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $mutated.constants = @('premature')
    $mutated.instructions = @(
        [pscustomobject][ordered]@{ op = 'PUSH_CONST'; arg = 0; type = 'Text'; line = 1 },
        [pscustomobject][ordered]@{ op = 'CONNECT_INTENT'; connection = 'HumanAI'; line = 1 },
        [pscustomobject][ordered]@{ op = 'HALT'; line = 2 }
    )
    $container = Read-AriaContainerBytes -Bytes (ConvertTo-AriaContainerBytes -BytecodeModel $mutated)
    $rejected = $false
    try { $null = Invoke-AriaContainer -Container $container -PolicyPath $policy -WorkspaceRoot $root -PassThru }
    catch { $rejected = $true }
    Assert-True $rejected 'Connection intent before open unexpectedly executed.'
}

Test-Case 'runtime profile resolves CI deterministically' {
    $beforeCI = $env:CI
    $beforeOutput = $env:ARIA_OUTPUT
    try {
        $env:CI = 'true'
        $env:ARIA_OUTPUT = ''
        $profile = Get-AriaRuntimeProfile
        Assert-Equal 'ci' $profile.mode 'CI profile mismatch.'
        Assert-True (-not $profile.animation) 'CI profile unexpectedly enables animation.'
    }
    finally {
        $env:CI = $beforeCI
        $env:ARIA_OUTPUT = $beforeOutput
    }
}

Test-Case 'signal subset emits allowlisted fields only' {
  $items=@([pscustomobject][ordered]@{branch='main';coherence='aligned';token='secret'})
  $s=New-AriaSignalSubset -Items $items -Fields branch,coherence -Purpose test -Source test -ConsentBasis test -ConsentScope test
  Assert-True ('token' -in @($s.excludedFields)) 'Excluded field missing.'
  Assert-True ($null-eq$s.items[0].PSObject.Properties['token']) 'Excluded value leaked.'
}
Test-Case 'signal subset enforces limit' {
  $items=1..5|ForEach-Object{[pscustomobject][ordered]@{value=$_}}
  $s=New-AriaSignalSubset -Items $items -Fields value -Purpose test -Source test -ConsentBasis test -ConsentScope test -Limit 2
  Assert-Equal 5 $s.sourceCount 'Source count mismatch.'
  Assert-Equal 2 $s.emittedCount 'Limit was not enforced.'
}
Test-Case 'signal subset digest is deterministic' {
  $items=@([pscustomobject][ordered]@{branch='main';exitCode=0})
  $a=New-AriaSignalSubset -Items $items -Fields branch,exitCode -Purpose test -Source test -ConsentBasis test -ConsentScope test
  $b=New-AriaSignalSubset -Items $items -Fields exitCode,branch -Purpose test -Source test -ConsentBasis test -ConsentScope test
  Assert-Equal $a.digest $b.digest 'Digest changed with field argument order.'
}
Test-Case 'signal subset rejects tampering' {
  $s=New-AriaSignalSubset -Items @([pscustomobject][ordered]@{branch='main'}) -Fields branch -Purpose test -Source test -ConsentBasis test -ConsentScope test
  $s.items[0].branch='other'
  Assert-True (-not(Test-AriaSignalSubset $s).valid) 'Tampered subset verified.'
}
Test-Case 'signal subset survives transmission round trip' {
  $s=New-AriaSignalSubset -Items @([pscustomobject][ordered]@{branch='main';exitCode=0}) -Fields branch,exitCode -Purpose test -Source test -ConsentBasis test -ConsentScope test
  $t=New-AriaSubsetTransmission -Subset $s -Channel github -Status pass
  $decoded=Read-AriaTransmissionBytes (ConvertTo-AriaTransmissionBytes $t)
  Assert-True (Test-AriaSignalSubset $decoded.payload).valid 'Decoded subset failed verification.'
}
Test-Case 'transmission canonical digest is deterministic' {
    $payload = [pscustomobject][ordered]@{ repository='ARIA'; checks=@('pass','pass','pass') }
    $one = New-AriaTransmission -Channel github -Kind workflow -Status pass -Source test -Payload $payload
    $two = New-AriaTransmission -Channel github -Kind workflow -Status pass -Source test -Payload $payload
    Assert-Equal $one.digest $two.digest 'Transmission digest changed for identical content.'
}

Test-Case 'compressed transmission round-trip verifies' {
    $record = New-AriaTransmission -Channel github -Kind workflow -Status pass -Source test -Payload ([pscustomobject][ordered]@{run=7; conclusion='success'})
    [byte[]]$bytes = ConvertTo-AriaTransmissionBytes -Transmission $record
    $decoded = Read-AriaTransmissionBytes -Bytes $bytes
    Assert-Equal $record.digest $decoded.digest 'Transmission round-trip digest mismatch.'
    Assert-Equal 'github' $decoded.channel 'Transmission round-trip channel mismatch.'
}

Test-Case 'transmission container rejects tampering' {
    $record = New-AriaTransmission -Channel github -Kind workflow -Status pass -Source test -Payload ([pscustomobject][ordered]@{run=7})
    [byte[]]$bytes = ConvertTo-AriaTransmissionBytes -Transmission $record
    $bytes[$bytes.Length-1] = $bytes[$bytes.Length-1] -bxor 1
    $rejected = $false
    try { $null = Read-AriaTransmissionBytes -Bytes $bytes } catch { $rejected = $true }
    Assert-True $rejected 'Tampered transmission unexpectedly passed verification.'
}
Test-Case 'event digest is deterministic for fixed time' {
    $operationId = 'aria.operation.test:' + ('a' * 64)
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact -OperationId $operationId
    $time = [datetime]'2026-01-01T00:00:00Z'
    $one = New-AriaEvent -Domain runtime -Phase probe -State PASS -Energy verify -Information stable -Coherence sealed -OccurredAt $time
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact -OperationId $operationId
    $two = New-AriaEvent -Domain runtime -Phase probe -State PASS -Energy verify -Information stable -Coherence sealed -OccurredAt $time
    Assert-Equal $one.digest $two.digest 'Event digest changed for identical content.'
}

Test-Case 'event spine publishes to subscriber and buffer' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $script:ObservedEvent = $null
    $null = Register-AriaEventSubscriber -Handler { param($event) $script:ObservedEvent = $event }
    $published = Send-AriaEvent -Domain runtime -Phase subscriber -State PASS -Energy dispatch -Information event -Coherence observed -PassThru
    Assert-Equal $published.digest $script:ObservedEvent.digest 'Subscriber did not receive published event.'
    Assert-Equal 1 @(Get-AriaEventBuffer).Count 'Event buffer count mismatch.'
}

Test-Case 'event verifier rejects tampering' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $event = New-AriaEvent -Domain runtime -Phase tamper -State PASS -Energy verify -Information original -Coherence sealed
    $event.information = 'mutated'
    $verification = Test-AriaEvent -Event $event
    Assert-True (-not $verification.valid) 'Tampered event unexpectedly passed.'
}

Test-Case 'event ledger persists and replays verified events' {
    $workspace = Join-Path $tempRoot ('aria-event-ledger-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path $workspace -Force | Out-Null
        $null = Initialize-AriaEventSpine -WorkspaceRoot $workspace -Profile compact -Persist
        $null = Send-AriaEvent -Domain transmission -Phase replay -State PASS -Energy persist -Information ledger -Coherence verified
        $events = @(Read-AriaEventLedger -WorkspaceRoot $workspace)
        Assert-Equal 1 $events.Count 'Event ledger replay count mismatch.'
        Assert-Equal 'transmission' $events[0].domain 'Event ledger domain mismatch.'
    }
    finally { Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue }
}
Test-Case 'runtime spine maps compiler event to Etherflow' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $event = New-AriaEvent -Domain compiler -Phase compile -State ACTIVE -Energy translation -Information hello.aria -Coherence engaged
    $ether = ConvertTo-AriaEtherEvent -Event $event
    Assert-Equal 'compiler.compile' $ether.phase 'Compiler event phase mismatch.'
    Assert-Equal 'translation' $ether.energy 'Compiler energy mismatch.'
}

Test-Case 'runtime spine preserves verifier authority boundary' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $event = New-AriaEvent -Domain verifier -Phase artifact -State PASS -Energy verification -Information hello.ariac -Coherence accepted
    $verification = Test-AriaEvent -Event $event
    Assert-True $verification.valid 'Verifier event failed event verification.'
    Assert-Equal 'verifier' $event.domain 'Verifier domain mismatch.'
}

Test-Case 'runtime spine records VM activation and halt order' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $null = Send-AriaEvent -Domain vm -Phase execute -State ACTIVE -Energy execution -Information HelloARIA -Coherence active
    $null = Send-AriaEvent -Domain vm -Phase halt -State PASS -Energy completion -Information HelloARIA -Coherence halted
    $events = @(Get-AriaEventBuffer)
    Assert-Equal 2 $events.Count 'VM event count mismatch.'
    Assert-Equal 'execute' $events[0].phase 'VM activation order mismatch.'
    Assert-Equal 'halt' $events[1].phase 'VM halt order mismatch.'
}

Test-Case 'runtime spine connection lifecycle is ordered' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    foreach($phase in @('intent','proposal','consent','closure')){
        $null = Send-AriaEvent -Domain connection -Phase $phase -State PASS -Energy lifecycle -Information $phase -Coherence verified
    }
    $events = @(Get-AriaEventBuffer)
    Assert-Equal 'intent' $events[0].phase 'Connection intent order mismatch.'
    Assert-Equal 'proposal' $events[1].phase 'Connection proposal order mismatch.'
    Assert-Equal 'consent' $events[2].phase 'Connection consent order mismatch.'
    Assert-Equal 'closure' $events[3].phase 'Connection closure order mismatch.'
}
Test-Case 'event digest survives JSON date materialization' {
    $null = Initialize-AriaEventSpine -WorkspaceRoot $root -Profile compact
    $event = New-AriaEvent `
        -Domain runtime `
        -Phase portability `
        -State PASS `
        -Energy verification `
        -Information timestamp `
        -Coherence invariant `
        -OccurredAt ([datetime]'2026-01-01T00:00:00Z')

    $reloaded = $event | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    $verification = Test-AriaEvent -Event $reloaded
    Assert-True $verification.valid 'Event digest changed after JSON date materialization.'
}
Test-Case 'gitflow process captures native output' {
    $result = Invoke-AriaGitProcess -Arguments @('--version') -RepositoryRoot $root
    Assert-Equal 0 $result.exitCode 'Git version command failed.'
    Assert-True ($result.stdout -match '^git version') 'Git output was not captured.'
}

Test-Case 'gitflow resolves local head deterministically' {
    $one = Get-AriaGitHead -RepositoryRoot $root
    $two = Get-AriaGitHead -RepositoryRoot $root
    Assert-Equal $one $two 'Local HEAD changed during deterministic probe.'
    Assert-True ($one -match '^[a-f0-9]{40}$') 'Local HEAD format mismatch.'
}

Test-Case 'gitflow clean-tree verifier uses isolated repository' {
    $repo = Join-Path $tempRoot ('aria-gitflow-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path $repo -Force | Out-Null

        $init = Invoke-AriaGitProcess -Arguments @('init') -RepositoryRoot $repo
        Assert-Equal 0 $init.exitCode 'Temporary Git initialization failed.'

        [IO.File]::WriteAllText(
            (Join-Path $repo 'probe.txt'),
            'ARIA Gitflow probe',
            [Text.UTF8Encoding]::new($false)
        )

        $add = Invoke-AriaGitProcess -Arguments @('add','probe.txt') -RepositoryRoot $repo
        Assert-Equal 0 $add.exitCode 'Temporary Git add failed.'

        $commit = Invoke-AriaGitProcess `
            -Arguments @(
                '-c','user.name=ARIA',
                '-c','user.email=aria@local.invalid',
                'commit','-m','initial'
            ) `
            -RepositoryRoot $repo
        Assert-Equal 0 $commit.exitCode 'Temporary Git commit failed.'

        $clean = Assert-AriaGitClean -RepositoryRoot $repo
        Assert-True $clean 'Clean-tree verification rejected an isolated clean repository.'
    }
    finally {
        Remove-Item -LiteralPath $repo -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Test-Case 'gitflow verification event is single-frame capable' {
    $command = Get-Command Write-AriaGitVerification -ErrorAction Stop
    Assert-Equal 'Function' ([string]$command.CommandType) 'Gitflow verification renderer is not exported.'
}
Test-Case 'gitflow process rejects function shadowing' {
    function git { param([string[]]$Arguments) throw 'shadow function should never execute' }
    try {
        $result = Invoke-AriaGitProcess -Arguments @('--version') -RepositoryRoot $root
        Assert-Equal 0 $result.exitCode 'Git application invocation failed.'
        Assert-True ($result.stdout -match '^git version') 'Git application output was not captured.'
    }
    finally {
        Remove-Item Function:\git -ErrorAction SilentlyContinue
    }
}
Test-Case 'oscillator frame preserves rectangular width' {
    $state = New-AriaBufferState -Label probe -Width 12
    $frame = Get-AriaBufferFrame -State $state
    Assert-True ($frame -match '⟦.{12}⟧$') 'Oscillator rectangle width changed.'
    Assert-Equal 1 ([regex]::Matches($frame,'◆').Count) 'Oscillator must contain one moving pulse.'
}

Test-Case 'oscillator reverses at both boundaries' {
    $state = New-AriaBufferState -Label probe -Width 8
    $state.position = 7
    $state.direction = 1
    $null = Step-AriaBuffer -State $state
    Assert-Equal '-1' ([string][int]$state.direction) 'Oscillator did not reverse at the right boundary.'

    $state.position = 0
    $state.direction = -1
    $null = Step-AriaBuffer -State $state
    Assert-Equal '1' ([string][int]$state.direction) 'Oscillator did not reverse at the left boundary.'
}

Test-Case 'oscillator suppresses animation in CI' {
    $prior = $env:CI
    try {
        $env:CI = 'true'
        Assert-True (-not (Test-AriaInteractiveBuffer)) 'CI animation suppression failed.'
    }
    finally {
        $env:CI = $prior
    }
}
Test-Case 'bufferflow never invents internal process phases' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    $phases = New-Object 'System.Collections.Generic.HashSet[string]'
    for ($index = 0; $index -lt 16; $index++) {
        [void]$phases.Add((Get-AriaTransmissionPhase -State $state))
        $null = Step-AriaTransmissionBuffer -State $state
    }

    Assert-Equal 1 $phases.Count 'Bufferflow invented more than one unobserved phase.'
    Assert-True ($phases.Contains('pending')) 'Bufferflow did not preserve the honest pending state.'
    foreach ($forbidden in @('mesh','transmit','align','verify')) {
        Assert-True (-not $phases.Contains($forbidden)) "Bufferflow invented '$forbidden'."
    }
}

Test-Case 'bufferflow heartbeat moves only while pending' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    $state.tick = 9
    $state.position = 0
    $before = [int]$state.position
    $null = Step-AriaTransmissionBuffer -State $state
    Assert-True ([int]$state.position -ne $before) 'Pending heartbeat did not move.'
    Assert-Equal 1 ([int]$state.heartbeatCount) 'Pending heartbeat count mismatch.'
    $state.active = $false
    $frozen = [int]$state.position
    $null = Step-AriaTransmissionBuffer -State $state
    Assert-Equal $frozen ([int]$state.position) 'Closed buffer continued moving.'
}

Test-Case 'bufferflow frame states pending without false progress' {
    $state = New-AriaTransmissionBuffer -Label probe -Width 12
    $state.interactive = $false
    $frame = Get-AriaTransmissionFrame -State $state
    Assert-True ($frame -match '⟦.{12}⟧') 'Transmission frame width changed.'
    Assert-True ($frame -match 'pending') 'Pending phase label missing.'
    Assert-True ($frame -match 'elapsed:') 'Measured elapsed time missing.'
    Assert-True ($frame -notmatch '%|mesh|transmit|align|verify') 'Frame contains false progress or an unobserved phase.'
}

Test-Case 'bufferflow process returns one typed result' {
    $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $git) {
        $git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    }

    $path = $null
    foreach ($propertyName in @('Path','Source','Definition','Name')) {
        $property = $git.PSObject.Properties[$propertyName]
        if ($null -ne $property -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            $path = [string]$property.Value
            break
        }
    }

    $result = @(Invoke-AriaBufferedProcess `
        -FilePath $path `
        -ArgumentList @('--version') `
        -WorkingDirectory $root `
        -Label 'probe.git' `
        -Mode verification)

    Assert-Equal '1' ([string]$result.Count) 'Buffered process emitted more than one pipeline object.'
    Assert-Equal '0' ([string][int]$result[0].exitCode) 'Buffered process exit code mismatch.'
}
Test-Case 'signal receipt reports duration bytes and coherence' {
    $start = [datetime]'2026-01-01T00:00:00Z'
    $end = $start.AddMilliseconds(125)
    $receipt = New-AriaTransmissionReceipt `
        -Label probe `
        -Mode remote `
        -ExitCode 0 `
        -StartedAt $start `
        -CompletedAt $end `
        -Stdout 'abc' `
        -Stderr ''

    Assert-Equal 'exit code 0' ([string]$receipt.coherence) 'Receipt coherence mismatch.'
    Assert-Equal '125' ([string][int]$receipt.durationMs) 'Receipt duration mismatch.'
    Assert-Equal '3' ([string][int]$receipt.totalBytes) 'Receipt byte count mismatch.'
}

Test-Case 'signal receipt formats as a subordinate line' {
    $start = [datetime]'2026-01-01T00:00:00Z'
    $receipt = New-AriaTransmissionReceipt `
        -Label probe `
        -Mode verification `
        -ExitCode 0 `
        -StartedAt $start `
        -CompletedAt $start `
        -Stdout '' `
        -Stderr ''

    $line = Format-AriaTransmissionReceipt -Receipt $receipt
    Assert-True ($line -match '^└─ ∿ verifier · exit code 0') 'Receipt is not subordinate transmission feedback.'
}

Test-Case 'buffered sequence activates every item' {
    $prior = $env:CI
    try {
        $env:CI = 'true'
        $items = @(
            [pscustomobject]@{ name = 'one'; mode = 'local'; action = { 'a' } },
            [pscustomobject]@{ name = 'two'; mode = 'verification'; action = { 'b' } }
        )

        $results = @(Invoke-AriaBufferedSequence -Items $items)
        Assert-Equal '2' ([string]$results.Count) 'Buffered sequence skipped an item.'
        Assert-Equal 'one' ([string]$results[0].name) 'First buffered item identity mismatch.'
        Assert-Equal 'two' ([string]$results[1].name) 'Second buffered item identity mismatch.'
    }
    finally {
        $env:CI = $prior
    }
}

Test-Case 'buffered process carries transmission receipt' {
    $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $git) {
        $git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    }

    $path = $null
    foreach ($propertyName in @('Path','Source','Definition','Name')) {
        $property = $git.PSObject.Properties[$propertyName]
        if ($null -ne $property -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            $path = [string]$property.Value
            break
        }
    }

    $prior = $env:CI
    try {
        $env:CI = 'true'
        $result = Invoke-AriaBufferedProcess `
            -FilePath $path `
            -ArgumentList @('--version') `
            -WorkingDirectory $root `
            -Label 'probe.git' `
            -Mode verification

        Assert-True ($null -ne $result.receipt) 'Buffered process receipt missing.'
        Assert-Equal 'exit code 0' ([string]$result.receipt.coherence) 'Buffered process receipt coherence mismatch.'
    }
    finally {
        $env:CI = $prior
    }
}
Test-Case 'typed core canonicalizes generic and record types' {
    $int = New-AriaType -Kind Int
    $text = New-AriaType -Kind Text
    $result = New-AriaType -Kind Result -Arguments @($int,$text)
    $record = New-AriaType -Kind Record -Fields @{ z=$text; a=$result }

    Assert-Equal 'Result<Int,Text>' (ConvertTo-AriaCanonicalType $result) 'Result type canonicalization failed.'
    Assert-Equal 'Record{a:Result<Int,Text>,z:Text}' (ConvertTo-AriaCanonicalType $record) 'Record fields are not canonicalized.'
}

Test-Case 'typed core rejects immutable reassignment' {
    $scope = New-AriaScope
    $int = New-AriaType -Kind Int
    $null = Add-AriaBinding -Scope $scope -Name value -Type $int -Value 1
    $error = Set-AriaBindingValue -Scope $scope -Name value -Type $int -Value 2

    Assert-Equal 'E_BIND_IMMUTABLE' ([string]$error.code) 'Immutable binding was not rejected.'
}

Test-Case 'typed core rejects wrong function argument types' {
    $int = New-AriaType -Kind Int
    $text = New-AriaType -Kind Text
    $signature = New-AriaFunctionSignature `
        -Name addOne `
        -Parameters @([pscustomobject]@{name='value';type=$int}) `
        -ReturnType $int

    $result = Test-AriaFunctionCall -Signature $signature -ArgumentTypes @($text)
    Assert-True (-not [bool]$result.valid) 'Wrong function argument type was accepted.'
    Assert-Equal 'E_CALL_TYPE' ([string]$result.errors[0].code) 'Wrong function error code.'
}

Test-Case 'typed core rejects missing function capabilities' {
    $unit = New-AriaType -Kind Unit
    $signature = New-AriaFunctionSignature `
        -Name send `
        -ReturnType $unit `
        -Effects @('network.send') `
        -Capabilities @('cap:network')

    $result = Test-AriaFunctionCall -Signature $signature -GrantedCapabilities @()
    Assert-True (-not [bool]$result.valid) 'Missing capability was accepted.'
    Assert-Equal 'E_CAPABILITY_MISSING' ([string]$result.errors[0].code) 'Capability error code mismatch.'
}

Test-Case 'typed core detects non-exhaustive branches' {
    $result = Test-AriaExhaustiveBranch `
        -Variants @('ok','error') `
        -Cases @('ok')

    Assert-True (-not [bool]$result.exhaustive) 'Non-exhaustive branch was accepted.'
    Assert-Equal 'error' ([string]$result.missing[0]) 'Missing variant was not reported.'
}

Test-Case 'typed core validates effect authority' {
    $denied = Test-AriaEffectAuthority -Effects @('memory.write') -Capabilities @()
    $allowed = Test-AriaEffectAuthority -Effects @('memory.write') -Capabilities @('cap:memory.write')

    Assert-True (-not [bool]$denied.valid) 'Unauthorized effect was accepted.'
    Assert-True ([bool]$allowed.valid) 'Authorized effect was rejected.'
}

Test-Case 'typed IR accepts valid golden fixture' {
    $path = Join-Path $root 'tests/fixtures/typed-core/valid-function.ariair.json'
    $result = Test-AriaTypedIrFile -Path $path

    Assert-True ([bool]$result.valid) 'Valid typed IR fixture was rejected.'
    Assert-Equal '64' ([string]$result.digest.Length) 'Typed IR digest length mismatch.'
}

Test-Case 'typed IR rejects missing capability fixture' {
    $path = Join-Path $root 'tests/fixtures/typed-core/invalid-capability.ariair.json'
    $result = Test-AriaTypedIrFile -Path $path

    Assert-True (-not [bool]$result.valid) 'Capability-invalid typed IR was accepted.'
    Assert-Equal 'E_EFFECT_AUTHORITY' ([string]$result.errors[0].code) 'Typed IR authority rejection mismatch.'
}

Test-Case 'typed IR digest is deterministic' {
    $path = Join-Path $root 'tests/fixtures/typed-core/valid-function.ariair.json'
    $first = Test-AriaTypedIrFile -Path $path
    $second = Test-AriaTypedIrFile -Path $path

    Assert-Equal ([string]$first.digest) ([string]$second.digest) 'Typed IR digest changed across verification.'
    Assert-Equal ([string]$first.canonical) ([string]$second.canonical) 'Typed IR canonical form changed.'
}

Test-Case 'typed IR rejects unknown opcode' {
    $document = [pscustomobject]@{
        schema = 'aria.typed-ir/0.2'
        entry = 'main'
        functions = @(
            [pscustomobject]@{
                name = 'main'
                parameters = @()
                returnType = 'Unit'
                effects = @()
                capabilities = @()
                instructions = @([pscustomobject]@{op='teleport'})
            }
        )
    }

    $result = Test-AriaTypedIr -Document $document
    Assert-True (-not [bool]$result.valid) 'Unknown opcode was accepted.'
    Assert-Equal 'E_IR_OPCODE' ([string]$result.errors[0].code) 'Unknown opcode error code mismatch.'
}
function New-TestGraphRule {
    [pscustomobject]@{
        schema = 'aria.graph-rule/0.3'
        name = 'grant_access'
        pattern = [pscustomobject]@{
            sourceType = 'User'
            edgeType = 'requests'
            targetType = 'Resource'
            sourceWhere = @{ status = 'active' }
            targetWhere = @{}
        }
        guard = [pscustomobject]@{
            kind = 'eq'
            left = 'source.status'
            right = 'active'
        }
        capabilities = @('cap:graph.write')
        rewrite = @(
            [pscustomobject]@{
                op = 'remove.edge'
                id = '$edge.id'
            },
            [pscustomobject]@{
                op = 'add.edge'
                id = 'edge:access:1'
                type = 'access'
                source = '$source.id'
                target = '$target.id'
            }
        )
    }
}

Test-Case 'graph core accepts valid typed graph' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $result = Test-AriaGraph $graph
    Assert-True ([bool]$result.valid) 'Valid typed graph was rejected.'
}

Test-Case 'graph core rejects dangling edge' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/invalid-dangling-edge.json') -Raw | ConvertFrom-Json
    $result = Test-AriaGraph $graph
    Assert-True (-not [bool]$result.valid) 'Dangling edge was accepted.'
    Assert-Equal 'E_GRAPH_EDGE_DANGLING' ([string]$result.errors[0].code) 'Dangling edge error mismatch.'
}

Test-Case 'graph core rejects duplicate node identity' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $graph.nodes = @($graph.nodes) + @([pscustomobject]@{id='user:42';type='User'})
    $result = Test-AriaGraph $graph
    Assert-True (-not [bool]$result.valid) 'Duplicate node identity was accepted.'
}

Test-Case 'graph core rejects endpoint type mismatch' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $graph.nodes[0].type = 'Resource'
    $result = Test-AriaGraph $graph
    Assert-True (-not [bool]$result.valid) 'Invalid edge endpoint typing was accepted.'
}

Test-Case 'graph pattern returns typed bindings' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $rule = New-TestGraphRule
    $matches = @(Find-AriaGraphMatches -Graph $graph -Pattern $rule.pattern)
    Assert-Equal '1' ([string]$matches.Count) 'Typed pattern match count mismatch.'
    Assert-Equal 'User' ([string]$matches[0].source.type) 'Source binding type mismatch.'
    Assert-Equal 'Resource' ([string]$matches[0].target.type) 'Target binding type mismatch.'
}

Test-Case 'graph guard rejects unsupported kind' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $rule = New-TestGraphRule
    $match = @(Find-AriaGraphMatches -Graph $graph -Pattern $rule.pattern)[0]
    $guard = Test-AriaGraphGuard -Guard ([pscustomobject]@{kind='execute'}) -Match $match
    Assert-True (-not [bool]$guard.valid) 'Unsupported graph guard was accepted.'
    Assert-Equal 'E_GRAPH_GUARD_KIND' ([string]$guard.error.code) 'Graph guard error mismatch.'
}

Test-Case 'graph rule rejects missing capability' {
    $rule = New-TestGraphRule
    $result = Test-AriaGraphRule -Rule $rule -GrantedCapabilities @()
    Assert-True (-not [bool]$result.valid) 'Missing graph capability was accepted.'
    Assert-Equal 'E_GRAPH_CAPABILITY' ([string]$result.errors[0].code) 'Graph capability error mismatch.'
}

Test-Case 'graph rewrite commits valid transaction' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $result = Invoke-AriaGraphRewrite -Graph $graph -Rule (New-TestGraphRule) -GrantedCapabilities @('cap:graph.write')
    Assert-True ([bool]$result.committed) 'Valid graph rewrite did not commit.'
    Assert-True ([string]$result.beforeDigest -cne [string]$result.afterDigest) 'Committed rewrite did not change graph identity.'
}

Test-Case 'graph rewrite removes matched edge' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $result = Invoke-AriaGraphRewrite -Graph $graph -Rule (New-TestGraphRule) -GrantedCapabilities @('cap:graph.write')
    $requests = @($result.graph.edges | Where-Object {$_.type -eq 'requests'})
    $access = @($result.graph.edges | Where-Object {$_.type -eq 'access'})
    Assert-Equal '0' ([string]$requests.Count) 'Matched request edge remained after rewrite.'
    Assert-Equal '1' ([string]$access.Count) 'Access edge was not created.'
}

Test-Case 'graph rewrite rejects false guard without mutation' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $rule = New-TestGraphRule
    $rule.guard.right = 'disabled'
    $before = Get-AriaGraphDigest $graph
    $result = Invoke-AriaGraphRewrite -Graph $graph -Rule $rule -GrantedCapabilities @('cap:graph.write')
    Assert-True ([bool]$result.rejected) 'False guard did not reject rewrite.'
    Assert-Equal 'guard-false' ([string]$result.reason) 'False guard rejection reason mismatch.'
    Assert-Equal $before ([string]$result.afterDigest) 'False guard changed graph identity.'
}

Test-Case 'graph rewrite rolls back invalid candidate' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $rule = New-TestGraphRule
    $rule.rewrite[1].target = 'resource:missing'
    $before = Get-AriaGraphDigest $graph
    $result = Invoke-AriaGraphRewrite -Graph $graph -Rule $rule -GrantedCapabilities @('cap:graph.write')
    Assert-True ([bool]$result.rejected) 'Invalid candidate graph was committed.'
    Assert-Equal 'result-invalid' ([string]$result.reason) 'Rollback rejection reason mismatch.'
    Assert-Equal $before ([string]$result.afterDigest) 'Rollback did not preserve original graph identity.'
}

Test-Case 'graph rewrite event is content addressed' {
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-core/valid-access-graph.json') -Raw | ConvertFrom-Json
    $result = Invoke-AriaGraphRewrite -Graph $graph -Rule (New-TestGraphRule) -GrantedCapabilities @('cap:graph.write')
    Assert-True ([string]$result.event.transaction -match '^sha256:[a-f0-9]{64}$') 'Graph transaction event is not content addressed.'
    Assert-Equal 'aria.graph.rewrite.committed' ([string]$result.event.type) 'Graph event type mismatch.'
}
function Get-TestReplayInputs {
    [pscustomobject]@{
        graph = Get-Content (Join-Path $root 'tests/fixtures/graph-replay/initial-access-graph.json') -Raw | ConvertFrom-Json
        rule = Get-Content (Join-Path $root 'tests/fixtures/graph-replay/grant-access-rule.json') -Raw | ConvertFrom-Json
    }
}

Test-Case 'semantic diff reports removed and added edges' {
    $input = Get-TestReplayInputs
    $rewrite = Invoke-AriaGraphRewrite -Graph $input.graph -Rule $input.rule -GrantedCapabilities @('cap:graph.write')
    $diff = Compare-AriaGraphSemantic -Before $input.graph -After $rewrite.graph

    Assert-True ([bool]$diff.valid) 'Semantic graph diff was invalid.'
    Assert-Equal '1' ([string]@($diff.edges.removed).Count) 'Removed edge was not reported.'
    Assert-Equal '1' ([string]@($diff.edges.added).Count) 'Added edge was not reported.'
}

Test-Case 'semantic diff is stable for identical graphs' {
    $input = Get-TestReplayInputs
    $diff = Compare-AriaGraphSemantic -Before $input.graph -After (Copy-AriaGraph $input.graph)

    Assert-True (-not [bool]$diff.changed) 'Identical graphs produced a semantic change.'
    Assert-Equal ([string]$diff.beforeDigest) ([string]$diff.afterDigest) 'Identical graph digests diverged.'
}

Test-Case 'graph transition is content addressed' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    Assert-True ([bool]$result.committed) 'Graph transition did not commit.'
    Assert-True ([string]$result.transition.id -match '^sha256:[a-f0-9]{64}$') 'Transition identity is not content addressed.'
}

Test-Case 'graph transition records capability authority' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    Assert-Equal 'cap:graph.write' ([string]$result.transition.grantedCapabilities[0]) 'Granted graph authority was not recorded.'
}

Test-Case 'graph transition rejects tampered identity' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $result.transition.id = 'sha256:' + ('0' * 64)
    $validation = Test-AriaGraphTransition $result.transition
    Assert-True (-not [bool]$validation.valid) 'Tampered transition identity was accepted.'
    Assert-Equal 'E_REPLAY_IDENTITY' ([string]$validation.errors[0].code) 'Transition identity rejection mismatch.'
}

Test-Case 'transition chain accepts coherent history' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $chain = Test-AriaGraphTransitionChain -InitialGraphDigest $before -Transitions @($result.transition)
    Assert-True ([bool]$chain.valid) 'Coherent transition chain was rejected.'
    Assert-Equal ([string]$result.transition.afterDigest) ([string]$chain.finalDigest) 'Transition chain final digest mismatch.'
}

Test-Case 'transition chain rejects parent fracture' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $result.transition.parent = 'sha256:' + ('1' * 64)
    $chain = Test-AriaGraphTransitionChain -InitialGraphDigest $before -Transitions @($result.transition)
    Assert-True (-not [bool]$chain.valid) 'Broken transition parent was accepted.'
}

Test-Case 'transition chain rejects sequence fracture' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $result.transition.sequence = 2
    $chain = Test-AriaGraphTransitionChain -InitialGraphDigest $before -Transitions @($result.transition)
    Assert-True (-not [bool]$chain.valid) 'Broken transition sequence was accepted.'
}

Test-Case 'graph replay reproduces recorded digest' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $replay = Invoke-AriaGraphReplay -InitialGraph $input.graph -Transitions @($result.transition)
    Assert-True ([bool]$replay.valid) 'Deterministic graph replay failed.'
    Assert-Equal ([string]$result.transition.afterDigest) ([string]$replay.digest) 'Replay digest did not reproduce recorded state.'
}

Test-Case 'graph replay rejects digest divergence' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $result.transition.afterDigest = ('f' * 64)
    $replay = Invoke-AriaGraphReplay -InitialGraph $input.graph -Transitions @($result.transition)
    Assert-True (-not [bool]$replay.valid) 'Replay digest divergence was accepted.'
}

Test-Case 'historical graph state reconstructs sequence zero' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $state = Get-AriaGraphStateAt -InitialGraph $input.graph -Transitions @($result.transition) -Sequence 0
    Assert-True ([bool]$state.valid) 'Sequence-zero graph reconstruction failed.'
    Assert-Equal $before ([string]$state.digest) 'Sequence-zero graph identity mismatch.'
}

Test-Case 'historical graph state reconstructs committed transition' {
    $input = Get-TestReplayInputs
    $before = Get-AriaGraphDigest $input.graph
    $result = New-AriaGraphTransition `
        -Sequence 1 `
        -Parent ("sha256:$before") `
        -BeforeGraph $input.graph `
        -Rule $input.rule `
        -GrantedCapabilities @('cap:graph.write')

    $state = Get-AriaGraphStateAt -InitialGraph $input.graph -Transitions @($result.transition) -Sequence 1
    Assert-True ([bool]$state.valid) 'Committed graph state reconstruction failed.'
    Assert-Equal ([string]$result.transition.afterDigest) ([string]$state.digest) 'Historical graph state digest mismatch.'
}
function Get-TestAuthorityInputs {
    [pscustomobject]@{
        root = Get-Content (Join-Path $root 'tests/fixtures/capability-authority/root-graph-write.cap.json') -Raw | ConvertFrom-Json
        delegated = Get-Content (Join-Path $root 'tests/fixtures/capability-authority/delegated-graph-write.cap.json') -Raw | ConvertFrom-Json
        policy = New-AriaIssuerTrustPolicy -TrustedIssuers @('operator:jackson') -MaxDelegationDepth 2
        ledger = New-AriaRevocationLedger
        decisionTime = '2026-06-01T00:00:00Z'
    }
}

Test-Case 'capability identity is deterministic' {
    $input = Get-TestAuthorityInputs
    $first = Test-AriaCapabilityTokenIdentity $input.root
    $second = Test-AriaCapabilityTokenIdentity $input.root

    Assert-True ([bool]$first.valid) 'Valid root capability identity was rejected.'
    Assert-Equal ([string]$first.expectedId) ([string]$second.expectedId) 'Capability identity was not deterministic.'
}

Test-Case 'capability rejects tampered identity' {
    $input = Get-TestAuthorityInputs
    $input.root.subject = 'agent:tampered'
    $result = Test-AriaCapabilityTokenIdentity $input.root

    Assert-True (-not [bool]$result.valid) 'Tampered capability identity was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_IDENTITY') 'Capability identity rejection code missing.'
}

Test-Case 'capability rejects unknown root issuer' {
    $input = Get-TestAuthorityInputs
    $token = New-AriaCapabilityToken `
        -Issuer 'operator:unknown' `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -Effects @('graph.write') `
        -NotBefore '2026-01-01T00:00:00Z' `
        -ExpiresAt '2027-01-01T00:00:00Z' `
        -Nonce 'unknown-issuer'

    $result = Test-AriaCapabilityChain `
        -Token $token `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Unknown capability issuer was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_ISSUER_UNTRUSTED') 'Untrusted issuer rejection missing.'
}

Test-Case 'capability rejects subject mismatch' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:intruder' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Capability subject mismatch was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_SUBJECT') 'Subject rejection missing.'
}

Test-Case 'capability rejects resource mismatch' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:staging' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Capability resource mismatch was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_RESOURCE') 'Resource rejection missing.'
}

Test-Case 'capability rejects missing effect' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('network.send') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Missing capability effect was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_EFFECT') 'Effect rejection missing.'
}

Test-Case 'capability rejects not-yet-active authority' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime '2025-12-31T23:59:59Z' `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Not-yet-active capability was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_NOT_ACTIVE') 'Activation rejection missing.'
}

Test-Case 'capability rejects expired authority' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime '2027-01-01T00:00:00Z' `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Expired capability was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_EXPIRED') 'Expiration rejection missing.'
}

Test-Case 'capability accepts attenuated delegation' {
    $input = Get-TestAuthorityInputs
    $result = Test-AriaCapabilityChain `
        -Token $input.delegated `
        -KnownTokens @($input.root) `
        -Policy $input.policy `
        -Subject 'agent:worker' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True ([bool]$result.valid) 'Valid attenuated delegation was rejected.'
    Assert-Equal '2' ([string]@($result.chain).Count) 'Delegation chain depth mismatch.'
}

Test-Case 'capability rejects delegated authority broadening' {
    $input = Get-TestAuthorityInputs
    $result = New-AriaDelegatedCapabilityToken `
        -ParentToken $input.root `
        -Subject 'agent:worker' `
        -Effects @('graph.write','network.send') `
        -NotBefore '2026-02-01T00:00:00Z' `
        -ExpiresAt '2026-12-01T00:00:00Z' `
        -Nonce 'broadened' `
        -MaxDelegationDepth 2

    Assert-True (-not [bool]$result.issued) 'Broadened delegated authority was issued.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_DELEGATION_BROADEN') 'Delegation broadening rejection missing.'
}

Test-Case 'capability rejects excessive delegation depth' {
    $input = Get-TestAuthorityInputs
    $policy = New-AriaIssuerTrustPolicy -TrustedIssuers @('operator:jackson') -MaxDelegationDepth 0
    $result = Test-AriaCapabilityChain `
        -Token $input.delegated `
        -KnownTokens @($input.root) `
        -Policy $policy `
        -Subject 'agent:worker' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Excessive delegation depth was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_DELEGATION_DEPTH') 'Delegation depth rejection missing.'
}

Test-Case 'capability rejects unknown parent' {
    $input = Get-TestAuthorityInputs
    $token = New-AriaCapabilityToken `
        -Issuer 'agent:hermes' `
        -Subject 'agent:worker' `
        -Resource 'graph:production' `
        -Effects @('graph.write') `
        -NotBefore '2026-02-01T00:00:00Z' `
        -ExpiresAt '2026-12-01T00:00:00Z' `
        -Nonce 'unknown-parent' `
        -DelegationDepth 1 `
        -Parent ('sha256:' + ('9' * 64))

    $result = Test-AriaCapabilityChain `
        -Token $token `
        -Policy $input.policy `
        -Subject 'agent:worker' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True (-not [bool]$result.valid) 'Unknown delegation parent was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_PARENT_UNKNOWN') 'Unknown parent rejection missing.'
}

Test-Case 'capability rejects reused single-use nonce' {
    $input = Get-TestAuthorityInputs
    $token = New-AriaCapabilityToken `
        -Issuer 'operator:jackson' `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -Effects @('graph.write') `
        -NotBefore '2026-01-01T00:00:00Z' `
        -ExpiresAt '2027-01-01T00:00:00Z' `
        -Nonce 'single-use-proof' `
        -SingleUse

    $result = Test-AriaCapabilityChain `
        -Token $token `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger `
        -UsedNonces @('single-use-proof')

    Assert-True (-not [bool]$result.valid) 'Reused single-use nonce was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_CAP_NONCE_REUSED') 'Nonce reuse rejection missing.'
}

Test-Case 'capability preserves historical revocation semantics' {
    $input = Get-TestAuthorityInputs
    $ledger = Add-AriaCapabilityRevocation `
        -Ledger $input.ledger `
        -CapabilityId $input.root.id `
        -RevokedAt '2026-07-01T00:00:00Z' `
        -Reason 'operator revocation'

    $before = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime '2026-06-01T00:00:00Z' `
        -RevocationLedger $ledger

    $after = Test-AriaCapabilityChain `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -RequestedEffects @('graph.write') `
        -DecisionTime '2026-08-01T00:00:00Z' `
        -RevocationLedger $ledger

    Assert-True ([bool]$before.valid) 'Authority before revocation was invalidated historically.'
    Assert-True (-not [bool]$after.valid) 'Authority after revocation was accepted.'
    Assert-True (@($after.errors.code) -contains 'E_CAP_REVOKED') 'Revocation rejection missing.'
}

Test-Case 'graph rewrite requires verified capability authority' {
    $input = Get-TestAuthorityInputs
    $graph = Get-Content (Join-Path $root 'tests/fixtures/graph-replay/initial-access-graph.json') -Raw | ConvertFrom-Json
    $rule = Get-Content (Join-Path $root 'tests/fixtures/graph-replay/grant-access-rule.json') -Raw | ConvertFrom-Json

    $approved = Invoke-AriaAuthorizedGraphRewrite `
        -Graph $graph `
        -Rule $rule `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:hermes' `
        -Resource 'graph:production' `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    $rejected = Invoke-AriaAuthorizedGraphRewrite `
        -Graph $graph `
        -Rule $rule `
        -Token $input.root `
        -Policy $input.policy `
        -Subject 'agent:intruder' `
        -Resource 'graph:production' `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True ([bool]$approved.committed) 'Verified graph authority did not permit rewrite.'
    Assert-Equal 'approved' ([string]$approved.authorityDecision.outcome) 'Approved authority decision missing.'
    Assert-True ([bool]$rejected.rejected) 'Invalid graph authority did not reject rewrite.'
    Assert-Equal 'authority-rejected' ([string]$rejected.reason) 'Authority rejection reason mismatch.'
    Assert-Equal ([string]$rejected.beforeDigest) ([string]$rejected.afterDigest) 'Rejected authority changed graph identity.'
}
function Get-TestGovernedEvolutionInputs {
    $snapshot = Get-Content (Join-Path $root 'tests/fixtures/governed-evolution/base-snapshot.json') -Raw | ConvertFrom-Json
    $proposal = Get-Content (Join-Path $root 'tests/fixtures/governed-evolution/valid-proposal.json') -Raw | ConvertFrom-Json
    $authorization = Get-Content (Join-Path $root 'tests/fixtures/governed-evolution/valid-authorization.json') -Raw | ConvertFrom-Json

    $token = New-AriaCapabilityToken `
        -Issuer 'operator:jackson' `
        -Subject 'agent:evolver' `
        -Resource 'repository:ARIA' `
        -Effects @('repository.write') `
        -NotBefore '2026-01-01T00:00:00Z' `
        -ExpiresAt '2027-01-01T00:00:00Z' `
        -Nonce 'aria-alpha20-evolution-authority'

    [pscustomobject]@{
        snapshot=$snapshot
        proposal=$proposal
        authorization=$authorization
        token=$token
        policy=New-AriaIssuerTrustPolicy -TrustedIssuers @('operator:jackson') -MaxDelegationDepth 1
        ledger=New-AriaRevocationLedger
        commit=('a' * 40)
        decisionTime='2026-06-01T00:00:00Z'
    }
}

Test-Case 'evolution proposal identity is deterministic' {
    $input=Get-TestGovernedEvolutionInputs
    $first=Test-AriaEvolutionProposal $input.proposal
    $second=Test-AriaEvolutionProposal $input.proposal

    Assert-True ([bool]$first.valid) 'Valid evolution proposal was rejected.'
    Assert-Equal ([string]$first.expectedId) ([string]$second.expectedId) 'Evolution proposal identity was not deterministic.'
}

Test-Case 'evolution proposal rejects tampered identity' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.targetVersion='9.9.9'
    $result=Test-AriaEvolutionProposal $input.proposal

    Assert-True (-not [bool]$result.valid) 'Tampered evolution proposal was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_IDENTITY') 'Evolution identity rejection missing.'
}

Test-Case 'evolution proposal rejects unsafe repository path' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.changes[0].path='../escape.txt'
    $result=Test-AriaEvolutionProposal $input.proposal

    Assert-True (-not [bool]$result.valid) 'Unsafe repository path was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_PATH') 'Unsafe path rejection missing.'
}

Test-Case 'evolution proposal rejects duplicate change path' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.changes=@($input.proposal.changes)+@($input.proposal.changes[0])
    $result=Test-AriaEvolutionProposal $input.proposal

    Assert-True (-not [bool]$result.valid) 'Duplicate proposal path was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_PATH_DUPLICATE') 'Duplicate path rejection missing.'
}

Test-Case 'evolution proposal requires all core gates' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.requiredGates=@('manifest','conformance')
    $result=Test-AriaEvolutionProposal $input.proposal

    Assert-True (-not [bool]$result.valid) 'Proposal without strict doctor gate was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_GATE_REQUIRED') 'Required gate rejection missing.'
}

Test-Case 'evolution proposal rejects incomplete rollback plan' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.rollbackPlan=@()
    $result=Test-AriaEvolutionProposal $input.proposal

    Assert-True (-not [bool]$result.valid) 'Proposal without rollback plan was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_ROLLBACK_MISSING') 'Rollback rejection missing.'
}

Test-Case 'evolution authority approves matching proposer scope' {
    $input=Get-TestGovernedEvolutionInputs
    $decision=New-AriaAuthorityDecision `
        -Token $input.token `
        -Policy $input.policy `
        -Subject 'agent:evolver' `
        -Resource 'repository:ARIA' `
        -RequestedEffects @('repository.write') `
        -DecisionTime $input.decisionTime `
        -RevocationLedger $input.ledger

    Assert-True ([bool]$decision.approved) 'Matching evolution authority was rejected.'
}

Test-Case 'evolution authority rejects proposer subject mismatch' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.proposer='agent:intruder'

    $plan=Invoke-AriaGovernedEvolutionPlan `
        -Proposal $input.proposal `
        -Authorization $input.authorization `
        -CapabilityToken $input.token `
        -IssuerPolicy $input.policy `
        -RevocationLedger $input.ledger `
        -DecisionTime $input.decisionTime `
        -TrustedAuthorizers @('operator:jackson') `
        -CurrentCommit $input.commit `
        -CurrentSnapshot $input.snapshot

    Assert-True (-not [bool]$plan.approved) 'Mismatched proposal subject was approved.'
    Assert-True (@($plan.errors.code) -contains 'E_CAP_SUBJECT') 'Evolution subject rejection missing.'
}

Test-Case 'evolution plan requires human authorization' {
    $input=Get-TestGovernedEvolutionInputs
    $input.authorization.decision='rejected'

    $plan=Invoke-AriaGovernedEvolutionPlan `
        -Proposal $input.proposal `
        -Authorization $input.authorization `
        -CapabilityToken $input.token `
        -IssuerPolicy $input.policy `
        -RevocationLedger $input.ledger `
        -DecisionTime $input.decisionTime `
        -TrustedAuthorizers @('operator:jackson') `
        -CurrentCommit $input.commit `
        -CurrentSnapshot $input.snapshot

    Assert-True (-not [bool]$plan.approved) 'Human-rejected evolution was approved.'
    Assert-True (@($plan.errors.code) -contains 'E_EVOLUTION_NOT_APPROVED') 'Human authorization rejection missing.'
}

Test-Case 'evolution authorization rejects tampered identity' {
    $input=Get-TestGovernedEvolutionInputs
    $input.authorization.authorizer='operator:tampered'
    $result=Test-AriaEvolutionAuthorization `
        -Authorization $input.authorization `
        -ProposalId $input.proposal.id `
        -TrustedAuthorizers @('operator:jackson')

    Assert-True (-not [bool]$result.valid) 'Tampered evolution authorization was accepted.'
    Assert-True (@($result.errors.code) -contains 'E_EVOLUTION_AUTH_IDENTITY') 'Authorization identity rejection missing.'
}

Test-Case 'evolution plan rejects base commit mismatch' {
    $input=Get-TestGovernedEvolutionInputs

    $plan=Invoke-AriaGovernedEvolutionPlan `
        -Proposal $input.proposal `
        -Authorization $input.authorization `
        -CapabilityToken $input.token `
        -IssuerPolicy $input.policy `
        -RevocationLedger $input.ledger `
        -DecisionTime $input.decisionTime `
        -TrustedAuthorizers @('operator:jackson') `
        -CurrentCommit ('b' * 40) `
        -CurrentSnapshot $input.snapshot

    Assert-True (-not [bool]$plan.approved) 'Mismatched base commit was approved.'
    Assert-True (@($plan.errors.code) -contains 'E_EVOLUTION_BASE_COMMIT') 'Base commit rejection missing.'
}

Test-Case 'evolution candidate applies expected content digest' {
    $input=Get-TestGovernedEvolutionInputs
    $candidate=Invoke-AriaEvolutionChanges `
        -Snapshot $input.snapshot `
        -Changes @($input.proposal.changes)

    Assert-True ([bool]$candidate.valid) 'Valid evolution change did not produce a candidate.'
    Assert-Equal ([string]$input.proposal.changes[0].afterDigest) ([string]$candidate.snapshot.files[0].digest) 'Candidate content digest mismatch.'
}

Test-Case 'evolution candidate rejects stale before digest' {
    $input=Get-TestGovernedEvolutionInputs
    $input.proposal.changes[0].beforeDigest=('f' * 64)
    $candidate=Invoke-AriaEvolutionChanges `
        -Snapshot $input.snapshot `
        -Changes @($input.proposal.changes)

    Assert-True (-not [bool]$candidate.valid) 'Stale proposal base digest was accepted.'
    Assert-Equal 'E_EVOLUTION_BASE_DIGEST' ([string]$candidate.errors[0].code) 'Stale base digest rejection mismatch.'
}

Test-Case 'evolution rollback reproduces original snapshot' {
    $input=Get-TestGovernedEvolutionInputs
    $candidate=Invoke-AriaEvolutionChanges `
        -Snapshot $input.snapshot `
        -Changes @($input.proposal.changes)

    $rollback=Test-AriaEvolutionRollback `
        -OriginalSnapshot $input.snapshot `
        -CandidateSnapshot $candidate.snapshot `
        -RollbackPlan @($input.proposal.rollbackPlan)

    Assert-True ([bool]$rollback.valid) 'Evolution rollback proof failed.'
    Assert-Equal ([string]$input.snapshot.id) ([string]$rollback.restoredSnapshot.id) 'Rollback did not reproduce original identity.'
}

Test-Case 'governed evolution emits content-addressed decision event' {
    $input=Get-TestGovernedEvolutionInputs

    $plan=Invoke-AriaGovernedEvolutionPlan `
        -Proposal $input.proposal `
        -Authorization $input.authorization `
        -CapabilityToken $input.token `
        -IssuerPolicy $input.policy `
        -RevocationLedger $input.ledger `
        -DecisionTime $input.decisionTime `
        -TrustedAuthorizers @('operator:jackson') `
        -CurrentCommit $input.commit `
        -CurrentSnapshot $input.snapshot

    Assert-True ([bool]$plan.approved) 'Valid governed evolution plan was rejected.'
    Assert-True ([bool]$plan.rollbackVerified) 'Governed evolution did not prove rollback.'
    Assert-Equal 'approved' ([string]$plan.authorityDecision.outcome) 'Authority decision was not approved.'
    Assert-Equal 'aria.evolution.plan.approved' ([string]$plan.event.type) 'Governed evolution event type mismatch.'
    Assert-True ([string]$plan.event.id -match '^sha256:[a-f0-9]{64}$') 'Governed evolution event is not content addressed.'
}

function New-TestEvolutionRequest {
    param([object[]]$Changes)
    [pscustomobject][ordered]@{
        schema='aria.evolution-request/0.7'
        proposer='agent:planner'
        targetVersion='0.5.0-alpha.23'
        resource='repository:ARIA'
        capabilityIds=@('sha256:'+('a'*64))
        changes=@($Changes)
        evidence=@([pscustomobject][ordered]@{
            kind='test'
            id='tests/evolution-planning'
            digest=('b'*64)
        })
    }
}

function New-TestEvolutionVerificationInputs {
    param([string]$Workspace,[string]$BaseCommit=('3'*40))

    $decisionTime='2026-07-23T12:00:00Z'
    $token=New-AriaCapabilityToken `
        -Issuer 'operator:test' `
        -Subject 'agent:planner' `
        -Resource 'repository:ARIA' `
        -Effects @('repository.write') `
        -NotBefore '2026-01-01T00:00:00Z' `
        -ExpiresAt '2027-01-01T00:00:00Z' `
        -Nonce 'verify-plan-test'
    $request=New-TestEvolutionRequest @([pscustomobject]@{path='new.md';operation='write';content="new`n"})
    $request.capabilityIds=@($token.id)
    $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $Workspace -BaseCommit $BaseCommit
    $authorization=New-AriaEvolutionAuthorization `
        -ProposalId $plan.proposal.id `
        -Authorizer 'operator:reviewer' `
        -Decision approved `
        -DecidedAt $decisionTime `
        -Nonce 'verify-plan-authorization'
    $verificationPolicy=[pscustomobject][ordered]@{
        schema='aria.evolution-verification-policy/0.8'
        trustedAuthorizers=@('operator:reviewer')
        issuerPolicy=New-AriaIssuerTrustPolicy -TrustedIssuers @('operator:test')
    }
    [pscustomobject]@{
        request=$request
        plan=$plan
        token=$token
        authorization=$authorization
        verificationPolicy=$verificationPolicy
        baseCommit=$BaseCommit
    }
}

Test-Case 'evolution request accepts a narrow write plan' {
    $request=New-TestEvolutionRequest @([pscustomobject]@{path='docs/plan.md';operation='write';content="planned`n"})
    $result=Test-AriaEvolutionRequest $request
    Assert-True ([bool]$result.valid) 'Valid evolution request was rejected.'
}

Test-Case 'evolution request rejects path traversal' {
    $request=New-TestEvolutionRequest @([pscustomobject]@{path='../escape.md';operation='write';content='escape'})
    $result=Test-AriaEvolutionRequest $request
    Assert-True (-not[bool]$result.valid) 'Evolution path traversal was accepted.'
    Assert-True (@($result.errors.code)-contains'E_EVOLUTION_REQUEST_PATH') 'Path traversal rejection code missing.'
}

Test-Case 'evolution request rejects duplicate paths' {
    $request=New-TestEvolutionRequest @(
        [pscustomobject]@{path='docs/same.md';operation='write';content='one'},
        [pscustomobject]@{path='docs/same.md';operation='write';content='two'}
    )
    $result=Test-AriaEvolutionRequest $request
    Assert-True (-not[bool]$result.valid) 'Duplicate evolution paths were accepted.'
    Assert-True (@($result.errors.code)-contains'E_EVOLUTION_REQUEST_DUPLICATE') 'Duplicate path rejection code missing.'
}

Test-Case 'evolution request requires capability identity' {
    $request=New-TestEvolutionRequest @([pscustomobject]@{path='docs/plan.md';operation='write';content='planned'})
    $request.capabilityIds=@()
    $result=Test-AriaEvolutionRequest $request
    Assert-True (-not[bool]$result.valid) 'Capability-free evolution request was accepted.'
    Assert-True (@($result.errors.code)-contains'E_EVOLUTION_REQUEST_CAPABILITY') 'Capability rejection code missing.'
}

Test-Case 'evolution planner binds current bytes and commit' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path (Join-Path $workspace 'docs') -Force|Out-Null
        Write-AriaUtf8NoBom (Join-Path $workspace 'docs/plan.md') "before`n"
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='docs/plan.md';operation='write';content="after`n"})
        $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('c'*40)
        Assert-Equal ('c'*40) ([string]$plan.proposal.baseCommit) 'Evolution plan did not bind the base commit.'
        Assert-Equal (Get-AriaEvolutionContentDigest "before`n") ([string]$plan.proposal.changes[0].beforeDigest) 'Evolution plan did not bind current bytes.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution planner proves rollback for added file' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='new.md';operation='write';content="new`n"})
        $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('d'*40)
        Assert-True ([bool]$plan.record.rollbackVerified) 'Added-file rollback was not verified.'
        Assert-Equal 'delete' ([string]$plan.proposal.rollbackPlan[0].operation) 'Added-file rollback is not a delete.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution planner represents deletion semantically' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        Write-AriaUtf8NoBom (Join-Path $workspace 'old.md') "old`n"
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='old.md';operation='delete'})
        $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('e'*40)
        Assert-Equal 'old.md' ([string]$plan.record.semanticDiff.removed[0].path) 'Deletion missing from semantic diff.'
        Assert-Equal 'write' ([string]$plan.proposal.rollbackPlan[0].operation) 'Deleted-file rollback is not a write.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution planning identity is deterministic' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='new.md';operation='write';content="new`n"})
        $first=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('f'*40)
        $second=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('f'*40)
        Assert-Equal ([string]$first.proposal.id) ([string]$second.proposal.id) 'Evolution proposal identity changed.'
        Assert-Equal ([string]$first.record.id) ([string]$second.record.id) 'Evolution record identity changed.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution planner persists five canonical records' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='new.md';operation='write';content="new`n"})
        $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('1'*40)
        $persisted=Write-AriaEvolutionPlanRecord -Plan $plan -WorkspaceRoot $workspace
        Assert-Equal '5' ([string]@(Get-ChildItem -LiteralPath $persisted.directory -File).Count) 'Evolution record file count mismatch.'
        Assert-True (Test-Path -LiteralPath (Join-Path $persisted.directory 'proposal.json')) 'Proposal record was not persisted.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution record persistence is idempotent' {
    $workspace=Join-Path $tempRoot ('aria-plan-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $request=New-TestEvolutionRequest @([pscustomobject]@{path='new.md';operation='write';content="new`n"})
        $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $workspace -BaseCommit ('2'*40)
        $first=Write-AriaEvolutionPlanRecord -Plan $plan -WorkspaceRoot $workspace
        $second=Write-AriaEvolutionPlanRecord -Plan $plan -WorkspaceRoot $workspace
        Assert-Equal ([string]$first.recordId) ([string]$second.recordId) 'Idempotent record identity changed.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification policy requires explicit authorizers' {
    $policy=[pscustomobject]@{
        schema='aria.evolution-verification-policy/0.8'
        trustedAuthorizers=@()
        issuerPolicy=New-AriaIssuerTrustPolicy -TrustedIssuers @('operator:test')
    }
    $result=Test-AriaEvolutionVerificationPolicy $policy
    Assert-True (-not[bool]$result.valid) 'Authorizer-free verification policy was accepted.'
    Assert-True (@($result.errors.code)-contains'E_EVOLUTION_VERIFY_POLICY_AUTHORIZER') 'Trusted authorizer rejection missing.'
}

Test-Case 'evolution plan record verifies deterministic identity' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $result=Test-AriaEvolutionPlanRecord $input.plan.record
        Assert-True ([bool]$result.valid) 'Valid evolution plan record was rejected.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification authorizes matching artifacts' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $result=Invoke-AriaEvolutionVerification `
            -Plan $input.plan `
            -CapabilityBundle $input.token `
            -Authorization $input.authorization `
            -VerificationPolicy $input.verificationPolicy `
            -CurrentCommit $input.baseCommit
        Assert-Equal 'authorized' ([string]$result.record.state) 'Verified evolution did not become authorized.'
        Assert-Equal 'approved' ([string]$result.authorityDecision.outcome) 'Capability authority was not approved.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification rejects wrong authorization' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $input.authorization.proposalId='sha256:'+('f'*64)
        $rejected=$false
        try{$null=Invoke-AriaEvolutionVerification -Plan $input.plan -CapabilityBundle $input.token -Authorization $input.authorization -VerificationPolicy $input.verificationPolicy -CurrentCommit $input.baseCommit}
        catch{$rejected=$true}
        Assert-True $rejected 'Mismatched human authorization was accepted.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification rejects capability subject mismatch' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $input.plan.proposal.proposer='agent:intruder'
        $rejected=$false
        try{$null=Invoke-AriaEvolutionVerification -Plan $input.plan -CapabilityBundle $input.token -Authorization $input.authorization -VerificationPolicy $input.verificationPolicy -CurrentCommit $input.baseCommit}
        catch{$rejected=$true}
        Assert-True $rejected 'Mismatched capability subject was accepted.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'persisted evolution plan reloads against stable workspace' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $persisted=Write-AriaEvolutionPlanRecord -Plan $input.plan -WorkspaceRoot $workspace
        $loaded=Read-AriaEvolutionPlanRecord -ProposalId $input.plan.proposal.id -WorkspaceRoot $workspace -CurrentCommit $input.baseCommit
        Assert-Equal ([string]$persisted.recordId) ([string]$loaded.record.id) 'Reloaded plan record identity changed.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'persisted evolution plan rejects workspace drift' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $null=Write-AriaEvolutionPlanRecord -Plan $input.plan -WorkspaceRoot $workspace
        Write-AriaUtf8NoBom (Join-Path $workspace 'new.md') "unexpected`n"
        $rejected=$false
        try{$null=Read-AriaEvolutionPlanRecord -ProposalId $input.plan.proposal.id -WorkspaceRoot $workspace -CurrentCommit $input.baseCommit}
        catch{$rejected=$true}
        Assert-True $rejected 'Workspace drift after planning was accepted.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'persisted evolution plan rejects base commit drift' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $null=Write-AriaEvolutionPlanRecord -Plan $input.plan -WorkspaceRoot $workspace
        $rejected=$false
        try{$null=Read-AriaEvolutionPlanRecord -ProposalId $input.plan.proposal.id -WorkspaceRoot $workspace -CurrentCommit ('4'*40)}
        catch{$rejected=$true}
        Assert-True $rejected 'Base commit drift after planning was accepted.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification persists append-only decision records' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $persistedPlan=Write-AriaEvolutionPlanRecord -Plan $input.plan -WorkspaceRoot $workspace
        $verification=Invoke-AriaEvolutionVerification -Plan $input.plan -CapabilityBundle $input.token -Authorization $input.authorization -VerificationPolicy $input.verificationPolicy -CurrentCommit $input.baseCommit
        $persisted=Write-AriaEvolutionVerificationRecord -Verification $verification -PlanDirectory $persistedPlan.directory
        Assert-Equal 'authorized' ([string]$persisted.state) 'Persisted verification state mismatch.'
        Assert-Equal '9' ([string]@(Get-ChildItem -LiteralPath $persisted.directory -File).Count) 'Authorized record file count mismatch.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'evolution verification persistence is idempotent' {
    $workspace=Join-Path $tempRoot ('aria-verify-'+[guid]::NewGuid().ToString('N'))
    try{
        New-Item -ItemType Directory -Path $workspace -Force|Out-Null
        $input=New-TestEvolutionVerificationInputs $workspace
        $persistedPlan=Write-AriaEvolutionPlanRecord -Plan $input.plan -WorkspaceRoot $workspace
        $verification=Invoke-AriaEvolutionVerification -Plan $input.plan -CapabilityBundle $input.token -Authorization $input.authorization -VerificationPolicy $input.verificationPolicy -CurrentCommit $input.baseCommit
        $first=Write-AriaEvolutionVerificationRecord -Verification $verification -PlanDirectory $persistedPlan.directory
        $second=Write-AriaEvolutionVerificationRecord -Verification $verification -PlanDirectory $persistedPlan.directory
        Assert-Equal ([string]$first.verificationId) ([string]$second.verificationId) 'Idempotent verification identity changed.'
    }
    finally{Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue}
}

Test-Case 'stable JSON permits shared custom object without false cycle' {
    $shared=[pscustomobject]@{value=7}
    $document=[pscustomobject]@{left=$shared;right=$shared}
    $json=ConvertTo-AriaStableJson $document

    Assert-Equal '{"left":{"value":7},"right":{"value":7}}' $json 'Shared custom object was mistaken for a cycle.'
}
Test-Case 'source lexer recognizes ordinary tokens' {
    $tokens=ConvertTo-AriaSourceTokens 'let answer: Int = 42; emit answer;'
    Assert-Equal 'Let' ([string]$tokens[0].kind) 'Source let token missing.'
    Assert-Equal 'Int' ([string]$tokens[5].kind) 'Source integer token missing.'
}

Test-Case 'source parser builds immutable binding' {
    $program=Read-AriaSourceProgram 'let answer: Int = 42; emit answer;'
    Assert-Equal 'let' ([string]$program.declarations[0].kind) 'Source binding AST missing.'
    Assert-Equal 'answer' ([string]$program.declarations[0].name) 'Source binding name mismatch.'
}

Test-Case 'source checker accepts typed arithmetic' {
    $result=Invoke-AriaSourceText 'let answer: Int = 2 + 3 * 4; emit answer;'
    Assert-True ([bool]$result.valid) 'Typed arithmetic program was rejected.'
    Assert-Equal '14' ([string]$result.output[0]) 'Arithmetic precedence mismatch.'
}

Test-Case 'source checker rejects binding type mismatch' {
    $result=Invoke-AriaSourceText 'let answer: Text = 42; emit answer;'
    Assert-True (-not[bool]$result.valid) 'Binding type mismatch was accepted.'
}

Test-Case 'source checker rejects unknown binding' {
    $result=Invoke-AriaSourceText 'emit missing;'
    Assert-True (-not[bool]$result.valid) 'Unknown binding was accepted.'
}

Test-Case 'source checker validates function argument types' {
    $result=Invoke-AriaSourceText 'fn double(x: Int) -> Int { x * 2 } emit double("x");'
    Assert-True (-not[bool]$result.valid) 'Invalid function argument type was accepted.'
}

Test-Case 'source evaluator runs pure function' {
    $result=Invoke-AriaSourceText 'fn add(x: Int, y: Int) -> Int { x + y } emit add(20, 22);'
    Assert-True ([bool]$result.valid) 'Pure function program was rejected.'
    Assert-Equal '42' ([string]$result.output[0]) 'Pure function output mismatch.'
}

Test-Case 'source conditional requires Bool condition' {
    $result=Invoke-AriaSourceText 'emit if 1 { 2 } else { 3 };'
    Assert-True (-not[bool]$result.valid) 'Non-Bool conditional was accepted.'
}

Test-Case 'source conditional requires matching branch types' {
    $result=Invoke-AriaSourceText 'emit if true { 2 } else { "three" };'
    Assert-True (-not[bool]$result.valid) 'Mismatched conditional branches were accepted.'
}

Test-Case 'source text concatenation is deterministic' {
    $result=Invoke-AriaSourceText 'emit "ARIA " + "online";'
    Assert-True ([bool]$result.valid) 'Text concatenation was rejected.'
    Assert-Equal 'ARIA online' ([string]$result.output[0]) 'Text concatenation mismatch.'
}

Test-Case 'source integer division rejects zero' {
    $rejected=$false
    try{
        $program=Read-AriaSourceProgram 'emit 7 / 0;'
        $null=Invoke-AriaSourceProgram $program
    }
    catch{
        if($_.Exception.Message-like'*Division by zero*'){$rejected=$true}
    }
    Assert-True $rejected 'Division by zero was not rejected.'
}

Test-Case 'source IR identity is deterministic' {
    $source='fn add(x: Int, y: Int) -> Int { x + y } emit add(1, 2);'
    $first=Invoke-AriaSourceText $source
    $second=Invoke-AriaSourceText $source
    Assert-Equal ([string]$first.ir.id) ([string]$second.ir.id) 'Source IR identity changed.'
}

Test-Case 'source examples all execute' {
    $paths=Get-ChildItem (Join-Path $root 'examples/source-core') -Filter '*.aria' -File
    Assert-Equal '10' ([string]$paths.Count) 'Expected ten source examples.'
    foreach($path in $paths){
        $result=Invoke-AriaSourceFile $path.FullName
        Assert-True ([bool]$result.valid) "Source example failed: $($path.Name)"
    }
}

Test-Case 'source rejects duplicate names' {
    $result=Invoke-AriaSourceText 'let value: Int = 1; let value: Int = 2; emit value;'
    Assert-True (-not[bool]$result.valid) 'Duplicate source name was accepted.'
}

Test-Case 'source has no effects in alpha22' {
    $result=Invoke-AriaSourceText 'emit 42;'
    Assert-True ([bool]$result.valid) 'Pure source program was rejected.'
    Assert-Equal '0' ([string]@($result.ir.effects).Count) 'Alpha.22 source unexpectedly declared effects.'
}

Test-Case 'source rejects unknown declared types' {
    $result=Invoke-AriaSourceText 'fn identity(value: Mystery) -> Mystery { value }'
    Assert-True (-not[bool]$result.valid) 'Unknown source types were accepted.'
    Assert-Equal 'E_SOURCE_TYPE_NAME' ([string]$result.errors[0].code) 'Unknown type rejection code mismatch.'
}

Test-Case 'source rejects direct recursion' {
    $result=Invoke-AriaSourceText 'fn loop(value: Int) -> Int { loop(value) }'
    Assert-True (-not[bool]$result.valid) 'Direct recursion was accepted.'
    Assert-Equal 'E_SOURCE_RECURSION' ([string]$result.errors[0].code) 'Direct recursion rejection code mismatch.'
}

Test-Case 'source rejects mutual recursion' {
    $source='fn left(value: Int) -> Int { right(value) } fn right(value: Int) -> Int { left(value) }'
    $result=Invoke-AriaSourceText $source
    Assert-True (-not[bool]$result.valid) 'Mutual recursion was accepted.'
    Assert-Equal 'E_SOURCE_RECURSION' ([string]$result.errors[0].code) 'Mutual recursion rejection code mismatch.'
}

Test-Case 'source rejects integer addition overflow' {
    $result=Invoke-AriaSourceText 'emit 9223372036854775807 + 1;'
    Assert-True (-not[bool]$result.valid) 'Integer addition overflow was accepted.'
    Assert-Equal 'E_SOURCE_INTEGER_OVERFLOW' ([string]$result.errors[0].code) 'Addition overflow rejection code mismatch.'
}

Test-Case 'source rejects integer multiplication overflow' {
    $result=Invoke-AriaSourceText 'emit 9223372036854775807 * 2;'
    Assert-True (-not[bool]$result.valid) 'Integer multiplication overflow was accepted.'
    Assert-Equal 'E_SOURCE_INTEGER_OVERFLOW' ([string]$result.errors[0].code) 'Multiplication overflow rejection code mismatch.'
}

Test-Case 'source rejects integer division overflow' {
    $result=Invoke-AriaSourceText 'emit (-9223372036854775807 - 1) / -1;'
    Assert-True (-not[bool]$result.valid) 'Integer division overflow was accepted.'
    Assert-Equal 'E_SOURCE_INTEGER_OVERFLOW' ([string]$result.errors[0].code) 'Division overflow rejection code mismatch.'
}

Test-Case 'source runtime failures have structured codes' {
    $result=Invoke-AriaSourceText 'emit 7 / 0;'
    Assert-True (-not[bool]$result.valid) 'Division by zero was accepted.'
    Assert-Equal 'E_SOURCE_DIVISION_ZERO' ([string]$result.errors[0].code) 'Division-by-zero rejection code mismatch.'
}

Test-Case 'source diagnostics retain line and column' {
    $result=Invoke-AriaSourceText "let value: Int = 1;`nemit value + `"text`";"
    Assert-True (-not[bool]$result.valid) 'Invalid operator program was accepted.'
    Assert-Equal '2' ([string]$result.errors[0].line) 'Diagnostic line was not preserved.'
    Assert-True ([int]$result.errors[0].column-gt0) 'Diagnostic column was not preserved.'
}

function New-AriaIntentTestBundle {
    param(
        [string[]]$ProgramEffects=@('repository.write'),
        $OutcomeValue=$true,
        [string[]]$ObservedForbiddenOutcomes=@(),
        [switch]$OmitEvidence,
        [switch]$OmitChallenge,
        [switch]$MaterialAmbiguity,
        [switch]$ResolveAmbiguity,
        [switch]$MaterialChallenge,
        [switch]$ResolveChallenge,
        [switch]$OmitClaimedObligation,
        [switch]$SameChallenger
    )
    $ambiguities=@()
    if($MaterialAmbiguity){$ambiguities=@([pscustomobject][ordered]@{id='publish-target';question='Public release or internal registry?';severity='material'})}
    $intent=New-AriaIntent `
        -Name 'PublishVerifiedRelease' `
        -Objective 'Publish a release without changing runtime behavior.' `
        -RequiredOutcomes @([pscustomobject][ordered]@{id='tests.pass';expected=$true}) `
        -ForbiddenOutcomes @('history.rewrite') `
        -AllowedEffects @('repository.write','network.send') `
        -AcceptanceCriteria @([pscustomobject][ordered]@{id='semantic-diff';evidenceKind='semantic-diff'}) `
        -Ambiguities $ambiguities `
        -RequireIndependentChallenge
    $claimed=@('tests.pass','semantic-diff')
    if($OmitClaimedObligation){$claimed=@('tests.pass')}
    $interpretation=New-AriaIntentInterpretation `
        -IntentId $intent.id `
        -Interpreter 'agent:producer' `
        -UnderstoodObjective 'Publish only after tests and a zero semantic diff.' `
        -ExpectedEffects @('repository.write','network.send') `
        -ClaimedObligations $claimed `
        -UnresolvedAmbiguities $(if($MaterialAmbiguity){@('publish-target')}else{@()}) `
        -ImplementationRef 'sha256:program'
    $issues=@()
    if($MaterialChallenge){$issues=@([pscustomobject][ordered]@{id='alternate-target';severity='material';message='The publication target is not explicit.'})}
    $challenges=@()
    if(-not$OmitChallenge){
        $challenges=@(New-AriaIntentChallenge `
            -IntentId $intent.id `
            -InterpretationId $interpretation.id `
            -Challenger $(if($SameChallenger){'agent:producer'}else{'agent:critic'}) `
            -Issues $issues)
    }
    $ambiguityResolutions=@()
    if($ResolveAmbiguity){$ambiguityResolutions=@([pscustomobject][ordered]@{id='publish-target';resolution='public release'})}
    $challengeResolutions=@()
    if($ResolveChallenge){$challengeResolutions=@([pscustomobject][ordered]@{id='alternate-target';resolution='public release confirmed'})}
    $approval=New-AriaIntentApproval `
        -IntentId $intent.id `
        -InterpretationId $interpretation.id `
        -Approver 'human:operator' `
        -Decision approved `
        -DecidedAt '2026-07-23T12:00:00Z' `
        -AmbiguityResolutions $ambiguityResolutions `
        -ChallengeResolutions $challengeResolutions `
        -Nonce 'intent-test-1'
    $program=New-AriaIntentProgramSummary `
        -ArtifactId 'sha256:program' `
        -RequestedEffects $ProgramEffects `
        -Outcomes @([pscustomobject][ordered]@{id='tests.pass';actual=$OutcomeValue}) `
        -ObservedForbiddenOutcomes $ObservedForbiddenOutcomes
    $evidence=@()
    if(-not$OmitEvidence){
        $evidence=@(New-AriaIntentEvidence `
            -CriterionId 'semantic-diff' `
            -Kind 'semantic-diff' `
            -SubjectId 'sha256:program' `
            -Digest 'sha256:evidence' `
            -Passed $true)
    }
    [pscustomobject][ordered]@{
        schema='aria.intent-verification-bundle/0.9'
        intent=$intent
        interpretation=$interpretation
        approval=$approval
        challenges=$challenges
        program=$program
        evidence=$evidence
        verificationPolicy=[pscustomobject][ordered]@{
            schema='aria.intent-verification-policy/0.9'
            trustedApprovers=@('human:operator')
        }
    }
}

Test-Case 'intent identities are canonical and deterministic' {
    $one=New-AriaIntentTestBundle
    $two=New-AriaIntentTestBundle
    Assert-Equal $one.intent.id $two.intent.id 'Intent identity changed.'
    Assert-Equal $one.interpretation.id $two.interpretation.id 'Interpretation identity changed.'
}

Test-Case 'intent verifier derives a satisfied verdict' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle)
    Assert-True ([bool]$result.satisfied) ('Valid intent bundle was rejected: '+(@($result.errors|ForEach-Object{$_.code})-join','))
    Assert-Equal 'satisfied' $result.proof.verdict 'Intent proof verdict mismatch.'
}

Test-Case 'intent verifier rejects tampered identities' {
    $bundle=New-AriaIntentTestBundle
    $bundle.intent.objective='silently changed'
    $result=Invoke-AriaIntentVerification $bundle
    Assert-True ('E_INTENT_IDENTITY'-in@($result.errors.code)) 'Tampered intent identity was not rejected.'
}

Test-Case 'intent verifier rejects excess program authority' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -ProgramEffects @('repository.write','secret.read'))
    Assert-True ('E_INTENT_EXCESS_AUTHORITY'-in@($result.errors.code)) 'Excess authority was not rejected.'
}

Test-Case 'intent verifier rejects mismatched required outcomes' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -OutcomeValue $false)
    Assert-True ('E_INTENT_REQUIRED_OUTCOME'-in@($result.errors.code)) 'Wrong required outcome was not rejected.'
}

Test-Case 'intent verifier rejects observed forbidden outcomes' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -ObservedForbiddenOutcomes @('history.rewrite'))
    Assert-True ('E_INTENT_FORBIDDEN_OUTCOME'-in@($result.errors.code)) 'Forbidden outcome was not rejected.'
}

Test-Case 'intent verifier requires criterion evidence' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -OmitEvidence)
    Assert-True ('E_INTENT_EVIDENCE_MISSING'-in@($result.errors.code)) 'Missing criterion evidence was accepted.'
}

Test-Case 'intent verifier gates material ambiguity' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -MaterialAmbiguity)
    Assert-True ('E_INTENT_AMBIGUITY_UNRESOLVED'-in@($result.errors.code)) 'Unresolved ambiguity was accepted.'
    $resolved=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -MaterialAmbiguity -ResolveAmbiguity)
    Assert-True ([bool]$resolved.satisfied) 'Human-resolved ambiguity was rejected.'
}

Test-Case 'intent verifier requires an independent challenge' {
    $missing=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -OmitChallenge)
    Assert-True ('E_INTENT_CHALLENGE_REQUIRED'-in@($missing.errors.code)) 'Missing challenge was accepted.'
}

Test-Case 'intent verifier rejects self-challenge' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -SameChallenger)
    Assert-True ('E_INTENT_CHALLENGE_INDEPENDENCE'-in@($result.errors.code)) 'Producer self-challenge was accepted.'
}

Test-Case 'intent verifier gates material critic disagreement' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -MaterialChallenge)
    Assert-True ('E_INTENT_CHALLENGE_UNRESOLVED'-in@($result.errors.code)) 'Unresolved critic disagreement was accepted.'
    $resolved=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -MaterialChallenge -ResolveChallenge)
    Assert-True ([bool]$resolved.satisfied) 'Human-resolved critic disagreement was rejected.'
}

Test-Case 'intent verifier catches interpretation omission' {
    $result=Invoke-AriaIntentVerification (New-AriaIntentTestBundle -OmitClaimedObligation)
    Assert-True ('E_INTENT_OBLIGATION_OMITTED'-in@($result.errors.code)) 'Interpretation obligation omission was accepted.'
}

Test-Case 'intent proofs are deterministic and contain derived obligations' {
    $one=Invoke-AriaIntentVerification (New-AriaIntentTestBundle)
    $two=Invoke-AriaIntentVerification (New-AriaIntentTestBundle)
    Assert-Equal $one.proof.id $two.proof.id 'Intent proof identity changed.'
    Assert-Equal '3' ([string]@($one.proof.obligations).Count) 'Derived obligation count mismatch.'
}
# Alpha.22 executable alchemical glyph triad.
Test-Case 'alchemical glyph registry is machine-readable and triadic' {
    $path = Join-Path $root 'grammar/alchemy.json'
    $document = Read-AriaUtf8Text $path | ConvertFrom-Json
    Assert-Equal 'aria.alchemical-syntax' ([string]$document.format) 'Alchemy registry format mismatch.'
    Assert-Equal '3' ([string]@($document.triad).Count) 'Alchemy registry is not triadic.'
    Assert-Equal '🜁' ([string]$document.triad[0].symbol) 'Air glyph mismatch.'
    Assert-Equal '🜂' ([string]$document.triad[1].symbol) 'Fire glyph mismatch.'
    Assert-Equal '🜄' ([string]$document.triad[2].symbol) 'Water glyph mismatch.'
}

Test-Case 'parser lowers executable glyph statements' {
    $source = Get-AriaSourceText -Path (Join-Path $root 'examples/glyph-triad.aria')
    $parsed = Parse-AriaSource -Source $source -SourceName '<glyph-triad>'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $parsed.diagnostics).Count 'Glyph parser emitted errors.'
    $statements = @($parsed.model.flows[0].statements)
    Assert-Equal 'emit' ([string]$statements[1].op) 'Fire did not lower to emit.'
    Assert-Equal 'remember' ([string]$statements[2].op) 'Water did not lower to remember.'
    Assert-Equal 'recall' ([string]$statements[3].op) 'Air recall did not lower correctly.'
    Assert-Equal 'let' ([string]$statements[4].op) 'Air binding did not lower correctly.'
}

Test-Case 'glyph syntax survives compilation and bytecode verification' {
    $gate = Invoke-AriaGate -SourcePath (Join-Path $root 'examples/glyph-triad.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $verification = Test-AriaBytecodeModel -BytecodeModel $gate.bytecode
    Assert-True ([bool]$verification.valid) ('Glyph bytecode failed verification: ' + ($verification.errors -join '; '))
    Assert-True ('EMIT' -in @($gate.bytecode.instructions.op)) 'Fire glyph emitted no EMIT opcode.'
    Assert-True ('MEM_SET' -in @($gate.bytecode.instructions.op)) 'Water glyph emitted no MEM_SET opcode.'
    Assert-True ('MEM_GET' -in @($gate.bytecode.instructions.op)) 'Air recall emitted no MEM_GET opcode.'
}

Test-Case 'glyph triad executes through the existing VM' {
    $compiled = Invoke-AriaCompile -SourcePath (Join-Path $root 'examples/glyph-triad.aria') -PolicyPath $policy -WorkspaceRoot $root -Quiet
    $result = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $policy -WorkspaceRoot $root -PassThru
    Assert-Equal 'ARIA glyph syntax is online.' ([string]$result.outputs[0]) 'Fire text output mismatch.'
    Assert-Equal 'active' ([string]$result.outputs[1]) 'Air recall output mismatch.'
    Assert-Equal '42' ([string]$result.outputs[2]) 'Air binding output mismatch.'
}

Test-Case 'glyph syntax and word syntax lower to equivalent operations' {
    $glyphSource = @(
        'aria 0.4.0'
        'program GlyphEquivalent version 0.1.0'
        'entry Main'
        'memory Project {'
        '  status = "booting"'
        '}'
        'flow Main {'
        '  🜄 Project.status = "active"'
        '  🜁 Project.status -> state: Text'
        '  🜂 state'
        '}'
    ) -join "`n"

    $wordSource = @(
        'aria 0.4.0'
        'program WordEquivalent version 0.1.0'
        'entry Main'
        'memory Project {'
        '  status = "booting"'
        '}'
        'flow Main {'
        '  remember Project.status = "active"'
        '  recall Project.status -> state: Text'
        '  emit state'
        '}'
    ) -join "`n"

    $glyph = Parse-AriaSource -Source $glyphSource -SourceName '<glyph-equivalent>'
    $word = Parse-AriaSource -Source $wordSource -SourceName '<word-equivalent>'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $glyph.diagnostics).Count 'Glyph equivalence source failed.'
    Assert-Equal 0 (Get-AriaErrorDiagnostics -Diagnostics $word.diagnostics).Count 'Word equivalence source failed.'
    Assert-Equal (@($word.model.flows[0].statements.op)) (@($glyph.model.flows[0].statements.op)) 'Glyph and word operations diverged.'
}
$script:SuiteClock.Stop()

if ($script:ObservedTests -ne $expectedTests) {
    throw (
        "ARIA conformance registry divergence: expected {0} test(s), observed {1}." -f `
            $expectedTests,
            $script:ObservedTests
    )
}

$null = Complete-AriaEnumerator -Detail (
    "{0} passed · {1} failed · lane {2}" -f `
        $script:Passed,
        $script:Failed,
        $Lane
)

if ($script:Failed -gt 0) {
    throw "ARIA test suite failed: $script:Failed failure(s)."
}
