Set-StrictMode -Version Latest

$commonPath=Join-Path $PSScriptRoot 'Aria.Common.psm1'
if(-not(Get-Module Aria.Common)){Import-Module $commonPath -DisableNameChecking}
$typedCorePath=Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if(-not(Get-Module Aria.TypedCore)){Import-Module $typedCorePath -DisableNameChecking}
$evolutionPath=Join-Path $PSScriptRoot 'Aria.GovernedEvolution.psm1'
if(-not(Get-Module Aria.GovernedEvolution)){Import-Module $evolutionPath -DisableNameChecking}

function Get-AriaPlanningProperty {
    param($Object,[string]$Name,$Default=$null)
    if($null-eq$Object){return $Default}
    $property=$Object.PSObject.Properties|Where-Object{$_.Name-ceq$Name}|Select-Object -First 1
    if($null-eq$property){return $Default}
    $property.Value
}

function Test-AriaEvolutionRequest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Request)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaPlanningProperty $Request 'schema')-cne'aria.evolution-request/0.7'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_SCHEMA' -Message 'Unsupported evolution request schema.' -Path '$.schema'))
    }
    foreach($field in @('proposer','targetVersion','resource')){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaPlanningProperty $Request $field))){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_FIELD' -Message "Evolution request field '$field' is required." -Path ("$.{0}"-f$field)))
        }
    }
    if(-not(Test-AriaSemanticVersion ([string](Get-AriaPlanningProperty $Request 'targetVersion')))){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_VERSION' -Message 'Evolution targetVersion is not semantic.' -Path '$.targetVersion'))
    }

    $capabilityIds=@((Get-AriaPlanningProperty $Request 'capabilityIds' @()))
    if($capabilityIds.Count-eq0){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_CAPABILITY' -Message 'At least one capability identity is required.' -Path '$.capabilityIds'))
    }
    foreach($id in $capabilityIds){
        if([string]$id-cnotmatch'^sha256:[a-f0-9]{64}$'){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_CAPABILITY' -Message "Invalid capability identity '$id'." -Path '$.capabilityIds'))
        }
    }

    $changes=@((Get-AriaPlanningProperty $Request 'changes' @()))
    if($changes.Count-eq0){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_CHANGES' -Message 'At least one requested change is required.' -Path '$.changes'))
    }
    $seen=@{}
    foreach($change in $changes){
        $path=[string](Get-AriaPlanningProperty $change 'path')
        $pathResult=Test-AriaEvolutionPath $path
        if(-not[bool]$pathResult.valid){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_PATH' -Message "Unsafe evolution request path '$path'." -Path '$.changes.path'))
            continue
        }
        if($seen.ContainsKey($pathResult.normalized)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_DUPLICATE' -Message "Duplicate evolution request path '$($pathResult.normalized)'." -Path '$.changes.path'))
        }
        else{$seen[$pathResult.normalized]=$true}
        $operation=[string](Get-AriaPlanningProperty $change 'operation')
        if($operation-notin@('write','delete')){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_OPERATION' -Message "Unsupported change operation '$operation'." -Path '$.changes.operation'))
        }
        $hasContent=$null-ne($change.PSObject.Properties|Where-Object{$_.Name-ceq'content'}|Select-Object -First 1)
        if($operation-eq'write' -and-not$hasContent){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_CONTENT' -Message "Write change '$path' requires content." -Path '$.changes.content'))
        }
        if($operation-eq'delete' -and$hasContent -and $null-ne(Get-AriaPlanningProperty $change 'content')){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_CONTENT' -Message "Delete change '$path' cannot contain replacement content." -Path '$.changes.content'))
        }
    }

    $evidence=@((Get-AriaPlanningProperty $Request 'evidence' @()))
    if($evidence.Count-eq0){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_EVIDENCE' -Message 'At least one evidence reference is required.' -Path '$.evidence'))
    }
    foreach($item in $evidence){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaPlanningProperty $item 'kind')) -or
           [string]::IsNullOrWhiteSpace([string](Get-AriaPlanningProperty $item 'id')) -or
           [string](Get-AriaPlanningProperty $item 'digest')-cnotmatch'^[a-f0-9]{64}$'){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_REQUEST_EVIDENCE' -Message 'Evidence requires kind, id, and a lowercase SHA-256 digest.' -Path '$.evidence'))
        }
    }

    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray())}
}

