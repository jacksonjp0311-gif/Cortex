# Cortex Hermetic Attach — Quick Start

**Zero friction. External home. Host sovereign. Ritual interlock.**

Attach Cortex to *any* repository without writing into the host tree and without cloning the Cortex source as your project.

Repository: https://github.com/jacksonjp0311-gif/Cortex

> **Pick one method only.** Do not run uvx *and* python *and* the script.  
> Do not `cd` to a fake path like `C:\path\to\your\project` — use your real folder (e.g. `PulseMesh`).  
> Re-running attach is safe (idempotent) but unnecessary if the first run finished with `Returned to ROOT.`

---

## Ranked install mechanisms

| Rank | Mechanism | When |
|------|-----------|------|
| **1** | **uvx** (recommended) | You have [uv](https://github.com/astral-sh/uv) |
| **2** | **pipx** | Python tooling, no global env pollution |
| **3** | **npx** thin wrapper | Node present; still runs Python backend |
| **4** | **One-liner scripts** | curl/iwr bootstrap of `scripts/attach_one.*` |
| **5** | **pip install -e / git** | Dev, offline, air-gapped (after wheel copy) |

All paths use **external-home** by default: body at `~/.cortex` (or `CORTEX_HOME`), **no** `.cortex/` pollution in the host unless you deliberately use internal bootstrap.

---

## Primary (uvx)

```bash
# From inside any project directory
uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .
```

```powershell
uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .
```

---

## pipx

```bash
pipx run --spec "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .
```

---

## npx (secondary)

```bash
npx --yes github:jacksonjp0311-gif/Cortex/js/cortex-attach
# or after clone:
npx --yes ./js/cortex-attach .
```

Requires Python 3.10+ available as `python` / `python3`.

---

## One-liners

**Bash**

```bash
# From inside YOUR project (real path — not /path/to/your/app)
curl -fsSL https://raw.githubusercontent.com/jacksonjp0311-gif/Cortex/main/scripts/attach_one.sh | bash -s -- .
# Stop at "Returned to ROOT." — do not also run uvx/python attach
```

**PowerShell**

```powershell
# Reliable: download then run in THIS shell (dot = current project)
irm https://raw.githubusercontent.com/jacksonjp0311-gif/Cortex/main/scripts/attach_one.ps1 -OutFile $env:TEMP\cortex-attach.ps1
& $env:TEMP\cortex-attach.ps1 .

# Avoid nested:  powershell -File $env:TEMP\cortex-attach.ps1 .
#   (can truncate the ritual mid-way and look like a hang)
# Avoid: irm ... | iex  (param binding is unreliable when piped)
```

---

## Local / editable (developers)

```bash
git clone https://github.com/jacksonjp0311-gif/Cortex.git
cd Cortex && pip install -e .
cd /path/to/your/app
cortex-attach . --name MyApp
# or
python -m cortex attach . --name MyApp
```

---

## Environment

| Variable | Meaning |
|----------|---------|
| `CORTEX_HOME` | Body directory (default `~/.cortex`) — **never** inside host |
| `CORTEX_ATTACH_RITUAL=0` | Disable Hermetic glow (CI/scripts) |
| `CORTEX_ATTACH_RITUAL=1` | Force ritual even in CI |
| `NO_COLOR=1` | No ANSI |

---

## After attach

```bash
python -m cortex --home "$HOME/.cortex" activate --repo <Name> --task "Map entrypoints" --json
python -m cortex --home "$HOME/.cortex" claim --repo <Name> --json
python -m cortex --home "$HOME/.cortex" interconnect --repo <Name> --json
```

---

## Fallback detection

1. No Python → install Python 3.10+ or uv  
2. No network → use local wheel + `pip install ./cortex_memory-*.whl` then `cortex-attach`  
3. Air-gapped → copy wheel + `CORTEX_HOME` volume  
4. CI → `CORTEX_ATTACH_RITUAL=0 cortex-attach . --json --no-ritual`

---

## Psychological note

The Hermetic display is **interface design** for liminal peak and re-integration (`Returned to ROOT.`).  
It does **not** claim consciousness, sacred authority, or host mutation rights.  
Host remains sovereign. Cortex remains the living memory organ (recommend-only).

---

## Docker isolation test

```bash
bash scripts/ci/docker_attach_ritual_test.sh
```

Runs attach against a **dummy repo only**, external home inside the container, full ritual cycle (or quiet), then wipes the container. Never mounts the real Cortex source as the host under test.
