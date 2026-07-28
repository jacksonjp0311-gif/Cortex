Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-AriaGlyphMemoryProperty {
    param(
        [Parameter(Mandatory=$true)]$Object,
        [Parameter(Mandatory=$true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]

    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Sort-AriaGlyphMemoryStringsOrdinal {
    [CmdletBinding()]
    param(
        [AllowEmptyCollection()][object[]]$Values = @(),
        [switch]$Unique
    )

    [string[]]$items = @(
        @($Values) |
            ForEach-Object { [string]$_ }
    )

    [Array]::Sort($items,[StringComparer]::Ordinal)

    if (-not $Unique) {
        return $items
    }

    $result = New-Object System.Collections.Generic.List[string]
    $hasPrevious = $false
    $previous = ''

    foreach ($item in $items) {
        if (
            -not $hasPrevious -or
            -not [string]::Equals(
                $previous,
                $item,
                [StringComparison]::Ordinal
            )
        ) {
            $result.Add($item)
            $previous = $item
            $hasPrevious = $true
        }
    }

    return $result.ToArray()
}

function Sort-AriaGlyphMemoryObjectsOrdinal {
    [CmdletBinding()]
    param(
        [AllowEmptyCollection()][object[]]$Values = @(),
        [Parameter(Mandatory=$true)][scriptblock]$KeySelector
    )

    $sorted = [System.Collections.SortedList]::new(
        [StringComparer]::Ordinal
    )
    $index = 0

    foreach ($value in @($Values)) {
        $baseKey = [string](& $KeySelector $value)
        $key = (
            $baseKey +
            [char]0 +
            $index.ToString(
                'D10',
                [Globalization.CultureInfo]::InvariantCulture
            )
        )

        $sorted.Add($key,$value)
        $index++
    }

    return @(
        $sorted.Values |
            ForEach-Object { $_ }
    )
}

function ConvertTo-AriaGlyphCardCanonicalBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Card)

    $inputs = @(
        @(Get-AriaGlyphMemoryProperty $Card 'inputs') |
            ForEach-Object {
                [pscustomobject][ordered]@{
                    name = [string](Get-AriaGlyphMemoryProperty $_ 'name')
                    type = [string](Get-AriaGlyphMemoryProperty $_ 'type')
                }
            }
    )

    $effects = @(
        @(Get-AriaGlyphMemoryProperty $Card 'effects') |
            ForEach-Object { [string]$_ }
    )

    $capabilities = @(
        @(Get-AriaGlyphMemoryProperty $Card 'capabilities') |
            ForEach-Object { [string]$_ }
    )

    $tests = @(
        @(Get-AriaGlyphMemoryProperty $Card 'tests') |
            ForEach-Object { [string]$_ }
    )

    [pscustomobject][ordered]@{
        format = [string](Get-AriaGlyphMemoryProperty $Card 'format')
        version = [int](Get-AriaGlyphMemoryProperty $Card 'version')
        id = [string](Get-AriaGlyphMemoryProperty $Card 'id')
        symbol = [string](Get-AriaGlyphMemoryProperty $Card 'symbol')
        spoken = [string](Get-AriaGlyphMemoryProperty $Card 'spoken')
        family = [string](Get-AriaGlyphMemoryProperty $Card 'family')
        category = [string](Get-AriaGlyphMemoryProperty $Card 'category')
        fixity = [string](Get-AriaGlyphMemoryProperty $Card 'fixity')
        arity = [int](Get-AriaGlyphMemoryProperty $Card 'arity')
        inputs = $inputs
        output = [string](Get-AriaGlyphMemoryProperty $Card 'output')
        purity = [string](Get-AriaGlyphMemoryProperty $Card 'purity')
        deterministic = [bool](Get-AriaGlyphMemoryProperty $Card 'deterministic')
        effects = @(
            Sort-AriaGlyphMemoryStringsOrdinal `
                -Values $effects `
                -Unique
        )
        capabilities = @(
            Sort-AriaGlyphMemoryStringsOrdinal `
                -Values $capabilities `
                -Unique
        )
        lowering = [pscustomobject][ordered]@{
            kind = [string](
                Get-AriaGlyphMemoryProperty `
                    (Get-AriaGlyphMemoryProperty $Card 'lowering') `
                    'kind'
            )
            target = [string](
                Get-AriaGlyphMemoryProperty `
                    (Get-AriaGlyphMemoryProperty $Card 'lowering') `
                    'target'
            )
        }
        status = [string](Get-AriaGlyphMemoryProperty $Card 'status')
        tests = @(
            Sort-AriaGlyphMemoryStringsOrdinal `
                -Values $tests `
                -Unique
        )
    }
}

function Get-AriaGlyphCardDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Card)

    $body = ConvertTo-AriaGlyphCardCanonicalBody -Card $Card
    return ('sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $body)))
}