function New-AriaEvolutionPlan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Request,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string]$BaseCommit
    )

    $validation=Test-AriaEvolutionRequest $Request
    if(-not[bool]$validation.valid){
        throw "ARIA evolution request rejected: $(@($validation.errors|ForEach-Object{$_.code+': '+$_.message})-join'; ')"
    }
    if($BaseCommit-cnotmatch'^[a-fA-F0-9]{40,64}$'){throw 'ARIA evolution planning requires an exact Git commit identity.'}

    $workspace=[IO.Path]::GetFullPath((Resolve-Path -LiteralPath $WorkspaceRoot).Path)
    $beforeFiles=New-Object 'System.Collections.Generic.List[object]'
    $changes=New-Object 'System.Collections.Generic.List[object]'
    $rollbacks=New-Object 'System.Collections.Generic.List[object]'
    foreach($requested in @((Get-AriaPlanningProperty $Request 'changes' @())|Sort-Object path)){
        $path=[string](Get-AriaPlanningProperty $requested 'path')
        $operation=[string](Get-AriaPlanningProperty $requested 'operation')
        $resolved=Resolve-AriaConfinedPath -WorkspaceRoot $workspace -Scope '.' -RequestedPath $path
        $exists=Test-Path -LiteralPath $resolved -PathType Leaf
        if($operation-eq'delete' -and-not$exists){throw "ARIA evolution delete target does not exist: $path"}
        if(Test-Path -LiteralPath $resolved -PathType Container){throw "ARIA evolution target is a directory: $path"}
        $before=if($exists){[IO.File]::ReadAllText($resolved)}else{$null}
        if($exists){[void]$beforeFiles.Add([pscustomobject]@{path=$path;content=$before})}
        $after=if($operation-eq'write'){[string](Get-AriaPlanningProperty $requested 'content')}else{$null}
        $change=New-AriaEvolutionChange -Path $path -Operation $operation -BeforeContent $before -AfterContent $after
        [void]$changes.Add($change)
        if($exists){
            [void]$rollbacks.Add((New-AriaEvolutionRollbackStep -Path $path -Operation write -ExpectedDigest $change.afterDigest -RestoreContent $before))
        }
        else{
            [void]$rollbacks.Add((New-AriaEvolutionRollbackStep -Path $path -Operation delete -ExpectedDigest $change.afterDigest -RestoreContent $null))
        }
    }

    $original=New-AriaRepositorySnapshot -Files @($beforeFiles.ToArray())
    $proposal=New-AriaEvolutionProposal `
        -Proposer ([string](Get-AriaPlanningProperty $Request 'proposer')) `
        -BaseCommit $BaseCommit `
        -TargetVersion ([string](Get-AriaPlanningProperty $Request 'targetVersion')) `
        -Resource ([string](Get-AriaPlanningProperty $Request 'resource')) `
        -RequestedEffects @('repository.write') `
        -CapabilityIds @((Get-AriaPlanningProperty $Request 'capabilityIds' @())) `
        -Changes @($changes.ToArray()) `
        -Evidence @((Get-AriaPlanningProperty $Request 'evidence' @())) `
        -RollbackPlan @($rollbacks.ToArray())
    $proposalValidation=Test-AriaEvolutionProposal $proposal
    if(-not[bool]$proposalValidation.valid){throw "Generated proposal failed verification: $(@($proposalValidation.errors.code)-join', ')"}
    $candidate=Invoke-AriaEvolutionChanges -Snapshot $original -Changes @($changes.ToArray())
    if(-not[bool]$candidate.valid){throw "Generated candidate failed verification: $(@($candidate.errors.code)-join', ')"}
    $rollback=Test-AriaEvolutionRollback -OriginalSnapshot $original -CandidateSnapshot $candidate.snapshot -RollbackPlan @($rollbacks.ToArray())
    if(-not[bool]$rollback.valid){throw "Generated rollback proof failed: $(@($rollback.errors.code)-join', ')"}
    $diff=New-AriaEvolutionSemanticDiff -OriginalSnapshot $original -CandidateSnapshot $candidate.snapshot

    $identity=[ordered]@{
        schema='aria.evolution-plan-record/0.7'
        state='awaiting-authorization'
        proposalId=$proposal.id
        baseCommit=$BaseCommit.ToLowerInvariant()
        originalSnapshotId=$original.id
        candidateSnapshotId=$candidate.snapshot.id
        semanticDiff=$diff
        rollbackVerified=$true
        requiredGates=@($proposal.requiredGates)
    }
    $record=[pscustomobject][ordered]@{
        schema=$identity.schema
        state=$identity.state
        proposalId=$identity.proposalId
        baseCommit=$identity.baseCommit
        originalSnapshotId=$identity.originalSnapshotId
        candidateSnapshotId=$identity.candidateSnapshotId
        semanticDiff=$identity.semanticDiff
        rollbackVerified=$identity.rollbackVerified
        requiredGates=@($identity.requiredGates)
        id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    }
    [pscustomobject][ordered]@{
        request=$Request
        proposal=$proposal
        originalSnapshot=$original
        candidateSnapshot=$candidate.snapshot
        record=$record
    }
}

function Write-AriaEvolutionPlanRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Plan,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot
    )

    $digest=([string]$Plan.proposal.id)-replace'^sha256:',''
    if($digest-cnotmatch'^[a-f0-9]{64}$'){throw 'Cannot persist an evolution plan without a valid proposal identity.'}
    $root=Join-Path ([IO.Path]::GetFullPath($WorkspaceRoot)) '.aria/evolution'
    $directory=Join-Path $root $digest
    if(-not(Test-Path -LiteralPath $directory -PathType Container)){New-Item -ItemType Directory -Path $directory -Force|Out-Null}
    $documents=[ordered]@{
        'request.json'=$Plan.request
        'proposal.json'=$Plan.proposal
        'original-snapshot.json'=$Plan.originalSnapshot
        'candidate-snapshot.json'=$Plan.candidateSnapshot
        'plan.json'=$Plan.record
    }
    foreach($entry in $documents.GetEnumerator()){
        $path=Join-Path $directory $entry.Key
        $text=(ConvertTo-AriaStableJson $entry.Value)+[Environment]::NewLine
        if(Test-Path -LiteralPath $path -PathType Leaf){
            $existing=Read-AriaUtf8Text $path
            if($existing-cne$text){throw "Evolution record identity collision at '$path'."}
        }
        else{Write-AriaUtf8NoBom -Path $path -Text $text}
    }
    [pscustomobject][ordered]@{directory=$directory;proposalId=$Plan.proposal.id;recordId=$Plan.record.id;state=$Plan.record.state}
}

function Invoke-AriaEvolutionPlanFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string]$BaseCommit
    )

    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "Evolution request not found: $Path"}
    try{$request=Read-AriaUtf8Text $Path|ConvertFrom-Json}
    catch{throw "Evolution request JSON is invalid: $($_.Exception.Message)"}
    $plan=New-AriaEvolutionPlan -Request $request -WorkspaceRoot $WorkspaceRoot -BaseCommit $BaseCommit
    $persisted=Write-AriaEvolutionPlanRecord -Plan $plan -WorkspaceRoot $WorkspaceRoot
    [pscustomobject][ordered]@{plan=$plan;persisted=$persisted}
}

function Test-AriaEvolutionPlanRecord {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Record)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaPlanningProperty $Record 'schema')-cne'aria.evolution-plan-record/0.7'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_RECORD_SCHEMA' -Message 'Unsupported evolution plan record schema.' -Path '$.schema'))
    }
    if([string](Get-AriaPlanningProperty $Record 'state')-cne'awaiting-authorization'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_RECORD_STATE' -Message 'Evolution plan is not awaiting authorization.' -Path '$.state'))
    }
    $identity=[ordered]@{
        schema=Get-AriaPlanningProperty $Record 'schema'
        state=Get-AriaPlanningProperty $Record 'state'
        proposalId=Get-AriaPlanningProperty $Record 'proposalId'
        baseCommit=Get-AriaPlanningProperty $Record 'baseCommit'
        originalSnapshotId=Get-AriaPlanningProperty $Record 'originalSnapshotId'
        candidateSnapshotId=Get-AriaPlanningProperty $Record 'candidateSnapshotId'
        semanticDiff=Get-AriaPlanningProperty $Record 'semanticDiff'
        rollbackVerified=[bool](Get-AriaPlanningProperty $Record 'rollbackVerified' $false)
        requiredGates=@((Get-AriaPlanningProperty $Record 'requiredGates' @()))
    }
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaPlanningProperty $Record 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_RECORD_IDENTITY' -Message 'Evolution plan record identity mismatch.' -Path '$.id'))
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$expected}
}

function Read-AriaEvolutionPlanRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string]$CurrentCommit
    )

    $digest=$ProposalId-replace'^sha256:',''
    if($digest-cnotmatch'^[a-f0-9]{64}$'){throw 'Evolution verification requires a valid proposal identity.'}
    $directory=Join-Path (Join-Path ([IO.Path]::GetFullPath($WorkspaceRoot)) '.aria/evolution') $digest
    if(-not(Test-Path -LiteralPath $directory -PathType Container)){throw "Evolution plan record not found: $ProposalId"}
    $documents=@{}
    foreach($name in @('request','proposal','original-snapshot','candidate-snapshot','plan')){
        $path=Join-Path $directory ($name+'.json')
        if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Evolution plan record is incomplete: $($name).json"}
        try{$documents[$name]=Read-AriaUtf8Text $path|ConvertFrom-Json}
        catch{throw "Evolution plan record '$($name).json' is invalid JSON: $($_.Exception.Message)"}
    }

    $proposalValidation=Test-AriaEvolutionProposal $documents['proposal']
    if(-not[bool]$proposalValidation.valid){throw "Persisted proposal failed verification: $(@($proposalValidation.errors.code)-join', ')"}
    foreach($name in @('original-snapshot','candidate-snapshot')){
        $snapshotValidation=Test-AriaRepositorySnapshot $documents[$name]
        if(-not[bool]$snapshotValidation.valid){throw "Persisted $name failed verification: $(@($snapshotValidation.errors.code)-join', ')"}
    }
    $recordValidation=Test-AriaEvolutionPlanRecord $documents['plan']
    if(-not[bool]$recordValidation.valid){throw "Persisted plan record failed verification: $(@($recordValidation.errors.code)-join', ')"}
    if([string]$documents['proposal'].id-cne"sha256:$digest"){throw 'Evolution directory identity does not match its proposal.'}
    if([string]$documents['plan'].proposalId-cne[string]$documents['proposal'].id -or
       [string]$documents['plan'].originalSnapshotId-cne[string]$documents['original-snapshot'].id -or
       [string]$documents['plan'].candidateSnapshotId-cne[string]$documents['candidate-snapshot'].id){
        throw 'Evolution plan record references inconsistent artifact identities.'
    }
    if([string]$documents['proposal'].baseCommit-cne$CurrentCommit.ToLowerInvariant()){
        throw 'Current Git commit no longer matches the persisted evolution proposal.'
    }

    $regenerated=New-AriaEvolutionPlan `
        -Request $documents['request'] `
        -WorkspaceRoot $WorkspaceRoot `
        -BaseCommit $CurrentCommit
    if([string]$regenerated.proposal.id-cne[string]$documents['proposal'].id -or
       [string]$regenerated.originalSnapshot.id-cne[string]$documents['original-snapshot'].id -or
       [string]$regenerated.candidateSnapshot.id-cne[string]$documents['candidate-snapshot'].id -or
       [string]$regenerated.record.id-cne[string]$documents['plan'].id){
        throw 'Evolution plan no longer matches current repository bytes or persisted records.'
    }
    [pscustomobject][ordered]@{
        directory=$directory
        request=$documents['request']
        proposal=$documents['proposal']
        originalSnapshot=$documents['original-snapshot']
        candidateSnapshot=$documents['candidate-snapshot']
        record=$documents['plan']
    }
}

