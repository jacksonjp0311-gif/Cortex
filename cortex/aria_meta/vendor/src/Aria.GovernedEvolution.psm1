Set-StrictMode -Version Latest

$typedCorePath = Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if (-not (Get-Module Aria.TypedCore)) {
    Import-Module $typedCorePath -DisableNameChecking
}

$authorityPath = Join-Path $PSScriptRoot 'Aria.CapabilityAuthority.psm1'
if (-not (Get-Module Aria.CapabilityAuthority)) {
    Import-Module $authorityPath -DisableNameChecking
}

function Get-AriaEvolutionProperty {
    param(
        [object]$Object,
        [Parameter(Mandatory=$true)][string]$Name,
        [object]$Default = $null
    )

    if($null-eq$Object){return $Default}

    if($Object-is[Collections.IDictionary]){
        if($Object.Contains($Name)){return $Object[$Name]}
        return $Default
    }

    $property=$Object.PSObject.Properties[$Name]
    if($null-eq$property){return $Default}
    return $property.Value
}

function Get-AriaEvolutionContentDigest {
    [CmdletBinding()]
    param([AllowNull()][object]$Content)

    if($null-eq$Content){return 'absent'}
    Get-AriaSha256Hex ([string]$Content)
}

function Test-AriaEvolutionPath {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)

    $normalized=$Path.Replace('\','/').Trim()
    $valid=$true
    $reason=''

    if([string]::IsNullOrWhiteSpace($normalized)){
        $valid=$false
        $reason='empty'
    }
    elseif($normalized.StartsWith('/') -or $normalized.StartsWith('./') -or $normalized.Contains(':')){
        $valid=$false
        $reason='rooted'
    }
    elseif($normalized-eq'.git' -or $normalized.StartsWith('.git/')){
        $valid=$false
        $reason='git-internal'
    }
    else{
        foreach($segment in @($normalized -split '/')){
            if($segment-eq'..'){
                $valid=$false
                $reason='traversal'
                break
            }
        }
    }

    [pscustomobject][ordered]@{
        valid=$valid
        normalized=$normalized
        reason=$reason
    }
}

function New-AriaRepositorySnapshot {
    [CmdletBinding()]
    param([object[]]$Files=@())

    $entries=New-Object 'System.Collections.Generic.List[object]'
    $seen=@{}

    foreach($file in @($Files)){
        $path=[string](Get-AriaEvolutionProperty $file 'path')
        $pathCheck=Test-AriaEvolutionPath $path
        if(-not[bool]$pathCheck.valid){throw "Unsafe snapshot path '$path'."}
        $path=$pathCheck.normalized

        if($seen.ContainsKey($path)){throw "Duplicate snapshot path '$path'."}
        $seen[$path]=$true

        $content=[string](Get-AriaEvolutionProperty $file 'content' '')
        [void]$entries.Add([pscustomobject][ordered]@{
            path=$path
            content=$content
            digest=Get-AriaEvolutionContentDigest $content
        })
    }

    $sorted=@($entries.ToArray() | Sort-Object path)
    $identity=[ordered]@{
        schema='aria.repository-snapshot/0.6'
        files=$sorted
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        files=@($identity.files)
        id=$id
    }
}

