Set-StrictMode -Version Latest

$typedCorePath=Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if(-not(Get-Module Aria.TypedCore)){Import-Module $typedCorePath -DisableNameChecking}
$authorityPath=Join-Path $PSScriptRoot 'Aria.CapabilityAuthority.psm1'
if(-not(Get-Module Aria.CapabilityAuthority)){Import-Module $authorityPath -DisableNameChecking}

function Get-AriaIntentProperty {
    param($Object,[string]$Name,$Default=$null)
    if($null-eq$Object){return $Default}
    $property=$Object.PSObject.Properties|Where-Object{$_.Name-ceq$Name}|Select-Object -First 1
    if($null-eq$property){return $Default}
    $property.Value
}

function New-AriaIntentIdentity {
    param([string]$Schema,$Fields)
    $identity=[ordered]@{schema=$Schema}
    foreach($entry in $Fields.GetEnumerator()){$identity[$entry.Key]=$entry.Value}
    [pscustomobject][ordered]@{
        identity=$identity
        id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    }
}

function Test-AriaIntentIdentity {
    param($Artifact,[string]$Schema,[string[]]$Fields,[string]$CodePrefix)
    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaIntentProperty $Artifact 'schema')-cne$Schema){
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
    if([string](Get-AriaIntentProperty $Artifact 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError -Code ($CodePrefix+'_IDENTITY') -Message 'Artifact identity mismatch.' -Path '$.id'))
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$expected}
}

function New-AriaIntent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Objective,
        [string[]]$Assumptions=@(),
        [object[]]$RequiredOutcomes=@(),
        [string[]]$ForbiddenOutcomes=@(),
        [string[]]$AllowedEffects=@(),
        [object[]]$AcceptanceCriteria=@(),
        [object[]]$Ambiguities=@(),
        [switch]$RequireIndependentChallenge
    )
    $fields=[ordered]@{
        name=$Name
        objective=$Objective
        assumptions=@($Assumptions|Sort-Object -Unique)
        requiredOutcomes=@($RequiredOutcomes|Sort-Object id)
        forbiddenOutcomes=@($ForbiddenOutcomes|Sort-Object -Unique)
        allowedEffects=@($AllowedEffects|Sort-Object -Unique)
        acceptanceCriteria=@($AcceptanceCriteria|Sort-Object id)
        ambiguities=@($Ambiguities|Sort-Object id)
        requireIndependentChallenge=[bool]$RequireIndependentChallenge
    }
    $result=New-AriaIntentIdentity 'aria.intent/0.9' $fields
    $artifact=[ordered]@{}
    foreach($entry in $result.identity.GetEnumerator()){$artifact[$entry.Key]=$entry.Value}
    $artifact.id=$result.id
    [pscustomobject]$artifact
}

