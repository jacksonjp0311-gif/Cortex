from __future__ import annotations

import json
import shlex
import stat
import sys
from pathlib import Path
from typing import Any

from .config import RepoConfig, save_repo_config

MANAGED_BEGIN = "<!-- CORTEX:MANAGED:BEGIN -->"
MANAGED_END = "<!-- CORTEX:MANAGED:END -->"

AGENT_BLOCK = f"""{MANAGED_BEGIN}
## Cortex Repository Memory Protocol

This repository uses Cortex for verified repository assimilation, selective recall, and sparse neural interlinking.
Every activation is first routed through the local deterministic Thalamus planner, which allocates memory lanes and inhibits irrelevant evidence.

### Mandatory startup sequence

Before broad repository reading, planning, editing, or code generation:

1. Run `.\\.cortex\\bin\\cortex.ps1 activate -Task \"<current task>\"` on Windows PowerShell, or `./.cortex/bin/cortex.sh activate --task \"<current task>\"` on Bash.
2. Inspect the returned bootstrap status, governor mode, learned environment, evidence references, neural support paths, and structural neighborhood.
3. If the bootstrap certificate is missing, degraded, or stale, run the wrapper's `bootstrap` command before relying on memory.
4. Read only the cited files and line ranges first. Expand context only when the packet is insufficient.
5. Treat repository source, tests, compiler output, and current runtime evidence as more authoritative than summaries.
6. Record decisions, discoveries, invariants, failures, fixes, and outcomes with the wrapper's `remember` command.
7. Run `consolidate` at task completion to create a provenance-bearing Discovery Card.
8. Prefer `ritual` to close activate→remember→consolidate in one step.
9. Obey packet `agent_protocol` and governor mode (`read_only` = no host edits).

### Authority boundary

Cortex provides memory, relationships, telemetry, sparse activation, and evidence references. Neural plasticity changes only bounded internal association weights; it never authorizes durable source mutation. The host repository's rules and explicit human authorization remain controlling.

### Required commands

```powershell
.\\.cortex\\bin\\cortex.ps1 activate -Task "<task>"
.\\.cortex\\bin\\cortex.ps1 query -Query "<narrow question>"
.\\.cortex\\bin\\cortex.ps1 remember -Kind decision -Text "<decision>"
.\\.cortex\\bin\\cortex.ps1 consolidate
.\\.cortex\\bin\\cortex.ps1 ritual -Task "<task>" -Text "<durable fact>"
```

```bash
./.cortex/bin/cortex.sh activate --task "<task>"
./.cortex/bin/cortex.sh query --query "<narrow question>"
./.cortex/bin/cortex.sh remember --kind decision --text "<decision>"
./.cortex/bin/cortex.sh consolidate
./.cortex/bin/cortex.sh ritual --task "<task>" --text "<durable fact>"
```
{MANAGED_END}"""