function Test-AriaRepositorySnapshot {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Snapshot)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $seen=@{}

    if([string](Get-AriaEvolutionProperty $Snapshot 'schema')-ne'aria.repository-snapshot/0.6'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_SNAPSHOT_SCHEMA' `
            -Message 'Unsupported repository snapshot schema.' `
            -Path '$.schema'))
    }

    foreach($file in @((Get-AriaEvolutionProperty $Snapshot 'files' @()))){
        $path=[string](Get-AriaEvolutionProperty $file 'path')
        $pathCheck=Test-AriaEvolutionPath $path
        if(-not[bool]$pathCheck.valid){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_PATH' `
                -Message "Unsafe repository path '$path'." `
                -Path '$.files.path'))
            continue
        }

        if($seen.ContainsKey($pathCheck.normalized)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_PATH_DUPLICATE' `
                -Message "Duplicate repository path '$($pathCheck.normalized)'." `
                -Path '$.files.path'))
        }
        else{$seen[$pathCheck.normalized]=$true}

        $actual=Get-AriaEvolutionContentDigest (Get-AriaEvolutionProperty $file 'content')
        if([string](Get-AriaEvolutionProperty $file 'digest')-cne$actual){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_SNAPSHOT_DIGEST' `
                -Message "Snapshot digest mismatch for '$($pathCheck.normalized)'." `
                -Path '$.files.digest'))
        }
    }

    $identity=[ordered]@{
        schema=Get-AriaEvolutionProperty $Snapshot 'schema'
        files=@((Get-AriaEvolutionProperty $Snapshot 'files' @()) | Sort-Object path)
    }
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaEvolutionProperty $Snapshot 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_SNAPSHOT_IDENTITY' `
            -Message 'Repository snapshot identity mismatch.' `
            -Path '$.id'))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        expectedId=$expected
    }
}

function Get-AriaEvolutionSnapshotMap {
    param([Parameter(Mandatory=$true)]$Snapshot)

    $map=@{}
    foreach($file in @((Get-AriaEvolutionProperty $Snapshot 'files' @()))){
        $map[[string](Get-AriaEvolutionProperty $file 'path')]=[string](Get-AriaEvolutionProperty $file 'content')
    }
    return $map
}

function New-AriaEvolutionChange {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][ValidateSet('write','delete')][string]$Operation,
        [AllowNull()][object]$BeforeContent,
        [AllowNull()][object]$AfterContent
    )

    $pathCheck=Test-AriaEvolutionPath $Path
    if(-not[bool]$pathCheck.valid){throw "Unsafe evolution path '$Path'."}

    if($Operation-eq'delete' -and $null-ne$AfterContent){
        throw 'Delete changes must use a null after-content value.'
    }
    if($Operation-eq'write' -and $null-eq$AfterContent){
        throw 'Write changes require after-content.'
    }

    [pscustomobject][ordered]@{
        path=$pathCheck.normalized
        operation=$Operation
        beforeDigest=Get-AriaEvolutionContentDigest $BeforeContent
        afterDigest=Get-AriaEvolutionContentDigest $AfterContent
        content=$AfterContent
    }
}

function New-AriaEvolutionRollbackStep {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][ValidateSet('write','delete')][string]$Operation,
        [Parameter(Mandatory=$true)][string]$ExpectedDigest,
        [AllowNull()][object]$RestoreContent
    )

    $pathCheck=Test-AriaEvolutionPath $Path
    if(-not[bool]$pathCheck.valid){throw "Unsafe rollback path '$Path'."}

    if($Operation-eq'delete' -and $null-ne$RestoreContent){
        throw 'Delete rollback steps must use null restore content.'
    }
    if($Operation-eq'write' -and $null-eq$RestoreContent){
        throw 'Write rollback steps require restore content.'
    }

    [pscustomobject][ordered]@{
        path=$pathCheck.normalized
        operation=$Operation
        expectedDigest=$ExpectedDigest
        restoreDigest=Get-AriaEvolutionContentDigest $RestoreContent
        content=$RestoreContent
    }
}

function Get-AriaEvolutionProposalIdentityInput {
    param([Parameter(Mandatory=$true)]$Proposal)

    [ordered]@{
        schema=Get-AriaEvolutionProperty $Proposal 'schema'
        proposer=Get-AriaEvolutionProperty $Proposal 'proposer'
        baseCommit=Get-AriaEvolutionProperty $Proposal 'baseCommit'
        targetVersion=Get-AriaEvolutionProperty $Proposal 'targetVersion'
        resource=Get-AriaEvolutionProperty $Proposal 'resource'
        requestedEffects=@((Get-AriaEvolutionProperty $Proposal 'requestedEffects' @()))
        capabilityIds=@((Get-AriaEvolutionProperty $Proposal 'capabilityIds' @()))
        changes=@((Get-AriaEvolutionProperty $Proposal 'changes' @()))
        evidence=@((Get-AriaEvolutionProperty $Proposal 'evidence' @()))
        requiredGates=@((Get-AriaEvolutionProperty $Proposal 'requiredGates' @()))
        rollbackPlan=@((Get-AriaEvolutionProperty $Proposal 'rollbackPlan' @()))
        signature=Get-AriaEvolutionProperty $Proposal 'signature'
    }
}

function New-AriaEvolutionProposal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Proposer,
        [Parameter(Mandatory=$true)][string]$BaseCommit,
        [Parameter(Mandatory=$true)][string]$TargetVersion,
        [Parameter(Mandatory=$true)][string]$Resource,
        [Parameter(Mandatory=$true)][string[]]$RequestedEffects,
        [Parameter(Mandatory=$true)][string[]]$CapabilityIds,
        [Parameter(Mandatory=$true)][object[]]$Changes,
        [Parameter(Mandatory=$true)][object[]]$Evidence,
        [string[]]$RequiredGates=@('manifest','doctor.strict','conformance'),
        [Parameter(Mandatory=$true)][object[]]$RollbackPlan,
        [object]$Signature=$null
    )

    if($null-eq$Signature){
        $Signature=[pscustomobject][ordered]@{
            algorithm='none'
            value=''
        }
    }

    $identity=[ordered]@{
        schema='aria.evolution-proposal/0.6'
        proposer=$Proposer
        baseCommit=$BaseCommit.ToLowerInvariant()
        targetVersion=$TargetVersion
        resource=$Resource
        requestedEffects=@($RequestedEffects | Sort-Object -Unique)
        capabilityIds=@($CapabilityIds | Sort-Object -Unique)
        changes=@($Changes | Sort-Object path)
        evidence=@($Evidence | Sort-Object kind,id)
        requiredGates=@($RequiredGates | Sort-Object -Unique)
        rollbackPlan=@($RollbackPlan | Sort-Object path)
        signature=$Signature
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        proposer=$identity.proposer
        baseCommit=$identity.baseCommit
        targetVersion=$identity.targetVersion
        resource=$identity.resource
        requestedEffects=@($identity.requestedEffects)
        capabilityIds=@($identity.capabilityIds)
        changes=@($identity.changes)
        evidence=@($identity.evidence)
        requiredGates=@($identity.requiredGates)
        rollbackPlan=@($identity.rollbackPlan)
        signature=$identity.signature
        id=$id
    }
}

function Test-AriaEvolutionProposal {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Proposal)

    $errors=New-Object 'System.Collections.Generic.List[object]'

    if([string](Get-AriaEvolutionProperty $Proposal 'schema')-ne'aria.evolution-proposal/0.6'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_SCHEMA' `
            -Message 'Unsupported evolution proposal schema.' `
            -Path '$.schema'))
    }

    foreach($field in @('proposer','baseCommit','targetVersion','resource')){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaEvolutionProperty $Proposal $field))){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_FIELD' `
                -Message "Evolution proposal field '$field' is required." `
                -Path ("$.{0}" -f $field)))
        }
    }

    if([string](Get-AriaEvolutionProperty $Proposal 'baseCommit')-notmatch'^[a-fA-F0-9]{40,64}$'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_BASE_FORMAT' `
            -Message 'Base commit must be a hexadecimal Git identity.' `
            -Path '$.baseCommit'))
    }

    if([string](Get-AriaEvolutionProperty $Proposal 'targetVersion')-notmatch'^\d+\.\d+\.\d+([\-+][0-9A-Za-z.-]+)?$'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_VERSION' `
            -Message 'Target version is not a valid semantic version.' `
            -Path '$.targetVersion'))
    }

    if(@((Get-AriaEvolutionProperty $Proposal 'requestedEffects' @())).Count-eq0){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_EFFECTS' `
            -Message 'Evolution proposal requires at least one effect.' `
            -Path '$.requestedEffects'))
    }

    if(@((Get-AriaEvolutionProperty $Proposal 'capabilityIds' @())).Count-eq0){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_CAPABILITIES' `
            -Message 'Evolution proposal requires capability identities.' `
            -Path '$.capabilityIds'))
    }

    $seen=@{}
    $changes=@((Get-AriaEvolutionProperty $Proposal 'changes' @()))
    if($changes.Count-eq0){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_CHANGES' `
            -Message 'Evolution proposal contains no changes.' `
            -Path '$.changes'))
    }

    foreach($change in $changes){
        $path=[string](Get-AriaEvolutionProperty $change 'path')
        $pathCheck=Test-AriaEvolutionPath $path
        if(-not[bool]$pathCheck.valid){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_PATH' `
                -Message "Unsafe evolution path '$path'." `
                -Path '$.changes.path'))
            continue
        }

        if($seen.ContainsKey($pathCheck.normalized)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_PATH_DUPLICATE' `
                -Message "Duplicate evolution path '$($pathCheck.normalized)'." `
                -Path '$.changes.path'))
        }
        else{$seen[$pathCheck.normalized]=$true}

        $operation=[string](Get-AriaEvolutionProperty $change 'operation')
        if($operation-notin@('write','delete')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_OPERATION' `
                -Message "Unsupported evolution operation '$operation'." `
                -Path '$.changes.operation'))
            continue
        }

        $content=Get-AriaEvolutionProperty $change 'content'
        $actualAfter=Get-AriaEvolutionContentDigest $content
        if($operation-eq'delete'){$actualAfter='absent'}

        if([string](Get-AriaEvolutionProperty $change 'afterDigest')-cne$actualAfter){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_CHANGE_DIGEST' `
                -Message "After digest mismatch for '$($pathCheck.normalized)'." `
                -Path '$.changes.afterDigest'))
        }

        if([string](Get-AriaEvolutionProperty $change 'beforeDigest')-ceq
           [string](Get-AriaEvolutionProperty $change 'afterDigest')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_NOOP' `
                -Message "Change '$($pathCheck.normalized)' does not alter identity." `
                -Path '$.changes'))
        }
    }

    $required=@((Get-AriaEvolutionProperty $Proposal 'requiredGates' @()))
    foreach($gate in @('manifest','doctor.strict','conformance')){
        if($gate-notin$required){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_GATE_REQUIRED' `
                -Message "Required gate '$gate' is missing." `
                -Path '$.requiredGates'))
        }
    }

    if(@((Get-AriaEvolutionProperty $Proposal 'evidence' @())).Count-eq0){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_EVIDENCE' `
            -Message 'Evolution proposal requires evidence.' `
            -Path '$.evidence'))
    }

    $rollback=@((Get-AriaEvolutionProperty $Proposal 'rollbackPlan' @()))
    foreach($change in $changes){
        $path=[string](Get-AriaEvolutionProperty $change 'path')
        $step=@($rollback | Where-Object {
            [string](Get-AriaEvolutionProperty $_ 'path')-ceq$path
        }) | Select-Object -First 1

        if($null-eq$step){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_ROLLBACK_MISSING' `
                -Message "Rollback step missing for '$path'." `
                -Path '$.rollbackPlan'))
            continue
        }

        if([string](Get-AriaEvolutionProperty $step 'expectedDigest')-cne
           [string](Get-AriaEvolutionProperty $change 'afterDigest')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_ROLLBACK_EXPECTED' `
                -Message "Rollback expected digest mismatch for '$path'." `
                -Path '$.rollbackPlan.expectedDigest'))
        }

        if([string](Get-AriaEvolutionProperty $step 'restoreDigest')-cne
           [string](Get-AriaEvolutionProperty $change 'beforeDigest')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_ROLLBACK_RESTORE' `
                -Message "Rollback restore digest mismatch for '$path'." `
                -Path '$.rollbackPlan.restoreDigest'))
        }
    }

    $signature=Get-AriaEvolutionProperty $Proposal 'signature'
    if([string](Get-AriaEvolutionProperty $signature 'algorithm')-ne'none' -or
       -not[string]::IsNullOrEmpty([string](Get-AriaEvolutionProperty $signature 'value'))){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_SIGNATURE_MODE' `
            -Message 'Alpha.20 accepts only the reserved unsigned proposal signature form.' `
            -Path '$.signature'))
    }

    $identity=Get-AriaEvolutionProposalIdentityInput $Proposal
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaEvolutionProperty $Proposal 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_IDENTITY' `
            -Message 'Evolution proposal identity mismatch.' `
            -Path '$.id'))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        expectedId=$expected
    }
}

function Get-AriaEvolutionAuthorizationIdentityInput {
    param([Parameter(Mandatory=$true)]$Authorization)

    [ordered]@{
        schema=Get-AriaEvolutionProperty $Authorization 'schema'
        proposalId=Get-AriaEvolutionProperty $Authorization 'proposalId'
        authorizer=Get-AriaEvolutionProperty $Authorization 'authorizer'
        decision=Get-AriaEvolutionProperty $Authorization 'decision'
        decidedAt=Get-AriaEvolutionProperty $Authorization 'decidedAt'
        nonce=Get-AriaEvolutionProperty $Authorization 'nonce'
        signature=Get-AriaEvolutionProperty $Authorization 'signature'
    }
}

function New-AriaEvolutionAuthorization {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string]$Authorizer,
        [Parameter(Mandatory=$true)][ValidateSet('approved','rejected')][string]$Decision,
        [Parameter(Mandatory=$true)][string]$DecidedAt,
        [Parameter(Mandatory=$true)][string]$Nonce,
        [object]$Signature=$null
    )

    if($null-eq$Signature){
        $Signature=[pscustomobject][ordered]@{
            algorithm='none'
            value=''
        }
    }

    $identity=[ordered]@{
        schema='aria.evolution-authorization/0.6'
        proposalId=$ProposalId
        authorizer=$Authorizer
        decision=$Decision
        decidedAt=ConvertTo-AriaUtcTimestamp $DecidedAt
        nonce=$Nonce
        signature=$Signature
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        proposalId=$identity.proposalId
        authorizer=$identity.authorizer
        decision=$identity.decision
        decidedAt=$identity.decidedAt
        nonce=$identity.nonce
        signature=$identity.signature
        id=$id
    }
}

function Test-AriaEvolutionAuthorization {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Authorization,
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string[]]$TrustedAuthorizers
    )

    $errors=New-Object 'System.Collections.Generic.List[object]'

    if([string](Get-AriaEvolutionProperty $Authorization 'schema')-ne'aria.evolution-authorization/0.6'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTH_SCHEMA' `
            -Message 'Unsupported evolution authorization schema.' `
            -Path '$.schema'))
    }

    if([string](Get-AriaEvolutionProperty $Authorization 'proposalId')-cne$ProposalId){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTH_PROPOSAL' `
            -Message 'Human authorization references a different proposal.' `
            -Path '$.proposalId'))
    }

    if([string](Get-AriaEvolutionProperty $Authorization 'authorizer')-notin$TrustedAuthorizers){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTHORIZER' `
            -Message 'Evolution authorizer is not trusted.' `
            -Path '$.authorizer'))
    }

    if([string](Get-AriaEvolutionProperty $Authorization 'decision')-ne'approved'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_NOT_APPROVED' `
            -Message 'Evolution proposal is not human-approved.' `
            -Path '$.decision'))
    }

    try{$null=ConvertTo-AriaUtcTimestamp ([string](Get-AriaEvolutionProperty $Authorization 'decidedAt'))}
    catch{
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTH_TIME' `
            -Message 'Evolution authorization time is invalid.' `
            -Path '$.decidedAt'))
    }

    $signature=Get-AriaEvolutionProperty $Authorization 'signature'
    if([string](Get-AriaEvolutionProperty $signature 'algorithm')-ne'none' -or
       -not[string]::IsNullOrEmpty([string](Get-AriaEvolutionProperty $signature 'value'))){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTH_SIGNATURE_MODE' `
            -Message 'Alpha.20 accepts only the reserved unsigned authorization signature form.' `
            -Path '$.signature'))
    }

    $identity=Get-AriaEvolutionAuthorizationIdentityInput $Authorization
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaEvolutionProperty $Authorization 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_AUTH_IDENTITY' `
            -Message 'Evolution authorization identity mismatch.' `
            -Path '$.id'))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        expectedId=$expected
    }
}

function Invoke-AriaEvolutionChanges {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Snapshot,
        [Parameter(Mandatory=$true)][object[]]$Changes
    )

    $validation=Test-AriaRepositorySnapshot $Snapshot
    if(-not[bool]$validation.valid){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@($validation.errors)
            snapshot=$Snapshot
        }
    }

    $map=Get-AriaEvolutionSnapshotMap $Snapshot
    $errors=New-Object 'System.Collections.Generic.List[object]'

    foreach($change in @($Changes | Sort-Object path)){
        $path=[string](Get-AriaEvolutionProperty $change 'path')
        $existing=$null
        if($map.ContainsKey($path)){$existing=$map[$path]}
        $actualBefore=Get-AriaEvolutionContentDigest $existing
        $expectedBefore=[string](Get-AriaEvolutionProperty $change 'beforeDigest')

        if($actualBefore-cne$expectedBefore){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_BASE_DIGEST' `
                -Message "Current content for '$path' does not match the proposal base." `
                -Path '$.changes.beforeDigest' `
                -Evidence @{expected=$expectedBefore;actual=$actualBefore}))
            continue
        }

        $operation=[string](Get-AriaEvolutionProperty $change 'operation')
        if($operation-eq'write'){
            $map[$path]=[string](Get-AriaEvolutionProperty $change 'content')
        }
        elseif($operation-eq'delete'){
            [void]$map.Remove($path)
        }
        else{
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_OPERATION' `
                -Message "Unsupported operation '$operation'." `
                -Path '$.changes.operation'))
            continue
        }

        $after=$null
        if($map.ContainsKey($path)){$after=$map[$path]}
        $actualAfter=Get-AriaEvolutionContentDigest $after
        if($actualAfter-cne[string](Get-AriaEvolutionProperty $change 'afterDigest')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_EVOLUTION_APPLY_DIGEST' `
                -Message "Applied content for '$path' does not match the proposal." `
                -Path '$.changes.afterDigest'))
        }
    }

    if($errors.Count){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@($errors.ToArray())
            snapshot=$Snapshot
        }
    }

    $files=New-Object 'System.Collections.Generic.List[object]'
    foreach($path in @($map.Keys | Sort-Object)){
        [void]$files.Add([pscustomobject][ordered]@{
            path=$path
            content=[string]$map[$path]
        })
    }

    [pscustomobject][ordered]@{
        valid=$true
        errors=@()
        snapshot=New-AriaRepositorySnapshot -Files @($files.ToArray())
    }
}

function Test-AriaEvolutionRollback {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$OriginalSnapshot,
        [Parameter(Mandatory=$true)]$CandidateSnapshot,
        [Parameter(Mandatory=$true)][object[]]$RollbackPlan
    )

    $changes=New-Object 'System.Collections.Generic.List[object]'
    foreach($step in @($RollbackPlan)){
        [void]$changes.Add([pscustomobject][ordered]@{
            path=[string](Get-AriaEvolutionProperty $step 'path')
            operation=[string](Get-AriaEvolutionProperty $step 'operation')
            beforeDigest=[string](Get-AriaEvolutionProperty $step 'expectedDigest')
            afterDigest=[string](Get-AriaEvolutionProperty $step 'restoreDigest')
            content=Get-AriaEvolutionProperty $step 'content'
        })
    }

    $rolled=Invoke-AriaEvolutionChanges -Snapshot $CandidateSnapshot -Changes @($changes.ToArray())
    if(-not[bool]$rolled.valid){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@($rolled.errors)
            restoredSnapshot=$CandidateSnapshot
        }
    }

    $valid=[string](Get-AriaEvolutionProperty $rolled.snapshot 'id')-ceq
           [string](Get-AriaEvolutionProperty $OriginalSnapshot 'id')

    $errors=@()
    if(-not$valid){
        $errors=@(New-AriaStructuredError `
            -Code 'E_EVOLUTION_ROLLBACK_IDENTITY' `
            -Message 'Rollback did not reproduce the original repository snapshot.' `
            -Path '$.rollbackPlan')
    }

    [pscustomobject][ordered]@{
        valid=$valid
        errors=$errors
        restoredSnapshot=$rolled.snapshot
    }
}

