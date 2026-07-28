Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSha256Text -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -Force -DisableNameChecking
}

function Get-AriaContinuityProperty {
    param($Object, [string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    $property = $Object.PSObject.Properties | Where-Object { $_.Name -ceq $Name } | Select-Object -First 1
    if ($null -eq $property) { return $Default }
    return $property.Value
}

function Test-AriaContinuityDigest {
    param([string]$Value)
    return [bool]($Value -match '^sha256:[a-f0-9]{64}$')
}

function Add-AriaContinuityDigest {
    param([Parameter(Mandatory=$true)]$Body)
    $result = [ordered]@{}
    foreach ($property in $Body.PSObject.Properties) { $result[$property.Name] = $property.Value }
    $result.digest = 'sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $Body))
    return [pscustomobject]$result
}

function Test-AriaContinuityIdentity {
    param($Record, [string]$ExpectedSchema)
    if ([string](Get-AriaContinuityProperty $Record schema) -ne $ExpectedSchema) { return $false }
    $body = [ordered]@{}
    foreach ($property in $Record.PSObject.Properties) {
        if ($property.Name -ne 'digest') { $body[$property.Name] = $property.Value }
    }
    $expected = 'sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson ([pscustomobject]$body)))
    return ([string](Get-AriaContinuityProperty $Record digest) -ceq $expected)
}

function New-AriaSemanticReplay {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$HandshakeDigest,
        [Parameter(Mandatory=$true)][string]$SessionId,
        [Parameter(Mandatory=$true)][string]$BaselineDigest,
        [Parameter(Mandatory=$true)][string]$IntentDigest,
        [Parameter(Mandatory=$true)][string]$InterpretationDigest,
        [Parameter(Mandatory=$true)][string]$ProposalDigest,
        [Parameter(Mandatory=$true)][string]$ConsentDigest,
        [Parameter(Mandatory=$true)][string]$PolicyDigest,
        [Parameter(Mandatory=$true)][string[]]$EvidenceDigests,
        [Parameter(Mandatory=$true)][string]$StateDigest
    )
    $body = [pscustomobject][ordered]@{
        schema = 'aria.semantic-replay/1'
        protocol = 'semantic-replay/1'
        sessionId = $SessionId
        handshakeDigest = $HandshakeDigest
        baselineDigest = $BaselineDigest
        intentDigest = $IntentDigest
        interpretationDigest = $InterpretationDigest
        proposalDigest = $ProposalDigest
        consentDigest = $ConsentDigest
        policyDigest = $PolicyDigest
        evidenceDigests = @($EvidenceDigests)
        stateDigest = $StateDigest
        replay = [pscustomobject][ordered]@{
            mode = 'verify-only'
            repeatsExternalEffects = $false
            firstDriftRequired = $true
        }
        authority = [pscustomobject][ordered]@{
            grantsAuthority = $false
            capabilities = @()
        }
    }
    $record = Add-AriaContinuityDigest $body
    $verified = Test-AriaSemanticReplay $record
    if (-not $verified.valid) { throw ('Invalid semantic replay: ' + (@($verified.errors) -join ', ')) }
    return $record
}

function Test-AriaSemanticReplay {
    param([Parameter(Mandatory=$true)]$Replay)
    $errors = New-Object System.Collections.Generic.List[string]
    if ([string](Get-AriaContinuityProperty $Replay schema) -ne 'aria.semantic-replay/1') { $errors.Add('E_REPLAY_SCHEMA') }
    if ([string](Get-AriaContinuityProperty $Replay protocol) -ne 'semantic-replay/1') { $errors.Add('E_REPLAY_PROTOCOL') }
    if ([string]::IsNullOrWhiteSpace([string](Get-AriaContinuityProperty $Replay sessionId))) { $errors.Add('E_REPLAY_SESSION') }
    foreach ($field in @('handshakeDigest','baselineDigest','intentDigest','interpretationDigest','proposalDigest','consentDigest','policyDigest','stateDigest')) {
        if (-not (Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $Replay $field)))) { $errors.Add('E_REPLAY_REFERENCE') }
    }
    $evidence = @((Get-AriaContinuityProperty $Replay evidenceDigests @()))
    if ($evidence.Count -eq 0 -or @($evidence | Where-Object { -not (Test-AriaContinuityDigest ([string]$_)) }).Count) { $errors.Add('E_REPLAY_EVIDENCE') }
    if (@($evidence | Sort-Object -Unique).Count -ne $evidence.Count) { $errors.Add('E_REPLAY_EVIDENCE_DUPLICATE') }
    $mode = Get-AriaContinuityProperty $Replay replay
    if ([string](Get-AriaContinuityProperty $mode mode) -ne 'verify-only' -or
        [bool](Get-AriaContinuityProperty $mode repeatsExternalEffects $true) -or
        -not [bool](Get-AriaContinuityProperty $mode firstDriftRequired $false)) { $errors.Add('E_REPLAY_MODE') }
    $authority = Get-AriaContinuityProperty $Replay authority
    if ([bool](Get-AriaContinuityProperty $authority grantsAuthority $true) -or @((Get-AriaContinuityProperty $authority capabilities @())).Count) { $errors.Add('E_REPLAY_AUTHORITY') }
    if (-not (Test-AriaContinuityIdentity $Replay 'aria.semantic-replay/1')) { $errors.Add('E_REPLAY_DIGEST') }
    return [pscustomobject][ordered]@{ valid=($errors.Count-eq0); errors=@($errors.ToArray()|Sort-Object -Unique); digest=[string](Get-AriaContinuityProperty $Replay digest) }
}