function Test-AriaGlyphCard {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Card)

    $errors = New-Object System.Collections.Generic.List[string]
    $format = [string](Get-AriaGlyphMemoryProperty $Card 'format')
    $version = Get-AriaGlyphMemoryProperty $Card 'version'
    $id = [string](Get-AriaGlyphMemoryProperty $Card 'id')
    $symbol = [string](Get-AriaGlyphMemoryProperty $Card 'symbol')
    $spoken = [string](Get-AriaGlyphMemoryProperty $Card 'spoken')
    $family = [string](Get-AriaGlyphMemoryProperty $Card 'family')
    $category = [string](Get-AriaGlyphMemoryProperty $Card 'category')
    $fixity = [string](Get-AriaGlyphMemoryProperty $Card 'fixity')
    $arity = Get-AriaGlyphMemoryProperty $Card 'arity'
    $inputs = @(Get-AriaGlyphMemoryProperty $Card 'inputs')
    $output = [string](Get-AriaGlyphMemoryProperty $Card 'output')
    $purity = [string](Get-AriaGlyphMemoryProperty $Card 'purity')
    $deterministic = Get-AriaGlyphMemoryProperty $Card 'deterministic'
    $effects = @(Get-AriaGlyphMemoryProperty $Card 'effects')
    $capabilities = @(Get-AriaGlyphMemoryProperty $Card 'capabilities')
    $lowering = Get-AriaGlyphMemoryProperty $Card 'lowering'
    $status = [string](Get-AriaGlyphMemoryProperty $Card 'status')
    $tests = @(Get-AriaGlyphMemoryProperty $Card 'tests')
    $digest = [string](Get-AriaGlyphMemoryProperty $Card 'digest')

    if ($format -ne 'aria.glyph-card') {
        $errors.Add('E_GLYPH_CARD_FORMAT')
    }

    if ($null -eq $version -or [int]$version -ne 1) {
        $errors.Add('E_GLYPH_CARD_VERSION')
    }

    if ($id -notmatch '^[a-z][a-z0-9.-]*$') {
        $errors.Add('E_GLYPH_CARD_ID')
    }

    if ([string]::IsNullOrWhiteSpace($symbol)) {
        $errors.Add('E_GLYPH_CARD_SYMBOL')
    }
    else {
        try {
            $textElements = [Globalization.StringInfo]::ParseCombiningCharacters(
                $symbol
            )

            if ($textElements.Count -ne 1) {
                $errors.Add('E_GLYPH_CARD_SYMBOL_ARITY')
            }
        }
        catch {
            $errors.Add('E_GLYPH_CARD_SYMBOL')
        }
    }

    if ([string]::IsNullOrWhiteSpace($spoken)) {
        $errors.Add('E_GLYPH_CARD_SPOKEN')
    }

    if ($family -notin @(
        'primitive',
        'function',
        'composition',
        'algorithm',
        'control',
        'intelligence',
        'authority'
    )) {
        $errors.Add('E_GLYPH_CARD_FAMILY')
    }

    if ([string]::IsNullOrWhiteSpace($category)) {
        $errors.Add('E_GLYPH_CARD_CATEGORY')
    }

    if ($fixity -notin @('prefix','infix','postfix','block','entity')) {
        $errors.Add('E_GLYPH_CARD_FIXITY')
    }

    if (
        $null -eq $arity -or
        -not (
            $arity -is [byte] -or
            $arity -is [int16] -or
            $arity -is [int32] -or
            $arity -is [int64]
        ) -or
        [int]$arity -lt 0 -or
        [int]$arity -gt 8
    ) {
        $errors.Add('E_GLYPH_CARD_ARITY')
    }
    elseif ($inputs.Count -ne [int]$arity) {
        $errors.Add('E_GLYPH_CARD_INPUT_COUNT')
    }

    foreach ($input in $inputs) {
        $inputName = [string](Get-AriaGlyphMemoryProperty $input 'name')
        $inputType = [string](Get-AriaGlyphMemoryProperty $input 'type')

        if ($inputName -notmatch '^[a-z][A-Za-z0-9]*$') {
            $errors.Add('E_GLYPH_CARD_INPUT_NAME')
        }

        if ([string]::IsNullOrWhiteSpace($inputType)) {
            $errors.Add('E_GLYPH_CARD_INPUT_TYPE')
        }
    }

    if ([string]::IsNullOrWhiteSpace($output)) {
        $errors.Add('E_GLYPH_CARD_OUTPUT')
    }

    if ($purity -notin @('pure','effectful')) {
        $errors.Add('E_GLYPH_CARD_PURITY')
    }

    if (-not ($deterministic -is [bool])) {
        $errors.Add('E_GLYPH_CARD_DETERMINISM')
    }

    if ($purity -eq 'pure' -and $effects.Count -gt 0) {
        $errors.Add('E_GLYPH_CARD_PURE_EFFECT')
    }

    foreach ($effect in $effects) {
        if ([string]$effect -notmatch '^[a-z][a-z0-9.-]*$') {
            $errors.Add('E_GLYPH_CARD_EFFECT')
        }
    }

    foreach ($capability in $capabilities) {
        if ([string]$capability -notmatch '^cap:[a-z][a-z0-9.:-]*$') {
            $errors.Add('E_GLYPH_CARD_CAPABILITY')
        }
    }

    $loweringKind = [string](
        Get-AriaGlyphMemoryProperty $lowering 'kind'
    )
    $loweringTarget = [string](
        Get-AriaGlyphMemoryProperty $lowering 'target'
    )

    if ($loweringKind -notin @('alias','composition','builtin')) {
        $errors.Add('E_GLYPH_CARD_LOWERING_KIND')
    }

    if ([string]::IsNullOrWhiteSpace($loweringTarget)) {
        $errors.Add('E_GLYPH_CARD_LOWERING_TARGET')
    }

    if ($status -notin @('specified','verified','deprecated')) {
        $errors.Add('E_GLYPH_CARD_STATUS')
    }

    if ($tests.Count -eq 0) {
        $errors.Add('E_GLYPH_CARD_TESTS')
    }

    $expected = ''

    try {
        $expected = Get-AriaGlyphCardDigest -Card $Card
    }
    catch {
        $errors.Add('E_GLYPH_CARD_DIGEST_CALCULATION')
    }

    if ($expected -and $digest -ne $expected) {
        $errors.Add('E_GLYPH_CARD_DIGEST')
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
        expectedDigest = $expected
    }
}

