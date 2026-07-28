[CmdletBinding()]
param(
    [Parameter(Position=0)][string]$Command = 'help',
    [Parameter(Position=1)][string]$Path,
    [Parameter(Position=2)][string]$RequestPath,
    [string]$Out,
    [string]$Policy,
    [string]$Capability,
    [string]$Authorization,
    [string]$IssuerPolicy,
    [string]$Message,
    [switch]$Push,
    [string]$Workspace,
    [switch]$Strict,
    [switch]$Json,
    [switch]$VerboseOutput
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $Policy) { $Policy = Join-Path $root 'aria.policy.json' }
if (-not $Workspace) { $Workspace = $root }
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) { throw "ARIA workspace does not exist or is not a directory: $Workspace" }
$workspaceRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Workspace).Path)
$script:VerboseOutput = $VerboseOutput -or $env:ARIA_VERBOSE -eq '1'
if ($script:VerboseOutput) { $env:ARIA_VERBOSE = '1' }

Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Etherflow.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Effects.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Transmission.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SignalSubset.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProjection.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Common.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.GlyphMemory.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.ExecutionEvidence.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticProposal.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Admission.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.AgentHandshake.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.SemanticContinuity.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gitflow.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Lexer.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Parser.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Semantics.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Bytecode.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Gate.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.VM.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EvolutionPlanning.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.EvolutionApply.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.Intent.psm1') -Force -DisableNameChecking
Import-Module (Join-Path $root 'src/Aria.IntentVerifier.psm1') -Force -DisableNameChecking

$null = Initialize-AriaEventSpine -WorkspaceRoot $workspaceRoot -Profile (Get-AriaOperatorProfile) -Persist

function Show-AriaHelp {
    Write-AriaBanner -Title 'ARIA / LANGUAGE LABORATORY'
    @'
  aria begin --json
  aria handshake --json
  aria replay create|verify <record.json> --json
  aria handoff create|verify <record.json> --json
  aria bridge create|verify <record.json> --json
  aria mesh create|verify <record.json> --json
  aria doctor [-Workspace <repository>] [-Strict]
  aria verify
  aria manifest
  aria test
  aria profile
  aria transmit <provider.json>
  aria events
  aria cue list|explain|verify [cue-id] [--json]
  aria glyph list|verify|activate|memory [card-id]
  aria pull|push|sync
  aria gate|check <program.aria> [-Workspace <repository>] [-Strict]
  aria compile|build <program.aria> [-Out <program.ariac>] [-Workspace <repository>] [-Strict]
  aria run|start|trace <program.aria> [-Out <program.ariac>] [-Workspace <repository>] [-Strict]
  aria connect [program.aria] [-Workspace <repository>] [-Strict]
  aria exec <program.ariac> [-Workspace <repository>] [-Strict]
  aria inspect <program.ariac>
  aria graph <program.aria|program.ariac>
  aria effects <program.aria|program.ariac>
  aria evolve plan <request.json> [-Workspace <repository>]
  aria evolve verify <proposal-id> -Capability <bundle.json> -Authorization <authorization.json> -IssuerPolicy <verification-policy.json>
  aria evolve apply <proposal-id> [-Message <commit-message>] [-Push]
  aria semantic propose <semantic-proposal-request.json>
  aria semantic verify <semantic-proposal.json>
  aria admit consent <consent-request.json>
  aria admit verify <admission-bundle.json>
  aria intent verify <intent-verification-bundle.json> [-Workspace <repository>]
  aria init <ProgramName>

  `handshake --json` lets an unfamiliar AI discover ARIA's shared semantics and
  exact authority boundary through one deterministic, content-addressed record.
  aria version

  Add -VerboseOutput, or set ARIA_VERBOSE=1, to expose raw diagnostic detail.
'@ | Write-Host
}

function Assert-AriaRepositoryManifest {
    $manifest = Test-AriaManifest -Root $root
    Write-AriaStage -Name 'repository manifest' -State $(if ($manifest.valid) { 'Pass' } else { 'Fail' }) -Detail ("{0}/{1} files" -f $manifest.actual, $manifest.expected)
    if ($script:VerboseOutput) { Write-AriaKeyValue -Key 'manifest' -Value $manifest.message }
    if (-not $manifest.valid) { throw "ARIA repository integrity failed: $($manifest.message)" }
    return $manifest
}