function Test-AriaEvolutionVerificationPolicy {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Policy)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaPlanningProperty $Policy 'schema')-cne'aria.evolution-verification-policy/0.8'){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_VERIFY_POLICY_SCHEMA' -Message 'Unsupported evolution verification policy schema.' -Path '$.schema'))
    }
    if($null-eq(Get-AriaPlanningProperty $Policy 'issuerPolicy')){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_VERIFY_POLICY_ISSUER' -Message 'Verification policy requires issuerPolicy.' -Path '$.issuerPolicy'))
    }
    if(@((Get-AriaPlanningProperty $Policy 'trustedAuthorizers' @())).Count-eq0){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_EVOLUTION_VERIFY_POLICY_AUTHORIZER' -Message 'Verification policy requires trustedAuthorizers.' -Path '$.trustedAuthorizers'))
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray())}
}

function Invoke-AriaEvolutionVerification {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Plan,
        [Parameter(Mandatory=$true)]$CapabilityBundle,
        [Parameter(Mandatory=$true)]$Authorization,
        [Parameter(Mandatory=$true)]$VerificationPolicy,
        [Parameter(Mandatory=$true)][string]$CurrentCommit
    )

    $policyValidation=Test-AriaEvolutionVerificationPolicy $VerificationPolicy
    if(-not[bool]$policyValidation.valid){throw "Evolution verification policy rejected: $(@($policyValidation.errors.code)-join', ')"}
    if([string](Get-AriaPlanningProperty $CapabilityBundle 'schema')-eq'aria.capability-bundle/0.8'){
        $token=Get-AriaPlanningProperty $CapabilityBundle 'token'
        $knownTokens=@((Get-AriaPlanningProperty $CapabilityBundle 'knownTokens' @()))
    }
    else{
        $token=$CapabilityBundle
        $knownTokens=@()
    }
    if($null-eq$token){throw 'Evolution capability bundle does not contain a token.'}
    $decisionTime=[string](Get-AriaPlanningProperty $Authorization 'decidedAt')
    $governed=Invoke-AriaGovernedEvolutionPlan `
        -Proposal $Plan.proposal `
        -Authorization $Authorization `
        -CapabilityToken $token `
        -KnownTokens $knownTokens `
        -IssuerPolicy (Get-AriaPlanningProperty $VerificationPolicy 'issuerPolicy') `
        -DecisionTime $decisionTime `
        -TrustedAuthorizers @((Get-AriaPlanningProperty $VerificationPolicy 'trustedAuthorizers' @())) `
        -CurrentCommit $CurrentCommit `
        -CurrentSnapshot $Plan.originalSnapshot
    if(-not[bool]$governed.approved){
        throw "Evolution verification rejected: $(@($governed.errors|ForEach-Object{$_.code+': '+$_.message})-join'; ')"
    }
    if([string]$governed.candidateSnapshot.id-cne[string]$Plan.candidateSnapshot.id){
        throw 'Authorized candidate identity differs from the persisted candidate.'
    }

    $identity=[ordered]@{
        schema='aria.evolution-verification-record/0.8'
        state='authorized'
        proposalId=[string]$Plan.proposal.id
        planRecordId=[string]$Plan.record.id
        authorizationId=[string]$Authorization.id
        authorityDecisionId=[string]$governed.authorityDecision.id
        governedEventId=[string]$governed.event.id
        baseCommit=$CurrentCommit.ToLowerInvariant()
        candidateSnapshotId=[string]$governed.candidateSnapshot.id
        rollbackVerified=[bool]$governed.rollbackVerified
        requiredGates=@($Plan.proposal.requiredGates)
    }
    $record=[pscustomobject][ordered]@{
        schema=$identity.schema
        state=$identity.state
        proposalId=$identity.proposalId
        planRecordId=$identity.planRecordId
        authorizationId=$identity.authorizationId
        authorityDecisionId=$identity.authorityDecisionId
        governedEventId=$identity.governedEventId
        baseCommit=$identity.baseCommit
        candidateSnapshotId=$identity.candidateSnapshotId
        rollbackVerified=$identity.rollbackVerified
        requiredGates=@($identity.requiredGates)
        id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    }
    [pscustomobject][ordered]@{
        authorization=$Authorization
        authorityDecision=$governed.authorityDecision
        governedEvent=$governed.event
        record=$record
    }
}

function Write-AriaEvolutionVerificationRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Verification,
        [Parameter(Mandatory=$true)][string]$PlanDirectory
    )

    $documents=[ordered]@{
        'authorization.json'=$Verification.authorization
        'authority-decision.json'=$Verification.authorityDecision
        'governed-event.json'=$Verification.governedEvent
        'verification.json'=$Verification.record
    }
    foreach($entry in $documents.GetEnumerator()){
        $path=Join-Path $PlanDirectory $entry.Key
        $text=(ConvertTo-AriaStableJson $entry.Value)+[Environment]::NewLine
        if(Test-Path -LiteralPath $path -PathType Leaf){
            if((Read-AriaUtf8Text $path)-cne$text){throw "Evolution verification identity collision at '$path'."}
        }
        else{Write-AriaUtf8NoBom -Path $path -Text $text}
    }
    [pscustomobject][ordered]@{
        directory=$PlanDirectory
        proposalId=$Verification.record.proposalId
        verificationId=$Verification.record.id
        state=$Verification.record.state
    }
}

function Invoke-AriaEvolutionVerificationFiles {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string]$CurrentCommit,
        [Parameter(Mandatory=$true)][string]$CapabilityPath,
        [Parameter(Mandatory=$true)][string]$AuthorizationPath,
        [Parameter(Mandatory=$true)][string]$VerificationPolicyPath
    )

    foreach($path in @($CapabilityPath,$AuthorizationPath,$VerificationPolicyPath)){
        if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Evolution verification input not found: $path"}
    }
    try{$capability=Read-AriaUtf8Text $CapabilityPath|ConvertFrom-Json}
    catch{throw "Capability JSON is invalid: $($_.Exception.Message)"}
    try{$authorization=Read-AriaUtf8Text $AuthorizationPath|ConvertFrom-Json}
    catch{throw "Authorization JSON is invalid: $($_.Exception.Message)"}
    try{$policy=Read-AriaUtf8Text $VerificationPolicyPath|ConvertFrom-Json}
    catch{throw "Verification policy JSON is invalid: $($_.Exception.Message)"}
    $plan=Read-AriaEvolutionPlanRecord -ProposalId $ProposalId -WorkspaceRoot $WorkspaceRoot -CurrentCommit $CurrentCommit
    $verification=Invoke-AriaEvolutionVerification `
        -Plan $plan `
        -CapabilityBundle $capability `
        -Authorization $authorization `
        -VerificationPolicy $policy `
        -CurrentCommit $CurrentCommit
    $persisted=Write-AriaEvolutionVerificationRecord -Verification $verification -PlanDirectory $plan.directory
    [pscustomobject][ordered]@{plan=$plan;verification=$verification;persisted=$persisted}
}

Export-ModuleMember -Function `
    Test-AriaEvolutionRequest, `
    New-AriaEvolutionPlan, `
    Write-AriaEvolutionPlanRecord, `
    Invoke-AriaEvolutionPlanFile, `
    Test-AriaEvolutionPlanRecord, `
    Read-AriaEvolutionPlanRecord, `
    Test-AriaEvolutionVerificationPolicy, `
    Invoke-AriaEvolutionVerification, `
    Write-AriaEvolutionVerificationRecord, `
    Invoke-AriaEvolutionVerificationFiles