function ConvertTo-AriaGlyphRegistryCanonicalBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Registry)

    $reservedValues = @(
        @(Get-AriaGlyphMemoryProperty $Registry 'reserved') |
            ForEach-Object {
                [pscustomobject][ordered]@{
                    symbol = [string](
                        Get-AriaGlyphMemoryProperty $_ 'symbol'
                    )
                    semanticRoot = [string](
                        Get-AriaGlyphMemoryProperty $_ 'semanticRoot'
                    )
                    source = [string](
                        Get-AriaGlyphMemoryProperty $_ 'source'
                    )
                }
            }
    )

    $reserved = @(
        Sort-AriaGlyphMemoryObjectsOrdinal `
            -Values $reservedValues `
            -KeySelector {
                param($entry)

                return (
                    [string]$entry.symbol +
                    [char]31 +
                    [string]$entry.semanticRoot +
                    [char]31 +
                    [string]$entry.source
                )
            }
    )

    $cardValues = @(
        @(Get-AriaGlyphMemoryProperty $Registry 'cards') |
            ForEach-Object {
                $body = ConvertTo-AriaGlyphCardCanonicalBody -Card $_

                [pscustomobject][ordered]@{
                    body = $body
                    digest = [string](
                        Get-AriaGlyphMemoryProperty $_ 'digest'
                    )
                }
            }
    )

    $cards = @(
        Sort-AriaGlyphMemoryObjectsOrdinal `
            -Values $cardValues `
            -KeySelector {
                param($entry)
                return [string]$entry.body.id
            }
    )

    [pscustomobject][ordered]@{
        format = [string](Get-AriaGlyphMemoryProperty $Registry 'format')
        version = [int](Get-AriaGlyphMemoryProperty $Registry 'version')
        reserved = $reserved
        cards = $cards
    }
}

function Get-AriaGlyphCardRegistryDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Registry)

    $body = ConvertTo-AriaGlyphRegistryCanonicalBody -Registry $Registry
    return ('sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $body)))
}

function Test-AriaGlyphCardRegistry {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Registry)

    $errors = New-Object System.Collections.Generic.List[string]
    $format = [string](Get-AriaGlyphMemoryProperty $Registry 'format')
    $version = Get-AriaGlyphMemoryProperty $Registry 'version'
    $reserved = @(Get-AriaGlyphMemoryProperty $Registry 'reserved')
    $cards = @(Get-AriaGlyphMemoryProperty $Registry 'cards')
    $digest = [string](Get-AriaGlyphMemoryProperty $Registry 'digest')

    if ($format -ne 'aria.glyph-card-registry') {
        $errors.Add('E_GLYPH_REGISTRY_FORMAT')
    }

    if ($null -eq $version -or [int]$version -ne 1) {
        $errors.Add('E_GLYPH_REGISTRY_VERSION')
    }

    if ($cards.Count -eq 0) {
        $errors.Add('E_GLYPH_REGISTRY_EMPTY')
    }

    $reservedSymbols = @{}
    $cardIds = @{}
    $cardSymbols = @{}

    foreach ($entry in $reserved) {
        $symbol = [string](Get-AriaGlyphMemoryProperty $entry 'symbol')
        $semanticRoot = [string](
            Get-AriaGlyphMemoryProperty $entry 'semanticRoot'
        )

        if (
            [string]::IsNullOrWhiteSpace($symbol) -or
            [string]::IsNullOrWhiteSpace($semanticRoot)
        ) {
            $errors.Add('E_GLYPH_REGISTRY_RESERVED')
            continue
        }

        if ($reservedSymbols.ContainsKey($symbol)) {
            $errors.Add('E_GLYPH_REGISTRY_RESERVED_DUPLICATE')
        }

        $reservedSymbols[$symbol] = $true
    }

    foreach ($card in $cards) {
        $validation = Test-AriaGlyphCard -Card $card

        foreach ($errorCode in @($validation.errors)) {
            $errors.Add([string]$errorCode)
        }

        $id = [string](Get-AriaGlyphMemoryProperty $card 'id')
        $symbol = [string](Get-AriaGlyphMemoryProperty $card 'symbol')

        if ($cardIds.ContainsKey($id)) {
            $errors.Add('E_GLYPH_REGISTRY_CARD_ID_DUPLICATE')
        }

        if ($cardSymbols.ContainsKey($symbol)) {
            $errors.Add('E_GLYPH_REGISTRY_CARD_SYMBOL_DUPLICATE')
        }

        if ($reservedSymbols.ContainsKey($symbol)) {
            $errors.Add('E_GLYPH_CARD_SYMBOL_RESERVED')
        }

        $cardIds[$id] = $true
        $cardSymbols[$symbol] = $true
    }

    $expected = ''

    try {
        $expected = Get-AriaGlyphCardRegistryDigest -Registry $Registry
    }
    catch {
        $errors.Add('E_GLYPH_REGISTRY_DIGEST_CALCULATION')
    }

    if ($expected -and $digest -ne $expected) {
        $errors.Add('E_GLYPH_REGISTRY_DIGEST')
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
        expectedDigest = $expected
        cardCount = $cards.Count
    }
}

function Seal-AriaGlyphCardRegistry {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Glyph card registry is missing: $Path"
    }

    $registry = Read-AriaUtf8Text -Path $Path | ConvertFrom-Json

    foreach ($card in @(Get-AriaGlyphMemoryProperty $registry 'cards')) {
        $card.digest = Get-AriaGlyphCardDigest -Card $card
    }

    $registry.digest = Get-AriaGlyphCardRegistryDigest -Registry $registry
    $validation = Test-AriaGlyphCardRegistry -Registry $registry

    if (-not [bool]$validation.valid) {
        throw (
            'Glyph card registry sealing failed: ' +
            (@($validation.errors) -join ', ')
        )
    }

    $json = ($registry | ConvertTo-Json -Depth 100)
    $json = $json.Replace("`r`n","`n").Replace("`r","`n") + "`n"

    Write-AriaUtf8NoBom -Path $Path -Text $json

    return $registry
}