POWERSHELL_WRAPPER = r'''param(
    [Parameter(Position=0)]
    [ValidateSet(
        "activate", "bootstrap", "query", "remember", "consolidate", "ritual",
        "verify", "status", "graph", "telemetry", "environment", "meta-language",
        "thalamus", "interlink", "neural-replay", "doctor",
        "identity", "distill", "kernels", "interconnect", "immune", "metrics",
        "prune", "organism", "breathe", "causal"
    )]
    [string]$Command = "activate",
    [string]$Task = "",
    [string]$Query = "",
    [string]$Kind = "discovery",
    [string]$Text = "",
    [string]$Path = "",
    [string]$Action = "status",
    [string]$Profile = "agent",
    [ValidateSet("before", "after")]
    [string]$Slot = "before",
    [int]$Budget = 800,
    [int]$K = 8,
    [switch]$Learn,
    [switch]$DryRun,
    [switch]$NoSeal,
    [switch]$DoctrineOnly,
    [switch]$Annotate,
    [switch]$Decay
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ConfigPath = Join-Path $RepoRoot ".cortex\config.json"
if (-not (Test-Path $ConfigPath)) {
    throw "Cortex config is missing: $ConfigPath. Re-run repository bootstrap."
}

$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$RepoName = [string]$Config.repository_name
$CortexHome = [string]$Config.cortex_home
if ([string]::IsNullOrWhiteSpace($CortexHome)) { $CortexHome = [string]$env:CORTEX_HOME }
if ([string]::IsNullOrWhiteSpace($CortexHome)) { $CortexHome = '__CORTEX_HOME_PS__' }
$EngineModuleRoot = [string]$Config.engine_module_root
if ([string]::IsNullOrWhiteSpace($EngineModuleRoot)) { $EngineModuleRoot = '__CORTEX_ENGINE_MODULE_ROOT_PS__' }
if (-not [string]::IsNullOrWhiteSpace($EngineModuleRoot) -and (Test-Path $EngineModuleRoot)) {
    if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $env:PYTHONPATH = $EngineModuleRoot }
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH) -and -not $env:PYTHONPATH.StartsWith($EngineModuleRoot)) {
        $env:PYTHONPATH = "$EngineModuleRoot;$env:PYTHONPATH"
    }
}

$EnginePython = [string]$Config.engine_python
if ([string]::IsNullOrWhiteSpace($EnginePython)) { $EnginePython = [string]$env:CORTEX_PYTHON }
if ([string]::IsNullOrWhiteSpace($EnginePython)) { $EnginePython = '__CORTEX_ENGINE_PYTHON_PS__' }

$ResolvedPython = $null
if (Test-Path $EnginePython) { $ResolvedPython = (Resolve-Path $EnginePython).Path }
if ($null -eq $ResolvedPython) {
    $PythonCommand = Get-Command $EnginePython -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) { $ResolvedPython = $PythonCommand.Source }
}
if ($null -eq $ResolvedPython) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) { $ResolvedPython = $PythonCommand.Source }
}
if ($null -eq $ResolvedPython) {
    throw "Cortex Python was not found. Set CORTEX_PYTHON or re-run repository bootstrap."
}

& $ResolvedPython -c "import cortex" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "The selected Python cannot import Cortex. Set CORTEX_PYTHON or re-run repository bootstrap."
}

$ArgsList = @("-m", "cortex", "--home", $CortexHome)
if ($Command -eq "activate") {
    if ([string]::IsNullOrWhiteSpace($Task)) { throw "-Task is required for activate." }
    $ArgsList += @("activate", "--repo", $RepoName, "--task", $Task, "--budget", "$Budget", "--json")
}
if ($Command -eq "bootstrap") { $ArgsList += @("bootstrap", $RepoRoot, "--name", $RepoName, "--json") }
if ($Command -eq "query") {
    if ([string]::IsNullOrWhiteSpace($Query)) { throw "-Query is required for query." }
    $ArgsList += @("query", $Query, "--repo", $RepoName, "--json")
}
if ($Command -eq "remember") {
    if ([string]::IsNullOrWhiteSpace($Text)) { throw "-Text is required for remember." }
    $ArgsList += @("remember", "--repo", $RepoName, "--kind", $Kind, "--text", $Text, "--json")
}
if ($Command -eq "consolidate") { $ArgsList += @("consolidate", "--repo", $RepoName, "--json") }
if ($Command -eq "ritual") {
    if ([string]::IsNullOrWhiteSpace($Task)) { throw "-Task is required for ritual." }
    $ArgsList += @("ritual", "--repo", $RepoName, "--task", $Task, "--budget", "$Budget", "--json")
    if (-not [string]::IsNullOrWhiteSpace($Text)) {
        $ArgsList += @("--remember-kind", $Kind, "--remember-text", $Text)
    }
}
if ($Command -eq "verify") { $ArgsList += @("verify", "--repo", $RepoName, "--json") }
if ($Command -eq "status") { $ArgsList += @("status", "--repo", $RepoName, "--json") }
if ($Command -eq "graph") { $ArgsList += @("graph", "--repo", $RepoName, "--json") }
if ($Command -eq "telemetry") { $ArgsList += @("telemetry", "--repo", $RepoName, "--json") }
if ($Command -eq "environment") { $ArgsList += @("environment", "--repo", $RepoName, "--json") }
if ($Command -eq "meta-language") { $ArgsList += @("meta-language", "--repo", $RepoName, "--json") }
if ($Command -eq "thalamus") {
    if ([string]::IsNullOrWhiteSpace($Task)) { throw "-Task is required for thalamus." }
    $ArgsList += @("thalamus", "--repo", $RepoName, "--task", $Task, "--budget", "$Budget", "--json")
}
if ($Command -eq "doctor") { $ArgsList += @("doctor", "--repo", $RepoName, "--json") }
if ($Command -eq "neural-replay") { $ArgsList += @("neural-replay", "--repo", $RepoName, "--json") }
if ($Command -eq "interlink") {
    if ([string]::IsNullOrWhiteSpace($Task)) { throw "-Task is required for interlink." }
    $ArgsList += @("interlink", "--repo", $RepoName, "--task", $Task, "--json")
    if ($Learn) { $ArgsList += "--learn" }
}
if ($Command -eq "identity") {
    $ArgsList += @("identity", "--json")
    if (-not [string]::IsNullOrWhiteSpace($RepoName)) { $ArgsList += @("--repo", $RepoName) }
    if (-not [string]::IsNullOrWhiteSpace($Path)) { $ArgsList += @("--path", $Path) }
}
if ($Command -eq "distill") {
    $ArgsList += @("distill", "--repo", $RepoName, "--json")
    if ($NoSeal) { $ArgsList += "--no-seal" }
    if ($DoctrineOnly) { $ArgsList += "--doctrine-only" }
}
if ($Command -eq "kernels") {
    $ArgsList += @("kernels", "--repo", $RepoName, "--json")
    if ($Annotate) { $ArgsList += "--annotate" }
}
if ($Command -eq "interconnect") { $ArgsList += @("interconnect", "--repo", $RepoName, "--json") }
if ($Command -eq "immune") { $ArgsList += @("immune", "--repo", $RepoName, "--json") }
if ($Command -eq "metrics") { $ArgsList += @("metrics", "--repo", $RepoName, "--json") }
if ($Command -eq "prune") {
    $ArgsList += @("prune", "--repo", $RepoName, "--json")
    if ($DryRun) { $ArgsList += "--dry-run" }
    if ($Decay) { $ArgsList += "--decay" }
}
if ($Command -eq "organism") {
    if ([string]::IsNullOrWhiteSpace($Task)) { throw "-Task is required for organism." }
    $ArgsList += @("organism", "--repo", $RepoName, "--task", $Task, "--budget", "$Budget", "--profile", $Profile, "--json")
}
if ($Command -eq "breathe") {
    $ArgsList += @("breathe", "--repo", $RepoName, "--budget", "$Budget", "--profile", $Profile, "--json")
    if (-not [string]::IsNullOrWhiteSpace($Task)) { $ArgsList += @("--task", $Task) }
}
if ($Command -eq "causal") {
    $ValidCausal = @("status", "report", "evaluate", "probe")
    if ($ValidCausal -notcontains $Action) {
        throw "-Action for causal must be one of: status, report, evaluate, probe"
    }
    $ArgsList += @("causal", $Action, "--repo", $RepoName, "--json")
    if ($Action -eq "probe") {
        if ([string]::IsNullOrWhiteSpace($Task) -and [string]::IsNullOrWhiteSpace($Query)) {
            throw "-Task or -Query is required for causal probe."
        }
        $ProbeText = if (-not [string]::IsNullOrWhiteSpace($Task)) { $Task } else { $Query }
        $ArgsList += @("--task", $ProbeText, "--slot", $Slot, "--k", "$K")
    }
}

& $ResolvedPython @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
'''

