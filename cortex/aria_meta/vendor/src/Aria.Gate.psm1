Set-StrictMode -Version 2.0

function Write-AriaGateLine {
    param([string]$Name, [bool]$Passed, [string]$Detail = '')
    Write-AriaTreeStage -Name $Name -State $(if ($Passed) { 'Pass' } else { 'Fail' }) -Detail $Detail
}

function Invoke-AriaGate {
    param(
        [Parameter(Mandatory=$true)][string]$SourcePath,
        [Parameter(Mandatory=$true)][string]$PolicyPath,
        [string]$WorkspaceRoot = (Get-AriaRepositoryRoot),
        [switch]$Quiet,
        [switch]$StrictRepository
    )
    if ($StrictRepository) {
        $manifest = Test-AriaManifest -Root (Get-AriaRepositoryRoot)
        if (-not $Quiet) { Write-AriaGateLine -Name 'repository-manifest' -Passed $manifest.valid -Detail $manifest.message }
        if (-not $manifest.valid) { throw "ARIA strict gate rejected repository integrity: $($manifest.message)" }
    }

    $lock = Get-AriaLock
    $compilerCompatible = ([string](Get-AriaCompilerVersion) -eq [string]$lock.compilerVersion)
    if (-not $Quiet) { Write-AriaGateLine -Name 'compiler-lock' -Passed $compilerCompatible -Detail ([string]$lock.compilerVersion) }
    if (-not $compilerCompatible) { throw "ARIA compiler version does not match aria.lock.json." }

    $resolvedSource = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).Path
    $sourceInfo = Get-Item -LiteralPath $resolvedSource
    if ($sourceInfo.Length -gt 1048576) { throw 'ARIA bootstrap source files are limited to 1 MiB.' }
    $source = Get-AriaSourceText -Path $resolvedSource
    $policy = Get-AriaPolicy -PolicyPath $PolicyPath
    $parse = Parse-AriaSource -Source $source -SourceName $resolvedSource
    $parseErrors = Get-AriaErrorDiagnostics -Diagnostics $parse.diagnostics
    $syntaxPassed = $parseErrors.Count -eq 0
    if (-not $Quiet) { Write-AriaGateLine -Name 'syntax' -Passed $syntaxPassed }
    if (-not $syntaxPassed) {
        if (-not $Quiet) {
            foreach ($error in $parseErrors) { Write-AriaTreeStage -Depth 1 -Name ("line {0} · {1}" -f $error.line, $error.code) -State Fail -Detail $error.message }
        }
        throw "ARIA syntax gate rejected '$resolvedSource'."
    }

    $policyValidation = Test-AriaPolicyDocument -Policy $policy
    if (-not $Quiet) { Write-AriaGateLine -Name 'policy-shape' -Passed $policyValidation.valid -Detail 'typed deny-by-default policy' }
    if (-not $policyValidation.valid) { throw ('ARIA policy document is invalid: ' + ($policyValidation.errors -join '; ')) }

    $sourceCompatible = ([string]$parse.model.specVersion -eq [string]$lock.specVersion)
    if (-not $Quiet) { Write-AriaGateLine -Name 'spec-compatibility' -Passed $sourceCompatible -Detail ([string]$lock.specVersion) }
    if (-not $sourceCompatible) { throw "ARIA source spec '$($parse.model.specVersion)' is incompatible with locked spec '$($lock.specVersion)'." }

    $semantic = Test-AriaSemantics -ParseResult $parse -Policy $policy
    $errors = Get-AriaErrorDiagnostics -Diagnostics $semantic.diagnostics
    $semanticsPassed = $errors.Count -eq 0
    if (-not $Quiet) { Write-AriaGateLine -Name 'semantics' -Passed $semanticsPassed }
    if (-not $semanticsPassed) {
        if (-not $Quiet) {
            foreach ($error in $errors) { Write-AriaTreeStage -Depth 1 -Name ("line {0} · {1}" -f $error.line, $error.code) -State Fail -Detail $error.message }
        }
        throw "ARIA gate rejected '$resolvedSource'."
    }

    $policyPassed = $true
    if (-not $Quiet) { Write-AriaGateLine -Name 'policy' -Passed $policyPassed -Detail 'deny-by-default policy accepted all requested effects' }

    $bytecode = ConvertTo-AriaBytecodeModel -SemanticResult $semantic -SourceText $source
    $verification = Test-AriaBytecodeModel -BytecodeModel $bytecode
    if (-not $Quiet) { Write-AriaGateLine -Name 'bytecode-verifier' -Passed $verification.valid -Detail ("max-stack={0}" -f $verification.maxStack) }
    if (-not $verification.valid) { throw ('ARIA bytecode verifier rejected compiler output: ' + ($verification.errors -join '; ')) }

    $first = ConvertTo-AriaContainerBytes -BytecodeModel $bytecode
    $second = ConvertTo-AriaContainerBytes -BytecodeModel $bytecode
    $firstHash = Get-AriaSha256Bytes -Bytes $first
    $secondHash = Get-AriaSha256Bytes -Bytes $second
    $reproducible = $firstHash -eq $secondHash
    if (-not $Quiet) { Write-AriaGateLine -Name 'reproducibility' -Passed $reproducible -Detail $firstHash }
    if (-not $reproducible) { throw 'ARIA compiler produced non-deterministic container bytes.' }

    $verified = Read-AriaContainerBytes -Bytes $first
    $containerPassed = $verified.bytecode.sourceHash -eq (Get-AriaSha256Text -Text $source)
    if (-not $Quiet) { Write-AriaGateLine -Name 'container-integrity' -Passed $containerPassed }
    if (-not $containerPassed) { throw 'ARIA container source identity verification failed.' }

    return [pscustomobject][ordered]@{
        sourcePath = $resolvedSource
        sourceHash = $bytecode.sourceHash
        irHash = $bytecode.irHash
        buildHash = $firstHash
        bytecode = $bytecode
        bytes = $first
        diagnostics = $semantic.diagnostics
        effectGraph = $semantic.effectGraph
        policyPath = (Resolve-Path -LiteralPath $PolicyPath).Path
        workspaceRoot = [System.IO.Path]::GetFullPath($WorkspaceRoot)
    }
}