function New-AriaEvolutionSemanticDiff {
    param(
        [Parameter(Mandatory=$true)]$OriginalSnapshot,
        [Parameter(Mandatory=$true)]$CandidateSnapshot
    )

    $before=Get-AriaEvolutionSnapshotMap $OriginalSnapshot
    $after=Get-AriaEvolutionSnapshotMap $CandidateSnapshot
    $added=New-Object 'System.Collections.Generic.List[object]'
    $removed=New-Object 'System.Collections.Generic.List[object]'
    $modified=New-Object 'System.Collections.Generic.List[object]'

    foreach($path in @($after.Keys | Sort-Object)){
        if(-not$before.ContainsKey($path)){
            [void]$added.Add([pscustomobject][ordered]@{
                path=$path
                digest=Get-AriaEvolutionContentDigest $after[$path]
            })
        }
        elseif((Get-AriaEvolutionContentDigest $before[$path])-cne(Get-AriaEvolutionContentDigest $after[$path])){
            [void]$modified.Add([pscustomobject][ordered]@{
                path=$path
                beforeDigest=Get-AriaEvolutionContentDigest $before[$path]
                afterDigest=Get-AriaEvolutionContentDigest $after[$path]
            })
        }
    }

    foreach($path in @($before.Keys | Sort-Object)){
        if(-not$after.ContainsKey($path)){
            [void]$removed.Add([pscustomobject][ordered]@{
                path=$path
                digest=Get-AriaEvolutionContentDigest $before[$path]
            })
        }
    }

    [pscustomobject][ordered]@{
        added=@($added.ToArray())
        removed=@($removed.ToArray())
        modified=@($modified.ToArray())
    }
}

