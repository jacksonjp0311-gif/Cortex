# Zero-friction Hermetic attach (Windows PowerShell).
# Prefers: uvx → pipx → python -m pip → cortex-attach
param(
    [Parameter(Position = 0)]
    [string]$Path = ".",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)
$ErrorActionPreference = "Stop"
if (-not $env:CORTEX_HOME) { $env:CORTEX_HOME = Join-Path $HOME ".cortex" }
if (-not $env:CORTEX_ATTACH_RITUAL) { $env:CORTEX_ATTACH_RITUAL = "1" }

$spec = "git+https://github.com/jacksonjp0311-gif/Cortex@main"
$argsList = @($Path) + @($Rest)

if (Get-Command uvx -ErrorAction SilentlyContinue) {
    & uvx --from $spec cortex-attach @argsList
    exit $LASTEXITCODE
}
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    & pipx run --spec $spec cortex-attach @argsList
    exit $LASTEXITCODE
}
$py = $null
foreach ($c in @("python", "py", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Error "Python 3.10+ required. Install Python or uv (https://github.com/astral-sh/uv)."
    exit 1
}
& $py -m pip install -q --user $spec 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install -q $spec }
& $py -m cortex.attach_main @argsList
exit $LASTEXITCODE