function Test-AriaIntent {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Intent)

    $identity=Test-AriaIntentIdentity $Intent 'aria.intent/0.9' @(
        'name','objective','assumptions','requiredOutcomes','forbiddenOutcomes',
        'allowedEffects','acceptanceCriteria','ambiguities','requireIndependentChallenge'
    ) 'E_INTENT'
    $errors=New-Object 'System.Collections.Generic.List[object]'
    foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    foreach($field in @('name','objective')){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $Intent $field))){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_FIELD' -Message "Intent field '$field' is required." -Path ("$.{0}"-f$field)))
        }
    }
    $ids=@{}
    foreach($item in @((Get-AriaIntentProperty $Intent 'requiredOutcomes' @()))){
        $id=[string](Get-AriaIntentProperty $item 'id')
        if([string]::IsNullOrWhiteSpace($id) -or $null-eq($item.PSObject.Properties|Where-Object{$_.Name-ceq'expected'}|Select-Object -First 1)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_OUTCOME' -Message 'Required outcomes need id and expected.' -Path '$.requiredOutcomes'))
        }
        elseif($ids.ContainsKey($id)){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_DUPLICATE' -Message "Duplicate obligation '$id'." -Path '$.requiredOutcomes'))}
        else{$ids[$id]=$true}
    }
    foreach($item in @((Get-AriaIntentProperty $Intent 'acceptanceCriteria' @()))){
        $id=[string](Get-AriaIntentProperty $item 'id')
        if([string]::IsNullOrWhiteSpace($id) -or [string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $item 'evidenceKind'))){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_CRITERION' -Message 'Acceptance criteria need id and evidenceKind.' -Path '$.acceptanceCriteria'))
        }
        elseif($ids.ContainsKey($id)){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_DUPLICATE' -Message "Duplicate obligation '$id'." -Path '$.acceptanceCriteria'))}
        else{$ids[$id]=$true}
    }
    $ambiguities=@{}
    foreach($item in @((Get-AriaIntentProperty $Intent 'ambiguities' @()))){
        $id=[string](Get-AriaIntentProperty $item 'id')
        $severity=[string](Get-AriaIntentProperty $item 'severity')
        if([string]::IsNullOrWhiteSpace($id) -or [string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $item 'question')) -or $severity-notin@('minor','material')){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_AMBIGUITY' -Message 'Ambiguities need id, question, and minor or material severity.' -Path '$.ambiguities'))
        }
        elseif($ambiguities.ContainsKey($id)){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_DUPLICATE' -Message "Duplicate ambiguity '$id'." -Path '$.ambiguities'))}
        else{$ambiguities[$id]=$true}
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

function New-AriaIntentInterpretation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$IntentId,
        [Parameter(Mandatory=$true)][string]$Interpreter,
        [Parameter(Mandatory=$true)][string]$UnderstoodObjective,
        [string[]]$Assumptions=@(),
        [string[]]$ExpectedEffects=@(),
        [string[]]$ClaimedObligations=@(),
        [string[]]$UnresolvedAmbiguities=@(),
        [Parameter(Mandatory=$true)][string]$ImplementationRef
    )
    $fields=[ordered]@{
        intentId=$IntentId
        interpreter=$Interpreter
        understoodObjective=$UnderstoodObjective
        assumptions=@($Assumptions|Sort-Object -Unique)
        expectedEffects=@($ExpectedEffects|Sort-Object -Unique)
        claimedObligations=@($ClaimedObligations|Sort-Object -Unique)
        unresolvedAmbiguities=@($UnresolvedAmbiguities|Sort-Object -Unique)
        implementationRef=$ImplementationRef
    }
    $result=New-AriaIntentIdentity 'aria.intent-interpretation/0.9' $fields
    $artifact=[ordered]@{};foreach($entry in $result.identity.GetEnumerator()){$artifact[$entry.Key]=$entry.Value};$artifact.id=$result.id
    [pscustomobject]$artifact
}