BASH_WRAPPER = r'''#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-activate}"
if [[ $# -gt 0 ]]; then shift; fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_PATH="$REPO_ROOT/.cortex/config.json"
ENGINE_PYTHON=__CORTEX_ENGINE_PYTHON_SH__
ENGINE_MODULE_ROOT=__CORTEX_ENGINE_MODULE_ROOT_SH__
CORTEX_HOME_PATH=__CORTEX_HOME_SH__

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Cortex config is missing: $CONFIG_PATH. Re-run repository bootstrap." >&2
  exit 2
fi

if [[ -z "$ENGINE_PYTHON" && -n "${CORTEX_PYTHON:-}" ]]; then ENGINE_PYTHON="$CORTEX_PYTHON"; fi
if [[ -z "$CORTEX_HOME_PATH" && -n "${CORTEX_HOME:-}" ]]; then CORTEX_HOME_PATH="$CORTEX_HOME"; fi
if [[ -d "$ENGINE_MODULE_ROOT" ]]; then export PYTHONPATH="$ENGINE_MODULE_ROOT${PYTHONPATH:+:$PYTHONPATH}"; fi
if [[ "$ENGINE_PYTHON" == */* && ! -x "$ENGINE_PYTHON" ]]; then ENGINE_PYTHON=""; fi
if [[ -z "$ENGINE_PYTHON" ]] && command -v python3 >/dev/null 2>&1; then ENGINE_PYTHON="$(command -v python3)"; fi
if [[ -z "$ENGINE_PYTHON" ]] && command -v python >/dev/null 2>&1; then ENGINE_PYTHON="$(command -v python)"; fi
if [[ -z "$ENGINE_PYTHON" ]]; then
  echo "Cortex Python was not found. Set CORTEX_PYTHON or re-run repository bootstrap." >&2
  exit 2
fi
if ! "$ENGINE_PYTHON" -c 'import cortex' >/dev/null 2>&1; then
  echo "The selected Python cannot import Cortex. Set CORTEX_PYTHON or re-run repository bootstrap." >&2
  exit 2
fi

REPO_NAME="$("$ENGINE_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["repository_name"])' "$CONFIG_PATH")"

case "$COMMAND" in
  activate)
    TASK=""
    BUDGET="800"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --budget) BUDGET="${2:-800}"; shift 2 ;;
        *) echo "Unknown activate argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TASK" ]] || { echo "--task is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" activate --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --json
    ;;
  bootstrap)
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" bootstrap "$REPO_ROOT" --name "$REPO_NAME" --json
    ;;
  query)
    QUERY=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --query) QUERY="${2:-}"; shift 2 ;;
        *) echo "Unknown query argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$QUERY" ]] || { echo "--query is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" query "$QUERY" --repo "$REPO_NAME" --json
    ;;
  remember)
    KIND="discovery"
    TEXT=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --kind) KIND="${2:-discovery}"; shift 2 ;;
        --text) TEXT="${2:-}"; shift 2 ;;
        *) echo "Unknown remember argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TEXT" ]] || { echo "--text is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" remember --repo "$REPO_NAME" --kind "$KIND" --text "$TEXT" --json
    ;;
  ritual)
    TASK=""
    KIND="discovery"
    TEXT=""
    BUDGET="800"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --kind) KIND="${2:-discovery}"; shift 2 ;;
        --text) TEXT="${2:-}"; shift 2 ;;
        --budget) BUDGET="${2:-800}"; shift 2 ;;
        *) echo "Unknown ritual argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TASK" ]] || { echo "--task is required" >&2; exit 2; }
    if [[ -n "$TEXT" ]]; then
      exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" ritual --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --remember-kind "$KIND" --remember-text "$TEXT" --json
    else
      exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" ritual --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --json
    fi
    ;;
  interlink)
    TASK=""
    LEARN=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --learn) LEARN="--learn"; shift ;;
        *) echo "Unknown interlink argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TASK" ]] || { echo "--task is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" interlink --repo "$REPO_NAME" --task "$TASK" ${LEARN:+$LEARN} --json
    ;;
  thalamus)
    TASK=""
    BUDGET="800"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --budget) BUDGET="${2:-800}"; shift 2 ;;
        *) echo "Unknown thalamus argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TASK" ]] || { echo "--task is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" thalamus --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --json
    ;;
  identity)
    REPO_ARG=()
    PATH_ARG=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --repo) REPO_ARG=(--repo "${2:-}"); shift 2 ;;
        --path) PATH_ARG=(--path "${2:-}"); shift 2 ;;
        *) echo "Unknown identity argument: $1" >&2; exit 2 ;;
      esac
    done
    if [[ ${#REPO_ARG[@]} -eq 0 ]]; then REPO_ARG=(--repo "$REPO_NAME"); fi
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" identity "${REPO_ARG[@]}" "${PATH_ARG[@]}" --json
    ;;
  distill)
    EXTRA=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --no-seal) EXTRA+=(--no-seal); shift ;;
        --doctrine-only) EXTRA+=(--doctrine-only); shift ;;
        *) echo "Unknown distill argument: $1" >&2; exit 2 ;;
      esac
    done
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" distill --repo "$REPO_NAME" "${EXTRA[@]}" --json
    ;;
  kernels)
    EXTRA=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --annotate) EXTRA+=(--annotate); shift ;;
        *) echo "Unknown kernels argument: $1" >&2; exit 2 ;;
      esac
    done
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" kernels --repo "$REPO_NAME" "${EXTRA[@]}" --json
    ;;
  prune)
    EXTRA=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --dry-run) EXTRA+=(--dry-run); shift ;;
        --decay) EXTRA+=(--decay); shift ;;
        *) echo "Unknown prune argument: $1" >&2; exit 2 ;;
      esac
    done
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" prune --repo "$REPO_NAME" "${EXTRA[@]}" --json
    ;;
  organism)
    TASK=""
    BUDGET="800"
    PROFILE="agent"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --budget) BUDGET="${2:-800}"; shift 2 ;;
        --profile) PROFILE="${2:-agent}"; shift 2 ;;
        *) echo "Unknown organism argument: $1" >&2; exit 2 ;;
      esac
    done
    [[ -n "$TASK" ]] || { echo "--task is required" >&2; exit 2; }
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" organism --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --profile "$PROFILE" --json
    ;;
  breathe)
    TASK=""
    BUDGET="800"
    PROFILE="agent"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --task) TASK="${2:-}"; shift 2 ;;
        --budget) BUDGET="${2:-800}"; shift 2 ;;
        --profile) PROFILE="${2:-agent}"; shift 2 ;;
        *) echo "Unknown breathe argument: $1" >&2; exit 2 ;;
      esac
    done
    if [[ -n "$TASK" ]]; then
      exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" breathe --repo "$REPO_NAME" --task "$TASK" --budget "$BUDGET" --profile "$PROFILE" --json
    else
      exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" breathe --repo "$REPO_NAME" --budget "$BUDGET" --profile "$PROFILE" --json
    fi
    ;;
  causal)
    ACTION="${1:-status}"
    if [[ $# -gt 0 ]]; then shift; fi
    case "$ACTION" in
      status|report|evaluate)
        exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" causal "$ACTION" --repo "$REPO_NAME" --json
        ;;
      probe)
        TASK=""
        SLOT="before"
        K="8"
        while [[ $# -gt 0 ]]; do
          case "$1" in
            --task) TASK="${2:-}"; shift 2 ;;
            --query) TASK="${2:-}"; shift 2 ;;
            --slot) SLOT="${2:-before}"; shift 2 ;;
            --k) K="${2:-8}"; shift 2 ;;
            *) echo "Unknown causal probe argument: $1" >&2; exit 2 ;;
          esac
        done
        [[ -n "$TASK" ]] || { echo "--task is required for causal probe" >&2; exit 2; }
        exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" causal probe --repo "$REPO_NAME" --task "$TASK" --slot "$SLOT" --k "$K" --json
        ;;
      *) echo "Unknown causal action: $ACTION (status|report|evaluate|probe)" >&2; exit 2 ;;
    esac
    ;;
  consolidate|verify|status|graph|telemetry|environment|meta-language|neural-replay|doctor|interconnect|immune|metrics)
    exec "$ENGINE_PYTHON" -m cortex --home "$CORTEX_HOME_PATH" "$COMMAND" --repo "$REPO_NAME" --json
    ;;
  *) echo "Unknown command: $COMMAND" >&2; exit 2 ;;
esac
'''

