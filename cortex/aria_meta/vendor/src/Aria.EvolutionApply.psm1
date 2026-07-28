Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-AriaEvolutionRecordDirectory {
    param(
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot
    )
    $digest=$ProposalId
    if($digest.StartsWith('sha256:')){$digest=$digest.Substring(7)}
    if($digest-notmatch'^[a-f0-9]{64}$'){throw 'Evolution proposal identity must be a SHA-256 identity.'}
    $directory=Join-Path $WorkspaceRoot ('.aria/evolution/{0}' -f $digest)
    if(-not(Test-Path -LiteralPath $directory -PathType Container)){
        throw "Evolution proposal record not found: $ProposalId"
    }
    [IO.Path]::GetFullPath($directory)
}

function Read-AriaEvolutionJsonRecord {
    param(
        [Parameter(Mandatory=$true)][string]$Directory,
        [Parameter(Mandatory=$true)][string]$Name
    )
    $path=Join-Path $Directory $Name
    if(-not(Test-Path -LiteralPath $path -PathType Leaf)){
        throw "Evolution record is missing $Name."
    }
    try{Read-AriaUtf8Text $path|ConvertFrom-Json}
    catch{throw "Evolution record '$Name' is invalid JSON: $($_.Exception.Message)"}
}

function Test-AriaEvolutionApplyReadiness {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Plan,
        [Parameter(Mandatory=$true)]$Verification,
        [Parameter(Mandatory=$true)]$CandidateSnapshot,
        [Parameter(Mandatory=$true)][string]$CurrentCommit
    )

    $errors=New-Object System.Collections.Generic.List[string]
    if([string]$Verification.schema-ne'aria.evolution-verification-record/0.8'){
        $errors.Add('Verification record schema is not supported.')
    }
    if([string]$Verification.state-ne'authorized'){
        $errors.Add('Evolution verification state is not authorized.')
    }
    if([string]$Plan.proposalId-ne[string]$Verification.proposalId){
        $errors.Add('Plan and verification proposal identities differ.')
    }
    if([string]$Plan.id-ne[string]$Verification.planRecordId){
        $errors.Add('Verification does not bind to this plan record.')
    }
    if([string]$Plan.candidateSnapshotId-ne[string]$CandidateSnapshot.id){
        $errors.Add('Plan and candidate snapshot identities differ.')
    }
    if([string]$Verification.candidateSnapshotId-ne[string]$CandidateSnapshot.id){
        $errors.Add('Verification and candidate snapshot identities differ.')
    }
    if(-not[bool]$Plan.rollbackVerified-or-not[bool]$Verification.rollbackVerified){
        $errors.Add('Rollback proof is not verified.')
    }
    if([string]$Plan.baseCommit-ne$CurrentCommit){
        $errors.Add(("Authorized base commit {0} does not match current HEAD {1}." -f $Plan.baseCommit,$CurrentCommit))
    }
    [pscustomobject][ordered]@{
        ready=($errors.Count-eq0)
        errors=$errors.ToArray()
    }
}

function Assert-AriaEvolutionCandidateDigest {
    param(
        [Parameter(Mandatory=$true)]$File,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot
    )
    $path=Resolve-AriaConfinedPath -Root $WorkspaceRoot -Path ([string]$File.path)
    $content=[string]$File.content
    $actual=Get-AriaSha256Text $content
    if($actual-ne[string]$File.digest){
        throw "Candidate digest mismatch for $($File.path)."
    }
    [pscustomobject][ordered]@{path=$path;relativePath=([string]$File.path);content=$content}
}

