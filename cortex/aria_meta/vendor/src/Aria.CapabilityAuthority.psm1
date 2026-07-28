Set-StrictMode -Version Latest

$typedCorePath = Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if (-not (Get-Module Aria.TypedCore)) {
    Import-Module $typedCorePath -DisableNameChecking
}

$graphCorePath = Join-Path $PSScriptRoot 'Aria.GraphCore.psm1'
if (-not (Get-Module Aria.GraphCore)) {
    Import-Module $graphCorePath -DisableNameChecking
}

function Get-AriaPropertyValue {
    param(
        [object]$Object,
        [Parameter(Mandatory=$true)][string]$Name,
        [object]$Default = $null
    )

    if($null-eq$Object){return $Default}
    $property=$Object.PSObject.Properties[$Name]
    if($null-eq$property){return $Default}
    return $property.Value
}

function ConvertTo-AriaUtcTimestamp {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Value)

    $styles = [Globalization.DateTimeStyles]::AssumeUniversal -bor
              [Globalization.DateTimeStyles]::AdjustToUniversal
    $parsed = [DateTimeOffset]::Parse(
        $Value,
        [Globalization.CultureInfo]::InvariantCulture,
        $styles
    )
    $parsed.ToUniversalTime().ToString(
        'yyyy-MM-ddTHH:mm:ss.fffffffZ',
        [Globalization.CultureInfo]::InvariantCulture
    )
}

function Get-AriaCapabilityIdentityInput {
    param([Parameter(Mandatory=$true)]$Token)

    [ordered]@{
        schema = Get-AriaPropertyValue $Token 'schema'
        issuer = Get-AriaPropertyValue $Token 'issuer'
        subject = Get-AriaPropertyValue $Token 'subject'
        resource = Get-AriaPropertyValue $Token 'resource'
        effects = @((Get-AriaPropertyValue $Token 'effects' @()))
        notBefore = Get-AriaPropertyValue $Token 'notBefore'
        expiresAt = Get-AriaPropertyValue $Token 'expiresAt'
        delegationDepth = Get-AriaPropertyValue $Token 'delegationDepth' 0
        parent = Get-AriaPropertyValue $Token 'parent'
        nonce = Get-AriaPropertyValue $Token 'nonce'
        singleUse = [bool](Get-AriaPropertyValue $Token 'singleUse' $false)
        signature = Get-AriaPropertyValue $Token 'signature'
    }
}

function New-AriaCapabilityToken {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Issuer,
        [Parameter(Mandatory=$true)][string]$Subject,
        [Parameter(Mandatory=$true)][string]$Resource,
        [Parameter(Mandatory=$true)][string[]]$Effects,
        [Parameter(Mandatory=$true)][string]$NotBefore,
        [Parameter(Mandatory=$true)][string]$ExpiresAt,
        [Parameter(Mandatory=$true)][string]$Nonce,
        [ValidateRange(0,64)][int]$DelegationDepth = 0,
        [object]$Parent = $null,
        [switch]$SingleUse,
        [object]$Signature = $null
    )

    if([string]::IsNullOrWhiteSpace($Issuer)){throw 'Capability issuer is required.'}
    if([string]::IsNullOrWhiteSpace($Subject)){throw 'Capability subject is required.'}
    if([string]::IsNullOrWhiteSpace($Resource)){throw 'Capability resource is required.'}
    if(@($Effects).Count-eq0){throw 'Capability effects are required.'}
    if([string]::IsNullOrWhiteSpace($Nonce)){throw 'Capability nonce is required.'}

    $normalizedNotBefore=ConvertTo-AriaUtcTimestamp $NotBefore
    $normalizedExpiresAt=ConvertTo-AriaUtcTimestamp $ExpiresAt
    if([DateTimeOffset]::Parse($normalizedExpiresAt)-le[DateTimeOffset]::Parse($normalizedNotBefore)){
        throw 'Capability expiration must be after activation.'
    }

    if($null-eq$Signature){
        $Signature=[pscustomobject][ordered]@{
            algorithm='none'
            value=''
        }
    }

    $identity=[ordered]@{
        schema='aria.capability/0.5'
        issuer=$Issuer
        subject=$Subject
        resource=$Resource
        effects=@($Effects | Sort-Object -Unique)
        notBefore=$normalizedNotBefore
        expiresAt=$normalizedExpiresAt
        delegationDepth=$DelegationDepth
        parent=$Parent
        nonce=$Nonce
        singleUse=[bool]$SingleUse
        signature=$Signature
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        issuer=$identity.issuer
        subject=$identity.subject
        resource=$identity.resource
        effects=@($identity.effects)
        notBefore=$identity.notBefore
        expiresAt=$identity.expiresAt
        delegationDepth=$identity.delegationDepth
        parent=$identity.parent
        nonce=$identity.nonce
        singleUse=$identity.singleUse
        signature=$identity.signature
        id=$id
    }
}

