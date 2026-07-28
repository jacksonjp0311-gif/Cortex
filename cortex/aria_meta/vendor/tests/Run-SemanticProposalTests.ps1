[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GovernedEvolution.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProposal.psm1') -Force -DisableNameChecking

$script:Passed=0; $script:Failed=0; $script:Expected=20
function Assert-True { param([bool]$Condition,[string]$Message) if(-not$Condition){throw $Message} }
function Assert-Equal { param($Expected,$Actual,[string]$Message) if((ConvertTo-AriaJson $Expected)-ne(ConvertTo-AriaJson $Actual)){throw $Message} }
function Copy-Value { param($Value) $Value|ConvertTo-Json -Depth 100|ConvertFrom-Json }
function Test-Case {
    param([string]$Name,[scriptblock]$Body)
    try { & $Body; $script:Passed++; Write-Host ("◆  {0}"-f$Name) -ForegroundColor Green }
    catch { $script:Failed++; Write-Host ("⬗  {0} · {1}"-f$Name,$_.Exception.Message) -ForegroundColor Magenta }
}
function New-Fixture {
    $before='sha256:'+('1'*64); $after='sha256:'+('2'*64)
    New-AriaSemanticProposal `
        -IntentRef ('sha256:'+('a'*64)) `
        -ProposerId 'agent:codex-producer' `
        -BaseCommit ('b'*40) `
        -Subject ([pscustomobject][ordered]@{kind='semantic-card';id='algorithm.scan';revision='proposed'}) `
        -SemanticDelta ([pscustomobject][ordered]@{
            grammar=@();lowering=@('Scan');types=@('Sequence<T>');effects=@();opcodes=@();policies=@()
            authority=[pscustomobject][ordered]@{expandsAuthority=$false;requiresExplicitAdmission=$true}
        }) `
        -ChangedPaths @([pscustomobject][ordered]@{path='src/Aria.Scan.psm1';operation='write';beforeDigest=$before;afterDigest=$after}) `
        -ProofObligations @([pscustomobject][ordered]@{id='scan.behavior';kind='test';statement='Scan preserves deterministic prefix order.'}) `
        -TestPlan @([pscustomobject][ordered]@{id='scan.lattice';command='aria test';expected='pass'}) `
        -Compatibility ([pscustomobject][ordered]@{classification='compatible';rationale='Adds a new operation without changing existing cards.';migration='none'}) `
        -Rollback @([pscustomobject][ordered]@{path='src/Aria.Scan.psm1';expectedDigest=$after;restoreDigest=$before})
}

Write-Host '⧉  semantic-proposal lattice ×20' -ForegroundColor DarkGray
$proposal=New-Fixture
Test-Case 'schema is machine readable' {
    $schema=Read-AriaUtf8Text (Join-Path $root 'schemas/semantic-proposal.schema.json')|ConvertFrom-Json
    Assert-Equal 'aria.semantic-proposal/1' $schema.properties.schema.const 'Schema identity mismatch.'
}
Test-Case 'factory emits a valid canonical proposal' { Assert-True (Test-AriaSemanticProposal $proposal).valid 'Generated proposal invalid.' }
Test-Case 'identical inputs produce identical identity' { Assert-Equal $proposal.digest (New-Fixture).digest 'Proposal identity drifted.' }
Test-Case 'JSON round trip preserves identity' { Assert-True (Test-AriaSemanticProposal (Copy-Value $proposal)).valid 'Round trip invalid.' }
Test-Case 'proposal is explicitly non executable' { Assert-True (-not(Test-AriaSemanticProposal $proposal).executable) 'Proposal became executable.' }
Test-Case 'proposal carries no authority' {
    Assert-True (-not$proposal.authority.grantsAuthority) 'Proposal grants authority.'
    Assert-Equal 0 @($proposal.authority.capabilitiesGranted).Count 'Proposal carries capabilities.'
}
Test-Case 'embedded approval is rejected' {
    $copy=Copy-Value $proposal; $copy|Add-Member approval ([pscustomobject]@{decision='approved'})
    Assert-True (-not(Test-AriaSemanticProposal $copy).valid) 'Embedded approval verified.'
}
Test-Case 'approval state drift is rejected' {
    $copy=Copy-Value $proposal; $copy.approvalBoundary.state='approved'
    Assert-True ('E_SEMANTIC_PROPOSAL_SELF_APPROVAL'-in@(Test-AriaSemanticProposal $copy).errors) 'Approval drift verified.'
}
Test-Case 'authority claim is rejected' {
    $copy=Copy-Value $proposal; $copy.authority.grantsAuthority=$true
    Assert-True ('E_SEMANTIC_PROPOSAL_AUTHORITY'-in@(Test-AriaSemanticProposal $copy).errors) 'Authority claim verified.'
}
Test-Case 'implicit authority expansion is rejected' {
    $copy=Copy-Value $proposal; $copy.semanticDelta.authority.expandsAuthority=$true; $copy.semanticDelta.authority.requiresExplicitAdmission=$false
    Assert-True ('E_SEMANTIC_PROPOSAL_IMPLICIT_AUTHORITY'-in@(Test-AriaSemanticProposal $copy).errors) 'Implicit expansion verified.'
}
Test-Case 'explicit authority expansion remains unapproved' {
    $copy=Copy-Value $proposal; $copy.semanticDelta.authority.expandsAuthority=$true
    $copy.digest=Get-AriaSemanticProposalDigest $copy
    $result=Test-AriaSemanticProposal $copy
    Assert-True ($result.valid-and-not$result.executable) 'Declared expansion crossed admission boundary.'
}
Test-Case 'unsafe changed path is rejected' {
    $copy=Copy-Value $proposal; $copy.changedPaths[0].path='../secret'
    Assert-True ('E_SEMANTIC_PROPOSAL_PATH'-in@(Test-AriaSemanticProposal $copy).errors) 'Traversal path verified.'
}
Test-Case 'duplicate changed path is rejected' {
    $copy=Copy-Value $proposal; $copy.changedPaths=@($copy.changedPaths[0],$copy.changedPaths[0])
    Assert-True ('E_SEMANTIC_PROPOSAL_PATH_DUPLICATE'-in@(Test-AriaSemanticProposal $copy).errors) 'Duplicate path verified.'
}
Test-Case 'no-op change is rejected' {
    $copy=Copy-Value $proposal; $copy.changedPaths[0].afterDigest=$copy.changedPaths[0].beforeDigest
    Assert-True ('E_SEMANTIC_PROPOSAL_CHANGE'-in@(Test-AriaSemanticProposal $copy).errors) 'No-op verified.'
}
Test-Case 'missing rollback is rejected' {
    $copy=Copy-Value $proposal; $copy.rollback=@()
    Assert-True ('E_SEMANTIC_PROPOSAL_ROLLBACK_SCOPE'-in@(Test-AriaSemanticProposal $copy).errors) 'Missing rollback verified.'
}
Test-Case 'asymmetric rollback is rejected' {
    $copy=Copy-Value $proposal; $copy.rollback[0].restoreDigest='sha256:'+('3'*64)
    Assert-True ('E_SEMANTIC_PROPOSAL_ROLLBACK'-in@(Test-AriaSemanticProposal $copy).errors) 'Asymmetric rollback verified.'
}
Test-Case 'missing semantic dimension is rejected' {
    $copy=Copy-Value $proposal; $copy.semanticDelta.PSObject.Properties.Remove('opcodes')
    Assert-True ('E_SEMANTIC_PROPOSAL_DELTA'-in@(Test-AriaSemanticProposal $copy).errors) 'Incomplete delta verified.'
}
Test-Case 'empty obligations are rejected' {
    $copy=Copy-Value $proposal; $copy.proofObligations=@()
    Assert-True ('E_SEMANTIC_PROPOSAL_OBLIGATIONS'-in@(Test-AriaSemanticProposal $copy).errors) 'Empty obligations verified.'
}
Test-Case 'malformed execution evidence reference is rejected' {
    $copy=Copy-Value $proposal
    $copy.executionEvidenceRefs=@([pscustomobject]@{digest='invented';cardId='algorithm.map';artifactHash='invented'})
    Assert-True ('E_SEMANTIC_PROPOSAL_EVIDENCE_REF'-in@(Test-AriaSemanticProposal $copy).errors) 'Malformed evidence verified.'
}
Test-Case 'tampered proposal digest is rejected' {
    $copy=Copy-Value $proposal; $copy.subject.id='algorithm.changed'
    Assert-True ('E_SEMANTIC_PROPOSAL_DIGEST'-in@(Test-AriaSemanticProposal $copy).errors) 'Tampered proposal verified.'
}
if(($script:Passed+$script:Failed)-ne$script:Expected){throw 'Semantic proposal test count diverged.'}
Write-Host ("⧉  semantic-proposal lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'})) -ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Failed){throw "Semantic proposal lattice failed: $script:Failed failure(s)."}