function Read-AriaGlyphCardRegistry {
    [CmdletBinding()]
    param(
        [string]$Root = (Get-AriaRepositoryRoot),
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        $Path = Join-Path $Root 'grammar/glyph-cards.json'
    }

    $registry = Read-AriaUtf8Text -Path $Path | ConvertFrom-Json
    $validation = Test-AriaGlyphCardRegistry -Registry $registry

    if (-not [bool]$validation.valid) {
        throw (
            'Glyph card registry rejected: ' +
            (@($validation.errors) -join ', ')
        )
    }

    return $registry
}

function Get-AriaGlyphCard {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Id,
        $Registry,
        [string]$Root = (Get-AriaRepositoryRoot)
    )

    if ($null -eq $Registry) {
        $Registry = Read-AriaGlyphCardRegistry -Root $Root
    }

    $matches = @(
        @(Get-AriaGlyphMemoryProperty $Registry 'cards') |
            Where-Object {
                [string](Get-AriaGlyphMemoryProperty $_ 'id') -eq $Id
            }
    )

    if ($matches.Count -ne 1) {
        throw "Expected one glyph card '$Id'; found $($matches.Count)."
    }

    return $matches[0]
}

function ConvertTo-AriaGlyphActivationCanonicalBody {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Activation)

    [pscustomobject][ordered]@{
        format = [string](
            Get-AriaGlyphMemoryProperty $Activation 'format'
        )
        version = [int](
            Get-AriaGlyphMemoryProperty $Activation 'version'
        )
        cardId = [string](
            Get-AriaGlyphMemoryProperty $Activation 'cardId'
        )
        cardDigest = [string](
            Get-AriaGlyphMemoryProperty $Activation 'cardDigest'
        )
        symbol = [string](
            Get-AriaGlyphMemoryProperty $Activation 'symbol'
        )
        contextDigest = [string](
            Get-AriaGlyphMemoryProperty $Activation 'contextDigest'
        )
        policyDecision = [string](
            Get-AriaGlyphMemoryProperty $Activation 'policyDecision'
        )
        testsPassed = [int](
            Get-AriaGlyphMemoryProperty $Activation 'testsPassed'
        )
        testsFailed = [int](
            Get-AriaGlyphMemoryProperty $Activation 'testsFailed'
        )
        source = [string](
            Get-AriaGlyphMemoryProperty $Activation 'source'
        )
        state = [string](
            Get-AriaGlyphMemoryProperty $Activation 'state'
        )
    }
}

function Get-AriaGlyphActivationDigest {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Activation)

    $body = ConvertTo-AriaGlyphActivationCanonicalBody `
        -Activation $Activation

    return ('sha256:' + (Get-AriaSha256Text (ConvertTo-AriaJson $body)))
}

function New-AriaGlyphActivation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Card,
        [Parameter(Mandatory=$true)]
        [ValidatePattern('^sha256:[a-f0-9]{64}$')]
        [string]$ContextDigest,
        [ValidateSet('allow','deny')][string]$PolicyDecision = 'allow',
        [ValidateRange(0,1048576)][int]$TestsPassed = 0,
        [ValidateRange(0,1048576)][int]$TestsFailed = 0,
        [string]$Source = 'aria.runtime'
    )

    $cardValidation = Test-AriaGlyphCard -Card $Card

    if (-not [bool]$cardValidation.valid) {
        throw (
            'Cannot activate invalid glyph card: ' +
            (@($cardValidation.errors) -join ', ')
        )
    }

    if ([string]$Card.status -ne 'verified') {
        throw "Glyph card '$($Card.id)' is not verified."
    }

    if ($PolicyDecision -ne 'allow') {
        throw "Glyph card '$($Card.id)' was denied by policy."
    }

    if ($TestsPassed -le 0 -or $TestsFailed -ne 0) {
        throw "Glyph card '$($Card.id)' requires a clean test receipt."
    }

    $activation = [pscustomobject][ordered]@{
        format = 'aria.glyph-activation'
        version = 1
        cardId = [string]$Card.id
        cardDigest = [string]$Card.digest
        symbol = [string]$Card.symbol
        contextDigest = $ContextDigest
        policyDecision = $PolicyDecision
        testsPassed = $TestsPassed
        testsFailed = $TestsFailed
        source = $Source
        state = 'active'
        digest = ''
    }

    $activation.digest = Get-AriaGlyphActivationDigest `
        -Activation $activation

    return $activation
}

