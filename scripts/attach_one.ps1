# Zero-friction Hermetic attach (Windows PowerShell).
# Prefers: uvx → pipx → python -m pip → cortex.attach_main
# Run ONCE. Do not chain with separate uvx/python attach commands.
param(
    [Parameter(Position = 0)]
    [string]$Path = ".",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)
$ErrorActionPreference = "Stop"
if (-not $env:CORTEX_HOME) { $env:CORTEX_HOME = Join-Path $HOME ".cortex" }
# Nested powershell -File often has no interactive TTY; keep ritual but avoid hang
if (-not $env:CORTEX_ATTACH_RITUAL) { $env:CORTEX_ATTACH_RITUAL = "1" }

$spec = "git+https://github.com/jacksonjp0311-gif/Cortex@main"
# Resolve path now so nested tools see a real directory
$HostPath = (Resolve-Path -LiteralPath $Path).Path
$argsList = @($HostPath) + @($Rest)

function Invoke-AndExit([scriptblock]$Block) {
    & $Block
    exit $LASTEXITCODE
}

if (Get-Command uvx -ErrorAction SilentlyContinue) {
    Invoke-AndExit { & uvx --from $spec cortex-attach @argsList }
}
if (Get-Command pipx -ErrorAction SilentlyContinue) {
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
& $py -m pip install -q --user $spec 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install -q $spec
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# Stay in current process host — do not spawn nested powershell -File
& $py -m cortex.attach_main @argsList
exit $LASTEXITCODE