function Compare-AriaSemanticReplay {
    param([Parameter(Mandatory=$true)]$Expected, [Parameter(Mandatory=$true)]$Observed)
    $fields = @('handshakeDigest','baselineDigest','intentDigest','interpretationDigest','proposalDigest','consentDigest','policyDigest','evidenceDigests','stateDigest')
    foreach ($field in $fields) {
        $left = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=(Get-AriaContinuityProperty $Expected $field)})
        $right = ConvertTo-AriaJson ([pscustomobject][ordered]@{value=(Get-AriaContinuityProperty $Observed $field)})
        if ($left -cne $right) {
            return [pscustomobject][ordered]@{ verdict='drift'; coherent=$false; firstBoundary=$field; expected=$left; observed=$right }
        }
    }
    return [pscustomobject][ordered]@{ verdict='coherent'; coherent=$true; firstBoundary=$null; expected=$null; observed=$null }
}

function New-AriaSessionHandoff {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ReplayDigest,
        [Parameter(Mandatory=$true)][string]$FromAgent,
        [Parameter(Mandatory=$true)][string]$ToAgent,
        [Parameter(Mandatory=$true)][object[]]$ContextRefs,
        [Parameter(Mandatory=$true)][string]$ContinuationBoundary
    )
    $body = [pscustomobject][ordered]@{
        schema = 'aria.session-handoff/1'
        protocol = 'semantic-handoff/1'
        replayDigest = $ReplayDigest
        fromAgent = $FromAgent
        toAgent = $ToAgent
        contextRefs = @($ContextRefs)
        continuationBoundary = $ContinuationBoundary
        exclusions = @('prompts','secrets','credentials','private-payloads','unrelated-history')
        session = [pscustomobject][ordered]@{ resumable=$true; phase='transferred'; authority='none' }
        authority = [pscustomobject][ordered]@{ grantsAuthority=$false; consentTransfers=$false; capabilities=@() }
    }
    $record = Add-AriaContinuityDigest $body
    $verified = Test-AriaSessionHandoff $record
    if (-not $verified.valid) { throw ('Invalid session handoff: ' + (@($verified.errors) -join ', ')) }
    return $record
}