function Test-AriaCapabilityTokenIdentity {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Token)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $schema=[string](Get-AriaPropertyValue $Token 'schema')
    if($schema-ne'aria.capability/0.5'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_SCHEMA' `
            -Message 'Unsupported capability schema.' `
            -Path '$.schema'))
    }

    foreach($field in @('issuer','subject','resource','nonce')){
        $value=[string](Get-AriaPropertyValue $Token $field)
        if([string]::IsNullOrWhiteSpace($value)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_FIELD' `
                -Message "Capability field '$field' is required." `
                -Path ("$.{0}" -f $field)))
        }
    }

    if(@((Get-AriaPropertyValue $Token 'effects' @())).Count-eq0){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_EFFECTS' `
            -Message 'Capability requires at least one effect.' `
            -Path '$.effects'))
    }

    try{
        $notBefore=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $Token 'notBefore'))
        $expiresAt=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $Token 'expiresAt'))
        if([DateTimeOffset]::Parse($expiresAt)-le[DateTimeOffset]::Parse($notBefore)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_INTERVAL' `
                -Message 'Capability expiration must be after activation.' `
                -Path '$.expiresAt'))
        }
    }
    catch{
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_TIME' `
            -Message 'Capability time is invalid.' `
            -Path '$.notBefore'))
    }

    $depth=[int](Get-AriaPropertyValue $Token 'delegationDepth' 0)
    $parent=Get-AriaPropertyValue $Token 'parent'
    if($depth-eq0 -and $null-ne$parent){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_PARENT_DEPTH' `
            -Message 'Root capability cannot declare a parent.' `
            -Path '$.parent'))
    }
    if($depth-gt0 -and [string]::IsNullOrWhiteSpace([string]$parent)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_PARENT_REQUIRED' `
            -Message 'Delegated capability requires a parent identity.' `
            -Path '$.parent'))
    }

    $signature=Get-AriaPropertyValue $Token 'signature'
    $algorithm=[string](Get-AriaPropertyValue $signature 'algorithm')
    $signatureValue=[string](Get-AriaPropertyValue $signature 'value')
    if($algorithm-ne'none' -or -not[string]::IsNullOrEmpty($signatureValue)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_SIGNATURE_MODE' `
            -Message 'Alpha.19 accepts only the reserved unsigned signature form.' `
            -Path '$.signature'))
    }

    $identity=Get-AriaCapabilityIdentityInput $Token
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaPropertyValue $Token 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_IDENTITY' `
            -Message 'Capability identity mismatch.' `
            -Path '$.id' `
            -Evidence @{
                expected=$expected
                actual=[string](Get-AriaPropertyValue $Token 'id')
            }))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        expectedId=$expected
    }
}

function New-AriaIssuerTrustPolicy {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string[]]$TrustedIssuers,
        [ValidateRange(0,64)][int]$MaxDelegationDepth = 0
    )

    $identity=[ordered]@{
        schema='aria.issuer-trust/0.5'
        trustedIssuers=@($TrustedIssuers | Sort-Object -Unique)
        maxDelegationDepth=$MaxDelegationDepth
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        trustedIssuers=@($identity.trustedIssuers)
        maxDelegationDepth=$identity.maxDelegationDepth
        id=$id
    }
}

