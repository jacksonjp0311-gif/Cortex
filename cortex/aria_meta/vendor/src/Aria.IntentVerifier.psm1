Set-StrictMode -Version Latest

$typedCorePath=Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if(-not(Get-Module Aria.TypedCore)){Import-Module $typedCorePath -DisableNameChecking}
$commonPath=Join-Path $PSScriptRoot 'Aria.Common.psm1'
if(-not(Get-Module Aria.Common)){Import-Module $commonPath -DisableNameChecking}
$effectsPath=Join-Path $PSScriptRoot 'Aria.Effects.psm1'
if(-not(Get-Module Aria.Effects)){Import-Module $effectsPath -DisableNameChecking}
$bytecodePath=Join-Path $PSScriptRoot 'Aria.Bytecode.psm1'
if(-not(Get-Module Aria.Bytecode)){Import-Module $bytecodePath -DisableNameChecking}
$intentPath=Join-Path $PSScriptRoot 'Aria.Intent.psm1'
if(-not(Get-Module Aria.Intent)){Import-Module $intentPath -DisableNameChecking}

function Get-AriaIntentVerifierProperty {
    param($Object,[string]$Name,$Default=$null)
    if($null-eq$Object){return $Default}
    $property=$Object.PSObject.Properties|Where-Object{$_.Name-ceq$Name}|Select-Object -First 1
    if($null-eq$property){return $Default}
    $property.Value
}

function New-AriaIntentVerifierArtifact {
    param([string]$Schema,$Fields)
    $identity=[ordered]@{schema=$Schema}
    foreach($entry in $Fields.GetEnumerator()){$identity[$entry.Key]=$entry.Value}
    $artifact=[ordered]@{}
    foreach($entry in $identity.GetEnumerator()){$artifact[$entry.Key]=$entry.Value}
    $artifact.id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    [pscustomobject]$artifact
}

function Test-AriaIntentVerifierIdentity {
    param($Artifact,[string]$Schema,[string[]]$Fields,[string]$CodePrefix)
    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaIntentVerifierProperty $Artifact 'schema')-cne$Schema){
        [void]$errors.Add((New-AriaStructuredError -Code ($CodePrefix+'_SCHEMA') -Message "Unsupported artifact schema; expected '$Schema'." -Path '$.schema'))
    }
    $schemaProperty=$Artifact.PSObject.Properties|Where-Object{$_.Name-ceq'schema'}|Select-Object -First 1
    $identity=[ordered]@{schema=$null}
    if($null-ne$schemaProperty){$identity.schema=$schemaProperty.Value}
    foreach($field in $Fields){
        $property=$Artifact.PSObject.Properties|Where-Object{$_.Name-ceq$field}|Select-Object -First 1
        $identity[$field]=$null
        if($null-ne$property){$identity[$field]=$property.Value}
    }
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaIntentVerifierProperty $Artifact 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError -Code ($CodePrefix+'_IDENTITY') -Message 'Artifact identity mismatch.' -Path '$.id'))
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$expected}
}

function New-AriaIntentProgramSummary {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ArtifactId,
        [string[]]$RequestedEffects=@(),
        [object[]]$Outcomes=@(),
        [string[]]$ObservedForbiddenOutcomes=@()
    )
    New-AriaIntentVerifierArtifact 'aria.intent-program-summary/0.9' ([ordered]@{
        artifactId=$ArtifactId
        requestedEffects=@($RequestedEffects|Sort-Object -Unique)
        outcomes=@($Outcomes|Sort-Object id)
        observedForbiddenOutcomes=@($ObservedForbiddenOutcomes|Sort-Object -Unique)
    })
}

