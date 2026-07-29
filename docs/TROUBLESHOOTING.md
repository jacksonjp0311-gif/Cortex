# Troubleshooting

## PowerShell script execution is blocked

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
```

Then run the script again in the same PowerShell window.

## Python cannot import Cortex

Run the all-one installer or reinstall from the Cortex root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

```bash
./.venv/bin/python -m pip install -e .
```

## Repository wrapper points to an old engine location

Re-run bootstrap from the current engine. The wrapper bindings in `.cortex/config.json` will be refreshed.

## Repository wrapper opens the wrong Cortex database

Current wrappers are bound to the Cortex home and Python engine recorded during bootstrap. Re-run bootstrap when intentionally moving the database or engine. Unrelated inherited `CORTEX_HOME` or `CORTEX_PYTHON` values will not override an already bound repository wrapper.

## Identity continuity vs temporary CORTEX_HOME

`python -m cortex identity --repo MyProject --json` reports whether multiple names share a path and whether the bound home looks temporary.

- Same filesystem path + same `repository_id` ⇒ one body (name aliases are fine).
- Same path + different `repository_id` (e.g. CI name vs teach name in **different** homes) ⇒ separate durable namespaces; do not merge without an explicit check.
- `continuity.temporary_home: true` means `.cortex/config.json` points at OS/CI temp storage. Memory is correct **inside** that home but will not survive across sessions.

Production pattern:

```powershell
$env:CORTEX_HOME = Join-Path $env:USERPROFILE ".cortex"
python -m cortex bootstrap . --name MyProject --json
.\.cortex\bin\cortex.ps1 identity
```

```bash
export CORTEX_HOME="$HOME/.cortex"
python -m cortex bootstrap . --name MyProject --json
./.cortex/bin/cortex.sh identity
```

## Wrapper rejects `identity` (or other lean-era commands)

Re-run bootstrap so `.cortex/bin/cortex.ps1` / `cortex.sh` are regenerated. Current wrappers expose `identity`, `distill`, `kernels`, `interconnect`, `immune`, `metrics`, `prune`, `organism`, `breathe`, and `causal` (including `causal probe`).

## Health shows drift right after `mirror` or `contact`

Mirror and contact use an isolated Cortex home and now restore host `.cortex/config.json` after the run. Mid-run health queries can still show transient `manifest_drift` / read-only because stress bootstraps a parallel name into a temp DB.

Treat the end of mirror as a re-verification boundary:

```powershell
python -m cortex activate --repo CortexTeach --task "post-mirror re-verify" --json
python -m cortex health --repo CortexTeach --json
```

Mirror reports `host_binding.restored` and `phases.generic` vs `phases.aria_wake` so dormant-mode notes are not read as Aria failures.

## Causal evaluate returns `missing_recall_pair`

That is intentional restraint: resonance and structural health are not proof of retrieval improvement. Capture a matched pair:

```bash
python -m cortex causal probe --repo MyProject --task "ARIA implementation proof" --slot before --json
# ... apply change or re-index ...
python -m cortex causal probe --repo MyProject --task "ARIA implementation proof" --slot after --json
python -m cortex causal evaluate --repo MyProject --json
```

Or pass explicit scores: `--recall-before 0.4 --recall-after 0.7`.

## Activation is read-only

Inspect:

```bash
python -m cortex verify --repo MyProject --json
python -m cortex doctor --repo MyProject --json
```

Common causes are manifest drift with refresh disabled, a missing or degraded certificate, database integrity failure, incomplete integration files, or a broken neural ledger.

## Neural graph has zero synapses

Small repositories can verify with nodes and no relationships. For a larger repository, inspect the structural graph:

```bash
python -m cortex graph --repo MyProject --json
```

Re-run bootstrap with `--force` if parsers or source relationships changed.

## Embedded Cortex folder appears in host memory

Re-run bootstrap from the embedded engine. Current bootstrap adds the engine-relative path to the host repository exclusion list. Confirm the path in `.cortex/config.json` under `exclude`.

## FTS5 unavailable

Use a normal CPython distribution with SQLite FTS5. `doctor` reports availability.

## PowerShell 5.1 compatibility

The included scripts avoid PowerShell 7-only syntax. Use the provided launchers rather than copying Bash command forms into Windows PowerShell.
