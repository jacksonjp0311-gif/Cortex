Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSha256Text -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command Test-AriaEvolutionPath -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.GovernedEvolution.psm1') -Force -DisableNameChecking
}
if ($null -eq (Get-Command Test-AriaCardExecutionEvidence -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.ExecutionEvidence.psm1') -Force -DisableNameChecking
}

function Get-AriaSemanticProposalProperty {
    param($Object,[string]$Name,$Default=$null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $Default
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $Default }
    $property.Value
}

function Get-AriaSemanticProposalBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Proposal)
    [pscustomobject][ordered]@{
        schema = [string](Get-AriaSemanticProposalProperty $Proposal schema)
        intentRef = [string](Get-AriaSemanticProposalProperty $Proposal intentRef)
        proposer = Get-AriaSemanticProposalProperty $Proposal proposer
        baseline = Get-AriaSemanticProposalProperty $Proposal baseline
        subject = Get-AriaSemanticProposalProperty $Proposal subject
        semanticDelta = Get-AriaSemanticProposalProperty $Proposal semanticDelta
        changedPaths = @((Get-AriaSemanticProposalProperty $Proposal changedPaths @()))
        proofObligations = @((Get-AriaSemanticProposalProperty $Proposal proofObligations @()))
        testPlan = @((Get-AriaSemanticProposalProperty $Proposal testPlan @()))
        compatibility = Get-AriaSemanticProposalProperty $Proposal compatibility
        rollback = @((Get-AriaSemanticProposalProperty $Proposal rollback @()))
        executionEvidenceRefs = @((Get-AriaSemanticProposalProperty $Proposal executionEvidenceRefs @()))
        approvalBoundary = Get-AriaSemanticProposalProperty $Proposal approvalBoundary
        authority = Get-AriaSemanticProposalProperty $Proposal authority
    }
}

function Get-AriaSemanticProposalDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Proposal)
    'sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson (Get-AriaSemanticProposalBody $Proposal)))
}

function New-AriaSemanticProposal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$IntentRef,
        [Parameter(Mandatory=$true)][string]$ProposerId,
        [Parameter(Mandatory=$true)][string]$BaseCommit,
        [Parameter(Mandatory=$true)]$Subject,
        [Parameter(Mandatory=$true)]$SemanticDelta,
        [Parameter(Mandatory=$true)][object[]]$ChangedPaths,
        [Parameter(Mandatory=$true)][object[]]$ProofObligations,
        [Parameter(Mandatory=$true)][object[]]$TestPlan,
        [Parameter(Mandatory=$true)]$Compatibility,
        [Parameter(Mandatory=$true)][object[]]$Rollback,
        [object[]]$ExecutionEvidenceRefs=@()
    )
    $proposal = [pscustomobject][ordered]@{
        schema = 'aria.semantic-proposal/1'
        intentRef = $IntentRef
        proposer = [pscustomobject][ordered]@{ id=$ProposerId; role='producer' }
        baseline = [pscustomobject][ordered]@{
            commit=$BaseCommit.ToLowerInvariant()
            compilerVersion=(Get-AriaCompilerVersion)
        }
        subject = $Subject
        semanticDelta = $SemanticDelta
        changedPaths = @($ChangedPaths | Sort-Object path)
        proofObligations = @($ProofObligations | Sort-Object id)
        testPlan = @($TestPlan | Sort-Object id)
        compatibility = $Compatibility
        rollback = @($Rollback | Sort-Object path)
        executionEvidenceRefs = @($ExecutionEvidenceRefs | Sort-Object digest)
        approvalBoundary = [pscustomobject][ordered]@{
            state='unapproved'
            selfApprovalForbidden=$true
            requiredApproverRole='human'
        }
        authority = [pscustomobject][ordered]@{
            class='proposal'
            grantsAuthority=$false
            capabilitiesGranted=@()
        }
        digest = ''
    }
    $proposal.digest = Get-AriaSemanticProposalDigest $proposal
    $validation = Test-AriaSemanticProposal $proposal
    if (-not $validation.valid) {
        throw ('ARIA semantic proposal rejected: ' + (@($validation.errors) -join ', '))
    }
    $proposal
}