function Test-AriaIntentProgramSummary {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Program)
    $schema=[string](Get-AriaIntentVerifierProperty $Program 'schema')
    $fields=@('artifactId','requestedEffects','outcomes','observedForbiddenOutcomes')
    if($schema-ceq'aria.intent-program-summary/1.0'){
        $fields=@('artifactId','effectGraphId','requestedEffects','outcomes','observedForbiddenOutcomes')
    }
    $expectedSchema=$(if($schema-ceq'aria.intent-program-summary/1.0'){'aria.intent-program-summary/1.0'}else{'aria.intent-program-summary/0.9'})
    $identity=Test-AriaIntentVerifierIdentity $Program $expectedSchema $fields 'E_INTENT_PROGRAM'
    $errors=New-Object 'System.Collections.Generic.List[object]'
    foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    if([string]::IsNullOrWhiteSpace([string](Get-AriaIntentVerifierProperty $Program 'artifactId'))){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_PROGRAM_ARTIFACT' -Message 'Program summary requires an artifact identity.' -Path '$.artifactId'))
    }
    $ids=@{}
    foreach($outcome in @((Get-AriaIntentVerifierProperty $Program 'outcomes' @()))){
        $id=[string](Get-AriaIntentVerifierProperty $outcome 'id')
        $actualProperty=$outcome.PSObject.Properties|Where-Object{$_.Name-ceq'actual'}|Select-Object -First 1
        if([string]::IsNullOrWhiteSpace($id)-or$null-eq$actualProperty){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_PROGRAM_OUTCOME' -Message 'Program outcomes need id and actual.' -Path '$.outcomes'))
        }
        elseif($ids.ContainsKey($id)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_PROGRAM_DUPLICATE' -Message "Duplicate program outcome '$id'." -Path '$.outcomes'))
        }
        else{$ids[$id]=$true}
    }
    if($schema-ceq'aria.intent-program-summary/1.0'){
        if([string](Get-AriaIntentVerifierProperty $Program 'artifactId')-notmatch'^sha256:[0-9a-f]{64}$'){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_PROGRAM_ARTIFACT' -Message 'Derived program summary requires a SHA-256 artifact identity.' -Path '$.artifactId'))
        }
        if([string](Get-AriaIntentVerifierProperty $Program 'effectGraphId')-notmatch'^sha256:[0-9a-f]{64}$'){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_PROGRAM_EFFECT_GRAPH' -Message 'Derived program summary requires a verified effect-graph identity.' -Path '$.effectGraphId'))
        }
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

function New-AriaIntentProgramSummaryFromArtifact {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][byte[]]$ArtifactBytes,
        [object[]]$Outcomes=@(),
        [string[]]$ObservedForbiddenOutcomes=@()
    )

    $container=Read-AriaContainerBytes -Bytes $ArtifactBytes
    $verification=Test-AriaBytecodeModel -BytecodeModel $container.bytecode
    if(-not[bool]$verification.valid){
        throw ('Intent program derivation rejected bytecode: '+(@($verification.errors)-join'; '))
    }
    $effectValidation=Test-AriaEffectGraph -Graph $container.bytecode.effectGraph
    if(-not[bool]$effectValidation.valid){
        throw ('Intent program derivation rejected effect graph: '+(@($effectValidation.errors)-join'; '))
    }

    $effects=New-Object 'System.Collections.Generic.List[string]'
    foreach($summary in @($container.bytecode.effectGraph.functions)){
        foreach($effect in @($summary.transitiveEffects)){[void]$effects.Add([string]$effect)}
    }

    New-AriaIntentVerifierArtifact 'aria.intent-program-summary/1.0' ([ordered]@{
        artifactId="sha256:$(Get-AriaSha256Bytes -Bytes $ArtifactBytes)"
        effectGraphId=[string]$container.bytecode.effectGraph.digest
        requestedEffects=@(
            Sort-AriaEffectStringsOrdinal @($effects.ToArray())
        )
        outcomes=@($Outcomes|Sort-Object id)
        observedForbiddenOutcomes=@($ObservedForbiddenOutcomes|Sort-Object -Unique)
    })
}

function New-AriaIntentEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$CriterionId,
        [Parameter(Mandatory=$true)][string]$Kind,
        [Parameter(Mandatory=$true)][string]$SubjectId,
        [Parameter(Mandatory=$true)][string]$Digest,
        [Parameter(Mandatory=$true)][bool]$Passed
    )
    New-AriaIntentVerifierArtifact 'aria.intent-evidence/0.9' ([ordered]@{
        criterionId=$CriterionId
        kind=$Kind
        subjectId=$SubjectId
        digest=$Digest
        passed=$Passed
    })
}

function Test-AriaIntentEvidence {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Evidence)
    $identity=Test-AriaIntentVerifierIdentity $Evidence 'aria.intent-evidence/0.9' @(
        'criterionId','kind','subjectId','digest','passed'
    ) 'E_INTENT_EVIDENCE'
    $errors=New-Object 'System.Collections.Generic.List[object]'
    foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    foreach($field in @('criterionId','kind','subjectId','digest')){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaIntentVerifierProperty $Evidence $field))){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_EVIDENCE_FIELD' -Message "Evidence field '$field' is required." -Path ("$.{0}"-f$field)))
        }
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

function Add-AriaIntentFailure {
    param($Failures,[string]$Code,[string]$Message,[string]$Path)
    [void]$Failures.Add((New-AriaStructuredError -Code $Code -Message $Message -Path $Path))
}