function Test-AriaSessionHandoff {
    param([Parameter(Mandatory=$true)]$Handoff)
    $errors = New-Object System.Collections.Generic.List[string]
    if ([string](Get-AriaContinuityProperty $Handoff schema) -ne 'aria.session-handoff/1') { $errors.Add('E_HANDOFF_SCHEMA') }
    if (-not (Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $Handoff replayDigest)))) { $errors.Add('E_HANDOFF_REPLAY') }
    $from=[string](Get-AriaContinuityProperty $Handoff fromAgent);$to=[string](Get-AriaContinuityProperty $Handoff toAgent)
    if ([string]::IsNullOrWhiteSpace($from)-or[string]::IsNullOrWhiteSpace($to)-or$from-ceq$to) { $errors.Add('E_HANDOFF_PARTICIPANTS') }
    if ([string]::IsNullOrWhiteSpace([string](Get-AriaContinuityProperty $Handoff continuationBoundary))) { $errors.Add('E_HANDOFF_BOUNDARY') }
    $refs=@((Get-AriaContinuityProperty $Handoff contextRefs @()));$allowed=@('intent','interpretation','proposal','consent','evidence','replay')
    if ($refs.Count-eq0) { $errors.Add('E_HANDOFF_CONTEXT') }
    foreach($ref in $refs){
        $names=@($ref.PSObject.Properties.Name)
        if([string](Get-AriaContinuityProperty $ref kind)-notin$allowed-or-not(Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $ref digest))) -or @($names|Where-Object{$_-notin@('kind','digest')}).Count){$errors.Add('E_HANDOFF_CONTEXT')}
    }
    $refDigests=@($refs|ForEach-Object{[string](Get-AriaContinuityProperty $_ digest)})
    if(@($refDigests|Sort-Object -Unique).Count-ne$refDigests.Count){$errors.Add('E_HANDOFF_CONTEXT_DUPLICATE')}
    $exclusions=@((Get-AriaContinuityProperty $Handoff exclusions @()))
    foreach($required in @('prompts','secrets','credentials','private-payloads','unrelated-history')){if($required-notin$exclusions){$errors.Add('E_HANDOFF_PRIVACY')}}
    $authority=Get-AriaContinuityProperty $Handoff authority
    if([bool](Get-AriaContinuityProperty $authority grantsAuthority $true)-or[bool](Get-AriaContinuityProperty $authority consentTransfers $true)-or@((Get-AriaContinuityProperty $authority capabilities @())).Count){$errors.Add('E_HANDOFF_AUTHORITY')}
    if(-not(Test-AriaContinuityIdentity $Handoff 'aria.session-handoff/1')){$errors.Add('E_HANDOFF_DIGEST')}
    return [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray()|Sort-Object -Unique);digest=[string](Get-AriaContinuityProperty $Handoff digest)}
}

function New-AriaProviderBridge {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$HandoffDigest,
        [Parameter(Mandatory=$true)][string]$ProviderId,
        [Parameter(Mandatory=$true)][string]$ModelId,
        [Parameter(Mandatory=$true)][string]$Operation,
        [string[]]$RequestedCapabilities=@(),
        [string[]]$CapabilityCeiling=@(),
        [Parameter(Mandatory=$true)][string]$ConsentDigest
    )
    $excess=@($RequestedCapabilities|Where-Object{$_-notin$CapabilityCeiling})
    $body=[pscustomobject][ordered]@{
        schema='aria.provider-bridge/1';protocol='provider-membrane/1';handoffDigest=$HandoffDigest
        provider=[pscustomobject][ordered]@{id=$ProviderId;model=$ModelId}
        operation=$Operation;requestedCapabilities=@($RequestedCapabilities);capabilityCeiling=@($CapabilityCeiling);consentDigest=$ConsentDigest
        decision=$(if($excess.Count-eq0){'eligible'}else{'rejected'})
        transport=[pscustomobject][ordered]@{networkExecution=$false;providerCalled=$false;payloadIncluded=$false;nextBoundary='capability-gated transport adapter'}
        authority=[pscustomobject][ordered]@{grantsAuthority=$false;capabilitiesActivated=@()}
    }
    $record=Add-AriaContinuityDigest $body
    $verified=Test-AriaProviderBridge $record
    if(-not$verified.valid){throw('Invalid provider bridge: '+(@($verified.errors)-join', '))}
    return $record
}