function Test-AriaIssuerTrustPolicy {
    param([Parameter(Mandatory=$true)]$Policy)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    if([string](Get-AriaPropertyValue $Policy 'schema')-ne'aria.issuer-trust/0.5'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_POLICY_SCHEMA' `
            -Message 'Unsupported issuer trust policy schema.' `
            -Path '$.schema'))
    }

    $identity=[ordered]@{
        schema=Get-AriaPropertyValue $Policy 'schema'
        trustedIssuers=@((Get-AriaPropertyValue $Policy 'trustedIssuers' @()))
        maxDelegationDepth=[int](Get-AriaPropertyValue $Policy 'maxDelegationDepth' 0)
    }
    $expected="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"
    if([string](Get-AriaPropertyValue $Policy 'id')-cne$expected){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_POLICY_IDENTITY' `
            -Message 'Issuer trust policy identity mismatch.' `
            -Path '$.id'))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        expectedId=$expected
    }
}

function New-AriaRevocationLedger {
    [CmdletBinding()]
    param([object[]]$Entries=@())

    $normalized=New-Object 'System.Collections.Generic.List[object]'
    foreach($entry in @($Entries)){
        [void]$normalized.Add([pscustomobject][ordered]@{
            capabilityId=[string](Get-AriaPropertyValue $entry 'capabilityId')
            revokedAt=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $entry 'revokedAt'))
            reason=[string](Get-AriaPropertyValue $entry 'reason')
        })
    }

    $sorted=@($normalized.ToArray() | Sort-Object capabilityId,revokedAt,reason)
    $identity=[ordered]@{
        schema='aria.revocations/0.5'
        entries=$sorted
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    [pscustomobject][ordered]@{
        schema=$identity.schema
        entries=@($identity.entries)
        id=$id
    }
}

function Add-AriaCapabilityRevocation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Ledger,
        [Parameter(Mandatory=$true)][string]$CapabilityId,
        [Parameter(Mandatory=$true)][string]$RevokedAt,
        [Parameter(Mandatory=$true)][string]$Reason
    )

    $entries=@((Get-AriaPropertyValue $Ledger 'entries' @())) + @(
        [pscustomobject][ordered]@{
            capabilityId=$CapabilityId
            revokedAt=$RevokedAt
            reason=$Reason
        }
    )
    New-AriaRevocationLedger -Entries $entries
}

function New-AriaDelegatedCapabilityToken {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$ParentToken,
        [Parameter(Mandatory=$true)][string]$Subject,
        [Parameter(Mandatory=$true)][string[]]$Effects,
        [Parameter(Mandatory=$true)][string]$NotBefore,
        [Parameter(Mandatory=$true)][string]$ExpiresAt,
        [Parameter(Mandatory=$true)][string]$Nonce,
        [ValidateRange(0,64)][int]$MaxDelegationDepth = 8,
        [switch]$SingleUse
    )

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $parentValidation=Test-AriaCapabilityTokenIdentity $ParentToken
    foreach($error in @($parentValidation.errors)){[void]$errors.Add($error)}

    $parentEffects=@((Get-AriaPropertyValue $ParentToken 'effects' @()))
    foreach($effect in @($Effects | Sort-Object -Unique)){
        if([string]$effect-notin$parentEffects){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_BROADEN' `
                -Message "Delegated effect '$effect' exceeds parent authority." `
                -Path '$.effects'))
        }
    }

    $childDepth=[int](Get-AriaPropertyValue $ParentToken 'delegationDepth' 0)+1
    if($childDepth-gt$MaxDelegationDepth){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_DELEGATION_DEPTH' `
            -Message 'Delegation depth exceeds policy maximum.' `
            -Path '$.delegationDepth'))
    }

    $childNotBefore=ConvertTo-AriaUtcTimestamp $NotBefore
    $childExpiresAt=ConvertTo-AriaUtcTimestamp $ExpiresAt
    $parentNotBefore=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $ParentToken 'notBefore'))
    $parentExpiresAt=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $ParentToken 'expiresAt'))

    if([DateTimeOffset]::Parse($childNotBefore)-lt[DateTimeOffset]::Parse($parentNotBefore) -or
       [DateTimeOffset]::Parse($childExpiresAt)-gt[DateTimeOffset]::Parse($parentExpiresAt)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_DELEGATION_INTERVAL' `
            -Message 'Delegated activation interval must be contained by parent authority.' `
            -Path '$.expiresAt'))
    }

    if($errors.Count){
        return [pscustomobject][ordered]@{
            issued=$false
            errors=@($errors.ToArray())
            token=$null
        }
    }

    $token=New-AriaCapabilityToken `
        -Issuer ([string](Get-AriaPropertyValue $ParentToken 'subject')) `
        -Subject $Subject `
        -Resource ([string](Get-AriaPropertyValue $ParentToken 'resource')) `
        -Effects $Effects `
        -NotBefore $childNotBefore `
        -ExpiresAt $childExpiresAt `
        -Nonce $Nonce `
        -DelegationDepth $childDepth `
        -Parent ([string](Get-AriaPropertyValue $ParentToken 'id')) `
        -SingleUse:$SingleUse

    [pscustomobject][ordered]@{
        issued=$true
        errors=@()
        token=$token
    }
}

function Get-AriaCapabilityIndex {
    param(
        [Parameter(Mandatory=$true)]$Token,
        [object[]]$KnownTokens=@()
    )

    $index=@{}
    foreach($candidate in @($KnownTokens)+@($Token)){
        if($null-eq$candidate){continue}
        $id=[string](Get-AriaPropertyValue $candidate 'id')
        if(-not[string]::IsNullOrWhiteSpace($id)){$index[$id]=$candidate}
    }
    return $index
}

function Test-AriaCapabilityChain {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Token,
        [object[]]$KnownTokens=@(),
        [Parameter(Mandatory=$true)]$Policy,
        [Parameter(Mandatory=$true)][string]$Subject,
        [Parameter(Mandatory=$true)][string]$Resource,
        [string[]]$RequestedEffects=@(),
        [Parameter(Mandatory=$true)][string]$DecisionTime,
        [object]$RevocationLedger=$null,
        [string[]]$UsedNonces=@()
    )

    if($null-eq$RevocationLedger){$RevocationLedger=New-AriaRevocationLedger}

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $policyValidation=Test-AriaIssuerTrustPolicy $Policy
    foreach($error in @($policyValidation.errors)){[void]$errors.Add($error)}

    $decision=ConvertTo-AriaUtcTimestamp $DecisionTime
    $decisionInstant=[DateTimeOffset]::Parse($decision)
    $index=Get-AriaCapabilityIndex -Token $Token -KnownTokens $KnownTokens
    $visited=@{}
    $leafToRoot=New-Object 'System.Collections.Generic.List[object]'
    $current=$Token

    while($null-ne$current){
        $id=[string](Get-AriaPropertyValue $current 'id')
        if($visited.ContainsKey($id)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_CHAIN_CYCLE' `
                -Message 'Capability delegation chain contains a cycle.' `
                -Path '$.parent'))
            break
        }
        $visited[$id]=$true
        [void]$leafToRoot.Add($current)

        $identityValidation=Test-AriaCapabilityTokenIdentity $current
        foreach($error in @($identityValidation.errors)){[void]$errors.Add($error)}

        try{
            $active=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $current 'notBefore'))))
            $expires=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $current 'expiresAt'))))
            if($decisionInstant-lt$active){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_CAP_NOT_ACTIVE' `
                    -Message 'Capability is not active at the decision time.' `
                    -Path '$.notBefore'))
            }
            if($decisionInstant-ge$expires){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_CAP_EXPIRED' `
                    -Message 'Capability is expired at the decision time.' `
                    -Path '$.expiresAt'))
            }
        }
        catch{
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_TIME' `
                -Message 'Capability time could not be evaluated.' `
                -Path '$.notBefore'))
        }

        foreach($entry in @((Get-AriaPropertyValue $RevocationLedger 'entries' @()))){
            if([string](Get-AriaPropertyValue $entry 'capabilityId')-cne$id){continue}
            $revoked=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $entry 'revokedAt'))))
            if($revoked-le$decisionInstant){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_CAP_REVOKED' `
                    -Message 'Capability was revoked at the decision time.' `
                    -Path '$.id' `
                    -Evidence @{
                        capabilityId=$id
                        revokedAt=ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $entry 'revokedAt'))
                    }))
            }
        }

        $depth=[int](Get-AriaPropertyValue $current 'delegationDepth' 0)
        if($depth-gt[int](Get-AriaPropertyValue $Policy 'maxDelegationDepth' 0)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_DEPTH' `
                -Message 'Capability delegation depth exceeds issuer policy.' `
                -Path '$.delegationDepth'))
        }

        $parentId=Get-AriaPropertyValue $current 'parent'
        if($null-eq$parentId -or [string]::IsNullOrWhiteSpace([string]$parentId)){break}

        if(-not$index.ContainsKey([string]$parentId)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_PARENT_UNKNOWN' `
                -Message 'Capability parent is not available for verification.' `
                -Path '$.parent'))
            break
        }

        $parent=$index[[string]$parentId]
        if([string](Get-AriaPropertyValue $current 'issuer')-cne[string](Get-AriaPropertyValue $parent 'subject')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_ISSUER' `
                -Message 'Delegated capability issuer does not match parent subject.' `
                -Path '$.issuer'))
        }

        if([int](Get-AriaPropertyValue $current 'delegationDepth' 0)-ne
           ([int](Get-AriaPropertyValue $parent 'delegationDepth' 0)+1)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_DEPTH' `
                -Message 'Delegated capability depth does not follow its parent.' `
                -Path '$.delegationDepth'))
        }

        if([string](Get-AriaPropertyValue $current 'resource')-cne[string](Get-AriaPropertyValue $parent 'resource')){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_RESOURCE' `
                -Message 'Delegated capability resource exceeds parent scope.' `
                -Path '$.resource'))
        }

        foreach($effect in @((Get-AriaPropertyValue $current 'effects' @()))){
            if([string]$effect-notin@((Get-AriaPropertyValue $parent 'effects' @()))){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_CAP_DELEGATION_BROADEN' `
                    -Message "Delegated effect '$effect' exceeds parent authority." `
                    -Path '$.effects'))
            }
        }

        $childActive=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $current 'notBefore'))))
        $childExpires=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $current 'expiresAt'))))
        $parentActive=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $parent 'notBefore'))))
        $parentExpires=[DateTimeOffset]::Parse((ConvertTo-AriaUtcTimestamp ([string](Get-AriaPropertyValue $parent 'expiresAt'))))
        if($childActive-lt$parentActive -or $childExpires-gt$parentExpires){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_DELEGATION_INTERVAL' `
                -Message 'Delegated activation interval exceeds parent authority.' `
                -Path '$.expiresAt'))
        }

        $current=$parent
    }

    $root=$leafToRoot[$leafToRoot.Count-1]
    if([string](Get-AriaPropertyValue $root 'issuer')-notin@((Get-AriaPropertyValue $Policy 'trustedIssuers' @()))){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_ISSUER_UNTRUSTED' `
            -Message 'Capability root issuer is not trusted.' `
            -Path '$.issuer'))
    }

    if([string](Get-AriaPropertyValue $Token 'subject')-cne$Subject){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_SUBJECT' `
            -Message 'Capability subject does not match the executor.' `
            -Path '$.subject'))
    }

    if([string](Get-AriaPropertyValue $Token 'resource')-cne$Resource){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_RESOURCE' `
            -Message 'Capability resource does not match the requested resource.' `
            -Path '$.resource'))
    }

    foreach($effect in @($RequestedEffects | Sort-Object -Unique)){
        if([string]$effect-notin@((Get-AriaPropertyValue $Token 'effects' @()))){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAP_EFFECT' `
                -Message "Capability does not grant effect '$effect'." `
                -Path '$.effects'))
        }
    }

    if([bool](Get-AriaPropertyValue $Token 'singleUse' $false) -and
       [string](Get-AriaPropertyValue $Token 'nonce')-in@($UsedNonces)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CAP_NONCE_REUSED' `
            -Message 'Single-use capability nonce has already been consumed.' `
            -Path '$.nonce'))
    }

    $rootToLeaf=@()
    for($index=$leafToRoot.Count-1;$index-ge0;$index--){
        $rootToLeaf+=,$leafToRoot[$index]
    }
    $chainIds=@($rootToLeaf | ForEach-Object {[string](Get-AriaPropertyValue $_ 'id')})
    $chainDigest=Get-AriaSha256Hex (ConvertTo-AriaStableJson $chainIds)

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        chain=@($rootToLeaf)
        chainDigest=$chainDigest
        decisionTime=$decision
    }
}

function New-AriaAuthorityDecision {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Token,
        [object[]]$KnownTokens=@(),
        [Parameter(Mandatory=$true)]$Policy,
        [Parameter(Mandatory=$true)][string]$Subject,
        [Parameter(Mandatory=$true)][string]$Resource,
        [string[]]$RequestedEffects=@(),
        [Parameter(Mandatory=$true)][string]$DecisionTime,
        [object]$RevocationLedger=$null,
        [string[]]$UsedNonces=@()
    )

    if($null-eq$RevocationLedger){$RevocationLedger=New-AriaRevocationLedger}

    $chain=Test-AriaCapabilityChain `
        -Token $Token `
        -KnownTokens $KnownTokens `
        -Policy $Policy `
        -Subject $Subject `
        -Resource $Resource `
        -RequestedEffects $RequestedEffects `
        -DecisionTime $DecisionTime `
        -RevocationLedger $RevocationLedger `
        -UsedNonces $UsedNonces

    $codes=@($chain.errors | ForEach-Object {[string]$_.code} | Sort-Object -Unique)
    $identity=[ordered]@{
        schema='aria.authority-decision/0.5'
        capabilityId=[string](Get-AriaPropertyValue $Token 'id')
        subject=$Subject
        resource=$Resource
        requestedEffects=@($RequestedEffects | Sort-Object -Unique)
        decisionTime=$chain.decisionTime
        outcome=if($chain.valid){'approved'}else{'rejected'}
        reasonCodes=$codes
        chainDigest=$chain.chainDigest
        policyId=[string](Get-AriaPropertyValue $Policy 'id')
        revocationLedgerId=[string](Get-AriaPropertyValue $RevocationLedger 'id')
    }
    $id="sha256:$(Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity))"

    $decision=[pscustomobject][ordered]@{
        schema=$identity.schema
        capabilityId=$identity.capabilityId
        subject=$identity.subject
        resource=$identity.resource
        requestedEffects=@($identity.requestedEffects)
        decisionTime=$identity.decisionTime
        outcome=$identity.outcome
        reasonCodes=@($identity.reasonCodes)
        chainDigest=$identity.chainDigest
        policyId=$identity.policyId
        revocationLedgerId=$identity.revocationLedgerId
        id=$id
    }

    [pscustomobject][ordered]@{
        approved=[bool]$chain.valid
        errors=@($chain.errors)
        decision=$decision
        chain=@($chain.chain)
    }
}

