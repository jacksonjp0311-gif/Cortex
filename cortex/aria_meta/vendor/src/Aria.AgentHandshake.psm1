Set-StrictMode -Version 2.0

if ($null -eq (Get-Command Get-AriaSha256Text -ErrorAction SilentlyContinue)) {
    Import-Module (Join-Path $PSScriptRoot 'Aria.Common.psm1') -Force -DisableNameChecking
}

function Get-AriaAgentContract {
    param([string]$RepositoryRoot = (Get-AriaRepositoryRoot))

    $path = Join-Path $RepositoryRoot 'ARIA-CONNECT.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'ARIA-CONNECT.json is missing.'
    }

    $contract = Read-AriaUtf8Text -Path $path | ConvertFrom-Json
    $validation = Test-AriaAgentContract -Contract $contract
    if (-not $validation.valid) {
        throw ('Invalid ARIA agent connection contract: ' + (@($validation.errors) -join ', '))
    }
    return $contract
}

function Test-AriaAgentContract {
    param([Parameter(Mandatory=$true)]$Contract)

    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Contract.schema -ne 'aria.agent-connection/1') { $errors.Add('E_AGENT_CONTRACT_SCHEMA') }
    if ([string]$Contract.protocol -ne 'semantic-sync/1') { $errors.Add('E_AGENT_CONTRACT_PROTOCOL') }
    if ([string]$Contract.identity.name -ne 'ARIA') { $errors.Add('E_AGENT_CONTRACT_IDENTITY') }
    if ([string]$Contract.entrypoint.command -ne './aria.cmd handshake --json') { $errors.Add('E_AGENT_CONTRACT_ENTRYPOINT') }

    $expectedPhases = @('discover', 'orient', 'verify', 'align', 'propose')
    $actualPhases = @($Contract.phases | ForEach-Object { [string]$_.id })
    if (($actualPhases -join '|') -cne ($expectedPhases -join '|')) { $errors.Add('E_AGENT_CONTRACT_PHASES') }

    $readOrder = @($Contract.readOrder | ForEach-Object { [string]$_ })
    if ($readOrder.Count -lt 4 -or $readOrder[0] -ne 'ARIA-CONNECT.json') { $errors.Add('E_AGENT_CONTRACT_READ_ORDER') }
    if (@($readOrder | Sort-Object -Unique).Count -ne $readOrder.Count) { $errors.Add('E_AGENT_CONTRACT_READ_ORDER_DUPLICATE') }

    $terms = @($Contract.vocabulary | ForEach-Object { [string]$_.term })
    if ($terms.Count -lt 8 -or @($terms | Sort-Object -Unique).Count -ne $terms.Count) { $errors.Add('E_AGENT_CONTRACT_VOCABULARY') }
    $milestones = @($Contract.continuity | ForEach-Object { [string]$_.milestone })
    if (($milestones -join '|') -cne 'alpha.14|alpha.15|alpha.16|alpha.17|alpha.18') { $errors.Add('E_AGENT_CONTRACT_CONTINUITY') }

    if (
        [string]$Contract.authority.initial -ne 'none' -or
        [bool]$Contract.authority.proposalGrantsAuthority -or
        [bool]$Contract.authority.interpretationSelfApproves -or
        -not [bool]$Contract.authority.humanConsentRequired -or
        -not [bool]$Contract.authority.capabilityAndPolicyRequired
    ) {
        $errors.Add('E_AGENT_CONTRACT_AUTHORITY')
    }

    return [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
    }
}