function Test-AriaProviderBridge {
    param([Parameter(Mandatory=$true)]$Bridge)
    $errors=New-Object System.Collections.Generic.List[string]
    if([string](Get-AriaContinuityProperty $Bridge schema)-ne'aria.provider-bridge/1'){$errors.Add('E_BRIDGE_SCHEMA')}
    if(-not(Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $Bridge handoffDigest)))-or-not(Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $Bridge consentDigest)))){$errors.Add('E_BRIDGE_REFERENCE')}
    $provider=Get-AriaContinuityProperty $Bridge provider
    if([string]::IsNullOrWhiteSpace([string](Get-AriaContinuityProperty $provider id))-or[string]::IsNullOrWhiteSpace([string](Get-AriaContinuityProperty $provider model))){$errors.Add('E_BRIDGE_PROVIDER')}
    if([string]::IsNullOrWhiteSpace([string](Get-AriaContinuityProperty $Bridge operation))){$errors.Add('E_BRIDGE_OPERATION')}
    $requested=@((Get-AriaContinuityProperty $Bridge requestedCapabilities @()));$ceiling=@((Get-AriaContinuityProperty $Bridge capabilityCeiling @()))
    if(@($requested|Sort-Object -Unique).Count-ne$requested.Count-or@($ceiling|Sort-Object -Unique).Count-ne$ceiling.Count){$errors.Add('E_BRIDGE_CAPABILITY_DUPLICATE')}
    $excess=@($requested|Where-Object{$_-notin$ceiling});$expected=$(if($excess.Count-eq0){'eligible'}else{'rejected'})
    if([string](Get-AriaContinuityProperty $Bridge decision)-ne$expected){$errors.Add('E_BRIDGE_DECISION')}
    $transport=Get-AriaContinuityProperty $Bridge transport
    if([bool](Get-AriaContinuityProperty $transport networkExecution $true)-or[bool](Get-AriaContinuityProperty $transport providerCalled $true)-or[bool](Get-AriaContinuityProperty $transport payloadIncluded $true)){$errors.Add('E_BRIDGE_TRANSPORT')}
    $authority=Get-AriaContinuityProperty $Bridge authority
    if([bool](Get-AriaContinuityProperty $authority grantsAuthority $true)-or@((Get-AriaContinuityProperty $authority capabilitiesActivated @())).Count){$errors.Add('E_BRIDGE_AUTHORITY')}
    if(-not(Test-AriaContinuityIdentity $Bridge 'aria.provider-bridge/1')){$errors.Add('E_BRIDGE_DIGEST')}
    return [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray()|Sort-Object -Unique);decision=$expected;digest=[string](Get-AriaContinuityProperty $Bridge digest)}
}

function New-AriaCooperativeMesh {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$SharedStateDigest,
        [Parameter(Mandatory=$true)][object[]]$Members,
        [Parameter(Mandatory=$true)][string[]]$BridgeDigests
    )
    $body=[pscustomobject][ordered]@{
        schema='aria.cooperative-mesh/1';protocol='cooperative-mesh/1';sharedStateDigest=$SharedStateDigest
        members=@($Members);bridgeDigests=@($BridgeDigests)
        coordination=[pscustomobject][ordered]@{mode='challenge-and-reconcile';conflictResolution='human-required';sharedAuthority=$false;selfApprovalAllowed=$false}
        consensus=[pscustomobject][ordered]@{claimed=$false;materialDisagreementBlocks=$true}
        authority=[pscustomobject][ordered]@{aggregationAllowed=$false;grantsAuthority=$false;capabilities=@()}
    }
    $record=Add-AriaContinuityDigest $body
    $verified=Test-AriaCooperativeMesh $record
    if(-not$verified.valid){throw('Invalid cooperative mesh: '+(@($verified.errors)-join', '))}
    return $record
}

