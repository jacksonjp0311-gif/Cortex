Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$script:TransmissionMagic = [Text.Encoding]::ASCII.GetBytes('ARIAT001')

function Get-AriaRuntimeProfile {
    [CmdletBinding()]
    param()

    $width = 120
    try {
        if ($Host -and $Host.UI -and $Host.UI.RawUI) {
            $candidate = [int]$Host.UI.RawUI.WindowSize.Width
            if ($candidate -gt 0) { $width = $candidate }
        }
    }
    catch { }

    $redirected = $false
    try { $redirected = [Console]::IsOutputRedirected } catch { }

    $ci = ([string]$env:CI).ToLowerInvariant() -eq 'true'
    $machine = ([string]$env:ARIA_OUTPUT).ToLowerInvariant() -eq 'json'
    if ($redirected -and -not $ci -and -not $env:ARIA_OUTPUT) { $machine = $true }

    if ($machine) { $mode = 'machine' }
    elseif ($ci) { $mode = 'ci' }
    elseif ($width -lt 88) { $mode = 'compact' }
    else { $mode = 'operator' }

    [pscustomobject][ordered]@{
        format = 'aria.runtime-profile'
        version = 1
        mode = $mode
        width = $width
        interactive = (-not $redirected)
        ci = $ci
        unicode = ([string]$env:ARIA_ASCII -ne '1')
        animation = (-not $ci -and [string]$env:ARIA_ANIMATION -ne '0' -and -not $redirected)
        verbose = ([string]$env:ARIA_VERBOSE -eq '1')
    }
}

function Get-AriaTransmissionCanonicalBody {
    param([Parameter(Mandatory=$true)]$Transmission)
    [pscustomobject][ordered]@{
        format = [string]$Transmission.format
        version = [int]$Transmission.version
        channel = [string]$Transmission.channel
        kind = [string]$Transmission.kind
        status = [string]$Transmission.status
        source = [string]$Transmission.source
        payload = $Transmission.payload
    }
}

function Get-AriaTransmissionDigest {
    param([Parameter(Mandatory=$true)]$Transmission)
    $body = Get-AriaTransmissionCanonicalBody -Transmission $Transmission
    $json = ConvertTo-AriaJson -Value $body
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    Get-AriaSha256Bytes -Bytes $bytes
}

function New-AriaTransmission {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9._-]*$')][string]$Channel,
        [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9._-]*$')][string]$Kind,
        [ValidateSet('pass','reject','warn','fail','info')][string]$Status = 'info',
        [string]$Source = 'external',
        [Parameter(Mandatory=$true)]$Payload
    )

    $record = [pscustomobject][ordered]@{
        format = 'aria.transmission'
        version = 1
        channel = $Channel.ToLowerInvariant()
        kind = $Kind.ToLowerInvariant()
        status = $Status.ToLowerInvariant()
        source = $Source
        payload = $Payload
        digest = ''
    }
    $record.digest = Get-AriaTransmissionDigest -Transmission $record
    $record
}

function Test-AriaTransmission {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Transmission)

    $errors = New-Object System.Collections.Generic.List[string]
    if ([string]$Transmission.format -ne 'aria.transmission') { $errors.Add('format must be aria.transmission') }
    if ([int]$Transmission.version -ne 1) { $errors.Add('version must be 1') }
    if ([string]$Transmission.channel -notmatch '^[a-z0-9][a-z0-9._-]*$') { $errors.Add('channel is invalid') }
    if ([string]$Transmission.kind -notmatch '^[a-z0-9][a-z0-9._-]*$') { $errors.Add('kind is invalid') }
    if ([string]$Transmission.status -notin @('pass','reject','warn','fail','info')) { $errors.Add('status is invalid') }

    $expected = ''
    try { $expected = Get-AriaTransmissionDigest -Transmission $Transmission }
    catch { $errors.Add($_.Exception.Message) }

    if ($expected -and [string]$Transmission.digest -ne $expected) { $errors.Add('digest mismatch') }

    [pscustomobject][ordered]@{
        valid = ($errors.Count -eq 0)
        errors = @($errors)
        digest = $expected
    }
}

function ConvertTo-AriaTransmissionBytes {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Transmission)

    $verification = Test-AriaTransmission -Transmission $Transmission
    if (-not $verification.valid) { throw ('Transmission rejected: ' + ($verification.errors -join '; ')) }

    $json = ConvertTo-AriaJson -Value $Transmission
    [byte[]]$plain = [Text.Encoding]::UTF8.GetBytes($json)

    $compressedStream = New-Object IO.MemoryStream
    try {
        $gzip = New-Object IO.Compression.GzipStream($compressedStream,[IO.Compression.CompressionMode]::Compress,$true)
        try { $gzip.Write($plain,0,$plain.Length) } finally { $gzip.Dispose() }
        [byte[]]$compressed = $compressedStream.ToArray()
    }
    finally { $compressedStream.Dispose() }

    [byte[]]$digest = for($i=0;$i-lt64;$i+=2){[Convert]::ToByte($Transmission.digest.Substring($i,2),16)}
    [byte[]]$length = [BitConverter]::GetBytes([int]$plain.Length)

    $output = New-Object IO.MemoryStream
    try {
        $output.Write($script:TransmissionMagic,0,$script:TransmissionMagic.Length)
        $output.Write($digest,0,$digest.Length)
        $output.Write($length,0,$length.Length)
        $output.Write($compressed,0,$compressed.Length)
        $output.ToArray()
    }
    finally { $output.Dispose() }
}