function Get-AriaAgentHandshakeBody {
    param(
        [Parameter(Mandatory=$true)]$Contract,
        [Parameter(Mandatory=$true)]$Runtime,
        [Parameter(Mandatory=$true)]$Manifest,
        [Parameter(Mandatory=$true)][string]$RepositoryRoot
    )

    return [pscustomobject][ordered]@{
        schema = 'aria.agent-handshake/1'
        protocol = [string]$Contract.protocol
        status = $(if ($Manifest.valid) { 'ready' } else { 'degraded' })
        purpose = [string]$Contract.purpose
        repository = [pscustomobject][ordered]@{
            name = [string]$Runtime.repository.name
            release = [string]$Runtime.release
            languageEvolution = [string]$Runtime.languageEvolution
            stableTag = [string]$Runtime.continuity.stableTag
        }
        contract = [pscustomobject][ordered]@{
            path = 'ARIA-CONNECT.json'
            digest = 'sha256:' + (Get-AriaSha256File (Join-Path $RepositoryRoot 'ARIA-CONNECT.json'))
        }
        runtime = [pscustomobject][ordered]@{
            path = 'ARIA-RUNTIME.json'
            digest = 'sha256:' + (Get-AriaSha256File (Join-Path $RepositoryRoot 'ARIA-RUNTIME.json'))
        }
        guide = [pscustomobject][ordered]@{
            path = 'AGENTS.md'
            digest = 'sha256:' + (Get-AriaSha256File (Join-Path $RepositoryRoot 'AGENTS.md'))
        }
        manifest = [pscustomobject][ordered]@{
            path = 'MANIFEST.sha256'
            digest = 'sha256:' + (Get-AriaSha256File (Join-Path $RepositoryRoot 'MANIFEST.sha256'))
        }
        baseline = [pscustomobject][ordered]@{
            manifestValid = [bool]$Manifest.valid
            verifiedFiles = [int]$Manifest.actual
            declaredFiles = [int]$Manifest.expected
        }
        session = [pscustomobject][ordered]@{
            phase = 'discovered'
            authority = 'none'
            proposalGrantsAuthority = $false
            nextAction = [string]$Contract.nextAction.command
            meaning = [string]$Contract.nextAction.meaning
        }
        synchronization = [pscustomobject][ordered]@{
            phases = @($Contract.phases)
            vocabulary = @($Contract.vocabulary)
            invariants = @($Contract.invariants)
            continuity = @($Contract.continuity)
        }
        readOrder = @($Contract.readOrder)
        commands = $Contract.commands
    }
}

function Get-AriaAgentHandshake {
    param([string]$RepositoryRoot = (Get-AriaRepositoryRoot))

    $contract = Get-AriaAgentContract -RepositoryRoot $RepositoryRoot
    $runtimePath = Join-Path $RepositoryRoot 'ARIA-RUNTIME.json'
    $runtime = Read-AriaUtf8Text -Path $runtimePath | ConvertFrom-Json
    $manifest = Test-AriaManifest -Root $RepositoryRoot
    $body = Get-AriaAgentHandshakeBody -Contract $contract -Runtime $runtime -Manifest $manifest -RepositoryRoot $RepositoryRoot
    $identity = 'sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $body))

    $result = [ordered]@{}
    foreach ($property in $body.PSObject.Properties) {
        $result[$property.Name] = $property.Value
    }
    $result['digest'] = $identity
    return [pscustomobject]$result
}

function Test-AriaAgentHandshake {
    param(
        [Parameter(Mandatory=$true)]$Handshake,
        [string]$RepositoryRoot = (Get-AriaRepositoryRoot)
    )

    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Handshake.schema -ne 'aria.agent-handshake/1') { $errors.Add('E_AGENT_HANDSHAKE_SCHEMA') }
    if ([string]$Handshake.protocol -ne 'semantic-sync/1') { $errors.Add('E_AGENT_HANDSHAKE_PROTOCOL') }
    if ([string]$Handshake.status -notin @('ready','degraded')) { $errors.Add('E_AGENT_HANDSHAKE_STATUS') }
    if ([string]::IsNullOrWhiteSpace([string]$Handshake.purpose)) { $errors.Add('E_AGENT_HANDSHAKE_PURPOSE') }
    if ([string]$Handshake.session.phase -ne 'discovered') { $errors.Add('E_AGENT_HANDSHAKE_PHASE') }
    if ([string]$Handshake.session.authority -ne 'none' -or [bool]$Handshake.session.proposalGrantsAuthority) {
        $errors.Add('E_AGENT_HANDSHAKE_AUTHORITY')
    }
    $phaseIds = @($Handshake.synchronization.phases | ForEach-Object { [string]$_.id })
    if (($phaseIds -join '|') -cne 'discover|orient|verify|align|propose') {
        $errors.Add('E_AGENT_HANDSHAKE_SYNCHRONIZATION')
    }

    $body = [ordered]@{}
    foreach ($property in $Handshake.PSObject.Properties) {
        if ($property.Name -ne 'digest') { $body[$property.Name] = $property.Value }
    }
    $expected = 'sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson ([pscustomobject]$body)))
    if ([string]$Handshake.digest -cne $expected) { $errors.Add('E_AGENT_HANDSHAKE_DIGEST') }

    foreach ($resource in @($Handshake.contract, $Handshake.runtime, $Handshake.guide, $Handshake.manifest)) {
        $path = Join-Path $RepositoryRoot ([string]$resource.path)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $errors.Add('E_AGENT_HANDSHAKE_RESOURCE')
            continue
        }
        $actual = 'sha256:' + (Get-AriaSha256File $path)
        if ([string]$resource.digest -cne $actual) { $errors.Add('E_AGENT_HANDSHAKE_RESOURCE_DIGEST') }
    }

    return [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
    }
}

Export-ModuleMember -Function Get-AriaAgentContract, Test-AriaAgentContract, Get-AriaAgentHandshakeBody, Get-AriaAgentHandshake, Test-AriaAgentHandshake