function Test-AriaSemanticProposal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Proposal,
        [object[]]$ReceiptCatalog=@()
    )
    $errors = New-Object System.Collections.Generic.List[string]
    if ([string](Get-AriaSemanticProposalProperty $Proposal schema) -ne 'aria.semantic-proposal/1') {
        $errors.Add('E_SEMANTIC_PROPOSAL_SCHEMA')
    }
    foreach ($identity in @(
        [string](Get-AriaSemanticProposalProperty $Proposal intentRef),
        [string](Get-AriaSemanticProposalProperty (Get-AriaSemanticProposalProperty $Proposal baseline) commit)
    )) {
        if ($identity -notmatch '^(sha256:)?[a-f0-9]{40,64}$') { $errors.Add('E_SEMANTIC_PROPOSAL_IDENTITY') }
    }
    $proposer = Get-AriaSemanticProposalProperty $Proposal proposer
    if ([string]::IsNullOrWhiteSpace([string](Get-AriaSemanticProposalProperty $proposer id)) -or
        [string](Get-AriaSemanticProposalProperty $proposer role) -ne 'producer') {
        $errors.Add('E_SEMANTIC_PROPOSAL_PROPOSER')
    }
    if ($null -ne $Proposal.PSObject.Properties['approval'] -or
        [string](Get-AriaSemanticProposalProperty (Get-AriaSemanticProposalProperty $Proposal approvalBoundary) state) -ne 'unapproved' -or
        -not [bool](Get-AriaSemanticProposalProperty (Get-AriaSemanticProposalProperty $Proposal approvalBoundary) selfApprovalForbidden) -or
        [string](Get-AriaSemanticProposalProperty (Get-AriaSemanticProposalProperty $Proposal approvalBoundary) requiredApproverRole) -ne 'human') {
        $errors.Add('E_SEMANTIC_PROPOSAL_SELF_APPROVAL')
    }
    $authority = Get-AriaSemanticProposalProperty $Proposal authority
    if ([string](Get-AriaSemanticProposalProperty $authority class) -ne 'proposal' -or
        [bool](Get-AriaSemanticProposalProperty $authority grantsAuthority) -or
        @((Get-AriaSemanticProposalProperty $authority capabilitiesGranted @())).Count -ne 0) {
        $errors.Add('E_SEMANTIC_PROPOSAL_AUTHORITY')
    }

    $delta = Get-AriaSemanticProposalProperty $Proposal semanticDelta
    foreach ($dimension in @('grammar','lowering','types','effects','opcodes','policies')) {
        if ($null -eq $delta -or $null -eq $delta.PSObject.Properties[$dimension]) {
            $errors.Add('E_SEMANTIC_PROPOSAL_DELTA')
        }
    }
    $authorityDelta = Get-AriaSemanticProposalProperty $delta authority
    if ($null -eq $authorityDelta -or $null -eq $authorityDelta.PSObject.Properties['expandsAuthority'] -or
        $null -eq $authorityDelta.PSObject.Properties['requiresExplicitAdmission']) {
        $errors.Add('E_SEMANTIC_PROPOSAL_AUTHORITY_DELTA')
    }
    elseif ([bool]$authorityDelta.expandsAuthority -and -not [bool]$authorityDelta.requiresExplicitAdmission) {
        $errors.Add('E_SEMANTIC_PROPOSAL_IMPLICIT_AUTHORITY')
    }

    $changes = @((Get-AriaSemanticProposalProperty $Proposal changedPaths @()))
    $rollbacks = @((Get-AriaSemanticProposalProperty $Proposal rollback @()))
    if ($changes.Count -eq 0) { $errors.Add('E_SEMANTIC_PROPOSAL_SCOPE_EMPTY') }
    $changeMap=@{}; $rollbackMap=@{}
    foreach ($change in $changes) {
        $path=[string](Get-AriaSemanticProposalProperty $change path)
        $pathCheck=Test-AriaEvolutionPath $path
        if (-not $pathCheck.valid) { $errors.Add('E_SEMANTIC_PROPOSAL_PATH'); continue }
        if ($changeMap.ContainsKey($pathCheck.normalized)) { $errors.Add('E_SEMANTIC_PROPOSAL_PATH_DUPLICATE') }
        $changeMap[$pathCheck.normalized]=$change
        if ([string](Get-AriaSemanticProposalProperty $change operation) -notin @('write','delete') -or
            [string](Get-AriaSemanticProposalProperty $change beforeDigest) -notmatch '^(absent|sha256:[a-f0-9]{64})$' -or
            [string](Get-AriaSemanticProposalProperty $change afterDigest) -notmatch '^(absent|sha256:[a-f0-9]{64})$' -or
            [string](Get-AriaSemanticProposalProperty $change beforeDigest) -eq [string](Get-AriaSemanticProposalProperty $change afterDigest)) {
            $errors.Add('E_SEMANTIC_PROPOSAL_CHANGE')
        }
    }
    foreach ($step in $rollbacks) {
        $path=[string](Get-AriaSemanticProposalProperty $step path)
        if ($rollbackMap.ContainsKey($path)) { $errors.Add('E_SEMANTIC_PROPOSAL_ROLLBACK_DUPLICATE') }
        $rollbackMap[$path]=$step
    }
    if ($changeMap.Count -ne $rollbackMap.Count) { $errors.Add('E_SEMANTIC_PROPOSAL_ROLLBACK_SCOPE') }
    foreach ($path in $changeMap.Keys) {
        if (-not $rollbackMap.ContainsKey($path)) { $errors.Add('E_SEMANTIC_PROPOSAL_ROLLBACK_MISSING'); continue }
        $change=$changeMap[$path]; $step=$rollbackMap[$path]
        if ([string](Get-AriaSemanticProposalProperty $step expectedDigest) -ne [string](Get-AriaSemanticProposalProperty $change afterDigest) -or
            [string](Get-AriaSemanticProposalProperty $step restoreDigest) -ne [string](Get-AriaSemanticProposalProperty $change beforeDigest)) {
            $errors.Add('E_SEMANTIC_PROPOSAL_ROLLBACK')
        }
    }
    foreach ($collection in @('proofObligations','testPlan')) {
        $items=@((Get-AriaSemanticProposalProperty $Proposal $collection @()))
        if ($items.Count -eq 0 -or @($items | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.id) }).Count) {
            $errors.Add('E_SEMANTIC_PROPOSAL_OBLIGATIONS')
        }
    }
    $compatibility=Get-AriaSemanticProposalProperty $Proposal compatibility
    if ([string](Get-AriaSemanticProposalProperty $compatibility classification) -notin @('compatible','breaking','unknown') -or
        [string]::IsNullOrWhiteSpace([string](Get-AriaSemanticProposalProperty $compatibility rationale))) {
        $errors.Add('E_SEMANTIC_PROPOSAL_COMPATIBILITY')
    }

    $catalog=@{}
    foreach ($receipt in @($ReceiptCatalog)) { $catalog[[string]$receipt.digest]=$receipt }
    foreach ($reference in @((Get-AriaSemanticProposalProperty $Proposal executionEvidenceRefs @()))) {
        $digest=[string](Get-AriaSemanticProposalProperty $reference digest)
        if ($digest -notmatch '^sha256:[a-f0-9]{64}$' -or
            [string](Get-AriaSemanticProposalProperty $reference cardId) -notmatch '^algorithm\.(map|filter|reduce)$' -or
            [string](Get-AriaSemanticProposalProperty $reference artifactHash) -notmatch '^sha256:[a-f0-9]{64}$') {
            $errors.Add('E_SEMANTIC_PROPOSAL_EVIDENCE_REF')
        }
        if ($ReceiptCatalog.Count -gt 0) {
            if (-not $catalog.ContainsKey($digest)) { $errors.Add('E_SEMANTIC_PROPOSAL_EVIDENCE_MISSING') }
            else {
                $receipt=$catalog[$digest]
                $verified=Test-AriaCardExecutionEvidence $receipt
                if (-not $verified.valid -or [string]$receipt.card.id -ne [string]$reference.cardId -or
                    [string]$receipt.program.artifactHash -ne [string]$reference.artifactHash) {
                    $errors.Add('E_SEMANTIC_PROPOSAL_EVIDENCE_BINDING')
                }
            }
        }
    }
    $expected=''
    try { $expected=Get-AriaSemanticProposalDigest $Proposal }
    catch { $errors.Add('E_SEMANTIC_PROPOSAL_DIGEST_CALCULATION') }
    if ($expected -and [string](Get-AriaSemanticProposalProperty $Proposal digest) -ne $expected) {
        $errors.Add('E_SEMANTIC_PROPOSAL_DIGEST')
    }
    [pscustomobject][ordered]@{
        valid=($errors.Count -eq 0)
        errors=@($errors.ToArray() | Sort-Object -Unique)
        digest=$expected
        executable=$false
        approvalState='unapproved'
    }
}

function Invoke-AriaSemanticProposalFile {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Semantic proposal request not found: $Path" }
    $request=Read-AriaUtf8Text $Path | ConvertFrom-Json
    New-AriaSemanticProposal `
        -IntentRef $request.intentRef `
        -ProposerId $request.proposerId `
        -BaseCommit $request.baseCommit `
        -Subject $request.subject `
        -SemanticDelta $request.semanticDelta `
        -ChangedPaths @($request.changedPaths) `
        -ProofObligations @($request.proofObligations) `
        -TestPlan @($request.testPlan) `
        -Compatibility $request.compatibility `
        -Rollback @($request.rollback) `
        -ExecutionEvidenceRefs @($request.executionEvidenceRefs)
}

Export-ModuleMember -Function `
    Get-AriaSemanticProposalBody, `
    Get-AriaSemanticProposalDigest, `
    New-AriaSemanticProposal, `
    Test-AriaSemanticProposal, `
    Invoke-AriaSemanticProposalFile
