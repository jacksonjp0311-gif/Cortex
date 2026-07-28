Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Invoke-AriaGitProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [switch]$VerboseBuffer
    )

    $gitCommand = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $gitCommand) {
        $gitCommand = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if (-not $gitCommand) {
        throw 'ARIA Gitflow could not locate a Git application.'
    }

    $gitPath = $null
    foreach ($propertyName in @('Path','Source','Definition','Name')) {
        $property = $gitCommand.PSObject.Properties[$propertyName]
        if ($null -ne $property) {
            $candidate = [string]$property.Value
            if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                $gitPath = $candidate
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($gitPath)) {
        throw 'ARIA Gitflow resolved Git without a usable launch path.'
    }

    $operation = if ($Arguments.Count -gt 0) { [string]$Arguments[0] } else { 'transport' }
    $mode = if ($operation -in @('push','fetch','ls-remote')) { 'remote' } else { 'verification' }

    Invoke-AriaBufferedProcess `
        -FilePath $gitPath `
        -ArgumentList $Arguments `
        -WorkingDirectory $RepositoryRoot `
        -Label ("github.{0}" -f $operation) `
        -Mode $mode `
        -VerboseBuffer:$VerboseBuffer
}
function Assert-AriaGitResult {
    param(
        [Parameter(Mandatory=$true)]$Result,
        [Parameter(Mandatory=$true)][string]$Operation
    )

    if ([int]$Result.exitCode -ne 0) {
        $message = ([string]$Result.stderr + [Environment]::NewLine + [string]$Result.stdout).Trim()
        throw ("ARIA Gitflow {0} failed: {1}" -f $Operation,$message)
    }
}

function Get-AriaGitHead {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$RepositoryRoot)

    $result = Invoke-AriaGitProcess -Arguments @('rev-parse','HEAD') -RepositoryRoot $RepositoryRoot
    Assert-AriaGitResult -Result $result -Operation 'local-head'
    $result.stdout.Trim()
}

function Get-AriaGitRemoteHead {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [string]$Remote = 'origin',
        [string]$Branch = 'main'
    )

    $result = Invoke-AriaGitProcess `
        -Arguments @('ls-remote',$Remote,("refs/heads/{0}" -f $Branch)) `
        -RepositoryRoot $RepositoryRoot

    Assert-AriaGitResult -Result $result -Operation 'remote-head'
    $line = $result.stdout.Trim()
    if (-not $line) { throw "ARIA Gitflow could not resolve $Remote/$Branch." }
    ($line -split '\s+')[0]
}

function Assert-AriaGitClean {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$RepositoryRoot)

    $result = Invoke-AriaGitProcess -Arguments @('status','--porcelain') -RepositoryRoot $RepositoryRoot
    Assert-AriaGitResult -Result $result -Operation 'clean-tree'
    if ($result.stdout.Trim()) {
        throw 'ARIA Gitflow requires a clean working tree.'
    }
    $true
}

