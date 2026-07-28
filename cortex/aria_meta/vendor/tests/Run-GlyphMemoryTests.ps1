[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$root = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path `
    ([IO.Path]::GetTempPath()) `
    ('aria-glyph-memory-tests-' + [guid]::NewGuid().ToString('N'))

Import-Module `
    (Join-Path $root 'src/Aria.Common.psm1') `
    -Force `
    -DisableNameChecking

Import-Module `
    (Join-Path $root 'src/Aria.GlyphMemory.psm1') `
    -Force `
    -DisableNameChecking

$script:passed = 0
$script:failed = 0
$script:expected = 8

function Assert-True {
    param([bool]$Condition,[string]$Message)

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Equal {
    param($Expected,$Actual,[string]$Message)

    if (
        (ConvertTo-AriaJson ([pscustomobject][ordered]@{v=$Expected})) -ne
        (ConvertTo-AriaJson ([pscustomobject][ordered]@{v=$Actual}))
    ) {
        throw "$Message Expected=$Expected Actual=$Actual"
    }
}

function Test-GlyphMemoryCase {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Body
    )

    try {
        & $Body
        $script:passed++
        Write-Host ("◆  {0}" -f $Name) -ForegroundColor Green
    }
    catch {
        $script:failed++
        Write-Host (
            "⬗  {0} · {1}" -f
                $Name,
                $_.Exception.Message
        ) -ForegroundColor Magenta
    }
}

$null = New-Item -ItemType Directory -Path $tempRoot -Force

try {
    Write-Host ''
    Write-Host '⌬  ARIA / GLYPH MEMORY' -ForegroundColor Cyan
    Write-Host '⧉  glyph-memory lattice ×8' -ForegroundColor DarkGray

    $registry = Read-AriaGlyphCardRegistry -Root $root

    Test-GlyphMemoryCase 'registry is sealed and valid' {
        $validation = Test-AriaGlyphCardRegistry -Registry $registry
        Assert-True $validation.valid (
            'Registry rejected: ' +
            (@($validation.errors) -join ', ')
        )
        Assert-Equal 6 $validation.cardCount 'Card count mismatch.'
    }

    Test-GlyphMemoryCase 'new glyph symbols are collision-free' {
        $symbols = @($registry.cards.symbol)
        Assert-Equal 6 @($symbols | Sort-Object -Unique).Count `
            'Card symbols are not unique.'

        $reserved = @($registry.reserved.symbol)

        Assert-Equal 0 @(
            $symbols |
                Where-Object { $_ -in $reserved }
        ).Count 'A new card reused a reserved glyph.'
    }

    Test-GlyphMemoryCase 'card identity is deterministic' {
        $card = Get-AriaGlyphCard `
            -Id 'function.invoke' `
            -Registry $registry

        $cardDigest = Get-AriaGlyphCardDigest -Card $card
        $registryDigest = Get-AriaGlyphCardRegistryDigest -Registry $registry

        Assert-Equal $card.digest $cardDigest `
            'Stored card digest mismatch.'
        Assert-Equal $registry.digest $registryDigest `
            'Stored registry digest mismatch.'

        $originalCulture = [Threading.Thread]::CurrentThread.CurrentCulture
        $originalUiCulture = [Threading.Thread]::CurrentThread.CurrentUICulture
        $cultures = New-Object System.Collections.Generic.List[object]
        $cultures.Add([Globalization.CultureInfo]::InvariantCulture)

        foreach ($cultureName in @('en-US','tr-TR','de-DE')) {
            try {
                $cultures.Add(
                    [Globalization.CultureInfo]::GetCultureInfo($cultureName)
                )
            }
            catch {
            }
        }

        try {
            foreach ($culture in $cultures) {
                [Threading.Thread]::CurrentThread.CurrentCulture = $culture
                [Threading.Thread]::CurrentThread.CurrentUICulture = $culture

                Assert-Equal $cardDigest `
                    (Get-AriaGlyphCardDigest -Card $card) `
                    "Card digest changed under culture '$($culture.Name)'."

                Assert-Equal $registryDigest `
                    (Get-AriaGlyphCardRegistryDigest -Registry $registry) `
                    "Registry digest changed under culture '$($culture.Name)'."
            }
        }
        finally {
            [Threading.Thread]::CurrentThread.CurrentCulture = $originalCulture
            [Threading.Thread]::CurrentThread.CurrentUICulture = $originalUiCulture
        }
    }

    Test-GlyphMemoryCase 'tampered card identity is rejected' {
        $card = (
            Get-AriaGlyphCard `
                -Id 'function.invoke' `
                -Registry $registry
        ) | ConvertTo-Json -Depth 100 | ConvertFrom-Json

        $card.spoken = 'mutated'
        $validation = Test-AriaGlyphCard -Card $card

        Assert-True (-not $validation.valid) `
            'Tampered card unexpectedly verified.'

        Assert-True (
            'E_GLYPH_CARD_DIGEST' -in @($validation.errors)
        ) 'Tamper rejection code missing.'
    }

    Test-GlyphMemoryCase 'reserved symbol collision is rejected' {
        $copy = $registry |
            ConvertTo-Json -Depth 100 |
            ConvertFrom-Json

        $copy.cards[2].symbol = '◆'
        $copy.cards[2].digest = Get-AriaGlyphCardDigest `
            -Card $copy.cards[2]

        $copy.digest = Get-AriaGlyphCardRegistryDigest `
            -Registry $copy

        $validation = Test-AriaGlyphCardRegistry -Registry $copy

        Assert-True (-not $validation.valid) `
            'Reserved symbol collision unexpectedly verified.'

        Assert-True (
            'E_GLYPH_CARD_SYMBOL_RESERVED' -in
            @($validation.errors)
        ) 'Reserved-symbol rejection code missing.'
    }

    Test-GlyphMemoryCase 'verified card activates with clean evidence' {
        $card = Get-AriaGlyphCard `
            -Id 'function.invoke' `
            -Registry $registry

        $context = 'sha256:' + (
            Get-AriaSha256Text 'glyph-memory-test-context'
        )

        $activation = New-AriaGlyphActivation `
            -Card $card `
            -ContextDigest $context `
            -PolicyDecision allow `
            -TestsPassed 3 `
            -TestsFailed 0 `
            -Source 'tests'

        $validation = Test-AriaGlyphActivation `
            -Activation $activation

        Assert-True $validation.valid `
            'Verified activation was rejected.'

        Assert-Equal 'active' $activation.state `
            'Activation state mismatch.'
    }

    Test-GlyphMemoryCase 'verified filter activates with clean evidence' {
        $card = Get-AriaGlyphCard `
            -Id 'algorithm.filter' `
            -Registry $registry

        $context = 'sha256:' + (
            Get-AriaSha256Text 'glyph-memory-test-context'
        )

        $activation = New-AriaGlyphActivation `
            -Card $card `
            -ContextDigest $context `
            -PolicyDecision allow `
            -TestsPassed 24 `
            -TestsFailed 0 `
            -Source 'tests'

        Assert-True (Test-AriaGlyphActivation $activation).valid `
            'Verified filter activation was rejected.'
    }

    Test-GlyphMemoryCase 'activation memory round-trips and detects tampering' {
        $workspace = Join-Path $tempRoot 'memory'
        $null = New-Item -ItemType Directory -Path $workspace -Force

        $card = Get-AriaGlyphCard `
            -Id 'function.return' `
            -Registry $registry

        $context = 'sha256:' + (
            Get-AriaSha256Text 'glyph-memory-ledger-context'
        )

        $activation = New-AriaGlyphActivation `
            -Card $card `
            -ContextDigest $context `
            -PolicyDecision allow `
            -TestsPassed 3 `
            -Source 'tests'

        $written = Write-AriaGlyphActivationMemory `
            -Activation $activation `
            -WorkspaceRoot $workspace

        $records = @(
            Read-AriaGlyphActivationMemory `
                -WorkspaceRoot $workspace
        )

        Assert-Equal 1 $records.Count `
            'Activation memory count mismatch.'

        Assert-Equal $activation.digest $records[0].digest `
            'Activation digest changed after replay.'

        $line = Get-Content -LiteralPath $written.path -Raw
        $record = $line | ConvertFrom-Json
        $record.source = 'tampered'

        [IO.File]::WriteAllText(
            $written.path,
            (($record | ConvertTo-Json -Depth 100 -Compress) + "`n"),
            (New-Object Text.UTF8Encoding($false))
        )

        $rejected = $false

        try {
            $null = Read-AriaGlyphActivationMemory `
                -WorkspaceRoot $workspace
        }
        catch {
            $rejected = $true
        }

        Assert-True $rejected `
            'Tampered activation memory unexpectedly replayed.'
    }

    if (($script:passed + $script:failed) -ne $script:expected) {
        throw (
            "Glyph-memory test count diverged. Expected={0} Observed={1}" -f
                $script:expected,
                ($script:passed + $script:failed)
        )
    }

    Write-Host (
        '⧉  glyph-memory lattice {0}/{1} · {2}' -f
            $script:passed,
            $script:expected,
            $(if ($script:failed -eq 0) {
                'coherent'
            }
            else {
                "$($script:failed) fracture(s)"
            })
    ) -ForegroundColor $(if ($script:failed -eq 0) {
        'Green'
    }
    else {
        'Magenta'
    })

    if ($script:failed -gt 0) {
        throw "Glyph-memory test suite failed: $script:failed failure(s)."
    }
}
finally {
    Remove-Item `
        -LiteralPath $tempRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
}