function Invoke-AriaIntentVerification {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Bundle)

    $failures=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaIntentVerifierProperty $Bundle 'schema')-cne'aria.intent-verification-bundle/0.9'){
        Add-AriaIntentFailure $failures 'E_INTENT_BUNDLE_SCHEMA' 'Unsupported intent verification bundle schema.' '$.schema'
    }
    $intent=Get-AriaIntentVerifierProperty $Bundle 'intent'
    $interpretation=Get-AriaIntentVerifierProperty $Bundle 'interpretation'
    $approval=Get-AriaIntentVerifierProperty $Bundle 'approval'
    $program=Get-AriaIntentVerifierProperty $Bundle 'program'
    $policy=Get-AriaIntentVerifierProperty $Bundle 'verificationPolicy'
    $challenges=@((Get-AriaIntentVerifierProperty $Bundle 'challenges' @()))
    $evidence=@((Get-AriaIntentVerifierProperty $Bundle 'evidence' @()))

    $intentCheck=Test-AriaIntent -Intent $intent
    foreach($error in @($intentCheck.errors)){[void]$failures.Add($error)}
    $interpretationCheck=Test-AriaIntentInterpretation -Interpretation $interpretation -Intent $intent
    foreach($error in @($interpretationCheck.errors)){[void]$failures.Add($error)}
    $trustedApprovers=@((Get-AriaIntentVerifierProperty $policy 'trustedApprovers' @()))
    if([string](Get-AriaIntentVerifierProperty $policy 'schema')-cne'aria.intent-verification-policy/0.9'-or$trustedApprovers.Count-eq0){
        Add-AriaIntentFailure $failures 'E_INTENT_POLICY' 'Verification policy requires its supported schema and at least one trusted approver.' '$.verificationPolicy'
    }
    $approvalCheck=Test-AriaIntentApproval -Approval $approval -Intent $intent -Interpretation $interpretation -TrustedApprovers $trustedApprovers
    foreach($error in @($approvalCheck.errors)){[void]$failures.Add($error)}
    $programCheck=Test-AriaIntentProgramSummary -Program $program
    foreach($error in @($programCheck.errors)){[void]$failures.Add($error)}

    $challengeIds=New-Object 'System.Collections.Generic.List[string]'
    $materialChallengeIds=New-Object 'System.Collections.Generic.List[string]'
    foreach($challenge in $challenges){
        $check=Test-AriaIntentChallenge -Challenge $challenge -Intent $intent -Interpretation $interpretation
        foreach($error in @($check.errors)){[void]$failures.Add($error)}
        [void]$challengeIds.Add([string]$challenge.id)
        foreach($issue in @($challenge.issues)){
            if([string]$issue.severity-ceq'material'){[void]$materialChallengeIds.Add([string]$issue.id)}
        }
    }
    if([bool]$intent.requireIndependentChallenge-and$challenges.Count-eq0){
        Add-AriaIntentFailure $failures 'E_INTENT_CHALLENGE_REQUIRED' 'Intent requires an independent challenge artifact.' '$.challenges'
    }

    $allowedEffects=@($intent.allowedEffects)
    foreach($effect in @($interpretation.expectedEffects)){
        if([string]$effect-cnotin$allowedEffects){Add-AriaIntentFailure $failures 'E_INTENT_INTERPRETATION_AUTHORITY' "Interpretation expects undeclared effect '$effect'." '$.interpretation.expectedEffects'}
    }
    foreach($effect in @($program.requestedEffects)){
        if([string]$effect-cnotin$allowedEffects){Add-AriaIntentFailure $failures 'E_INTENT_EXCESS_AUTHORITY' "Program requests undeclared effect '$effect'." '$.program.requestedEffects'}
    }

    $declaredObligations=@(@($intent.requiredOutcomes|ForEach-Object{$_.id})+@($intent.acceptanceCriteria|ForEach-Object{$_.id}))
    foreach($obligation in $declaredObligations){
        if([string]$obligation-cnotin@($interpretation.claimedObligations)){
            Add-AriaIntentFailure $failures 'E_INTENT_OBLIGATION_OMITTED' "Interpretation omitted declared obligation '$obligation'." '$.interpretation.claimedObligations'
        }
    }

    $ambiguityResolutionIds=@($approval.ambiguityResolutions|ForEach-Object{$_.id})
    foreach($ambiguity in @($intent.ambiguities)){
        if([string]$ambiguity.severity-ceq'material'-and[string]$ambiguity.id-cnotin$ambiguityResolutionIds){
            Add-AriaIntentFailure $failures 'E_INTENT_AMBIGUITY_UNRESOLVED' "Material ambiguity '$($ambiguity.id)' has no human resolution." '$.approval.ambiguityResolutions'
        }
    }
    $challengeResolutionIds=@($approval.challengeResolutions|ForEach-Object{$_.id})
    foreach($issueId in $materialChallengeIds){
        if([string]$issueId-cnotin$challengeResolutionIds){
            Add-AriaIntentFailure $failures 'E_INTENT_CHALLENGE_UNRESOLVED' "Material challenge '$issueId' has no human resolution." '$.approval.challengeResolutions'
        }
    }

    $obligations=New-Object 'System.Collections.Generic.List[object]'
    foreach($required in @($intent.requiredOutcomes)){
        $actual=@($program.outcomes|Where-Object{[string]$_.id-ceq[string]$required.id})
        $passed=$actual.Count-eq1-and(ConvertTo-AriaStableJson $actual[0].actual)-ceq(ConvertTo-AriaStableJson $required.expected)
        [void]$obligations.Add([pscustomobject][ordered]@{id=[string]$required.id;kind='required-outcome';satisfied=$passed})
        if(-not$passed){Add-AriaIntentFailure $failures 'E_INTENT_REQUIRED_OUTCOME' "Required outcome '$($required.id)' is absent or does not match." '$.program.outcomes'}
    }
    foreach($forbidden in @($intent.forbiddenOutcomes)){
        $passed=[string]$forbidden-cnotin@($program.observedForbiddenOutcomes)
        [void]$obligations.Add([pscustomobject][ordered]@{id=[string]$forbidden;kind='forbidden-outcome';satisfied=$passed})
        if(-not$passed){Add-AriaIntentFailure $failures 'E_INTENT_FORBIDDEN_OUTCOME' "Forbidden outcome '$forbidden' was observed." '$.program.observedForbiddenOutcomes'}
    }

    $evidenceIds=New-Object 'System.Collections.Generic.List[string]'
    foreach($item in $evidence){
        $check=Test-AriaIntentEvidence -Evidence $item
        foreach($error in @($check.errors)){[void]$failures.Add($error)}
        [void]$evidenceIds.Add([string]$item.id)
    }
    foreach($criterion in @($intent.acceptanceCriteria)){
        $matches=@($evidence|Where-Object{
            [string]$_.criterionId-ceq[string]$criterion.id-and
            [string]$_.kind-ceq[string]$criterion.evidenceKind-and
            [string]$_.subjectId-ceq[string]$program.artifactId-and
            [bool]$_.passed
        })
        $passed=$matches.Count-gt0
        [void]$obligations.Add([pscustomobject][ordered]@{id=[string]$criterion.id;kind='acceptance-evidence';satisfied=$passed})
        if(-not$passed){Add-AriaIntentFailure $failures 'E_INTENT_EVIDENCE_MISSING' "Acceptance criterion '$($criterion.id)' lacks passing evidence of the required kind." '$.evidence'}
    }

    $reasonCodes=@($failures|ForEach-Object{$_.code}|Sort-Object -Unique)
    $proof=New-AriaIntentVerifierArtifact 'aria.intent-proof/0.9' ([ordered]@{
        intentId=[string]$intent.id
        interpretationId=[string]$interpretation.id
        approvalId=[string]$approval.id
        challengeIds=@($challengeIds.ToArray()|Sort-Object -Unique)
        programId=[string]$program.id
        evidenceIds=@($evidenceIds.ToArray()|Sort-Object -Unique)
        verdict=$(if($failures.Count-eq0){'satisfied'}else{'rejected'})
        reasonCodes=$reasonCodes
        obligations=@($obligations.ToArray()|Sort-Object kind,id)
    })
    [pscustomobject][ordered]@{
        satisfied=($failures.Count-eq0)
        errors=@($failures.ToArray())
        proof=$proof
    }
}

