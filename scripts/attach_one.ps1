# Zero-friction Hermetic attach (Windows PowerShell).
# Prefers: uvx → pipx → python -m pip → cortex.attach_main
#
# Run ONCE from your project folder. Do NOT also run uvx/python attach.
# Prefer:  & $env:TEMP\cortex-attach.ps1 .
# Avoid:   powershell -File ...  (nested host can truncate/hang the ritual)
param(
    [Parameter(Position = 0)]
    [string]$Path = ".",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)
$ErrorActionPreference = "Stop"
$env:PYTHONUNBUFFERED = "1"
if (-not $env:CORTEX_HOME) { $env:CORTEX_HOME = Join-Path $HOME ".cortex" }

# Nested / non-interactive hosts: keep ritual short so it cannot look like a hang
$isNested = $false
try {
    if (-not [Environment]::UserInteractive) { $isNested = $true }
    if ($Host.Name -eq "ServerRemoteHost") { $isNested = $true }
} catch { }
if ($MyInvocation.CommandOrigin -eq "Runspace" -or $PSSenderInfo) { $isNested = $true }
# Detect classic nested: parent invoked us via powershell -File
if ($env:CORTEX_ATTACH_NESTED -eq "1") { $isNested = $true }
if ($isNested -and -not $env:CORTEX_ATTACH_FAST) {
    $env:CORTEX_ATTACH_FAST = "1"
}

$spec = "git+https://github.com/jacksonjp0311-gif/Cortex@main"

# Fail fast on bad / placeholder paths
if ($Path -match 'path[\\/]to[\\/]your' -or $Path -eq 'C:\path\to\your\project') {
    Write-Error "That path is a README placeholder. cd to your real project first, then pass . (dot)."
    exit 2
}
try {
    $HostPath = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
} catch {
    Write-Error "Host path not found: $Path  (cd to your project, then run with . )"
    exit 2
}
$argsList = @($HostPath) + @($Rest)

function Invoke-AndExit([scriptblock]$Block) {
    & $Block
    if ($null -eq $LASTEXITCODE) { exit 0 }
    exit $LASTEXITCODE
}

if (Get-Command uvx -ErrorAction SilentlyContinue) {
    Write-Host "Cortex attach via uvx → $HostPath" -ForegroundColor DarkGray
    Invoke-AndExit { & uvx --from $spec cortex-attach @argsList }
}
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    Write-Host "Cortex attach via pipx → $HostPath" -ForegroundColor DarkGray
    Invoke-AndExit { & pipx run --spec $spec cortex-attach @argsList }
}
$py = $null
foreach ($c in @("python", "py", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Error "Python 3.10+ required. Install Python or uv (https://github.com/astral-sh/uv)."
    exit 1
}
Write-Host "Cortex attach via $py → $HostPath" -ForegroundColor DarkGray
& $py -m pip install -q --user $spec 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install -q $spec
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# Stay in THIS PowerShell — never spawn nested powershell -File
& $py -m cortex.attach_main @argsList
if ($null -eq $LASTEXITCODE) { exit 0 }
exit $LASTEXITCODE
