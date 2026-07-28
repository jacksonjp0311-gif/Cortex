[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
$root=Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GovernedEvolution.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProposal.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Admission.psm1') -Force -DisableNameChecking

$script:Passed=0;$script:Failed=0;$script:Expected=24
function Assert-True { param([bool]$Condition,[string]$Message) if(-not$Condition){throw $Message} }
function Assert-Equal { param($Expected,$Actual,[string]$Message) if((ConvertTo-AriaJson $Expected)-ne(ConvertTo-AriaJson $Actual)){throw $Message} }
function Copy-Value { param($Value) $Value|ConvertTo-Json -Depth 100|ConvertFrom-Json }
function Test-Case {
    param([string]$Name,[scriptblock]$Body)
    try{&$Body;$script:Passed++;Write-Host("◆  {0}"-f$Name)-ForegroundColor Green}
    catch{$script:Failed++;Write-Host("⬗  {0} · {1}"-f$Name,$_.Exception.Message)-ForegroundColor Magenta}
}
function New-ProposalFixture {
    $before='sha256:'+('1'*64);$after='sha256:'+('2'*64)
    New-AriaSemanticProposal `
        -IntentRef ('sha256:'+('a'*64)) -ProposerId agent:producer -BaseCommit ('b'*40) `
        -Subject ([pscustomobject][ordered]@{kind='semantic-card';id='algorithm.scan'}) `
        -SemanticDelta ([pscustomobject][ordered]@{
            grammar=@();lowering=@('Scan');types=@('Sequence<T>');effects=@();opcodes=@();policies=@()
            authority=[pscustomobject][ordered]@{expandsAuthority=$false;requiresExplicitAdmission=$true}
        }) `
        -ChangedPaths @([pscustomobject][ordered]@{path='src/Aria.Scan.psm1';operation='write';beforeDigest=$before;afterDigest=$after}) `
        -ProofObligations @([pscustomobject][ordered]@{id='scan.behavior';kind='test'}) `
        -TestPlan @([pscustomobject][ordered]@{id='scan.lattice';command='aria test'}) `
        -Compatibility ([pscustomobject][ordered]@{classification='compatible';rationale='Additive operation.';migration='none'}) `
        -Rollback @([pscustomobject][ordered]@{path='src/Aria.Scan.psm1';expectedDigest=$after;restoreDigest=$before})
}

$proposal=New-ProposalFixture
$consent=New-AriaSemanticConsent -Proposal $proposal -ApproverId human:jackson -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce alpha12-test
$trusted=@('human:jackson')
$receipt=New-AriaAdmissionReceipt -Proposal $proposal -Consent $consent -CurrentCommit $proposal.baseline.commit -TrustedApprovers $trusted

Write-Host '⧉  consent-admission lattice ×24' -ForegroundColor DarkGray
Test-Case 'consent schema is machine readable' {
    $schema=Read-AriaUtf8Text (Join-Path $root 'schemas/semantic-consent.schema.json')|ConvertFrom-Json
    Assert-Equal 'aria.semantic-consent/1' $schema.properties.schema.const 'Consent schema mismatch.'
}
Test-Case 'admission schema is machine readable' {
    $schema=Read-AriaUtf8Text (Join-Path $root 'schemas/admission-receipt.schema.json')|ConvertFrom-Json
    Assert-Equal 'aria.admission-receipt/1' $schema.properties.schema.const 'Admission schema mismatch.'
}
Test-Case 'scope digest is deterministic' { Assert-Equal (Get-AriaSemanticScopeDigest $proposal) (Get-AriaSemanticScopeDigest (Copy-Value $proposal)) 'Scope drifted.' }
Test-Case 'consent is content addressed and valid' { Assert-True (Test-AriaSemanticConsent $consent $proposal $trusted).valid 'Consent invalid.' }
Test-Case 'identical consent inputs produce identical identity' {
    $copy=New-AriaSemanticConsent -Proposal $proposal -ApproverId human:jackson -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce alpha12-test
    Assert-Equal $consent.digest $copy.digest 'Consent identity drifted.'
    $materialized=Copy-Value $consent
    Assert-Equal $consent.digest (Get-AriaSemanticConsentDigest $materialized) 'Consent identity drifted across JSON materialization.'
}
Test-Case 'proposer cannot approve own proposal' {
    $copy=New-AriaSemanticConsent -Proposal $proposal -ApproverId agent:producer -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce self
    Assert-True ('E_CONSENT_IDENTITY_SEPARATION'-in@(Test-AriaSemanticConsent $copy $proposal @('agent:producer')).errors) 'Self approval verified.'
}
Test-Case 'untrusted approver is rejected' {
    $copy=New-AriaSemanticConsent -Proposal $proposal -ApproverId human:unknown -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce unknown
    Assert-True ('E_CONSENT_APPROVER_UNTRUSTED'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Untrusted approval verified.'
}
Test-Case 'proposal identity drift is rejected' {
    $copy=Copy-Value $proposal;$copy.digest='sha256:'+('9'*64)
    Assert-True ('E_CONSENT_PROPOSAL_DRIFT'-in@(Test-AriaSemanticConsent $consent $copy $trusted).errors) 'Proposal drift verified.'
}
Test-Case 'scope drift is rejected' {
    $copy=Copy-Value $consent;$copy.scopeDigest='sha256:'+('8'*64);$copy.digest=Get-AriaSemanticConsentDigest $copy
    Assert-True ('E_CONSENT_PROPOSAL_DRIFT'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Scope drift verified.'
}
Test-Case 'withheld consent remains valid evidence but rejects admission' {
    $denied=New-AriaSemanticConsent -Proposal $proposal -ApproverId human:jackson -Decision rejected -DecidedAt '2026-07-27T21:00:00Z' -Nonce denied
    Assert-True (Test-AriaSemanticConsent $denied $proposal $trusted).valid 'Rejection evidence invalid.'
    Assert-Equal 'rejected' (New-AriaAdmissionReceipt $proposal $denied $proposal.baseline.commit $trusted).verdict 'Withheld consent admitted.'
}
Test-Case 'invalid decision time is rejected' {
    $copy=Copy-Value $consent;$copy.decidedAt='not-time'
    Assert-True ('E_CONSENT_TIME'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Invalid time verified.'
}
Test-Case 'missing scope acknowledgement is rejected' {
    $copy=Copy-Value $consent;$copy.acknowledgements.scopeReviewed=$false;$copy.digest=Get-AriaSemanticConsentDigest $copy
    Assert-True ('E_CONSENT_ACKNOWLEDGEMENT'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Missing acknowledgement verified.'
}
Test-Case 'authority expansion requires explicit acknowledgement' {
    $expanded=Copy-Value $proposal;$expanded.semanticDelta.authority.expandsAuthority=$true;$expanded.digest=Get-AriaSemanticProposalDigest $expanded
    $copy=New-AriaSemanticConsent -Proposal $expanded -ApproverId human:jackson -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce expansion
    Assert-True ('E_CONSENT_AUTHORITY_EXPANSION'-in@(Test-AriaSemanticConsent $copy $expanded $trusted).errors) 'Unacknowledged expansion verified.'
}
Test-Case 'acknowledged authority expansion remains capability free' {
    $expanded=Copy-Value $proposal;$expanded.semanticDelta.authority.expandsAuthority=$true;$expanded.digest=Get-AriaSemanticProposalDigest $expanded
    $copy=New-AriaSemanticConsent -Proposal $expanded -ApproverId human:jackson -Decision approved -DecidedAt '2026-07-27T21:00:00Z' -Nonce expansion-ok -AuthorityExpansionReviewed $true
    $result=New-AriaAdmissionReceipt $expanded $copy $expanded.baseline.commit $trusted
    Assert-True ($result.eligibleForEvolutionPlanning-and-not$result.authority.grantsRepositoryAuthority) 'Expansion granted repository authority.'
}
Test-Case 'reserved signature tampering is rejected' {
    $copy=Copy-Value $consent;$copy.signature.algorithm='invented';$copy.digest=Get-AriaSemanticConsentDigest $copy
    Assert-True ('E_CONSENT_SIGNATURE'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Signature tamper verified.'
}
Test-Case 'consent digest tampering is rejected' {
    $copy=Copy-Value $consent;$copy.nonce='changed'
    Assert-True ('E_CONSENT_DIGEST'-in@(Test-AriaSemanticConsent $copy $proposal $trusted).errors) 'Consent tamper verified.'
}
Test-Case 'approved exact bundle is admitted' { Assert-Equal 'admitted' $receipt.verdict 'Exact bundle rejected.' }
Test-Case 'admission evaluates eight explicit obligations' {
    Assert-Equal 8 @($receipt.obligations).Count 'Obligation count mismatch.'
    Assert-Equal 0 @($receipt.obligations|Where-Object{-not$_.passed}).Count 'Admission obligation failed.'
}
Test-Case 'admission receipt is deterministic' {
    $again=New-AriaAdmissionReceipt $proposal $consent $proposal.baseline.commit $trusted
    Assert-Equal $receipt.digest $again.digest 'Admission identity drifted.'
}
Test-Case 'admission receipt grants no repository authority' {
    Assert-True (-not$receipt.authority.grantsRepositoryAuthority) 'Receipt grants authority.'
    Assert-Equal 0 @($receipt.authority.capabilitiesGranted).Count 'Receipt carries capabilities.'
}
Test-Case 'baseline drift rejects admission' {
    $result=New-AriaAdmissionReceipt $proposal $consent ('c'*40) $trusted
    Assert-Equal 'rejected' $result.verdict 'Stale baseline admitted.'
}
Test-Case 'tampered proposal invalidates existing receipt' {
    $copy=Copy-Value $proposal;$copy.subject.id='algorithm.changed'
    Assert-True (-not(Test-AriaAdmissionReceipt $receipt $copy $consent $proposal.baseline.commit $trusted).valid) 'Receipt survived proposal tamper.'
}
Test-Case 'tampered receipt is rejected' {
    $copy=Copy-Value $receipt;$copy.nextBoundary='none'
    Assert-True (-not(Test-AriaAdmissionReceipt $copy $proposal $consent $proposal.baseline.commit $trusted).valid) 'Receipt tamper verified.'
}
Test-Case 'admission is non mutating and stops at evolution planning' {
    Assert-Equal 'evolution-planning' $receipt.nextBoundary 'Wrong next boundary.'
    Assert-True (-not$receipt.authority.grantsRepositoryAuthority) 'Admission mutated authority.'
}
if(($script:Passed+$script:Failed)-ne$script:Expected){throw 'Admission test count diverged.'}
Write-Host("⧉  consent-admission lattice {0}/{1} · {2}"-f$script:Passed,$script:Expected,$(if($script:Failed){'fractured'}else{'coherent'}))-ForegroundColor $(if($script:Failed){'Magenta'}else{'Green'})
if($script:Failed){throw "Consent-admission lattice failed: $script:Failed failure(s)."}