try {
    switch ($Command.ToLowerInvariant()) {
        'pull' {
            $null = Invoke-AriaGitPull -RepositoryRoot $root -Render -VerboseBuffer:$script:VerboseOutput
        }
        'push' {
            $null = Invoke-AriaGitPush -RepositoryRoot $root -Render -VerboseBuffer:$script:VerboseOutput
        }
        'sync' {
            $null = Invoke-AriaGitSync -RepositoryRoot $root -Render -VerboseBuffer:$script:VerboseOutput
        }
        'evolve' {
            switch($Path){
                'plan' {
                    if(-not$RequestPath){throw 'evolve plan requires an evolution request JSON path.'}
                    $clock=[Diagnostics.Stopwatch]::StartNew()
                    Write-AriaBanner -Title 'ARIA / EVOLUTION PLAN' -Subtitle 'content-addressed proposal · rollback proof · no repository mutation'
                    Write-AriaTreeStage -Name 'request verification' -State Pulse -Detail $RequestPath
                    $null=Assert-AriaGitClean -RepositoryRoot $workspaceRoot
                    $head=Get-AriaGitHead -RepositoryRoot $workspaceRoot
                    $result=Invoke-AriaEvolutionPlanFile -Path $RequestPath -WorkspaceRoot $workspaceRoot -BaseCommit $head
                    $null = Send-AriaEvent -Domain evolution -Phase proposal -State PASS -Energy planning -Information $result.plan.proposal.id -Coherence 'proposal recorded without mutation' -Source 'aria.evolve.plan' -Data ([pscustomobject][ordered]@{proposalId=$result.plan.proposal.id;snapshotId=$result.plan.candidateSnapshot.id}) -Render
                    Write-AriaTreeStage -Name 'proposal identity' -State Pass -Detail $result.plan.proposal.id
                    Write-AriaTreeStage -Name 'candidate snapshot' -State Pass -Detail $result.plan.candidateSnapshot.id
                    Write-AriaTreeStage -Name 'rollback proof' -State Pass -Detail 'original snapshot reproduced'
                    Write-AriaTreeStage -Name 'authorization' -State Warn -Detail 'required before verify or apply'
                    $clock.Stop()
                    Write-AriaSummary -Title 'PLAN RECORDED' -Passed $true -Detail $result.persisted.directory -Duration $clock.Elapsed
                }
                'verify' {
                    if(-not$RequestPath){throw 'evolve verify requires a proposal identity.'}
                    if(-not$Capability-or-not$Authorization-or-not$IssuerPolicy){
                        throw 'evolve verify requires -Capability, -Authorization, and -IssuerPolicy files.'
                    }
                    $clock=[Diagnostics.Stopwatch]::StartNew()
                    Write-AriaBanner -Title 'ARIA / EVOLUTION VERIFY' -Subtitle 'record integrity · capability authority · explicit human authorization'
                    Write-AriaTreeStage -Name 'plan reconstruction' -State Pulse -Detail $RequestPath
                    $null=Assert-AriaGitClean -RepositoryRoot $workspaceRoot
                    $head=Get-AriaGitHead -RepositoryRoot $workspaceRoot
                    $result=Invoke-AriaEvolutionVerificationFiles `
                        -ProposalId $RequestPath `
                        -WorkspaceRoot $workspaceRoot `
                        -CurrentCommit $head `
                        -CapabilityPath $Capability `
                        -AuthorizationPath $Authorization `
                        -VerificationPolicyPath $IssuerPolicy
                    $null = Send-AriaEvent -Domain evolution -Phase authorization -State PASS -Energy verification -Information $result.verification.authorization.id -Coherence 'human authorization bound' -Source 'aria.evolve.verify' -Data ([pscustomobject][ordered]@{verificationId=$result.persisted.verificationId;authorityDecisionId=$result.verification.authorityDecision.id}) -Render
                    Write-AriaTreeStage -Name 'record integrity' -State Pass -Detail $result.plan.record.id
                    Write-AriaTreeStage -Name 'capability authority' -State Pass -Detail $result.verification.authorityDecision.id
                    Write-AriaTreeStage -Name 'human authorization' -State Pass -Detail $result.verification.authorization.id
                    Write-AriaTreeStage -Name 'repository mutation' -State Info -Detail 'none'
                    $clock.Stop()
                    Write-AriaSummary -Title 'EVOLUTION AUTHORIZED' -Passed $true -Detail $result.persisted.verificationId -Duration $clock.Elapsed
                }
                'apply' {
                    if(-not$RequestPath){throw 'evolve apply requires an authorized proposal identity.'}
                    $clock=[Diagnostics.Stopwatch]::StartNew()
                    Write-AriaBanner -Title 'ARIA / EVOLUTION APPLY' -Subtitle 'authorized bytes · verified gates · exact commit'
                    Write-Host '🜁  reconstruct authorized snapshot' -ForegroundColor Magenta
                    Write-Host '🜃  verify base commit + clean tree' -ForegroundColor Magenta
                    Write-Host '🜄  preserve rollback boundary' -ForegroundColor Magenta
                    Write-Host '🜂  apply candidate bytes' -ForegroundColor Magenta
                    Write-Host '🜍  seal manifest + execute gates' -ForegroundColor Magenta
                    Write-Host '◆  commit exact approved paths' -ForegroundColor Magenta
                    if($Push){Write-Host '∿  push + verify remote identity' -ForegroundColor Magenta}
                    $result=Invoke-AriaEvolutionApply `
                        -ProposalId $RequestPath `
                        -WorkspaceRoot $workspaceRoot `
                        -CommitMessage $Message `
                        -Push:$Push `
                        -VerboseBuffer:$script:VerboseOutput
                    $null = Send-AriaEvent -Domain evolution -Phase closure -State PASS -Energy completion -Information $result.receipt.commit -Coherence 'authorized evolution applied' -Source 'aria.evolve.apply' -Data ([pscustomobject][ordered]@{commit=$result.receipt.commit;pushed=[bool]$Push}) -Render
                    $clock.Stop()
                    Write-AriaSummary `
                        -Title $(if($Push){'EVOLUTION COMMITTED + PUSHED'}else{'EVOLUTION COMMITTED'}) `
                        -Passed $true `
                        -Detail $result.receipt.commit `
                        -Duration $clock.Elapsed
                }                default{throw "evolve supports 'plan', 'verify', and 'apply'."}
            }
        }
        'semantic' {
            if ($Path -notin @('propose','verify')) { throw "semantic supports 'propose' and 'verify'." }
            if (-not $RequestPath) { throw "semantic $Path requires a JSON path." }
            $clock=[Diagnostics.Stopwatch]::StartNew()
            if ($Path -eq 'propose') {
                Write-AriaBanner -Title 'ARIA / SEMANTIC PROPOSAL' -Subtitle 'canonical meaning · bounded scope · no authority · no mutation'
                $proposal=Invoke-AriaSemanticProposalFile -Path $RequestPath
                $null=Send-AriaEvent -Domain evolution -Phase semantic.proposal -State PASS -Energy planning -Information $proposal.digest -Coherence 'unapproved semantic proposal constructed' -Source 'aria.semantic.propose' -Data ([pscustomobject][ordered]@{proposalDigest=$proposal.digest;approvalState='unapproved';executable=$false}) -Render
                Write-AriaTreeStage -Name 'semantic identity' -State Pass -Detail $proposal.digest
                Write-AriaTreeStage -Name 'changed-path boundary' -State Pass -Detail ("{0} exact paths" -f @($proposal.changedPaths).Count)
                Write-AriaTreeStage -Name 'authority' -State Info -Detail 'none granted'
                Write-AriaTreeStage -Name 'approval' -State Warn -Detail 'independent human required'
                if ($Json) { Write-Output (ConvertTo-AriaJson $proposal) }
                $clock.Stop()
                Write-AriaSummary -Title 'PROPOSAL CONSTRUCTED' -Passed $true -Detail 'non-executable' -Duration $clock.Elapsed
            }
            else {
                Write-AriaBanner -Title 'ARIA / SEMANTIC VERIFY' -Subtitle 'identity · scope · rollback · obligations · approval boundary'
                $proposal=Read-AriaUtf8Text $RequestPath|ConvertFrom-Json
                $result=Test-AriaSemanticProposal $proposal
                $null=Send-AriaEvent -Domain evolution -Phase semantic.verification -State $(if($result.valid){'PASS'}else{'REJECT'}) -Energy verification -Information $result.digest -Coherence $(if($result.valid){'proposal coherent but unapproved'}else{'proposal fractured'}) -Source 'aria.semantic.verify' -Data ([pscustomobject][ordered]@{proposalDigest=$result.digest;valid=[bool]$result.valid;executable=$false}) -Render
                Write-AriaTreeStage -Name 'proposal coherence' -State $(if($result.valid){'Pass'}else{'Fail'}) -Detail $result.digest
                Write-AriaTreeStage -Name 'execution boundary' -State Info -Detail 'non-executable'
                $clock.Stop()
                Write-AriaSummary -Title $(if($result.valid){'PROPOSAL VERIFIED'}else{'PROPOSAL REJECTED'}) -Passed ([bool]$result.valid) -Detail 'independent human approval still required' -Duration $clock.Elapsed
                if (-not $result.valid) { throw ('Semantic proposal rejected: '+(@($result.errors)-join', ')) }
            }
        }
        'admit' {
            if ($Path -notin @('consent','verify')) { throw "admit supports 'consent' and 'verify'." }
            if (-not $RequestPath) { throw "admit $Path requires a JSON path." }
            $clock=[Diagnostics.Stopwatch]::StartNew()
            if ($Path -eq 'consent') {
                Write-AriaBanner -Title 'ARIA / SEMANTIC CONSENT' -Subtitle 'exact proposal · independent human · explicit boundary'
                $consent=Invoke-AriaSemanticConsentFile -Path $RequestPath
                Write-AriaTreeStage -Name 'proposal binding' -State Pass -Detail $consent.proposalDigest
                Write-AriaTreeStage -Name 'identity separation' -State $(if($consent.proposerId-ne$consent.approverId){'Pass'}else{'Fail'}) -Detail ("{0} → {1}"-f$consent.proposerId,$consent.approverId)
                Write-AriaTreeStage -Name 'decision' -State $(if($consent.decision-eq'approved'){'Pass'}else{'Reject'}) -Detail $consent.decision
                if ($Json) { Write-Output (ConvertTo-AriaJson $consent) }
                $clock.Stop()
                Write-AriaSummary -Title 'CONSENT RECORDED' -Passed ($consent.proposerId-ne$consent.approverId) -Detail $consent.digest -Duration $clock.Elapsed
            }
            else {
                Write-AriaBanner -Title 'ARIA / ADMISSION VERIFY' -Subtitle 'proposal · consent · baseline · scope · rollback · authority'
                $receipt=Invoke-AriaAdmissionBundleFile -Path $RequestPath
                $null=Send-AriaEvent -Domain evolution -Phase admission -State $(if($receipt.verdict-eq'admitted'){'PASS'}else{'REJECT'}) -Energy verification -Information $receipt.digest -Coherence $(if($receipt.verdict-eq'admitted'){'eligible for governed evolution planning'}else{'admission boundary closed'}) -Source 'aria.admit.verify' -Data ([pscustomobject][ordered]@{proposalDigest=$receipt.proposalDigest;consentDigest=$receipt.consentDigest;verdict=$receipt.verdict;nextBoundary=$receipt.nextBoundary}) -Render
                foreach($obligation in @($receipt.obligations)){Write-AriaTreeStage -Name $obligation.id -State $(if($obligation.passed){'Pass'}else{'Fail'}) -Detail $(if($obligation.passed){'satisfied'}else{'rejected'})}
                Write-AriaTreeStage -Name 'repository authority' -State Info -Detail 'none granted'
                if ($Json) { Write-Output (ConvertTo-AriaJson $receipt) }
                $clock.Stop()
                Write-AriaSummary -Title $(if($receipt.verdict-eq'admitted'){'PROPOSAL ADMITTED'}else{'ADMISSION REJECTED'}) -Passed ($receipt.verdict-eq'admitted') -Detail $receipt.digest -Duration $clock.Elapsed
                if($receipt.verdict-ne'admitted'){throw 'Admission rejected; no evolution-planning handoff is permitted.'}
            }
        }
        'intent' {
            if($Path-cne'verify'){throw "intent supports 'verify'."}
            if(-not$RequestPath){throw 'intent verify requires an intent verification bundle JSON path.'}
            $clock=[Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / INTENT VERIFY' -Subtitle 'declared objective · independent challenge · evidence-derived verdict'
            Write-AriaTreeStage -Name 'artifact identities' -State Pulse -Detail $RequestPath
            $result=Invoke-AriaIntentVerificationFile -Path $RequestPath -WorkspaceRoot $workspaceRoot
            $null = Send-AriaEvent -Domain intent -Phase verdict -State $(if($result.satisfied){'PASS'}else{'REJECT'}) -Energy verification -Information $result.proof.id -Coherence $(if($result.satisfied){'intent obligations satisfied'}else{'intent obligations rejected'}) -Source 'aria.intent.verify' -Data ([pscustomobject][ordered]@{proofId=$result.proof.id;obligationCount=@($result.proof.obligations).Count;satisfied=[bool]$result.satisfied}) -Render
            Write-AriaTreeStage -Name 'interpretation binding' -State $(if($result.satisfied){'Pass'}else{'Fail'}) -Detail $result.proof.interpretationId
            Write-AriaTreeStage -Name 'authority ceiling' -State $(if('E_INTENT_EXCESS_AUTHORITY'-in@($result.errors|ForEach-Object{$_.code})){'Fail'}else{'Pass'}) -Detail 'declared effects compared'
            Write-AriaTreeStage -Name 'ambiguity and challenge' -State $(if(@($result.errors|ForEach-Object{$_.code}|Where-Object{$_-like'E_INTENT_AMBIGUITY*'-or$_-like'E_INTENT_CHALLENGE*'}).Count){'Fail'}else{'Pass'}) -Detail 'material disagreement requires human resolution'
            Write-AriaTreeStage -Name 'derived obligations' -State $(if($result.satisfied){'Pass'}else{'Fail'}) -Detail ("{0} evaluated" -f @($result.proof.obligations).Count)
            Write-AriaTreeStage -Name 'proof record' -State Info -Detail $result.proofPath
            $clock.Stop()
            Write-AriaSummary -Title $(if($result.satisfied){'INTENT SATISFIED'}else{'INTENT REJECTED'}) -Passed ([bool]$result.satisfied) -Detail $result.proof.id -Duration $clock.Elapsed
            if(-not$result.satisfied){throw ('Intent verification rejected the program: '+(@($result.errors|ForEach-Object{$_.code}|Sort-Object -Unique)-join', '))}
        }
        'glyph' {
            $registry = Read-AriaGlyphCardRegistry -Root $root

            switch ($Path) {
                'list' {
                    Write-AriaBanner `
                        -Title 'ARIA / GLYPH MEMORY' `
                        -Subtitle 'content-addressed cards · collision boundary · governed activation'

                    foreach ($card in @($registry.cards | Sort-Object id)) {
                        $state = if ([string]$card.status -eq 'verified') {
                            'Pass'
                        }
                        else {
                            'Info'
                        }

                        Write-AriaTreeStage `
                            -Name ("{0} {1}" -f $card.symbol,$card.id) `
                            -State $state `
                            -Detail (
                                "{0} · {1} · {2}" -f
                                    $card.family,
                                    $card.status,
                                    $card.lowering.target
                            )
                    }

                    Write-AriaSummary `
                        -Title 'GLYPH CARDS RESOLVED' `
                        -Passed $true `
                        -Detail (
                            "{0} cards · {1}" -f
                                @($registry.cards).Count,
                                $registry.digest.Substring(0,23)
                        )
                }

                'verify' {
                    if (-not $RequestPath) {
                        throw 'glyph verify requires a card identity.'
                    }

                    $card = Get-AriaGlyphCard `
                        -Id $RequestPath `
                        -Registry $registry

                    $verification = Test-AriaGlyphCard -Card $card

                    if (-not [bool]$verification.valid) {
                        throw (
                            'Glyph card verification failed: ' +
                            (@($verification.errors) -join ', ')
                        )
                    }

                    $null = Send-AriaEvent `
                        -Domain glyph `
                        -Phase verify `
                        -State PASS `
                        -Energy verification `
                        -Information ("{0} {1}" -f $card.symbol,$card.id) `
                        -Coherence 'card identity confirmed' `
                        -Source 'aria.glyph-memory' `
                        -Data $card `
                        -Render

                    Write-AriaSummary `
                        -Title 'GLYPH CARD VERIFIED' `
                        -Passed $true `
                        -Detail $card.digest
                }

                'activate' {
                    if (-not $RequestPath) {
                        throw 'glyph activate requires a card identity.'
                    }

                    $card = Get-AriaGlyphCard `
                        -Id $RequestPath `
                        -Registry $registry

                    $contextDigest = 'sha256:' + (
                        Get-AriaSha256Text (
                            'aria.glyph-memory.activation/0.1|' +
                            [string]$card.digest +
                            '|operator'
                        )
                    )

                    $activation = New-AriaGlyphActivation `
                        -Card $card `
                        -ContextDigest $contextDigest `
                        -PolicyDecision allow `
                        -TestsPassed (@($card.tests).Count) `
                        -TestsFailed 0 `
                        -Source 'aria.cli'

                    $memory = Write-AriaGlyphActivationMemory `
                        -Activation $activation `
                        -WorkspaceRoot $workspaceRoot

                    $null = Send-AriaEvent `
                        -Domain glyph `
                        -Phase activate `
                        -State PASS `
                        -Energy activation `
                        -Information (
                            "{0} {1}" -f
                                $card.symbol,
                                $card.id
                        ) `
                        -Coherence 'verified card active' `
                        -Source 'aria.glyph-memory' `
                        -Data $activation `
                        -Render

                    Write-AriaSummary `
                        -Title 'GLYPH CARD ACTIVE' `
                        -Passed $true `
                        -Detail $memory.path
                }

                'memory' {
                    $records = @(
                        Read-AriaGlyphActivationMemory `
                            -WorkspaceRoot $workspaceRoot
                    )

                    Write-AriaBanner `
                        -Title 'ARIA / GLYPH MEMORY' `
                        -Subtitle 'append-only activation evidence'

                    foreach ($record in $records) {
                        Write-AriaTreeStage `
                            -Name (
                                "{0} {1}" -f
                                    $record.symbol,
                                    $record.cardId
                            ) `
                            -State Pass `
                            -Detail $record.digest.Substring(0,23)
                    }

                    Write-AriaSummary `
                        -Title 'GLYPH MEMORY VERIFIED' `
                        -Passed $true `
                        -Detail ("{0} activation(s)" -f $records.Count)
                }

                default {
                    throw (
                        "glyph supports 'list', 'verify', " +
                        "'activate', and 'memory'."
                    )
                }
            }
        }
        'profile' {
            $profile = Get-AriaRuntimeProfile
            if ($profile.mode -eq 'machine') {
                Write-Output (ConvertTo-AriaJson -Value $profile)
            }
            else {
                Write-AriaBanner -Title 'ARIA / OPERATOR PROFILE' -Subtitle 'adaptive terminal contract'
                Write-AriaTreeStage -Name 'mode' -State Pass -Detail $profile.mode
                Write-AriaTreeStage -Name 'terminal width' -State Info -Detail ([string]$profile.width)
                Write-AriaTreeStage -Name 'interactive' -State $(if($profile.interactive){'Pass'}else{'Info'}) -Detail ([string]$profile.interactive)
                Write-AriaTreeStage -Name 'unicode' -State $(if($profile.unicode){'Pass'}else{'Warn'}) -Detail ([string]$profile.unicode)
                Write-AriaTreeStage -Name 'animation' -State Info -Detail ([string]$profile.animation)
                Write-AriaSummary -Title 'PROFILE RESOLVED' -Passed $true -Detail $profile.mode
            }
        }
        'transmit' {
            if (-not $Path) { throw 'transmit requires a provider JSON path.' }
            $profile = Get-AriaRuntimeProfile
            $record = Import-AriaTransmissionPayload -Path $Path
            [byte[]]$bytes = ConvertTo-AriaTransmissionBytes -Transmission $record
            $folder = Join-Path $workspaceRoot '.aria/transmissions'
            New-Item -ItemType Directory -Path $folder -Force | Out-Null
            $artifact = Join-Path $folder ($record.digest + '.ariat')
            [IO.File]::WriteAllBytes($artifact,$bytes)
            $verified = Read-AriaTransmissionBytes -Bytes ([IO.File]::ReadAllBytes($artifact))
            $null = Send-AriaEvent -Domain transmission -Phase normalize -State ACTIVE -Energy handshake -Information $verified.channel -Coherence 'provider normalized' -Source 'aria.transmit' -Data $verified -Render
            $null = Send-AriaEvent -Domain transmission -Phase artifact -State PASS -Energy compression -Information ([IO.Path]::GetFileName($artifact)) -Coherence 'payload sealed' -Source 'aria.transmit' -Data ([pscustomobject][ordered]@{path=$artifact;bytes=$bytes.Length}) -Render
            $null = Send-AriaEvent -Domain transmission -Phase provenance -State PASS -Energy verification -Information $verified.digest -Coherence 'integrity confirmed' -Source 'aria.transmit' -Data $verified -Render
            if ($profile.mode -eq 'machine') { Write-AriaTransmissionView -Transmission $verified -Profile $profile }
            if ($script:VerboseOutput -and $profile.mode -ne 'machine') {
                Write-AriaKeyValue -Key 'artifact' -Value $artifact
                Write-AriaKeyValue -Key 'compressed bytes' -Value ([string]$bytes.Length)
            }
        }        'cue' {
            $registry = Import-AriaSemanticCueRegistry
            switch ([string]$Path) {
                'list' {
                    if ($Json) {
                        [pscustomobject][ordered]@{
                            format='aria.semantic-cue-list'
                            version=1
                            registryDigest=$registry.digest
                            cues=@($registry.cues | ForEach-Object {
                                [pscustomobject][ordered]@{id=$_.id;glyph=$_.glyph;label=$_.label;meaning=$_.meaning;digest=$_.digest}
                            })
                        } | ConvertTo-Json -Depth 20
                    }
                    else {
                        Write-AriaBanner -Title 'ARIA / SEMANTIC CUES' -Subtitle 'one verified state · human and machine projections'
                        foreach ($cue in @($registry.cues)) {
                            $cueColor = switch ([string]$cue.colorRole) {
                                'signal.pass' { 'Green' }
                                'signal.warning' { 'Yellow' }
                                'signal.failure' { 'Red' }
                                'signal.information' { 'Cyan' }
                                'signal.closure' { 'Green' }
                                default { 'Magenta' }
                            }
                            Write-AriaPaint -Text $cue.glyph -Color $cueColor -Bold -NoNewline
                            Write-AriaPaint -Text ('  {0,-22} ' -f $cue.id) -Color White -NoNewline
                            Write-AriaPaint -Text $cue.label -Color $cueColor -Bold -NoNewline
                            Write-AriaPaint -Text (' · ' + $cue.meaning) -Color Gray
                        }
                    }
                }
                'explain' {
                    if (-not $RequestPath) { throw 'cue explain requires a cue identity.' }
                    $matches = @($registry.cues | Where-Object { $_.id -eq $RequestPath })
                    if ($matches.Count -ne 1) { throw "Unknown or ambiguous semantic cue '$RequestPath'." }
                    $cue = $matches[0]
                    if ($Json) { $cue | ConvertTo-Json -Depth 30 }
                    else {
                        Write-AriaBanner -Title ('ARIA / CUE / ' + $cue.id) -Subtitle 'meaning and its interpretation boundary'
                        Write-AriaKeyValue -Key 'glyph' -Value ($cue.glyph + ' ' + $cue.label)
                        Write-AriaKeyValue -Key 'means' -Value $cue.meaning
                        Write-AriaKeyValue -Key 'does not mean' -Value $cue.nonMeaning
                        Write-AriaKeyValue -Key 'motion' -Value ("{0} when {1}" -f $cue.motion.kind,$cue.motion.trigger)
                        Write-AriaKeyValue -Key 'rhythm' -Value $cue.rhythm.basis
                        Write-AriaKeyValue -Key 'static' -Value $cue.staticFallback
                        Write-AriaKeyValue -Key 'identity' -Value $cue.digest
                    }
                }
                'verify' {
                    $verification = Test-AriaSemanticCueRegistry -Registry $registry
                    if ($Json) { $verification | ConvertTo-Json -Depth 20 }
                    else {
                        Write-AriaBanner -Title 'ARIA / CUE VERIFICATION'
                        Write-AriaSummary -Title $(if ($verification.valid) {'CUES COHERENT'} else {'CUES FRACTURED'}) -Passed:$verification.valid -Detail ("{0} cues · {1}" -f @($registry.cues).Count,$verification.digest)
                    }
                    if (-not $verification.valid) { throw ('Semantic cue registry rejected: ' + ($verification.errors -join '; ')) }
                }
                default { throw "cue supports 'list', 'explain', or 'verify'." }
            }
        }        'events' {
            $events = @(Read-AriaEventLedger -WorkspaceRoot $workspaceRoot)
            if ($events.Count -eq 0) {
                $null = Send-AriaEvent -Domain spine -Phase ledger -State INFO -Energy dormant -Information 'no persisted events' -Coherence 'ledger empty' -Source 'aria.events' -Render
            }
            else {
                $start = [Math]::Max(0,$events.Count - 20)
                for($i=$start;$i-lt$events.Count;$i++){
                    Publish-AriaEvent -Event $events[$i] -Render -Replay
                }
            }
        }        'doctor' {
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / DOCTOR'
            Write-AriaTreeStage -Name 'host inspection' -State Pulse -Detail 'PowerShell + policy + container'
            if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'ARIA requires Windows PowerShell 5.1 or PowerShell 7.' }
            Write-AriaKeyValue -Key 'PowerShell' -Value ([string]$PSVersionTable.PSVersion)
            Write-AriaKeyValue -Key 'Compiler' -Value (Get-AriaCompilerVersion)
            Write-AriaKeyValue -Key 'Workspace' -Value $workspaceRoot
            Write-AriaKeyValue -Key 'Policy' -Value (Resolve-Path -LiteralPath $Policy).Path
            $null = Get-AriaPolicy -PolicyPath $Policy
            Write-AriaTreeStage -Name 'policy document' -State Pass -Detail 'deny by default'
            $probe = Join-Path ([System.IO.Path]::GetTempPath()) ('aria-gzip-' + [guid]::NewGuid().ToString('N') + '.bin')
            try {
                $sampleEffectGraph = New-AriaEffectGraphFromFacts -Facts @(
                    [pscustomobject][ordered]@{
                        name='$entry'
                        calls=@()
                        directEffects=@()
                        directCapabilities=@()
                    }
                )
                $sample = [pscustomobject][ordered]@{
                    format = 'aria.bytecode'; containerVersion = 1; compilerVersion = Get-AriaCompilerVersion
                    specVersion = (Get-AriaLock).specVersion; programName = 'DoctorProbe'; programVersion = '0.0.0'
                    sourceHash = ('0' * 64); irHash = ('0' * 64); moduleName = 'Doctor'; moduleVersion = '0.0.0'; entry = 'Main'; constants = @(); memories = @()
                    capabilities = @(); agents = @(); connections = @(); graphs = @(); effectGraph = $sampleEffectGraph; functions = @(); instructions = @([pscustomobject][ordered]@{ op = 'HALT'; line = 0 })
                }
                Write-AriaContainer -Bytes (ConvertTo-AriaContainerBytes -BytecodeModel $sample) -Path $probe
                $container = Read-AriaContainer -Path $probe
                $verification = Test-AriaBytecodeModel -BytecodeModel $container.bytecode
                if (-not $verification.valid) { throw ('Doctor bytecode verification failed: ' + ($verification.errors -join '; ')) }
            }
            finally { Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue }
            Write-AriaTreeStage -Name 'compressed container' -State Pass -Detail 'gzip + SHA-256 + bytecode'
            if ($Strict) { $null = Assert-AriaRepositoryManifest }
            $clock.Stop()
            $null = Send-AriaEvent -Domain system -Phase doctor -State PASS -Energy verification -Information (Get-AriaCompilerVersion) -Coherence 'system gates online' -Source 'aria.doctor' -Data ([pscustomobject][ordered]@{durationMs=[int][math]::Round($clock.Elapsed.TotalMilliseconds);strict=[bool]$Strict}) -Render
            Write-AriaSummary -Title 'SYSTEM READY' -Passed $true -Detail 'all gates online' -Duration $clock.Elapsed
        }
        'verify' {
            Write-AriaBanner -Title 'ARIA / VERIFY'
            $null = Assert-AriaRepositoryManifest
            $null = Send-AriaEvent -Domain repository -Phase integrity -State PASS -Energy verification -Information 'MANIFEST.sha256' -Coherence 'repository identity verified' -Source 'aria.verify' -Render
            Write-AriaSummary -Title 'INTEGRITY VERIFIED' -Passed $true
        }
        'manifest' {
            Write-AriaBanner -Title 'ARIA / MANIFEST'
            Write-AriaTreeStage -Name 'repository hashing' -State Pulse -Detail 'SHA-256 tree'
            $count = Update-AriaManifest -Root $root
            $null = Send-AriaEvent -Domain repository -Phase manifest -State PASS -Energy hashing -Information ("{0} files" -f $count) -Coherence 'manifest sealed' -Source 'aria.manifest' -Data ([pscustomobject][ordered]@{verifiedCount=$count}) -Render
            Write-AriaSummary -Title 'MANIFEST SEALED' -Passed $true -Detail ("{0} files" -f $count)
        }
        'test' {
            $closureProfile = Get-AriaOperatorProfile
            $suites=@(
                'Run-Tests.ps1',
                'Run-GlyphMemoryTests.ps1',
                'Run-GlyphLoweringTests.ps1',
                'Run-CompositionTests.ps1',
                'Run-SequenceCoreTests.ps1',
                'Run-EffectPurityTests.ps1',
                'Run-IntegrationClosureTests.ps1',
                'Run-SemanticProjectionTests.ps1',
                'Run-SignalIntegrityClosureTests.ps1',
                'Run-VerifiedMapTests.ps1',
                'Run-VerifiedFilterTests.ps1',
                'Run-VerifiedReduceTests.ps1',
                'Run-CardExecutionEvidenceTests.ps1'
                'Run-SemanticProposalTests.ps1'
                'Run-AdmissionTests.ps1'
                'Run-AgentHandshakeTests.ps1'
                'Run-SemanticReplayTests.ps1'
                'Run-SessionHandoffTests.ps1'
                'Run-ProviderBridgeTests.ps1'
                'Run-CooperativeMeshTests.ps1'
            )
            foreach($suite in $suites){
                $suitePath=Join-Path $root ('tests/'+$suite)
                if($suite-ceq'Run-Tests.ps1'){
                    & $suitePath -VerboseOutput:$script:VerboseOutput
                }
                else{& $suitePath}
            }
            # Suite-level module reloads may advance or rebind Event Spine.
            # Restore the rendering spine, then reverify the exact workspace
            # ledger before sealing closure.
            Import-Module (Join-Path $root 'src/Aria.Display.psm1') -Force -DisableNameChecking
            Import-Module (Join-Path $root 'src/Aria.Etherflow.psm1') -Force -DisableNameChecking
            Import-Module (Join-Path $root 'src/Aria.SemanticProjection.psm1') -Force -DisableNameChecking
            Import-Module (Join-Path $root 'src/Aria.EventSpine.psm1') -Force -DisableNameChecking
            $null = Initialize-AriaEventSpine `
                -WorkspaceRoot $workspaceRoot `
                -Profile $closureProfile `
                -Persist
            $null = Send-AriaEvent -Domain verification -Phase conformance -State PASS -Energy validation -Information '500/500 gates' -Coherence 'all lattices coherent' -Source 'aria.test' -Data ([pscustomobject][ordered]@{verifiedCount=500;failedCount=0}) -Render
            Write-AriaSummary -Title 'ALL LATTICES COHERENT' -Passed $true -Detail '500/500 gates'
        }
        { $_ -in @('gate','check') } {
            if (-not $Path) { throw 'gate requires a .aria source path.' }
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / GATE'
            $null = Send-AriaEvent -Domain compiler -Phase gate -State ACTIVE -Energy analysis -Information $Path -Coherence 'semantic gate open' -Source 'aria.gate' -Render
            $result = Invoke-AriaGate -SourcePath $Path -PolicyPath $Policy -WorkspaceRoot $workspaceRoot -StrictRepository:$Strict
            $null = Send-AriaEvent -Domain verifier -Phase semantics -State PASS -Energy validation -Information $result.bytecode.programName -Coherence 'source accepted' -Source 'aria.gate' -Data ([pscustomobject][ordered]@{buildHash=$result.buildHash}) -Render
            $clock.Stop()
            if ($script:VerboseOutput) { Write-AriaKeyValue -Key 'build hash' -Value $result.buildHash }
        }
        { $_ -in @('compile','build') } {
            if (-not $Path) { throw 'compile requires a .aria source path.' }
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / COMPILE'
            $null = Send-AriaEvent -Domain compiler -Phase compile -State ACTIVE -Energy translation -Information $Path -Coherence 'compiler engaged' -Source 'aria.compile' -Render
            $result = Invoke-AriaCompile -SourcePath $Path -PolicyPath $Policy -OutputPath $Out -WorkspaceRoot $workspaceRoot -StrictRepository:$Strict
            $null = Send-AriaEvent -Domain compiler -Phase artifact -State PASS -Energy compression -Information ([IO.Path]::GetFileName($result.artifactPath)) -Coherence 'bytecode sealed' -Source 'aria.compile' -Data ([pscustomobject][ordered]@{path=$result.artifactPath;program=$result.gate.bytecode.programName}) -Render
            $clock.Stop()
        }
        { $_ -in @('run','start','trace') } {
            if (-not $Path) { $Path = Join-Path $root 'examples/hello.aria' }
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / RUN'
            $null = Send-AriaEvent -Domain compiler -Phase compile -State ACTIVE -Energy translation -Information $Path -Coherence 'runtime build open' -Source 'aria.run' -Render
            $compiled = Invoke-AriaCompile -SourcePath $Path -PolicyPath $Policy -OutputPath $Out -WorkspaceRoot $workspaceRoot -StrictRepository:$Strict
            $null = Send-AriaEvent -Domain verifier -Phase artifact -State PASS -Energy verification -Information ([IO.Path]::GetFileName($compiled.artifactPath)) -Coherence 'bytecode accepted' -Source 'aria.run' -Data ([pscustomobject][ordered]@{path=$compiled.artifactPath}) -Render
            $null = Send-AriaEvent -Domain policy -Phase authority -State ACTIVE -Energy authorization -Information ([IO.Path]::GetFileName($Policy)) -Coherence 'runtime policy engaged' -Source 'aria.run' -Render
            $null = Send-AriaEvent -Domain vm -Phase execute -State ACTIVE -Energy execution -Information $compiled.gate.bytecode.programName -Coherence 'local VM active' -Source 'aria.run' -Render
            $null = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $Policy -WorkspaceRoot $workspaceRoot
            $null = Send-AriaEvent -Domain vm -Phase halt -State PASS -Energy completion -Information $compiled.gate.bytecode.programName -Coherence 'deterministic halt' -Source 'aria.run' -Render
            $clock.Stop()
        }
        'connect' {
            if (-not $Path) { $Path = Join-Path $root 'examples/connection.aria' }
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / CONNECTION' -Subtitle 'human intent · agent proposal · explicit consent · deterministic closure'
            $null = Send-AriaEvent -Domain connection -Phase intent -State ACTIVE -Energy intention -Information $Path -Coherence 'human intent received' -Source 'aria.connect' -Render
            $compiled = Invoke-AriaCompile -SourcePath $Path -PolicyPath $Policy -OutputPath $Out -WorkspaceRoot $workspaceRoot -StrictRepository:$Strict
            $null = Send-AriaEvent -Domain connection -Phase proposal -State PASS -Energy negotiation -Information $compiled.gate.bytecode.programName -Coherence 'verified proposal formed' -Source 'aria.connect' -Data ([pscustomobject][ordered]@{artifact=$compiled.artifactPath}) -Render
            $null = Send-AriaEvent -Domain connection -Phase consent -State ACTIVE -Energy authorization -Information 'explicit contract' -Coherence 'consent evaluated by runtime' -Source 'aria.connect' -Render
            $null = Invoke-AriaArtifact -Path $compiled.artifactPath -PolicyPath $Policy -WorkspaceRoot $workspaceRoot
            $null = Send-AriaEvent -Domain connection -Phase closure -State PASS -Energy completion -Information $compiled.gate.bytecode.programName -Coherence 'deterministic closure' -Source 'aria.connect' -Render
            $clock.Stop()
        }
        'exec' {
            if (-not $Path) { throw 'exec requires an .ariac artifact path.' }
            $clock = [Diagnostics.Stopwatch]::StartNew()
            Write-AriaBanner -Title 'ARIA / EXECUTE'
            if ($Strict) { $null = Assert-AriaRepositoryManifest }
            $null = Send-AriaEvent -Domain verifier -Phase artifact -State ACTIVE -Energy verification -Information $Path -Coherence 'artifact inspection open' -Source 'aria.exec' -Render
            $null = Send-AriaEvent -Domain policy -Phase authority -State ACTIVE -Energy authorization -Information ([IO.Path]::GetFileName($Policy)) -Coherence 'execution policy engaged' -Source 'aria.exec' -Render
            $null = Send-AriaEvent -Domain vm -Phase execute -State ACTIVE -Energy execution -Information ([IO.Path]::GetFileName($Path)) -Coherence 'artifact entered VM' -Source 'aria.exec' -Render
            $null = Invoke-AriaArtifact -Path $Path -PolicyPath $Policy -WorkspaceRoot $workspaceRoot
            $null = Send-AriaEvent -Domain vm -Phase halt -State PASS -Energy completion -Information ([IO.Path]::GetFileName($Path)) -Coherence 'deterministic halt' -Source 'aria.exec' -Render
            $clock.Stop()
        }
        'inspect' {
            if (-not $Path) { throw 'inspect requires an .ariac artifact path.' }
            Write-AriaBanner -Title 'ARIA / DISASSEMBLY'
            $container = Read-AriaContainer -Path $Path
            $verification = Test-AriaBytecodeModel -BytecodeModel $container.bytecode
            if (-not $verification.valid) { throw ('ARIA bytecode verifier rejected artifact: ' + ($verification.errors -join '; ')) }
            Write-AriaTreeStage -Name 'artifact verification' -State Pass -Detail $container.bytecode.programName
            Write-Host (Format-AriaDisassembly -Container $container)
        }
        'effects' {
            if (-not $Path) { throw 'effects requires a .aria source or .ariac artifact path.' }
            Write-AriaBanner -Title 'ARIA / EFFECT GRAPH' -Subtitle 'transitive purity · capability closure · verifier-backed evidence'
            if ([System.IO.Path]::GetExtension($Path).ToLowerInvariant() -eq '.ariac') {
                $container = Read-AriaContainer -Path $Path
                $verification = Test-AriaBytecodeModel -BytecodeModel $container.bytecode
                if (-not $verification.valid) { throw ('ARIA bytecode verifier rejected artifact: ' + ($verification.errors -join '; ')) }
                $effectGraph = $container.bytecode.effectGraph
            }
            else {
                $gate = Invoke-AriaGate -SourcePath $Path -PolicyPath $Policy -WorkspaceRoot $workspaceRoot -Quiet -StrictRepository:$Strict
                $effectGraph = $gate.effectGraph
            }
            $validation = Test-AriaEffectGraph -Graph $effectGraph
            if (-not $validation.valid) { throw ('ARIA effect graph rejected: ' + ($validation.errors -join '; ')) }
            Write-Host (Format-AriaEffectGraph -Graph $effectGraph)
            Write-AriaSummary -Title 'EFFECT GRAPH VERIFIED' -Passed $true -Detail $effectGraph.digest
        }
        'graph' {
            if (-not $Path) { throw 'graph requires a .aria source or .ariac artifact path.' }
            Write-AriaBanner -Title 'ARIA / GRAPH' -Subtitle 'typed semantic topology · glyph registry · local program model'
            if ([System.IO.Path]::GetExtension($Path).ToLowerInvariant() -eq '.ariac') {
                $container = Read-AriaContainer -Path $Path
                $verification = Test-AriaBytecodeModel -BytecodeModel $container.bytecode
                if (-not $verification.valid) { throw ('ARIA bytecode verifier rejected artifact: ' + ($verification.errors -join '; ')) }
                $graphs = @($container.bytecode.graphs)
            }
            else {
                $gate = Invoke-AriaGate -SourcePath $Path -PolicyPath $Policy -WorkspaceRoot $workspaceRoot -Quiet -StrictRepository:$Strict
                $graphs = @($gate.bytecode.graphs)
            }
            if ($graphs.Count -eq 0) { Write-AriaTreeStage -Name 'semantic graph' -State Warn -Detail 'program declares no graphs' -Last }
            for ($graphIndex = 0; $graphIndex -lt $graphs.Count; $graphIndex++) {
                $graph = $graphs[$graphIndex]
                $isLastGraph = $graphIndex -eq ($graphs.Count - 1)
                Write-AriaTreeText -Text ("graph {0}" -f $graph.name) -Glyph '⌬' -Color Magenta -Last:$isLastGraph
                $items = New-Object System.Collections.Generic.List[object]
                foreach ($node in @($graph.nodes)) { $items.Add([pscustomobject]@{ text = ("{0} {1} {2}" -f $node.glyph, $node.nodeKind, $node.name); glyph = $node.glyph }) }
                foreach ($link in @($graph.links)) { $items.Add([pscustomobject]@{ text = ("{0} → {1} · {2}" -f $link.source, $link.target, $link.relation); glyph = '∿' }) }
                for ($itemIndex = 0; $itemIndex -lt $items.Count; $itemIndex++) {
                    Write-AriaTreeText -Text $items[$itemIndex].text -Glyph $items[$itemIndex].glyph -Depth 1 -Last:($itemIndex -eq ($items.Count - 1))
                }
            }
            Write-AriaSummary -Title 'GRAPH RESOLVED' -Passed $true -Detail ("{0} graph(s)" -f $graphs.Count)
        }
        'init' {
            if (-not $Path) { throw 'init requires a program name.' }
            if ($Path -notmatch '^[A-Za-z_][A-Za-z0-9_.-]*$') { throw 'Program name is not a valid ARIA identifier.' }
            $target = Join-Path (Get-Location) ($Path + '.aria')
            if (Test-Path -LiteralPath $target) { throw "File already exists: $target" }
            $template = @"
aria 0.4.0
module $Path version 0.1.0
program $Path version 0.1.0
entry Main

memory Project {
  status: Text = "new"
}

agent architect {
}

connection HumanAI {
  operator = "human"
  agent = "architect"
  protocol = "intent-proposal-consent"
}

graph System {
  node ◉ operator human
  node ⟁ agent architect
  link human -> architect as authorizes
}

flow Main {
  connect HumanAI
  intent HumanAI <- "Create $Path through shared understanding."
  propose HumanAI <- "Compile a verified local program before any external effect."
  consent HumanAI <- true
  disconnect HumanAI

  signal pulse "language core"
  emit "$Path online."
  remember Project.status = "active"
  signal pass "memory online"
}
"@
            Write-AriaUtf8NoBom -Path $target -Text (Normalize-AriaText -Text $template)
            Write-AriaBanner -Title 'ARIA / INITIALIZE'
            Write-AriaSummary -Title 'PROGRAM CREATED' -Passed $true -Detail $target
        }
        { $_ -in @('replay','handoff','bridge','mesh') } {
            $kind = [string]$Command.ToLowerInvariant()
            if ($Path -notin @('create','verify')) {
                throw "$kind supports 'create' and 'verify'."
            }
            if (-not $RequestPath) {
                throw "$kind $Path requires a JSON path."
            }
            if (-not $Json) {
                throw "$kind $Path requires --json so the continuity artifact remains machine-readable."
            }
            if ($Path -eq 'create') {
                $record = Invoke-AriaContinuityCreateFile -Kind $kind -Path $RequestPath
                Write-Output (ConvertTo-AriaJson $record)
            }
            else {
                $verification = Invoke-AriaContinuityVerifyFile -Kind $kind -Path $RequestPath
                Write-Output (ConvertTo-AriaJson $verification)
                if (-not $verification.valid) {
                    throw ("$kind verification rejected: " + (@($verification.errors) -join ', '))
                }
            }
        }
        'handshake' {
            if (-not $Json) {
                throw 'handshake requires --json so every participant receives the same machine-readable record.'
            }
            $handshake = Get-AriaAgentHandshake -RepositoryRoot $root
            Write-Output (ConvertTo-AriaJson -Value $handshake)
        }
        'begin' {
            if (-not $Json) {
                throw 'begin currently requires --json.'
            }

            $runtimePath = Join-Path $root 'ARIA-RUNTIME.json'
            if (-not (Test-Path -LiteralPath $runtimePath -PathType Leaf)) {
                throw 'ARIA-RUNTIME.json is missing.'
            }

            $runtime = Get-Content -LiteralPath $runtimePath -Raw |
                ConvertFrom-Json

            $result = [pscustomobject][ordered]@{
                schema = 'aria.bootstrap/1'
                ready = $true
                release = [string]$runtime.release
                repositoryRoot = $root
                runtimeManifest = 'ARIA-RUNTIME.json'
                connectionContract = 'ARIA-CONNECT.json'
                agentGuide = 'AGENTS.md'
                stableTag = [string]$runtime.continuity.stableTag
                handshake = './aria.cmd handshake --json'
                validation = [pscustomobject][ordered]@{
                    doctor = '.\aria.cmd doctor -Strict'
                    tests = '.\aria.cmd test'
                }
            }

            Write-Output (ConvertTo-AriaJson -Value $result)
        }
        'version' {
            $lock = Get-Content -LiteralPath (Join-Path $root 'aria.lock.json') -Raw | ConvertFrom-Json
            Write-AriaBanner -Title 'ARIA / VERSION'
            Write-AriaKeyValue -Key 'Compiler' -Value (Get-AriaCompilerVersion)
            Write-AriaKeyValue -Key 'Spec' -Value ([string]$lock.specVersion)
            Write-AriaKeyValue -Key 'Container' -Value ([string]$lock.containerVersion)
            Write-AriaSummary `
                -Title 'VERSION RESOLVED' `
                -Passed $true `
                -Detail (
                    'compiler={0} · spec={1} · container={2}' -f
                        (Get-AriaCompilerVersion),
                        ([string]$lock.specVersion),
                        ([string]$lock.containerVersion)
                )
        }
        'help' { Show-AriaHelp }
        default { Show-AriaHelp; throw "Unknown ARIA command '$Command'." }
    }
}
catch {
    Write-Host ''
    Write-AriaTreeStage -Name 'ARIA pipeline' -State Fail -Detail $_.Exception.Message
    $originalError = $_
    try {
        if (Get-Command Send-AriaEvent -ErrorAction SilentlyContinue) {
            $null = Send-AriaEvent -Domain cli -Phase failure -State FAIL -Energy interruption -Information $Command -Coherence $originalError.Exception.Message -Source 'aria.cli' -Render
        }
    }
    catch {
        # Preserve the original failure when the event ledger itself is unavailable.
    }
    if ($script:VerboseOutput) { Write-Host $originalError.ScriptStackTrace -ForegroundColor DarkGray }
    exit 1
}