function Invoke-AriaCompile {
    param(
        [Parameter(Mandatory=$true)][string]$SourcePath,
        [Parameter(Mandatory=$true)][string]$PolicyPath,
        [string]$OutputPath,
        [string]$WorkspaceRoot = (Get-AriaRepositoryRoot),
        [switch]$Quiet,
        [switch]$StrictRepository
    )
    $gate = Invoke-AriaGate -SourcePath $SourcePath -PolicyPath $PolicyPath -WorkspaceRoot $WorkspaceRoot -Quiet:$Quiet -StrictRepository:$StrictRepository
    if (-not $OutputPath) {
        $buildRoot = Resolve-AriaConfinedPath -WorkspaceRoot $WorkspaceRoot -Scope '.' -RequestedPath '.aria/build'
        $fileName = "$($gate.bytecode.programName)-$($gate.bytecode.programVersion).ariac"
        $OutputPath = Join-Path $buildRoot $fileName
    }
    $fullOutput = [System.IO.Path]::GetFullPath($OutputPath)
    Write-AriaContainer -Bytes $gate.bytes -Path $fullOutput

    $provenance = [pscustomobject][ordered]@{
        format = 'aria.provenance'
        generatedAtUtc = [DateTime]::UtcNow.ToString('o')
        builder = 'aria-powershell-bootstrap'
        compilerVersion = Get-AriaCompilerVersion
        sourcePath = $gate.sourcePath
        sourceHash = $gate.sourceHash
        irHash = $gate.irHash
        artifactPath = $fullOutput
        artifactHash = $gate.buildHash
        policyPath = $gate.policyPath
        policyHash = Get-AriaSha256File -Path $gate.policyPath
    }
    Write-AriaUtf8NoBom -Path ($fullOutput + '.aria-provenance.json') -Text (($provenance | ConvertTo-Json -Depth 20) + [Environment]::NewLine)
    return [pscustomobject][ordered]@{ gate = $gate; artifactPath = $fullOutput; provenance = $provenance }
}

Export-ModuleMember -Function Invoke-AriaGate, Invoke-AriaCompile