function Read-AriaTransmissionBytes {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][byte[]]$Bytes)

    if ($Bytes.Length -lt 45) { throw 'Transmission container is truncated.' }
    $magic = [Text.Encoding]::ASCII.GetString($Bytes,0,8)
    if ($magic -ne 'ARIAT001') { throw 'Transmission container magic is invalid.' }

    [byte[]]$digestBytes = New-Object byte[] 32
    [Array]::Copy($Bytes,8,$digestBytes,0,32)
    $headerDigest = -join ($digestBytes | ForEach-Object { $_.ToString('x2') })
    $expectedLength = [BitConverter]::ToInt32($Bytes,40)
    if ($expectedLength -lt 2 -or $expectedLength -gt 16777216) { throw 'Transmission payload length is invalid.' }

    $input = New-Object IO.MemoryStream
    try {
        $input.Write($Bytes,44,$Bytes.Length-44)
        $input.Position = 0
        $gzip = New-Object IO.Compression.GzipStream($input,[IO.Compression.CompressionMode]::Decompress)
        $plainStream = New-Object IO.MemoryStream
        try {
            $buffer = New-Object byte[] 8192
            while(($read=$gzip.Read($buffer,0,$buffer.Length)) -gt 0){
                $plainStream.Write($buffer,0,$read)
                if($plainStream.Length -gt 16777216){throw 'Transmission payload exceeds limit.'}
            }
            [byte[]]$plain=$plainStream.ToArray()
        }
        finally {
            $gzip.Dispose()
            $plainStream.Dispose()
        }
    }
    finally { $input.Dispose() }

    if ($plain.Length -ne $expectedLength) { throw 'Transmission payload length mismatch.' }
    $record = ([Text.Encoding]::UTF8.GetString($plain) | ConvertFrom-Json)
    $verification = Test-AriaTransmission -Transmission $record
    if (-not $verification.valid) { throw ('Transmission rejected: ' + ($verification.errors -join '; ')) }
    if ($record.digest -ne $headerDigest) { throw 'Transmission header digest mismatch.' }
    $record
}

function Import-AriaTransmissionPayload {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Transmission input not found: $Path" }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($raw.PSObject.Properties['format'] -and [string]$raw.format -eq 'aria.transmission') {
        $verification = Test-AriaTransmission -Transmission $raw
        if (-not $verification.valid) { throw ('Transmission rejected: ' + ($verification.errors -join '; ')) }
        return $raw
    }

    $channel = 'external'
    if ($raw.PSObject.Properties['channel'] -and $raw.channel) { $channel = ([string]$raw.channel).ToLowerInvariant() }
    elseif ($raw.PSObject.Properties['provider'] -and $raw.provider) { $channel = ([string]$raw.provider).ToLowerInvariant() }

    $kind = 'event'
    if ($raw.PSObject.Properties['kind'] -and $raw.kind) { $kind = ([string]$raw.kind).ToLowerInvariant() }

    $status = 'info'
    if ($raw.PSObject.Properties['status'] -and ([string]$raw.status).ToLowerInvariant() -in @('pass','reject','warn','fail','info')) {
        $status = ([string]$raw.status).ToLowerInvariant()
    }

    New-AriaTransmission -Channel $channel -Kind $kind -Status $status -Source ([IO.Path]::GetFileName($Path)) -Payload $raw
}

function Write-AriaTransmissionView {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Transmission,
        $Profile = (Get-AriaRuntimeProfile)
    )

    if ($Profile.mode -eq 'machine') {
        Write-Output (ConvertTo-AriaJson -Value $Transmission)
        return
    }

    Write-AriaBanner -Title 'ARIA / TRANSMISSION' -Subtitle 'typed provider membrane · canonical digest · compressed runtime record'
    Write-AriaTreeStage -Name 'channel' -State Pass -Detail $Transmission.channel
    Write-AriaTreeStage -Name 'kind' -State Pass -Detail $Transmission.kind
    $state = switch ($Transmission.status) {
        'pass' { 'Pass' }
        'reject' { 'Reject' }
        'warn' { 'Warn' }
        'fail' { 'Fail' }
        default { 'Info' }
    }
    Write-AriaTreeStage -Name 'provider result' -State $state -Detail $Transmission.status
    Write-AriaTreeStage -Name 'canonical digest' -State Pass -Detail ($Transmission.digest.Substring(0,16) + '…')
    Write-AriaSummary -Title 'TRANSMISSION VERIFIED' -Passed ($Transmission.status -ne 'fail') -Detail $Profile.mode
}

Export-ModuleMember -Function Get-AriaRuntimeProfile,New-AriaTransmission,Test-AriaTransmission,ConvertTo-AriaTransmissionBytes,Read-AriaTransmissionBytes,Import-AriaTransmissionPayload,Write-AriaTransmissionView