function Test-AriaIntentInterpretation {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Interpretation,[Parameter(Mandatory=$true)]$Intent)
    $identity=Test-AriaIntentIdentity $Interpretation 'aria.intent-interpretation/0.9' @(
        'intentId','interpreter','understoodObjective','assumptions','expectedEffects',
        'claimedObligations','unresolvedAmbiguities','implementationRef'
    ) 'E_INTERPRETATION'
    $errors=New-Object 'System.Collections.Generic.List[object]';foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    if([string]$Interpretation.intentId-cne[string]$Intent.id){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTERPRETATION_INTENT' -Message 'Interpretation references a different intent.' -Path '$.intentId'))}
    foreach($field in @('interpreter','understoodObjective','implementationRef')){
        if([string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $Interpretation $field))){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTERPRETATION_FIELD' -Message "Interpretation field '$field' is required." -Path ("$.{0}"-f$field)))}
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

function New-AriaIntentApproval {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$IntentId,
        [Parameter(Mandatory=$true)][string]$InterpretationId,
        [Parameter(Mandatory=$true)][string]$Approver,
        [Parameter(Mandatory=$true)][ValidateSet('approved','rejected')][string]$Decision,
        [Parameter(Mandatory=$true)][string]$DecidedAt,
        [object[]]$AmbiguityResolutions=@(),
        [object[]]$ChallengeResolutions=@(),
        [Parameter(Mandatory=$true)][string]$Nonce
    )
    $fields=[ordered]@{
        intentId=$IntentId
        interpretationId=$InterpretationId
        approver=$Approver
        decision=$Decision
        decidedAt=ConvertTo-AriaUtcTimestamp $DecidedAt
        ambiguityResolutions=@($AmbiguityResolutions|Sort-Object id)
        challengeResolutions=@($ChallengeResolutions|Sort-Object id)
        nonce=$Nonce
    }
    $result=New-AriaIntentIdentity 'aria.intent-approval/0.9' $fields
    $artifact=[ordered]@{};foreach($entry in $result.identity.GetEnumerator()){$artifact[$entry.Key]=$entry.Value};$artifact.id=$result.id
    [pscustomobject]$artifact
}

function Test-AriaIntentApproval {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Approval,[Parameter(Mandatory=$true)]$Intent,[Parameter(Mandatory=$true)]$Interpretation,[string[]]$TrustedApprovers)
    $identity=Test-AriaIntentIdentity $Approval 'aria.intent-approval/0.9' @(
        'intentId','interpretationId','approver','decision','decidedAt',
        'ambiguityResolutions','challengeResolutions','nonce'
    ) 'E_INTENT_APPROVAL'
    $errors=New-Object 'System.Collections.Generic.List[object]';foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    if([string]$Approval.intentId-cne[string]$Intent.id -or [string]$Approval.interpretationId-cne[string]$Interpretation.id){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_APPROVAL_REFERENCE' -Message 'Approval does not reference the exact intent and interpretation.' -Path '$'))
    }
    if([string]$Approval.decision-cne'approved'){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_NOT_APPROVED' -Message 'Intent interpretation is not approved.' -Path '$.decision'))}
    if([string]$Approval.approver-cnotin$TrustedApprovers){[void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_APPROVER_UNTRUSTED' -Message 'Intent approver is not trusted.' -Path '$.approver'))}
    foreach($collectionName in @('ambiguityResolutions','challengeResolutions')){
        $seen=@{}
        foreach($resolution in @((Get-AriaIntentProperty $Approval $collectionName @()))){
            $resolutionId=[string](Get-AriaIntentProperty $resolution 'id')
            if([string]::IsNullOrWhiteSpace($resolutionId)-or[string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $resolution 'resolution'))){
                [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_RESOLUTION' -Message 'Human resolutions need id and resolution.' -Path ("$.{0}"-f$collectionName)))
            }
            elseif($seen.ContainsKey($resolutionId)){
                [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_DUPLICATE' -Message "Duplicate resolution '$resolutionId'." -Path ("$.{0}"-f$collectionName)))
            }
            else{$seen[$resolutionId]=$true}
        }
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

function New-AriaIntentChallenge {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$IntentId,
        [Parameter(Mandatory=$true)][string]$InterpretationId,
        [Parameter(Mandatory=$true)][string]$Challenger,
        [object[]]$Issues=@()
    )
    $fields=[ordered]@{
        intentId=$IntentId
        interpretationId=$InterpretationId
        challenger=$Challenger
        issues=@($Issues|Sort-Object id)
    }
    $result=New-AriaIntentIdentity 'aria.intent-challenge/0.9' $fields
    $artifact=[ordered]@{};foreach($entry in $result.identity.GetEnumerator()){$artifact[$entry.Key]=$entry.Value};$artifact.id=$result.id
    [pscustomobject]$artifact
}

function Test-AriaIntentChallenge {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Challenge,[Parameter(Mandatory=$true)]$Intent,[Parameter(Mandatory=$true)]$Interpretation)
    $identity=Test-AriaIntentIdentity $Challenge 'aria.intent-challenge/0.9' @('intentId','interpretationId','challenger','issues') 'E_INTENT_CHALLENGE'
    $errors=New-Object 'System.Collections.Generic.List[object]';foreach($error in @($identity.errors)){[void]$errors.Add($error)}
    if([string]$Challenge.intentId-cne[string]$Intent.id -or [string]$Challenge.interpretationId-cne[string]$Interpretation.id){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_CHALLENGE_REFERENCE' -Message 'Challenge references different intent artifacts.' -Path '$'))
    }
    if([string]$Challenge.challenger-ceq[string]$Interpretation.interpreter){
        [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_CHALLENGE_INDEPENDENCE' -Message 'Challenge principal must differ from the interpretation producer.' -Path '$.challenger'))
    }
    $issueIds=@{}
    foreach($issue in @($Challenge.issues)){
        $issueId=[string](Get-AriaIntentProperty $issue 'id')
        if([string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $issue 'id')) -or
           [string](Get-AriaIntentProperty $issue 'severity')-notin@('minor','material') -or
           [string]::IsNullOrWhiteSpace([string](Get-AriaIntentProperty $issue 'message'))){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_CHALLENGE_ISSUE' -Message 'Challenge issues need id, severity, and message.' -Path '$.issues'))
        }
        elseif($issueIds.ContainsKey($issueId)){
            [void]$errors.Add((New-AriaStructuredError -Code 'E_INTENT_DUPLICATE' -Message "Duplicate challenge issue '$issueId'." -Path '$.issues'))
        }
        else{$issueIds[$issueId]=$true}
    }
    [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray());expectedId=$identity.expectedId}
}

Export-ModuleMember -Function `
    New-AriaIntent, `
    Test-AriaIntent, `
    New-AriaIntentInterpretation, `
    Test-AriaIntentInterpretation, `
    New-AriaIntentApproval, `
    Test-AriaIntentApproval, `
    New-AriaIntentChallenge, `
    Test-AriaIntentChallenge
