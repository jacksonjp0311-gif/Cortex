Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSha256Text -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command Test-AriaSemanticProposal -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.SemanticProposal.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command ConvertTo-AriaUtcTimestamp -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.CapabilityAuthority.psm1') -Force -DisableNameChecking
}

function Get-AriaAdmissionProperty {
    param($Object,[string]$Name,$Default=$null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $Default
    }
    $property=$Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $Default }
    $property.Value
}

function Get-AriaSemanticScopeDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Proposal)
    $scope=[pscustomobject][ordered]@{
        proposalDigest=[string](Get-AriaAdmissionProperty $Proposal digest)
        changedPaths=@((Get-AriaAdmissionProperty $Proposal changedPaths @()) | Sort-Object path)
        rollback=@((Get-AriaAdmissionProperty $Proposal rollback @()) | Sort-Object path)
    }
    'sha256:'+(Get-AriaSha256Text (ConvertTo-AriaJson $scope))
}

function ConvertTo-AriaAdmissionTimestamp {
    param($Value)
    if ($Value -is [datetime]) {
        return ([datetime]$Value).ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
    }
    ConvertTo-AriaUtcTimestamp ([string]$Value)
}

function Get-AriaSemanticConsentBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Consent)
    [pscustomobject][ordered]@{
        schema=[string](Get-AriaAdmissionProperty $Consent schema)
        proposalDigest=[string](Get-AriaAdmissionProperty $Consent proposalDigest)
        intentRef=[string](Get-AriaAdmissionProperty $Consent intentRef)
        scopeDigest=[string](Get-AriaAdmissionProperty $Consent scopeDigest)
        proposerId=[string](Get-AriaAdmissionProperty $Consent proposerId)
        approverId=[string](Get-AriaAdmissionProperty $Consent approverId)
        decision=[string](Get-AriaAdmissionProperty $Consent decision)
        decidedAt=ConvertTo-AriaAdmissionTimestamp (Get-AriaAdmissionProperty $Consent decidedAt)
        acknowledgements=Get-AriaAdmissionProperty $Consent acknowledgements
        nonce=[string](Get-AriaAdmissionProperty $Consent nonce)
        signature=Get-AriaAdmissionProperty $Consent signature
    }
}

function Get-AriaSemanticConsentDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Consent)
    'sha256:'+(Get-AriaSha256Text (ConvertTo-AriaJson (Get-AriaSemanticConsentBody $Consent)))
}

function New-AriaSemanticConsent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Proposal,
        [Parameter(Mandatory=$true)][string]$ApproverId,
        [Parameter(Mandatory=$true)][ValidateSet('approved','rejected')][string]$Decision,
        [Parameter(Mandatory=$true)][string]$DecidedAt,
        [Parameter(Mandatory=$true)][string]$Nonce,
        [bool]$AuthorityExpansionReviewed=$false
    )
    $consent=[pscustomobject][ordered]@{
        schema='aria.semantic-consent/1'
        proposalDigest=[string]$Proposal.digest
        intentRef=[string]$Proposal.intentRef
        scopeDigest=Get-AriaSemanticScopeDigest $Proposal
        proposerId=[string]$Proposal.proposer.id
        approverId=$ApproverId
        decision=$Decision
        decidedAt=ConvertTo-AriaUtcTimestamp $DecidedAt
        acknowledgements=[pscustomobject][ordered]@{
            proposalIsNotAuthority=$true
            scopeReviewed=$true
            rollbackReviewed=$true
            authorityExpansionReviewed=$AuthorityExpansionReviewed
        }
        nonce=$Nonce
        signature=[pscustomobject][ordered]@{algorithm='none';value=''}
        digest=''
    }
    $consent.digest=Get-AriaSemanticConsentDigest $consent
    $consent
}