REPO_CORTEX_README = """# INTERNAL CORTEX - Repository Integration

This directory is the explicitly labeled, repository-local integration surface for the installed Cortex engine. It is not a second source of truth and it is not the host repository's application code.

- `config.json` identifies this surface as `internal_repository_cortex`, identifies the host repository, records the Cortex Python interpreter/module location, and controls assimilation.
- `bootstrap_certificate.json` records the latest verified inventory and coverage state.
- `bin/cortex.ps1` and `bin/cortex.sh` are stable entry points for Codex and other agents.
- `runtime/` contains generated context and learned-environment packets and is intentionally ignored by Git.

## Stable CORTEX_HOME (production)

Cross-process identity and memory continuity require a durable home, not a temp directory.

- Prefer a fixed path such as `~/.cortex` (or another long-lived directory you control).
- Avoid binding `cortex_home` in `config.json` to OS temp paths (`%TEMP%`, `/tmp`, `TemporaryDirectory`, CI scratch).
- If `config.json` points at a temp home, re-bootstrap with an explicit stable home:

```powershell
$env:CORTEX_HOME = Join-Path $env:USERPROFILE ".cortex"
python -m cortex bootstrap . --name YourRepo --json
```

```bash
export CORTEX_HOME="$HOME/.cortex"
python -m cortex bootstrap . --name YourRepo --json
```

Then verify with the wrapper:

```powershell
.\\bin\\cortex.ps1 identity
```

```bash
./bin/cortex.sh identity
```

Cortex's global database normally lives at `~/.cortex/cortex.db`. The neural interlink shares that database and never creates a competing memory authority. Repository source remains authoritative.

### Operator commands on the wrapper

Beyond activate/query/remember, the installed wrappers also expose: `identity`, `distill`, `kernels`, `interconnect`, `immune`, `metrics`, `prune`, `organism`, `breathe`, and `causal` (including `causal probe` for matched recall pairs).
"""