function ConvertFrom-AriaCapabilityRequirement {
    param([Parameter(Mandatory=$true)][string]$Requirement)

    if($Requirement.StartsWith('cap:')){
        return $Requirement.Substring(4)
    }
    return $Requirement
}

function Invoke-AriaAuthorizedGraphRewrite {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Graph,
        [Parameter(Mandatory=$true)]$Rule,
        [Parameter(Mandatory=$true)]$Token,
        [object[]]$KnownTokens=@(),
        [Parameter(Mandatory=$true)]$Policy,
        [Parameter(Mandatory=$true)][string]$Subject,
        [Parameter(Mandatory=$true)][string]$Resource,
        [Parameter(Mandatory=$true)][string]$DecisionTime,
        [object]$RevocationLedger=$null,
        [string[]]$UsedNonces=@()
    )

    $requestedEffects=@(
        @((Get-AriaPropertyValue $Rule 'capabilities' @())) |
            ForEach-Object {ConvertFrom-AriaCapabilityRequirement ([string]$_)} |
            Sort-Object -Unique
    )

    $authority=New-AriaAuthorityDecision `
        -Token $Token `
        -KnownTokens $KnownTokens `
        -Policy $Policy `
        -Subject $Subject `
        -Resource $Resource `
        -RequestedEffects $requestedEffects `
        -DecisionTime $DecisionTime `
        -RevocationLedger $RevocationLedger `
        -UsedNonces $UsedNonces

    if(-not[bool]$authority.approved){
        $digest=Get-AriaGraphDigest $Graph
        return [pscustomobject][ordered]@{
            committed=$false
            rejected=$true
            reason='authority-rejected'
            errors=@($authority.errors)
            graph=$Graph
            beforeDigest=$digest
            afterDigest=$digest
            event=$null
            authorityDecision=$authority.decision
        }
    }

    $result=Invoke-AriaGraphRewrite `
        -Graph $Graph `
        -Rule $Rule `
        -GrantedCapabilities @((Get-AriaPropertyValue $Rule 'capabilities' @()))

    [pscustomobject][ordered]@{
        committed=[bool]$result.committed
        rejected=[bool]$result.rejected
        reason=[string]$result.reason
        errors=@($result.errors)
        graph=$result.graph
        beforeDigest=[string]$result.beforeDigest
        afterDigest=[string]$result.afterDigest
        event=$result.event
        authorityDecision=$authority.decision
    }
}

Export-ModuleMember -Function `
    ConvertTo-AriaUtcTimestamp, `
    New-AriaCapabilityToken, `
    Test-AriaCapabilityTokenIdentity, `
    New-AriaDelegatedCapabilityToken, `
    New-AriaIssuerTrustPolicy, `
    New-AriaRevocationLedger, `
    Add-AriaCapabilityRevocation, `
    Test-AriaCapabilityChain, `
    New-AriaAuthorityDecision, `
    Invoke-AriaAuthorizedGraphRewrite