function Write-AriaIntentProof {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Proof,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot
    )
    $intentId=[string]$Proof.intentId
    $safeIntent=$intentId.Replace('sha256:','')
    $safeProof=([string]$Proof.id).Replace('sha256:','')
    $directory=Join-Path $WorkspaceRoot ('.aria/intent/{0}'-f$safeIntent)
    New-Item -ItemType Directory -Path $directory -Force|Out-Null
    $path=Join-Path $directory ($safeProof+'.json')
    Write-AriaUtf8NoBom -Path $path -Text (ConvertTo-AriaJson -Value $Proof)
    $path
}

function Invoke-AriaIntentVerificationFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot
    )
    $resolved=(Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    $bundle=Read-AriaUtf8Text -Path $resolved|ConvertFrom-Json
    $result=Invoke-AriaIntentVerification -Bundle $bundle
    $proofPath=Write-AriaIntentProof -Proof $result.proof -WorkspaceRoot $WorkspaceRoot
    [pscustomobject][ordered]@{
        satisfied=$result.satisfied
        errors=$result.errors
        proof=$result.proof
        proofPath=$proofPath
    }
}

Export-ModuleMember -Function `
    New-AriaIntentProgramSummary, `
    New-AriaIntentProgramSummaryFromArtifact, `
    Test-AriaIntentProgramSummary, `
    New-AriaIntentEvidence, `
    Test-AriaIntentEvidence, `
    Invoke-AriaIntentVerification, `
    Write-AriaIntentProof, `
    Invoke-AriaIntentVerificationFile
