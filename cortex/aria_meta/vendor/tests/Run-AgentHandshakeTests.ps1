Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.AgentHandshake.psm1') -Force -DisableNameChecking

$script:Passed = 0
$script:Failed = 0
$script:Expected = 8

function Test-HandshakeCase {
    param([string]$Name, [scriptblock]$Body)
    try {
        & $Body
        $script:Passed++
        Write-Host ("◆  {0}" -f $Name) -ForegroundColor Green
    }
    catch {
        $script:Failed++
        Write-Host ("⬗  {0} · {1}" -f $Name, $_.Exception.Message) -ForegroundColor Magenta
    }
}

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ((ConvertTo-AriaJson ([pscustomobject][ordered]@{ value = $Expected })) -cne
        (ConvertTo-AriaJson ([pscustomobject][ordered]@{ value = $Actual }))) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

Test-HandshakeCase 'agent connection contract validates' {
    $contract = Get-AriaAgentContract -RepositoryRoot $root
    $validation = Test-AriaAgentContract -Contract $contract
    Assert-True $validation.valid (@($validation.errors) -join ', ')
}

Test-HandshakeCase 'semantic synchronization phases are ordered' {
    $contract = Get-AriaAgentContract -RepositoryRoot $root
    Assert-Equal @('discover','orient','verify','align','propose') @($contract.phases.id) 'Synchronization phase order changed.'
}

Test-HandshakeCase 'shared vocabulary is unique and bounded' {
    $contract = Get-AriaAgentContract -RepositoryRoot $root
    $terms = @($contract.vocabulary.term)
    Assert-True ($terms.Count -ge 8) 'Shared vocabulary is incomplete.'
    Assert-Equal $terms.Count @($terms | Sort-Object -Unique).Count 'Shared vocabulary contains duplicate terms.'
}

Test-HandshakeCase 'initial connection grants no authority' {
    $contract = Get-AriaAgentContract -RepositoryRoot $root
    Assert-Equal 'none' ([string]$contract.authority.initial) 'Initial authority changed.'
    Assert-True (-not [bool]$contract.authority.proposalGrantsAuthority) 'Proposal granted authority.'
    Assert-True (-not [bool]$contract.authority.interpretationSelfApproves) 'Interpretation self-approved.'
}

Test-HandshakeCase 'agent handshake identity is deterministic' {
    $left = Get-AriaAgentHandshake -RepositoryRoot $root
    $right = Get-AriaAgentHandshake -RepositoryRoot $root
    Assert-Equal ([string]$left.digest) ([string]$right.digest) 'Handshake identity changed for the same repository state.'
    Assert-Equal (ConvertTo-AriaJson $left) (ConvertTo-AriaJson $right) 'Handshake bytes are not canonical.'
}

Test-HandshakeCase 'handshake binds all discovery resources' {
    $handshake = Get-AriaAgentHandshake -RepositoryRoot $root
    $validation = Test-AriaAgentHandshake -Handshake $handshake -RepositoryRoot $root
    Assert-True $validation.valid (@($validation.errors) -join ', ')
    Assert-Equal @('ARIA-CONNECT.json','ARIA-RUNTIME.json','AGENTS.md','MANIFEST.sha256') @($handshake.contract.path,$handshake.runtime.path,$handshake.guide.path,$handshake.manifest.path) 'Handshake resource order changed.'
    Assert-Equal @('discover','orient','verify','align','propose') @($handshake.synchronization.phases.id) 'Handshake did not carry synchronization semantics.'
    Assert-True (@($handshake.synchronization.vocabulary).Count -ge 8) 'Handshake did not carry the shared vocabulary.'
    Assert-Equal @('alpha.14','alpha.15','alpha.16','alpha.17','alpha.18') @($handshake.synchronization.continuity.milestone) 'Handshake did not carry the continuity ladder.'
}

Test-HandshakeCase 'handshake rejects tampered identity' {
    $handshake = Get-AriaAgentHandshake -RepositoryRoot $root
    $tampered = $handshake | ConvertTo-Json -Depth 20 -Compress | ConvertFrom-Json
    $tampered.session.phase = 'proposed'
    $validation = Test-AriaAgentHandshake -Handshake $tampered -RepositoryRoot $root
    Assert-True (-not $validation.valid) 'Tampered handshake was accepted.'
    Assert-True ('E_AGENT_HANDSHAKE_DIGEST' -in @($validation.errors)) 'Tampered handshake did not fracture its digest.'
}

Test-HandshakeCase 'handshake projects actual manifest state' {
    $manifest = Test-AriaManifest -Root $root
    $handshake = Get-AriaAgentHandshake -RepositoryRoot $root
    Assert-Equal ([bool]$manifest.valid) ([bool]$handshake.baseline.manifestValid) 'Manifest validity projection changed.'
    Assert-Equal ([int]$manifest.actual) ([int]$handshake.baseline.verifiedFiles) 'Verified file count projection changed.'
    Assert-Equal $(if ($manifest.valid) { 'ready' } else { 'degraded' }) ([string]$handshake.status) 'Handshake readiness is not derived from manifest state.'
}

Write-Host ("⧉  agent-handshake lattice {0}/{1} · {2}" -f $script:Passed, $script:Expected, $(if ($script:Failed) { 'fractured' } else { 'coherent' })) -ForegroundColor $(if ($script:Failed) { 'Magenta' } else { 'Green' })
if ($script:Passed + $script:Failed -ne $script:Expected) { throw 'Agent handshake test count diverged.' }
if ($script:Failed -gt 0) { throw "Agent handshake lattice failed: $script:Failed failure(s)." }