function Test-AriaCooperativeMesh {
    param([Parameter(Mandatory=$true)]$Mesh)
    $errors=New-Object System.Collections.Generic.List[string]
    if([string](Get-AriaContinuityProperty $Mesh schema)-ne'aria.cooperative-mesh/1'){$errors.Add('E_MESH_SCHEMA')}
    if(-not(Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $Mesh sharedStateDigest)))){$errors.Add('E_MESH_STATE')}
    $members=@((Get-AriaContinuityProperty $Mesh members @()));$ids=@($members|ForEach-Object{[string](Get-AriaContinuityProperty $_ id)});$roles=@($members|ForEach-Object{[string](Get-AriaContinuityProperty $_ role)})
    if($members.Count-lt3-or@($ids|Sort-Object -Unique).Count-ne$ids.Count-or''-in$ids){$errors.Add('E_MESH_MEMBERS')}
    foreach($role in @('producer','critic','human')){if($role-notin$roles){$errors.Add('E_MESH_ROLES')}}
    foreach($member in $members){if([string](Get-AriaContinuityProperty $member role)-notin@('producer','critic','observer','human')-or-not(Test-AriaContinuityDigest ([string](Get-AriaContinuityProperty $member artifactDigest)))){$errors.Add('E_MESH_MEMBER_BINDING')}}
    $bridges=@((Get-AriaContinuityProperty $Mesh bridgeDigests @()));if($bridges.Count-lt2-or@($bridges|Where-Object{-not(Test-AriaContinuityDigest ([string]$_))}).Count-or@($bridges|Sort-Object -Unique).Count-ne$bridges.Count){$errors.Add('E_MESH_BRIDGES')}
    $coord=Get-AriaContinuityProperty $Mesh coordination
    if([string](Get-AriaContinuityProperty $coord conflictResolution)-ne'human-required'-or[bool](Get-AriaContinuityProperty $coord sharedAuthority $true)-or[bool](Get-AriaContinuityProperty $coord selfApprovalAllowed $true)){$errors.Add('E_MESH_COORDINATION')}
    $consensus=Get-AriaContinuityProperty $Mesh consensus;if([bool](Get-AriaContinuityProperty $consensus claimed $true)-or-not[bool](Get-AriaContinuityProperty $consensus materialDisagreementBlocks $false)){$errors.Add('E_MESH_CONSENSUS')}
    $authority=Get-AriaContinuityProperty $Mesh authority;if([bool](Get-AriaContinuityProperty $authority aggregationAllowed $true)-or[bool](Get-AriaContinuityProperty $authority grantsAuthority $true)-or@((Get-AriaContinuityProperty $authority capabilities @())).Count){$errors.Add('E_MESH_AUTHORITY')}
    if(-not(Test-AriaContinuityIdentity $Mesh 'aria.cooperative-mesh/1')){$errors.Add('E_MESH_DIGEST')}
    return [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=@($errors.ToArray()|Sort-Object -Unique);digest=[string](Get-AriaContinuityProperty $Mesh digest)}
}

function Invoke-AriaContinuityCreateFile {
    param([Parameter(Mandatory=$true)][ValidateSet('replay','handoff','bridge','mesh')][string]$Kind,[Parameter(Mandatory=$true)][string]$Path)
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "ARIA continuity request not found: $Path"}
    $r=Read-AriaUtf8Text $Path|ConvertFrom-Json
    switch($Kind){
        'replay'{New-AriaSemanticReplay -HandshakeDigest $r.handshakeDigest -SessionId $r.sessionId -BaselineDigest $r.baselineDigest -IntentDigest $r.intentDigest -InterpretationDigest $r.interpretationDigest -ProposalDigest $r.proposalDigest -ConsentDigest $r.consentDigest -PolicyDigest $r.policyDigest -EvidenceDigests @($r.evidenceDigests) -StateDigest $r.stateDigest}
        'handoff'{New-AriaSessionHandoff -ReplayDigest $r.replayDigest -FromAgent $r.fromAgent -ToAgent $r.toAgent -ContextRefs @($r.contextRefs) -ContinuationBoundary $r.continuationBoundary}
        'bridge'{New-AriaProviderBridge -HandoffDigest $r.handoffDigest -ProviderId $r.provider.id -ModelId $r.provider.model -Operation $r.operation -RequestedCapabilities @($r.requestedCapabilities) -CapabilityCeiling @($r.capabilityCeiling) -ConsentDigest $r.consentDigest}
        'mesh'{New-AriaCooperativeMesh -SharedStateDigest $r.sharedStateDigest -Members @($r.members) -BridgeDigests @($r.bridgeDigests)}
    }
}

function Invoke-AriaContinuityVerifyFile {
    param([Parameter(Mandatory=$true)][ValidateSet('replay','handoff','bridge','mesh')][string]$Kind,[Parameter(Mandatory=$true)][string]$Path)
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "ARIA continuity record not found: $Path"}
    $record=Read-AriaUtf8Text $Path|ConvertFrom-Json
    switch($Kind){
        'replay'{Test-AriaSemanticReplay $record}
        'handoff'{Test-AriaSessionHandoff $record}
        'bridge'{Test-AriaProviderBridge $record}
        'mesh'{Test-AriaCooperativeMesh $record}
    }
}

Export-ModuleMember -Function Get-AriaContinuityProperty,Test-AriaContinuityDigest,Add-AriaContinuityDigest,Test-AriaContinuityIdentity,New-AriaSemanticReplay,Test-AriaSemanticReplay,Compare-AriaSemanticReplay,New-AriaSessionHandoff,Test-AriaSessionHandoff,New-AriaProviderBridge,Test-AriaProviderBridge,New-AriaCooperativeMesh,Test-AriaCooperativeMesh,Invoke-AriaContinuityCreateFile,Invoke-AriaContinuityVerifyFile