function Invoke-AriaGovernedEvolutionPlan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Proposal,
        [Parameter(Mandatory=$true)]$Authorization,
        [Parameter(Mandatory=$true)]$CapabilityToken,
        [object[]]$KnownTokens=@(),
        [Parameter(Mandatory=$true)]$IssuerPolicy,
        [object]$RevocationLedger=$null,
        [Parameter(Mandatory=$true)][string]$DecisionTime,
        [Parameter(Mandatory=$true)][string[]]$TrustedAuthorizers,
        [Parameter(Mandatory=$true)][string]$CurrentCommit,
        [Parameter(Mandatory=$true)]$CurrentSnapshot
    )

    if($null-eq$RevocationLedger){$RevocationLedger=New-AriaRevocationLedger}

    $errors=New-Object 'System.Collections.Generic.List[object]'

    $proposalValidation=Test-AriaEvolutionProposal $Proposal
    foreach($error in @($proposalValidation.errors)){[void]$errors.Add($error)}

    if([string](Get-AriaEvolutionProperty $Proposal 'baseCommit').ToLowerInvariant()-cne$CurrentCommit.ToLowerInvariant()){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_BASE_COMMIT' `
            -Message 'Current commit does not match the proposal base commit.' `
            -Path '$.baseCommit' `
            -Evidence @{expected=Get-AriaEvolutionProperty $Proposal 'baseCommit';actual=$CurrentCommit}))
    }

    $authorizationValidation=Test-AriaEvolutionAuthorization `
        -Authorization $Authorization `
        -ProposalId ([string](Get-AriaEvolutionProperty $Proposal 'id')) `
        -TrustedAuthorizers $TrustedAuthorizers
    foreach($error in @($authorizationValidation.errors)){[void]$errors.Add($error)}

    if([string](Get-AriaEvolutionProperty $CapabilityToken 'id')-notin
       @((Get-AriaEvolutionProperty $Proposal 'capabilityIds' @()))){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_EVOLUTION_CAPABILITY_REFERENCE' `
            -Message 'Supplied capability token is not referenced by the proposal.' `
            -Path '$.capabilityIds'))
    }

    $authority=New-AriaAuthorityDecision `
        -Token $CapabilityToken `
        -KnownTokens $KnownTokens `
        -Policy $IssuerPolicy `
        -Subject ([string](Get-AriaEvolutionProperty $Proposal 'proposer')) `
        -Resource ([string](Get-AriaEvolutionProperty $Proposal 'resource')) `
        -RequestedEffects @((Get-AriaEvolutionProperty $Proposal 'requestedEffects' @())) `
        -DecisionTime $DecisionTime `
        -RevocationLedger $RevocationLedger

    foreach($error in @($authority.errors)){[void]$errors.Add($error)}

    $snapshotValidation=Test-AriaRepositorySnapshot $CurrentSnapshot
    foreach($error in @($snapshotValidation.errors)){[void]$errors.Add($error)}

    if($errors.Count){
        return [pscustomobject][ordered]@{
            approved=$false
            errors=@($errors.ToArray())
            candidateSnapshot=$CurrentSnapshot
            semanticDiff=$null
            rollbackVerified=$false
            authorityDecision=$authority.decision
            event=$null
        }
    }

    $candidate=Invoke-AriaEvolutionChanges `
        -Snapshot $CurrentSnapshot `
        -Changes @((Get-AriaEvolutionProperty $Proposal 'changes' @()))

    if(-not[bool]$candidate.valid){
        return [pscustomobject][ordered]@{
            approved=$false
            errors=@($candidate.errors)
            candidateSnapshot=$CurrentSnapshot
            semanticDiff=$null
            rollbackVerified=$false
            authorityDecision=$authority.decision
            event=$null
        }
    }

    $rollback=Test-AriaEvolutionRollback `
        -OriginalSnapshot $CurrentSnapshot `
        -CandidateSnapshot $candidate.snapshot `
        -RollbackPlan @((Get-AriaEvolutionProperty $Proposal 'rollbackPlan' @()))

    if(-not[bool]$rollback.valid){
        return [pscustomobject][ordered]@{
            approved=$false
            errors=@($rollback.errors)
            candidateSnapshot=$candidate.snapshot
            semanticDiff=New-AriaEvolutionSemanticDiff -OriginalSnapshot $CurrentSnapshot -CandidateSnapshot $candidate.snapshot
            rollbackVerified=$false
            authorityDecision=$authority.decision
            event=$null
        }
    }

    $semanticDiff=New-AriaEvolutionSemanticDiff `
        -OriginalSnapshot $CurrentSnapshot `
        -CandidateSnapshot $candidate.snapshot

    $eventIdentity=[ordered]@{
        type='aria.evolution.plan.approved'
        proposalId=[string](Get-AriaEvolutionProperty $Proposal 'id')
        authorizationId=[string](Get-AriaEvolutionProperty $Authorization 'id')
        authorityDecisionId=[string](Get-AriaEvolutionProperty $authority.decision 'id')
        baseCommit=$CurrentCommit.ToLowerInvariant()
        originalSnapshotId=[string](Get-AriaEvolutionProperty $CurrentSnapshot 'id')
        candidateSnapshotId=[string](Get-AriaEvolutionProperty $candidate.snapshot 'id')
        semanticDiff=$semanticDiff
        rollbackVerified=$true
        requiredGates=@((Get-AriaEvolutionProperty $Proposal 'requiredGates' @()))
    }
    $eventId="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $eventIdentity))"

    $event=[pscustomobject][ordered]@{
        type=$eventIdentity.type
        proposalId=$eventIdentity.proposalId
        authorizationId=$eventIdentity.authorizationId
        authorityDecisionId=$eventIdentity.authorityDecisionId
        baseCommit=$eventIdentity.baseCommit
        originalSnapshotId=$eventIdentity.originalSnapshotId
        candidateSnapshotId=$eventIdentity.candidateSnapshotId
        semanticDiff=$eventIdentity.semanticDiff
        rollbackVerified=$eventIdentity.rollbackVerified
        requiredGates=@($eventIdentity.requiredGates)
        id=$eventId
    }

    [pscustomobject][ordered]@{
        approved=$true
        errors=@()
        candidateSnapshot=$candidate.snapshot
        semanticDiff=$semanticDiff
        rollbackVerified=$true
        authorityDecision=$authority.decision
        event=$event
    }
}

Export-ModuleMember -Function `
    Get-AriaEvolutionContentDigest, `
    Test-AriaEvolutionPath, `
    New-AriaRepositorySnapshot, `
    Test-AriaRepositorySnapshot, `
    New-AriaEvolutionChange, `
    New-AriaEvolutionRollbackStep, `
    New-AriaEvolutionProposal, `
    Test-AriaEvolutionProposal, `
    New-AriaEvolutionAuthorization, `
    Test-AriaEvolutionAuthorization, `
    Invoke-AriaEvolutionChanges, `
    Test-AriaEvolutionRollback, `
    New-AriaEvolutionSemanticDiff, `
    Invoke-AriaGovernedEvolutionPlan