GITIGNORE = """runtime/
*.tmp
*.lock
"""

EXTERNAL_ATTACHMENT_README = """# EXTERNAL CORTEX ATTACHMENT

This attachment keeps Cortex configuration, certificates, and runtime packets
outside a sealed host repository. The host source and governance files are not
modified. Use the global Cortex CLI with the same `--home` value.
"""


def install_external_attachment(
    home: Path, root: Path, config: RepoConfig
) -> dict[str, Any]:
    from .config import external_repo_config_path

    config_path = external_repo_config_path(root, home)
    attachment_root = config_path.parent
    config.integration_mode = "external"
    config.integration_role = "external_repository_attachment"
    config.integration_label = "EXTERNAL CORTEX ATTACHMENT"
    config.agent_protocol_mode = "preserve"
    config.attachment_root = str(attachment_root)
    save_repo_config(root, config)
    (attachment_root / "runtime").mkdir(parents=True, exist_ok=True)
    (attachment_root / "README.md").write_text(
        EXTERNAL_ATTACHMENT_README, encoding="utf-8"
    )
    return {
        "config": str(config_path),
        "attachment_root": str(attachment_root),
        "host_files_modified": False,
        "agents_modified": False,
        "integration_mode": config.integration_mode,
        "integration_role": config.integration_role,
        "integration_label": config.integration_label,
        "agent_protocol_mode": config.agent_protocol_mode,
        "cortex_home": str(home),
    }