function Test-AriaGlyphActivation {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Activation)

    $errors = New-Object System.Collections.Generic.List[string]

    if ([string]$Activation.format -ne 'aria.glyph-activation') {
        $errors.Add('E_GLYPH_ACTIVATION_FORMAT')
    }

    if ([int]$Activation.version -ne 1) {
        $errors.Add('E_GLYPH_ACTIVATION_VERSION')
    }

    if ([string]$Activation.cardId -notmatch '^[a-z][a-z0-9.-]*$') {
        $errors.Add('E_GLYPH_ACTIVATION_CARD')
    }

    if ([string]$Activation.cardDigest -notmatch '^sha256:[a-f0-9]{64}$') {
        $errors.Add('E_GLYPH_ACTIVATION_CARD_DIGEST')
    }

    if ([string]$Activation.contextDigest -notmatch '^sha256:[a-f0-9]{64}$') {
        $errors.Add('E_GLYPH_ACTIVATION_CONTEXT')
    }

    if ([string]$Activation.policyDecision -ne 'allow') {
        $errors.Add('E_GLYPH_ACTIVATION_POLICY')
    }

    if (
        [int]$Activation.testsPassed -le 0 -or
        [int]$Activation.testsFailed -ne 0
    ) {
        $errors.Add('E_GLYPH_ACTIVATION_TESTS')
    }

    if ([string]$Activation.state -ne 'active') {
        $errors.Add('E_GLYPH_ACTIVATION_STATE')
    }

    $expected = ''

    try {
        $expected = Get-AriaGlyphActivationDigest -Activation $Activation
    }
    catch {
        $errors.Add('E_GLYPH_ACTIVATION_DIGEST_CALCULATION')
    }

    if ($expected -and [string]$Activation.digest -ne $expected) {
        $errors.Add('E_GLYPH_ACTIVATION_DIGEST')
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors.ToArray() | Sort-Object -Unique)
        expectedDigest = $expected
    }
}

function Write-AriaGlyphActivationMemory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Activation,
        [string]$WorkspaceRoot = (Get-AriaRepositoryRoot)
    )

    $validation = Test-AriaGlyphActivation -Activation $Activation

    if (-not [bool]$validation.valid) {
        throw (
            'Glyph activation memory rejected: ' +
            (@($validation.errors) -join ', ')
        )
    }

    $workspace = [IO.Path]::GetFullPath($WorkspaceRoot)
    $folder = Join-Path $workspace '.aria/memory'
    $path = Join-Path $folder 'glyph-memory.ndjson'

    $null = New-Item -ItemType Directory -Path $folder -Force
    $json = $Activation | ConvertTo-Json -Depth 100 -Compress

    [IO.File]::AppendAllText(
        $path,
        ($json + [Environment]::NewLine),
        (New-Object Text.UTF8Encoding($false))
    )

    [pscustomobject][ordered]@{
        path = $path
        digest = [string]$Activation.digest
        cardId = [string]$Activation.cardId
    }
}

function Read-AriaGlyphActivationMemory {
    [CmdletBinding()]
    param([string]$WorkspaceRoot = (Get-AriaRepositoryRoot))

    $workspace = [IO.Path]::GetFullPath($WorkspaceRoot)
    $path = Join-Path $workspace '.aria/memory/glyph-memory.ndjson'

    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return @()
    }

    $records = New-Object System.Collections.Generic.List[object]

    foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $record = $line | ConvertFrom-Json
        $validation = Test-AriaGlyphActivation -Activation $record

        if (-not [bool]$validation.valid) {
            throw (
                'Glyph activation ledger rejected: ' +
                (@($validation.errors) -join ', ')
            )
        }

        $records.Add($record)
    }

    return $records.ToArray()
}

Export-ModuleMember -Function `
    ConvertTo-AriaGlyphCardCanonicalBody, `
    Get-AriaGlyphCardDigest, `
    Test-AriaGlyphCard, `
    ConvertTo-AriaGlyphRegistryCanonicalBody, `
    Get-AriaGlyphCardRegistryDigest, `
    Test-AriaGlyphCardRegistry, `
    Seal-AriaGlyphCardRegistry, `
    Read-AriaGlyphCardRegistry, `
    Get-AriaGlyphCard, `
    ConvertTo-AriaGlyphActivationCanonicalBody, `
    Get-AriaGlyphActivationDigest, `
    New-AriaGlyphActivation, `
    Test-AriaGlyphActivation, `
    Write-AriaGlyphActivationMemory, `
    Read-AriaGlyphActivationMemory