function Restore-AriaEvolutionBase {
    param(
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string]$BaseCommit,
        [string[]]$AddedPaths=@()
    )
    $reset=Invoke-AriaGitProcess -Arguments @('reset','--hard',$BaseCommit) -RepositoryRoot $WorkspaceRoot
    Assert-AriaGitResult -Result $reset -Operation 'evolution-rollback'
    foreach($relative in @($AddedPaths)){
        $path=Resolve-AriaConfinedPath -Root $WorkspaceRoot -Path $relative
        if(Test-Path -LiteralPath $path){
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
}

function Invoke-AriaEvolutionGate {
    param(
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [Parameter(Mandatory=$true)][string]$Name
    )
    $command=Join-Path $WorkspaceRoot 'aria.cmd'
    & $command @Arguments
    if($LASTEXITCODE-ne0){throw "Evolution gate '$Name' failed with exit code $LASTEXITCODE."}
}

function Invoke-AriaEvolutionApply {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ProposalId,
        [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
        [string]$CommitMessage,
        [switch]$Push,
        [string]$Remote='origin',
        [string]$Branch='main',
        [switch]$VerboseBuffer
    )

    $WorkspaceRoot=[IO.Path]::GetFullPath($WorkspaceRoot)
    $null=Assert-AriaGitClean -RepositoryRoot $WorkspaceRoot
    $currentCommit=Get-AriaGitHead -RepositoryRoot $WorkspaceRoot
    $directory=Get-AriaEvolutionRecordDirectory -ProposalId $ProposalId -WorkspaceRoot $WorkspaceRoot
    $plan=Read-AriaEvolutionJsonRecord -Directory $directory -Name 'plan.json'
    $verification=Read-AriaEvolutionJsonRecord -Directory $directory -Name 'verification.json'
    $candidate=Read-AriaEvolutionJsonRecord -Directory $directory -Name 'candidate-snapshot.json'

    $readiness=Test-AriaEvolutionApplyReadiness `
        -Plan $plan `
        -Verification $verification `
        -CandidateSnapshot $candidate `
        -CurrentCommit $currentCommit
    if(-not$readiness.ready){
        throw ('Evolution apply rejected: '+($readiness.errors-join' '))
    }

    $candidateFiles=New-Object System.Collections.Generic.List[object]
    foreach($file in @($candidate.files)){
        $candidateFiles.Add((Assert-AriaEvolutionCandidateDigest -File $file -WorkspaceRoot $WorkspaceRoot))
    }

    $deleted=@($plan.semanticDiff.removed|ForEach-Object{[string]$_.path})
    $added=@($plan.semanticDiff.added|ForEach-Object{[string]$_.path})
    $targetPaths=@(
        @($candidateFiles|ForEach-Object{$_.relativePath})
        $deleted
        'MANIFEST.sha256'
    )|Sort-Object -Unique

    $committed=$false
    $commitId=$null
    try{
        foreach($file in $candidateFiles){
            $parent=Split-Path -Parent $file.path
            if(-not(Test-Path -LiteralPath $parent)){New-Item -ItemType Directory -Path $parent -Force|Out-Null}
            Write-AriaUtf8NoBom -Path $file.path -Text $file.content
        }
        foreach($relative in $deleted){
            $path=Resolve-AriaConfinedPath -Root $WorkspaceRoot -Path $relative
            if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path -Recurse -Force}
        }

        foreach($file in $candidateFiles){
            $actual=Get-AriaSha256File $file.path
            $record=@($candidate.files|Where-Object{[string]$_.path-eq$file.relativePath})[0]
            if($actual-ne[string]$record.digest){
                throw "Applied bytes do not match authorized digest for $($file.relativePath)."
            }
        }

        $null=Update-AriaManifest -Root $WorkspaceRoot
        $manifest=Test-AriaManifest -Root $WorkspaceRoot
        if(-not$manifest.valid){
            throw ('Manifest verification failed: '+($manifest.errors-join'; '))
        }

        Invoke-AriaEvolutionGate -WorkspaceRoot $WorkspaceRoot -Arguments @('doctor','-Strict') -Name 'doctor.strict'
        Invoke-AriaEvolutionGate -WorkspaceRoot $WorkspaceRoot -Arguments @('test') -Name 'conformance'

        $message=$CommitMessage
        if([string]::IsNullOrWhiteSpace($message)){
            $short=([string]$plan.proposalId).Substring(7,12)
            $message="Apply authorized ARIA evolution $short"
        }

        $commit=Invoke-AriaGitCommit `
            -RepositoryRoot $WorkspaceRoot `
            -Paths $targetPaths `
            -Message $message `
            -ExpectedPaths $targetPaths `
            -VerboseBuffer:$VerboseBuffer
        $commitId=$commit.head
        $committed=$true

        $pushResult=$null
        if($Push){
            $pushResult=Invoke-AriaGitPush `
                -RepositoryRoot $WorkspaceRoot `
                -Remote $Remote `
                -Branch $Branch `
                -Render `
                -VerboseBuffer:$VerboseBuffer
        }

        $receipt=[pscustomobject][ordered]@{
            schema='aria.evolution-application-receipt/0.1'
            proposalId=[string]$plan.proposalId
            verificationId=[string]$verification.id
            baseCommit=$currentCommit
            commit=$commitId
            candidateSnapshotId=[string]$candidate.id
            paths=$targetPaths
            manifestVerified=$true
            doctorStrict=$true
            conformance=$true
            pushed=[bool]$Push
            remote=$(if($Push){"$Remote/$Branch"}else{$null})
            appliedAt=[DateTimeOffset]::UtcNow.ToString('o')
            state=$(if($Push){'committed-and-pushed'}else{'committed'})
        }
        $receiptPath=Join-Path $directory 'application.json'
        Write-AriaUtf8NoBom -Path $receiptPath -Text (ConvertTo-AriaJson $receipt)

        [pscustomobject][ordered]@{
            plan=$plan
            verification=$verification
            receipt=$receipt
            receiptPath=$receiptPath
            commit=$commit
            push=$pushResult
        }
    }
    catch{
        if(-not$committed){
            Restore-AriaEvolutionBase `
                -WorkspaceRoot $WorkspaceRoot `
                -BaseCommit $currentCommit `
                -AddedPaths $added
        }
        throw
    }
}

Export-ModuleMember -Function `
    Get-AriaEvolutionRecordDirectory, `
    Read-AriaEvolutionJsonRecord, `
    Test-AriaEvolutionApplyReadiness, `
    Invoke-AriaEvolutionApply