function Test-AriaSemanticConsent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Consent,
        [Parameter(Mandatory=$true)]$Proposal,
        [string[]]$TrustedApprovers=@()
    )
    $errors=New-Object System.Collections.Generic.List[string]
    if ([string](Get-AriaAdmissionProperty $Consent schema) -ne 'aria.semantic-consent/1') { $errors.Add('E_CONSENT_SCHEMA') }
    if ([string](Get-AriaAdmissionProperty $Consent proposalDigest) -ne [string]$Proposal.digest -or
        [string](Get-AriaAdmissionProperty $Consent intentRef) -ne [string]$Proposal.intentRef -or
        [string](Get-AriaAdmissionProperty $Consent scopeDigest) -ne (Get-AriaSemanticScopeDigest $Proposal)) {
        $errors.Add('E_CONSENT_PROPOSAL_DRIFT')
    }
    $proposalProposer=Get-AriaAdmissionProperty $Proposal proposer
    $proposer=[string](Get-AriaAdmissionProperty $proposalProposer id)
    $approver=[string](Get-AriaAdmissionProperty $Consent approverId)
    if ([string](Get-AriaAdmissionProperty $Consent proposerId) -ne $proposer -or
        [string]::IsNullOrWhiteSpace($approver) -or $approver -eq $proposer) {
        $errors.Add('E_CONSENT_IDENTITY_SEPARATION')
    }
    if ($TrustedApprovers.Count -gt 0 -and $approver -notin $TrustedApprovers) { $errors.Add('E_CONSENT_APPROVER_UNTRUSTED') }
    if ([string](Get-AriaAdmissionProperty $Consent decision) -notin @('approved','rejected')) { $errors.Add('E_CONSENT_DECISION') }
    try {
        $rawTime=Get-AriaAdmissionProperty $Consent decidedAt
        $canonicalTime=ConvertTo-AriaAdmissionTimestamp $rawTime
        if ($rawTime -isnot [datetime] -and $canonicalTime -ne [string]$rawTime) { $errors.Add('E_CONSENT_TIME') }
    }
    catch { $errors.Add('E_CONSENT_TIME') }
    if ([string]::IsNullOrWhiteSpace([string](Get-AriaAdmissionProperty $Consent nonce))) { $errors.Add('E_CONSENT_NONCE') }
    $ack=Get-AriaAdmissionProperty $Consent acknowledgements
    if (-not [bool](Get-AriaAdmissionProperty $ack proposalIsNotAuthority) -or
        -not [bool](Get-AriaAdmissionProperty $ack scopeReviewed) -or
        -not [bool](Get-AriaAdmissionProperty $ack rollbackReviewed)) {
        $errors.Add('E_CONSENT_ACKNOWLEDGEMENT')
    }
    $proposalDelta=Get-AriaAdmissionProperty $Proposal semanticDelta
    $proposalAuthority=Get-AriaAdmissionProperty $proposalDelta authority
    $expands=[bool](Get-AriaAdmissionProperty $proposalAuthority expandsAuthority)
    if ($expands -and -not [bool](Get-AriaAdmissionProperty $ack authorityExpansionReviewed)) {
        $errors.Add('E_CONSENT_AUTHORITY_EXPANSION')
    }
    $signature=Get-AriaAdmissionProperty $Consent signature
    if ([string](Get-AriaAdmissionProperty $signature algorithm) -ne 'none' -or
        -not [string]::IsNullOrEmpty([string](Get-AriaAdmissionProperty $signature value))) {
        $errors.Add('E_CONSENT_SIGNATURE')
    }
    $expected=''
    try { $expected=Get-AriaSemanticConsentDigest $Consent }
    catch { $errors.Add('E_CONSENT_DIGEST_CALCULATION') }
    if ($expected -and [string](Get-AriaAdmissionProperty $Consent digest) -ne $expected) { $errors.Add('E_CONSENT_DIGEST') }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray()|Sort-Object -Unique);digest=$expected}
}

function Get-AriaAdmissionReceiptBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Receipt)
    [pscustomobject][ordered]@{
        schema=[string](Get-AriaAdmissionProperty $Receipt schema)
        proposalDigest=[string](Get-AriaAdmissionProperty $Receipt proposalDigest)
        consentDigest=[string](Get-AriaAdmissionProperty $Receipt consentDigest)
        baselineCommit=[string](Get-AriaAdmissionProperty $Receipt baselineCommit)
        scopeDigest=[string](Get-AriaAdmissionProperty $Receipt scopeDigest)
        verifier=Get-AriaAdmissionProperty $Receipt verifier
        verdict=[string](Get-AriaAdmissionProperty $Receipt verdict)
        obligations=@((Get-AriaAdmissionProperty $Receipt obligations @()))
        eligibleForEvolutionPlanning=[bool](Get-AriaAdmissionProperty $Receipt eligibleForEvolutionPlanning)
        nextBoundary=[string](Get-AriaAdmissionProperty $Receipt nextBoundary)
        authority=Get-AriaAdmissionProperty $Receipt authority
    }
}

function Get-AriaAdmissionReceiptDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Receipt)
    'sha256:'+(Get-AriaSha256Text (ConvertTo-AriaJson (Get-AriaAdmissionReceiptBody $Receipt)))
}

function New-AriaAdmissionReceipt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Proposal,
        [Parameter(Mandatory=$true)]$Consent,
        [Parameter(Mandatory=$true)][string]$CurrentCommit,
        [Parameter(Mandatory=$true)][string[]]$TrustedApprovers
    )
    $proposalResult=Test-AriaSemanticProposal $Proposal
    $consentResult=Test-AriaSemanticConsent -Consent $Consent -Proposal $Proposal -TrustedApprovers $TrustedApprovers
    $proposalBaseline=Get-AriaAdmissionProperty $Proposal baseline
    $proposalProposer=Get-AriaAdmissionProperty $Proposal proposer
    $proposalDelta=Get-AriaAdmissionProperty $Proposal semanticDelta
    $proposalAuthority=Get-AriaAdmissionProperty $proposalDelta authority
    $consentAcknowledgements=Get-AriaAdmissionProperty $Consent acknowledgements
    $baselineMatches=([string](Get-AriaAdmissionProperty $proposalBaseline commit) -eq $CurrentCommit.ToLowerInvariant())
    $approved=([string](Get-AriaAdmissionProperty $Consent decision) -eq 'approved')
    $checks=[ordered]@{
        'proposal.identity'=[bool]$proposalResult.valid
        'consent.identity'=[bool]$consentResult.valid
        'consent.approved'=$approved
        'identity.separated'=([string](Get-AriaAdmissionProperty $proposalProposer id) -ne [string](Get-AriaAdmissionProperty $Consent approverId))
        'baseline.current'=$baselineMatches
        'scope.bound'=([string]$Consent.scopeDigest -eq (Get-AriaSemanticScopeDigest $Proposal))
        'rollback.verified'=(-not ('E_SEMANTIC_PROPOSAL_ROLLBACK' -in @($proposalResult.errors)) -and -not ('E_SEMANTIC_PROPOSAL_ROLLBACK_SCOPE' -in @($proposalResult.errors)))
        'authority.explicit'=(-not [bool](Get-AriaAdmissionProperty $proposalAuthority expandsAuthority) -or [bool](Get-AriaAdmissionProperty $consentAcknowledgements authorityExpansionReviewed))
    }
    $obligations=New-Object System.Collections.Generic.List[object]
    foreach ($id in @($checks.Keys|Sort-Object)) {
        [void]$obligations.Add([pscustomobject][ordered]@{id=$id;passed=[bool]$checks[$id]})
    }
    $admitted=(@($checks.Values|Where-Object{-not[bool]$_}).Count-eq0)
    $receipt=[pscustomobject][ordered]@{
        schema='aria.admission-receipt/1'
        proposalDigest=[string](Get-AriaAdmissionProperty $Proposal digest)
        consentDigest=[string](Get-AriaAdmissionProperty $Consent digest)
        baselineCommit=$CurrentCommit.ToLowerInvariant()
        scopeDigest=Get-AriaSemanticScopeDigest $Proposal
        verifier=[pscustomobject][ordered]@{id='aria.admission-verifier';version=1}
        verdict=$(if($admitted){'admitted'}else{'rejected'})
        obligations=@($obligations.ToArray())
        eligibleForEvolutionPlanning=$admitted
        nextBoundary=$(if($admitted){'evolution-planning'}else{'none'})
        authority=[pscustomobject][ordered]@{
            class='admission-evidence'
            grantsRepositoryAuthority=$false
            capabilitiesGranted=@()
        }
        digest=''
    }
    $receipt.digest=Get-AriaAdmissionReceiptDigest $receipt
    $receipt
}