def install_integration(root: Path, config: RepoConfig) -> dict[str, Any]:
    cortex_dir = root / ".cortex"
    bin_dir = cortex_dir / "bin"
    runtime_dir = cortex_dir / "runtime"
    bin_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    engine_python = config.engine_python or str(Path(sys.executable))
    engine_module_root = config.engine_module_root or str(Path(__file__).resolve().parent.parent)
    cortex_home = config.cortex_home or str((Path.home() / ".cortex").resolve())
    config.engine_python = engine_python
    config.engine_module_root = engine_module_root
    config.cortex_home = cortex_home
    save_repo_config(root, config)

    (cortex_dir / "README.md").write_text(REPO_CORTEX_README, encoding="utf-8")
    (cortex_dir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    # A newline keeps strict host hashers that reject zero-byte inputs from
    # failing while this directory remains semantically empty.
    (runtime_dir / ".gitkeep").write_text("\n", encoding="utf-8")

    ps_path = bin_dir / "cortex.ps1"
    sh_path = bin_dir / "cortex.sh"
    ps_engine = engine_python.replace("'", "''")
    ps_module_root = engine_module_root.replace("'", "''")
    ps_cortex_home = cortex_home.replace("'", "''")
    ps_content = POWERSHELL_WRAPPER.replace("__CORTEX_ENGINE_PYTHON_PS__", ps_engine)
    ps_content = ps_content.replace("__CORTEX_ENGINE_MODULE_ROOT_PS__", ps_module_root)
    ps_content = ps_content.replace("__CORTEX_HOME_PS__", ps_cortex_home)
    sh_content = BASH_WRAPPER.replace(
        "__CORTEX_ENGINE_PYTHON_SH__", shlex.quote(engine_python)
    )
    sh_content = sh_content.replace(
        "__CORTEX_ENGINE_MODULE_ROOT_SH__", shlex.quote(engine_module_root)
    )
    sh_content = sh_content.replace("__CORTEX_HOME_SH__", shlex.quote(cortex_home))
    ps_path.write_text(ps_content, encoding="utf-8")
    sh_path.write_text(sh_content, encoding="utf-8", newline="\n")
    sh_path.chmod(sh_path.stat().st_mode | stat.S_IEXEC)

    agents_path = root / "AGENTS.md"
    agents_modified = False
    if config.agent_protocol_mode == "managed":
        existing = (
            agents_path.read_text(encoding="utf-8", errors="replace")
            if agents_path.exists()
            else "# AGENTS.md\n\n"
        )
        if MANAGED_BEGIN in existing and MANAGED_END in existing:
            before, rest = existing.split(MANAGED_BEGIN, 1)
            _, after = rest.split(MANAGED_END, 1)
            updated = before.rstrip() + "\n\n" + AGENT_BLOCK + after
        else:
            updated = existing.rstrip() + "\n\n" + AGENT_BLOCK + "\n"
        agents_path.write_text(updated, encoding="utf-8")
        agents_modified = True

    return {
        "config": str(cortex_dir / "config.json"),
        "agents": str(agents_path),
        "powershell_wrapper": str(ps_path),
        "bash_wrapper": str(sh_path),
        "runtime_directory": str(runtime_dir),
        "engine_python": engine_python,
        "engine_module_root": engine_module_root,
        "cortex_home": cortex_home,
        "integration_role": config.integration_role,
        "integration_label": config.integration_label,
        "agent_protocol_mode": config.agent_protocol_mode,
        "agents_modified": agents_modified,
    }


def integration_status(root: Path, config: RepoConfig | None = None) -> dict[str, Any]:
    if config is not None and config.integration_mode == "external":
        attachment = Path(config.attachment_root)
        required = [
            attachment / "config.json",
            attachment / "README.md",
            attachment / "runtime",
        ]
        return {
            "required_files": {str(path): path.exists() for path in required},
            "agents_managed_block": False,
            "integration_mode": "external",
            "integration_role": config.integration_role,
            "integration_label": config.integration_label,
            "labeled_internal": False,
            "agent_protocol_mode": "preserve",
            "host_files_modified": False,
            "complete": all(path.exists() for path in required),
        }
    required = [
        root / ".cortex" / "config.json",
        root / ".cortex" / "README.md",
        root / ".cortex" / "bin" / "cortex.ps1",
        root / ".cortex" / "bin" / "cortex.sh",
        root / "AGENTS.md",
    ]
    agents_text = (
        (root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
        if (root / "AGENTS.md").exists()
        else ""
    )
    managed = MANAGED_BEGIN in agents_text and MANAGED_END in agents_text
    config_path = root / ".cortex" / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    labeled_internal = (
        config.get("integration_role") == "internal_repository_cortex"
        and config.get("integration_label") == "INTERNAL CORTEX"
    )
    protocol_mode = config.get("agent_protocol_mode", "managed")
    protocol_ready = managed if protocol_mode == "managed" else protocol_mode == "preserve"
    return {
        "required_files": {str(path.relative_to(root)): path.exists() for path in required},
        "agents_managed_block": managed,
        "integration_role": config.get("integration_role"),
        "integration_label": config.get("integration_label"),
        "labeled_internal": labeled_internal,
        "agent_protocol_mode": protocol_mode,
        "complete": all(path.exists() for path in required[:-1]) and protocol_ready and labeled_internal,
    }