function Write-AriaGitVerification {
    param(
        [Parameter(Mandatory=$true)][ValidateSet('pull','push','sync')][string]$Operation,
        [Parameter(Mandatory=$true)][string]$Remote,
        [Parameter(Mandatory=$true)][string]$Branch,
        [Parameter(Mandatory=$true)][string]$Head
    )

    $short = $Head.Substring(0,7)
    $information = "{0}/{1} · {2}" -f $Remote,$Branch,$short

    $eventCommand = Get-Command Send-AriaEvent -ErrorAction SilentlyContinue
    if ($eventCommand) {
        $null = Send-AriaEvent `
            -Domain github `
            -Phase $Operation `
            -State PASS `
            -Energy transport `
            -Information $information `
            -Coherence 'remote identity verified' `
            -Source 'aria.gitflow' `
            -Data ([pscustomobject][ordered]@{
                remote = $Remote
                branch = $Branch
                head = $Head
                verified = $true
            }) `
            -Render
        return
    }

    $frameCommand = Get-Command Write-AriaCausalFrame -ErrorAction SilentlyContinue
    if ($frameCommand) {
        Write-AriaCausalFrame `
            -Domain github `
            -Phase $Operation `
            -State PASS `
            -Information $information `
            -Cause local `
            -Effect remote
        return
    }

    Write-Host ("◆  github.{0}  {1}  verified" -f $Operation,$information) -ForegroundColor Green
}

function Invoke-AriaGitPull {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [string]$Remote = 'origin',
        [string]$Branch = 'main',
        [switch]$Render,
        [switch]$VerboseBuffer
    )

    $null = Assert-AriaGitClean -RepositoryRoot $RepositoryRoot

    $fetch = Invoke-AriaGitProcess `
        -Arguments @('fetch',$Remote,$Branch) `
        -RepositoryRoot $RepositoryRoot `
        -VerboseBuffer:$VerboseBuffer
    Assert-AriaGitResult -Result $fetch -Operation 'fetch'

    $merge = Invoke-AriaGitProcess `
        -Arguments @('merge','--ff-only',("$Remote/$Branch")) `
        -RepositoryRoot $RepositoryRoot `
        -VerboseBuffer:$VerboseBuffer
    Assert-AriaGitResult -Result $merge -Operation 'pull'

    $local = Get-AriaGitHead -RepositoryRoot $RepositoryRoot
    $tracked = Invoke-AriaGitProcess `
        -Arguments @('rev-parse',("$Remote/$Branch")) `
        -RepositoryRoot $RepositoryRoot
    Assert-AriaGitResult -Result $tracked -Operation 'tracked-head'

    $trackedHead = $tracked.stdout.Trim()
    if ($local -ne $trackedHead) {
        throw 'ARIA Gitflow pull verification failed: local and tracking SHAs differ.'
    }

    if ($Render) {
        Write-AriaGitVerification -Operation pull -Remote $Remote -Branch $Branch -Head $local
    }

    [pscustomobject][ordered]@{
        operation = 'pull'
        verified = $true
        head = $local
        remote = $Remote
        branch = $Branch
    }
}

function Invoke-AriaGitPush {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [string]$Remote = 'origin',
        [string]$Branch = 'main',
        [switch]$Render,
        [switch]$VerboseBuffer
    )

    $null = Assert-AriaGitClean -RepositoryRoot $RepositoryRoot
    $local = Get-AriaGitHead -RepositoryRoot $RepositoryRoot

    $push = Invoke-AriaGitProcess `
        -Arguments @('push',$Remote,$Branch) `
        -RepositoryRoot $RepositoryRoot `
        -VerboseBuffer:$VerboseBuffer
    Assert-AriaGitResult -Result $push -Operation 'push'

    $remoteHead = Get-AriaGitRemoteHead `
        -RepositoryRoot $RepositoryRoot `
        -Remote $Remote `
        -Branch $Branch

    if ($local -ne $remoteHead) {
        throw 'ARIA Gitflow push verification failed: local and remote SHAs differ.'
    }

    if ($Render) {
        Write-AriaGitVerification -Operation push -Remote $Remote -Branch $Branch -Head $local
    }

    [pscustomobject][ordered]@{
        operation = 'push'
        verified = $true
        head = $local
        remote = $Remote
        branch = $Branch
    }
}

function Invoke-AriaGitSync {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [string]$Remote = 'origin',
        [string]$Branch = 'main',
        [switch]$Render,
        [switch]$VerboseBuffer
    )

    $pull = Invoke-AriaGitPull `
        -RepositoryRoot $RepositoryRoot `
        -Remote $Remote `
        -Branch $Branch `
        -VerboseBuffer:$VerboseBuffer

    $push = Invoke-AriaGitPush `
        -RepositoryRoot $RepositoryRoot `
        -Remote $Remote `
        -Branch $Branch `
        -VerboseBuffer:$VerboseBuffer

    if ($pull.head -ne $push.head) {
        throw 'ARIA Gitflow sync verification failed: pull and push identities differ.'
    }

    if ($Render) {
        Write-AriaGitVerification -Operation sync -Remote $Remote -Branch $Branch -Head $push.head
    }

    [pscustomobject][ordered]@{
        operation = 'sync'
        verified = $true
        head = $push.head
        remote = $Remote
        branch = $Branch
    }
}

function Get-AriaGitChangedPaths {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$RepositoryRoot)

    $tracked=Invoke-AriaGitProcess `
        -Arguments @('diff','--name-only','--') `
        -RepositoryRoot $RepositoryRoot
    Assert-AriaGitResult -Result $tracked -Operation 'changed-paths'

    $untracked=Invoke-AriaGitProcess `
        -Arguments @('ls-files','--others','--exclude-standard') `
        -RepositoryRoot $RepositoryRoot
    Assert-AriaGitResult -Result $untracked -Operation 'untracked-paths'

    @(
        @($tracked.stdout -split "`r?`n")
        @($untracked.stdout -split "`r?`n")
    ) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        ForEach-Object { ([string]$_).Replace('\','/') } |
        Sort-Object -Unique
}

function Invoke-AriaGitCommit {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$RepositoryRoot,
        [Parameter(Mandatory=$true)][string[]]$Paths,
        [Parameter(Mandatory=$true)][string]$Message,
        [string[]]$ExpectedPaths=$Paths,
        [switch]$VerboseBuffer
    )

    $actual=@(Get-AriaGitChangedPaths -RepositoryRoot $RepositoryRoot)
    $expected=@($ExpectedPaths|ForEach-Object{([string]$_).Replace('\','/')}|Sort-Object -Unique)
    $unexpected=@($actual|Where-Object{$_-notin$expected})
    $missing=@($expected|Where-Object{$_-notin$actual})
    if($unexpected.Count-or$missing.Count){
        throw ("ARIA Gitflow commit path verification failed. Unexpected: [{0}] Missing: [{1}]" -f ($unexpected-join', '),($missing-join', '))
    }

    $arguments=New-Object System.Collections.Generic.List[string]
    $arguments.Add('add')
    $arguments.Add('--')
    foreach($path in $Paths){$arguments.Add(([string]$path).Replace('\','/'))}
    $add=Invoke-AriaGitProcess `
        -Arguments $arguments.ToArray() `
        -RepositoryRoot $RepositoryRoot `
        -VerboseBuffer:$VerboseBuffer
    Assert-AriaGitResult -Result $add -Operation 'add'

    $commit=Invoke-AriaGitProcess `
        -Arguments @('commit','-m',$Message) `
        -RepositoryRoot $RepositoryRoot `
        -VerboseBuffer:$VerboseBuffer
    Assert-AriaGitResult -Result $commit -Operation 'commit'

    $head=Get-AriaGitHead -RepositoryRoot $RepositoryRoot
    $null=Assert-AriaGitClean -RepositoryRoot $RepositoryRoot
    [pscustomobject][ordered]@{
        operation='commit'
        verified=$true
        head=$head
        paths=$expected
        message=$Message
    }
}
Export-ModuleMember -Function `
    Invoke-AriaGitProcess, `
    Assert-AriaGitResult, `
    Get-AriaGitHead, `
    Get-AriaGitRemoteHead, `
    Assert-AriaGitClean, `
    Get-AriaGitChangedPaths, `
    Invoke-AriaGitCommit, `
    Write-AriaGitVerification, `
    Invoke-AriaGitPull, `
    Invoke-AriaGitPush, `
    Invoke-AriaGitSync