function Test-AriaAdmissionReceipt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Receipt,
        [Parameter(Mandatory=$true)]$Proposal,
        [Parameter(Mandatory=$true)]$Consent,
        [Parameter(Mandatory=$true)][string]$CurrentCommit,
        [Parameter(Mandatory=$true)][string[]]$TrustedApprovers
    )
    $errors=New-Object System.Collections.Generic.List[string]
    if ([string](Get-AriaAdmissionProperty $Receipt schema) -ne 'aria.admission-receipt/1') { $errors.Add('E_ADMISSION_SCHEMA') }
    $expected=New-AriaAdmissionReceipt -Proposal $Proposal -Consent $Consent -CurrentCommit $CurrentCommit -TrustedApprovers $TrustedApprovers
    if ((ConvertTo-AriaJson (Get-AriaAdmissionReceiptBody $Receipt)) -ne
        (ConvertTo-AriaJson (Get-AriaAdmissionReceiptBody $expected))) { $errors.Add('E_ADMISSION_RECONSTRUCTION') }
    $digest=''
    try { $digest=Get-AriaAdmissionReceiptDigest $Receipt }
    catch { $errors.Add('E_ADMISSION_DIGEST_CALCULATION') }
    if ($digest -and [string](Get-AriaAdmissionProperty $Receipt digest) -ne $digest) { $errors.Add('E_ADMISSION_DIGEST') }
    $authority=Get-AriaAdmissionProperty $Receipt authority
    if ([string](Get-AriaAdmissionProperty $authority class) -ne 'admission-evidence' -or
        [bool](Get-AriaAdmissionProperty $authority grantsRepositoryAuthority) -or
        @((Get-AriaAdmissionProperty $authority capabilitiesGranted @())).Count) {
        $errors.Add('E_ADMISSION_AUTHORITY')
    }
    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray()|Sort-Object -Unique)
        digest=$digest
        admitted=([string](Get-AriaAdmissionProperty $Receipt verdict)-eq'admitted')
    }
}

function Invoke-AriaAdmissionBundleFile {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Admission bundle not found: $Path" }
    $bundle=Read-AriaUtf8Text $Path|ConvertFrom-Json
    New-AriaAdmissionReceipt -Proposal $bundle.proposal -Consent $bundle.consent -CurrentCommit $bundle.currentCommit -TrustedApprovers @($bundle.trustedApprovers)
}

function Invoke-AriaSemanticConsentFile {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Consent request not found: $Path" }
    $request=Read-AriaUtf8Text $Path|ConvertFrom-Json
    New-AriaSemanticConsent `
        -Proposal $request.proposal `
        -ApproverId ([string]$request.approverId) `
        -Decision ([string]$request.decision) `
        -DecidedAt ([string]$request.decidedAt) `
        -Nonce ([string]$request.nonce) `
        -AuthorityExpansionReviewed ([bool]$request.authorityExpansionReviewed)
}

Export-ModuleMember -Function `
    Get-AriaSemanticScopeDigest, `
    Get-AriaSemanticConsentBody, `
    Get-AriaSemanticConsentDigest, `
    New-AriaSemanticConsent, `
    Test-AriaSemanticConsent, `
    Get-AriaAdmissionReceiptBody, `
    Get-AriaAdmissionReceiptDigest, `
    New-AriaAdmissionReceipt, `
    Test-AriaAdmissionReceipt, `
    Invoke-AriaSemanticConsentFile, `
    Invoke-AriaAdmissionBundleFile
