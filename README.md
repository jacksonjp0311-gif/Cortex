<!-- TOP CTA: first thing on the README -->
<p align="center">
  <a href="https://jacksonjp0311-gif.github.io/Cortex/embed.html">
    <img
      src="https://img.shields.io/badge/EMBED_ON_DESKTOP-open_live_HUD-a855f7?style=for-the-badge&logo=github&logoColor=white&labelColor=0f172a"
      alt="Embed on Desktop — open live HUD"
      height="40"
    />
  </a>
  &nbsp;&nbsp;
  <a href="https://jacksonjp0311-gif.github.io/Cortex/">
    <img
      src="https://img.shields.io/badge/STAR_LATTICE-live_chart-0ea5e9?style=for-the-badge&logo=github&logoColor=white&labelColor=0f172a"
      alt="Star lattice — live chart"
      height="40"
    />
  </a>
</p>

<p align="center">
  <b><a href="https://jacksonjp0311-gif.github.io/Cortex/embed.html">→ Embed Cortex on Desktop (live HUD)</a></b>
  ·
  <a href="https://jacksonjp0311-gif.github.io/Cortex/">Star lattice</a>
</p>

<p align="center">
  <img src="assets/cortex-neural-brain.png" alt="Cortex neural interlink brain" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/jacksonjp0311-gif/Cortex/actions"><img src="https://img.shields.io/badge/verification-tested-22c55e?style=for-the-badge" alt="Tests verified" /></a>
  <img src="https://img.shields.io/badge/version-7.2.0-0ea5e9?style=for-the-badge" alt="v7.2.0" />
  <img src="https://img.shields.io/badge/organism-living-a855f7?style=for-the-badge" alt="Living organism" />
  <img src="https://img.shields.io/badge/routing-Thalamus-8b5cf6?style=for-the-badge" alt="Thalamus routing" />
  <img src="https://img.shields.io/badge/storage-local--first-111827?style=for-the-badge" alt="Local first" />
  <img src="https://img.shields.io/badge/authority-recommend--only-f8fafc?style=for-the-badge&labelColor=111827" alt="Recommend only" />
</p>

# Cortex Neural Interlink

**Local-first repository memory, governed continuation, and session co-process for AI coding agents.**

Cortex is a portable memory organ you attach to a repository. It assimilates the tree once, then gives agents **bounded, provenance-backed context** instead of dumping the whole codebase into the prompt — without replacing host source, tests, or authorization.

**Current release: v7.2.0** — **Hermetic Attach**: one-command external-home interlock for any repo (`cortex-attach` / uvx / pipx); solar-lunar ritual CLI; host stays sovereign. Quick start: [`docs/ATTACH_QUICKSTART.md`](docs/ATTACH_QUICKSTART.md).

**Research (agents: read first):** [`docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md`](docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md) · index [`docs/research/README.md`](docs/research/README.md) · agent guide [`docs/AGENT_CONSTITUTIONAL_MATH.md`](docs/AGENT_CONSTITUTIONAL_MATH.md) · [`llms.txt`](llms.txt) · CSG [`docs/research/CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md`](docs/research/CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md).

### Hermetic attach (easiest — any project folder)

**Needs:** Python 3.10+ (and ideally [uv](https://github.com/astral-sh/uv)).  
**Body:** `~/.cortex` (or `$env:CORTEX_HOME`). Host stays clean (external mode).

> **Run only ONE block.** Do not paste every alternative.  
> Replace the `cd` path with your real project (example below uses `PulseMesh`).  
> Do **not** run `cd C:\path\to\your\project` — that is a placeholder and will error.

**PowerShell (Windows) — pick A *or* B *or* C**

```powershell
# Go to YOUR project (example)
cd "C:\Users\jacks\OneDrive\Desktop\PulseMesh"

# --- A) Best if you have uv (single command) ---
uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .

# --- B) Plain Python only (if A fails / no uv) ---
# python -m pip install -q "git+https://github.com/jacksonjp0311-gif/Cortex@main"
# python -m cortex.attach_main .

# --- C) Script fallback (if A and B fail) ---
# irm https://raw.githubusercontent.com/jacksonjp0311-gif/Cortex/main/scripts/attach_one.ps1 -OutFile $env:TEMP\cortex-attach.ps1
# & $env:TEMP\cortex-attach.ps1 .
```

**Bash / macOS / Linux — pick A *or* B *or* C**

```bash
cd ~/Projects/YourApp   # your real path

# A) uv
uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .

# B) plain Python
# python3 -m pip install -q "git+https://github.com/jacksonjp0311-gif/Cortex@main"
# python3 -m cortex.attach_main .

# C) script
# curl -fsSL https://raw.githubusercontent.com/jacksonjp0311-gif/Cortex/main/scripts/attach_one.sh | bash -s -- .
```

Already attached? One run is enough. Re-running is safe (idempotent) but **don’t** chain A+B+C.

Full guide: [`docs/ATTACH_QUICKSTART.md`](docs/ATTACH_QUICKSTART.md).

```bash
# After attach — daily agent loop (body under ~/.cortex)
python -m cortex --home "$HOME/.cortex" activate --repo YourProject --task "Map auth" --json
python -m cortex --home "$HOME/.cortex" claim --repo YourProject --json

# Dev clone of this engine (optional)
pip install -e .
python -m cortex bootstrap . --name MyProject --external --json

# Measure / mesh (durable body example: CortexTeach)
python -m cortex eval-coupling --repo CortexTeach --suite holdout --json
python -m cortex host-mesh --primary CortexTeach --query "governor policy" --json
python -m cortex self-org --repo CortexTeach --json
python -m cortex coherence --repo CortexTeach --json
```

**Trust order (unchanged):** host source & tests > runtime evidence > verified model > consolidated memory > learned associations > inference. Learned relevance never becomes host authority.

**Topology law:** `G_host` immutable · `G_evidence` via re-index · `G_learned` under Governor · `G_federated` query-only — see [`docs/intelligence/TOPOLOGY_LAW.md`](docs/intelligence/TOPOLOGY_LAW.md).

---

## Fusion co-process — regenerate geometry while connected to AI

**Goal:** While an AI coding agent works, Cortex acts as a **live co-process**: each generation token (or step) **regenerates memory geometry** — uncertainty \(U\), filter state \(\Lambda_g\), spectral ranking, optional invented synapses — and returns a compact **injection** the model can condition on. Shared **mind_hash** / self-model = one session state vector, not a second brain.

| Aspiration | Engineering |
|------------|-------------|
| Live co-processor fused to the model | `fuse-proxy` sits on `OPENAI_BASE_URL`; every streamed token → `fuse_tick` |
| Geometry regenerates every token | Spectral pulse + diffusion + ranker-primary on each tick |
| Spectral mesh drives attention | Primary ranking path on fuse ticks |
| Topology invents structure | Gated co-activation synapses (memory graph only) |
| Organism self-model | Telemetry `self_model` / sense / mind_hash — **not** consciousness |
| Shared mind-state | Agent + Cortex co-process one SQLite body — **recommend-only** for host edits |

### Auto-tick (closes the last gap)

Point any OpenAI-compatible client at Cortex; **no manual tick loop**:

```bash
# Terminal A — mock demo (no API key)
python -m cortex fuse-proxy --repo MyProject --mock --port 8787 --task "session work"

# Terminal B — client
# OPENAI_BASE_URL=http://127.0.0.1:8787/v1
curl -N http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"mock\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"

# Live upstream (example)
python -m cortex fuse-proxy --repo MyProject --port 8787 \
  --upstream https://api.openai.com/v1 --task "implement auth"
# then: OPENAI_BASE_URL=http://127.0.0.1:8787/v1  OPENAI_API_KEY=...
```

Manual co-process (MCP/CLI) still works:

```bash
python -m cortex fuse open --repo MyProject --task "..." --json
python -m cortex fuse tick --repo MyProject --token "partial..." --json
python -m cortex fuse state --repo MyProject --json
python -m cortex fuse close --repo MyProject --json
```

**Honest boundary:** the proxy fuses **generation I/O** to Cortex geometry. It does **not** merge model weights, invent host source files, or claim sentience. Details: [`docs/intelligence/PHASE_V6.14_FUSION.md`](docs/intelligence/PHASE_V6.14_FUSION.md).

### System coherence — emergent coupling indicators

One field over **blood · geometry · spectral · Λ_g · ranker · fusion · hygiene**.  
Not consciousness: multi-seam **co-activation** of independent telemetry.

| Indicator | Meaning when active |
|-----------|---------------------|
| `blood_geometry` | Certainty co-moves with spectral mesh |
| `geometry_learning` | Graph mass co-moves with ranker warmth |
| `ops_geometry` | Fusion/ops co-moves with \(\Lambda_g\) |
| `gates_aligned` | Governor open + prune hygiene |
| `blood_learning` | Certainty + ranker |
| `spectral_ops` | Spectral live under fuse traffic |

```bash
python -m cortex coherence --repo MyProject --json
# score ≥ 0.62 → above_threshold
# emergent_coupling → ≥3 active couples AND above threshold
# component_panel: active | latent | dark per channel
# Optional: CORTEX_FUSE_AUTO=1  # soft-opens fusion on activate
```

Activate, continuum, hygiene, fuse ticks, and organism mesh all carry these indicators.

### Emergence log (agents MUST read each turn)

Durable progress log of threshold crosses, couple activations, continuum seals, and notes.  
**Injected at the top of every activate/context `instructions`** and as protocol step `read_emergence_log`.

```bash
python -m cortex emergence-log --repo MyProject --json
python -m cortex emergence-log --repo MyProject --note "Shipped fuse-proxy wiring" --json
```

| Kind | Meaning |
|------|---------|
| `baseline` | First coherence observation |
| `threshold_crossed` / `threshold_lost` | Score vs 0.62 |
| `emergent_on` / `emergent_off` | Multi-couple co-activation |
| `couple_activated` | Named couple lit |
| `continuum_seal` | Multi-lane pass finished |
| `agent_note` | Human/agent milestone |

Use directives in the log to **enhance progress** (spectral-primary, fuse, evolve) — never as host authority or consciousness.

### Measure gate (eval-coupling)

Frozen path-substring corpus under three ablations: **baseline** (spectral enrich + ranker primary), **no_spectral**, **no_ranker**. Winner and gate flags direct evolution — not universal answer quality.

```bash
python -m cortex eval-coupling --repo CortexTeach --suite full --json
# suites: easy | hard | full — metrics: recall@k + MRR
# gate.spectral_helps / gate.ranker_helps / winner / divergence_cases
# logs under CORTEX_HOME/logs/eval-coupling-*.json + emergence measure_gate
```

**Teach the body:** ARIA memory packets under `examples/memory-packets/` distill interconnect
intelligence into durable cards via `cortex teach --seed` — so interconnect recalls doctrine,
not chat lore. Cortex is SQLite-backed, dependency-free in core install, and **recommend-only**.

---

## What agents get

| Surface | Purpose |
|---|---|
| **Immune ⚠** | `cortex immune` — read `block` + `immune_action` before host work |
| **Connect ⧉** | Each connect gathers metrics; metric graph grows; distill into body |
| **Packet** | Evidence + `instructions` + `agent_protocol` + `control_error` |
| **Organism ⊛** | Session co-process: shared living state (not consciousness) |
| **Ritual ⟳** | `activate → remember → consolidate` on one substrate |
| **Governor** | `normal` / `constrained` / `read_only` with forced hard stops |
| **Mirror / contact / ⟡** | Self-audit: glow when invariants hold |
| **ARIA** | Native semantic language — dormant by default, never auto-executed |

Read the packet in order: **control_error → instructions → agent_protocol → evidence**.  
See [`docs/TRANSCEND.md`](docs/TRANSCEND.md) and [`docs/ORGANISM.md`](docs/ORGANISM.md).

---

## Living organism interlink (v3.5) ⊛ ∽

For one task session, agent and Cortex share a **single living state vector** that
**keeps beating** as the agent works — not only at first activate.

```text
systole (activate) → diastole (remember) → breathe ∽ (rebind) → sealed (consolidate)
```

```text
identity ── nervous (thalamus + neural + ARIA)
    │
immune (governor + control_error) ── metabolism (surprise + efficiency)
    │
memory (evidence + events) ── intention (task + protocol)
    │
conscience (geometry) ── pulse / pulse_chain
```

| Role | Who | Lifetime |
|---|---|---|
| Durable body | Cortex (index, graph, ledger) | Across sessions |
| Temporary working cortex | The agent | This session only |
| Authority | Host rules + human | Always |

```bash
cortex organism --repo MyProject --task "Continue the investigation" --json
cortex breathe --repo MyProject --json   # mid-session rebind, no full re-index
# every remember continues the pulse; consolidate seals it
```

Not a second mind. Separable bond. Host remains sovereign.  
Docs: [`docs/ORGANISM.md`](docs/ORGANISM.md).

---

## Session ritual

```text
activate → work under host/human authority → remember → consolidate
```

```bash
cortex ritual --repo MyProject --task "Ship the fix" \
  --remember-kind discovery --remember-text "Root cause was nil config" --json
```

Remember is idempotent (same kind+text de-dupes). Consolidate returns explicit
statuses (`created`, `nothing_to_consolidate`, `duplicate_skip`,
`blocked_by_governor`).

---

## Packet profiles & control error

```bash
cortex activate --repo MyProject --task "..." --profile agent --json   # default
cortex activate --repo MyProject --task "..." --profile debug --json   # full telemetry
cortex activate --repo MyProject --task "..." --profile minimal --json # evidence + stops
```

Every packet includes **`control_error`** (⚠) — severity, `must_reverify`,
`work_allowed`. Read it first. Governor `read_only` prefixes hard STOP
instructions; ritual will not consolidate as success when re-verify is required
unless `--force`.

---

## Covenant geometry

Five interlocks must co-agree:

| Axis | Law |
|---|---|
| **Authority** | Never self-expand mutation rights |
| **Evidence** | Source/tests outrank learned memory |
| **Activation** | Known ≠ active ≠ searchable |
| **Language** | ARIA never auto-executes |
| **Economics** | Deferred cost stays visible |

Docs: [`docs/COVENANT.md`](docs/COVENANT.md) · [`docs/BRIGHT_POINT.md`](docs/BRIGHT_POINT.md) · [`docs/STEADY_STATE.md`](docs/STEADY_STATE.md).

---

## Self-audit (conscience loop)

```bash
cortex transcend-check --json   # ⟡ protocol + red modes + ritual + glow
cortex mirror --json            # coherence under stress
cortex contact --json           # mirror + fluency + synthetic foreign matrix
cortex teach                    # ☰ operator teaching surface
```

`glow: true` means break_count is zero on declared gates — not AGI, not
universal production proof. See [`docs/MIRROR.md`](docs/MIRROR.md).

---

## Progress glyphs (capability-free)

ARIA labels for operator speed — **no opcode, no auto-run, no authority**:

```text
⊛  organism pulse          packet.organism / cortex organism
⧉  connect pass            cortex metrics / packet.connect_pass
∽  organism breathe        cortex breathe (mid-session rebind)
⟡  transcend check         cortex transcend-check
▣  packet profile          --profile agent|debug|minimal
⚠  control error           packet.control_error
⌖  retrieval gate          cortex evaluate --mode retrieval
⟳  ritual idempotent       cortex ritual
Δ  incremental surprise    efficiency.surprise
☰  teach surface           cortex teach
⋈  context weave           constitutional balance
≋  constitutional potential
⌁  reversibility burden
↧  authority descent
↶  verified recovery
```

---

## Flow

```text
FIRST RUN — VERIFIED ASSIMILATION
repository
  -> inventory and classification
  -> environment learning
  -> content indexing and embeddings
  -> symbol and relationship extraction
  -> Git telemetry
  -> sparse neural interlink compilation
  -> retrieval probes and verification
  -> bootstrap certificate

LATER RUNS — SELECTIVE RECALL + ORGANISM BOND
current task
  -> manifest drift / surprise (Δ)
  -> incremental refresh when required
  -> Thalamus route + inhibition
  -> lexical + semantic retrieval
  -> sparse neural activation
  -> Governor + control_error (⚠)
  -> organism pulse (⊛)
  -> bounded packet (profile ▣)
  -> agent work under host authority
  -> remember → consolidate (ritual ⟳)
```

---

## GCMT (governed continuation)

Cortex implements Governed Continuation Memory Theory: memory as regulated
transformation with recoverable origin. Continuation packets, promotion gates,
rollback, federation, and constitutional supervision stay **recommend-only**.

```bash
cortex continuation --repo MyProject --task "Continue the release investigation" --json
cortex constitutional --repo MyProject --task "Balance anchored and adjacent context" --json
cortex federated-query "Where is authentication owned?" --repos Web API Shared --json
cortex lifecycle --repo MyProject --json
cortex dashboard --repo MyProject --json
cortex-mcp
```

See [`docs/GCMT.md`](docs/GCMT.md).

---

## Native ARIA semantic language

Cortex is implemented and executed in **Python**. It ships a self-contained
`INTERNAL ARIA META-LANGUAGE` snapshot (squashed subtree, not a submodule).

- Region: `internal_aria_substrate` — known always, **dormant by default**
- Bootstrap: anchors index immediately; bulk files stay `substrate_deferred` until wake
- Fluency cues are typed; false wakes are regression-gated
- Plans are **never** auto-executed or treated as mutation authority

```bash
cortex meta-language --repo MyProject --json
cortex meta-language --repo MyProject --task "Prepare a semantic replay" --json
```

See [`docs/ARIA_META_LANGUAGE.md`](docs/ARIA_META_LANGUAGE.md).

---

## Thalamus routing

Every normal activation is planned by a local deterministic Thalamus layer:
intent classification, memory-lane budgets, and auditable inhibition. Engineering
analogy only — not biology, not authority.

```bash
cortex thalamus --repo MyProject --task "Where is rate limiting?" --json
cortex thalamus-feedback --repo MyProject --memory-id <id> --outcome helpful --json
```

Benchmarks: `python benchmarks/thalamus_before_after.py`  
Self-host engine check: `python -m cortex self-test --json`  
Cross-domain notes: [`docs/CROSS_DOMAIN_ANALYSIS.md`](docs/CROSS_DOMAIN_ANALYSIS.md).

## What changed in the neural edition

The previous standalone `neuron` repository has been integrated as an internal Cortex organ rather than kept as a competing system.

Cortex remains responsible for:

- repository identity and assimilation;
- semantic, structural, temporal, and episodic memory;
- provenance and retrieval;
- working sessions and Discovery Card consolidation;
- trust reduction through the Governor;
- NexusGate packet production;
- the authority boundary.

The internal neural interlink adds:

- file-level neural nodes compiled from indexed repository surfaces;
- bounded synapses compiled from imports, resolved references, tests, documentation, calls, and co-change history;
- deterministic sparse activation seeded by hybrid retrieval;
- bounded support-path expansion;
- optional bounded Hebbian association strengthening;
- a hash-chained neural event ledger;
- replayable activation packets and state hashes.

There is one database, one episodic path, one consolidation path, and one authority boundary. The neural layer does not maintain a second memory store.

## Why this matters

A coding agent usually faces two inefficient choices:

1. load too much repository context and lose reasoning quality to token pressure; or
2. load too little and repeatedly rediscover architecture, commands, history, and prior decisions.

Cortex separates repository availability from prompt loading:

- the supported repository is assimilated once;
- every chunk retains path, line range, content hash, type, and metadata;
- unsupported, unreadable, binary, oversized, and unresolved surfaces remain visible;
- the environment profile records likely commands, ecosystems, frameworks, and entrypoints;
- structural and temporal relationships become reusable associations;
- only a sparse, task-relevant subset is activated and loaded;
- the AI receives evidence instead of an ungrounded recollection.

## Biological efficiency model

The terminology is an engineering analogy. Cortex does not claim biological fidelity, consciousness, or AGI.

| Component | Engineering role |
|---|---|
| Hippocampus | Active task focus and append-only episodic events |
| Durable cortex | Semantic, structural, temporal, and consolidated memory |
| Neural nodes | Indexed repository files and evidence surfaces |
| Synapses | Bounded structural and temporal associations |
| Sparse activation | Task-triggered selection and limited propagation |
| Plasticity | Bounded strengthening of repeatedly co-activated associations |
| Bridge | Deterministic consolidation into Discovery Cards |
| Governor | Negative feedback that narrows or blocks trust when memory drifts |
| Homeostasis | Manifest, database, integration, coverage, ledger, and retrieval verification |

The efficiency objective is not to simulate every neuron. It is to avoid scanning and loading every stored surface for every task.

## Single-substrate architecture

```text
AI agent (temporary working cortex)
            |
            v
     organism pulse ⊛  +  Governor / control_error ⚠
            |
            +--> Thalamus route + inhibition
            +--> hybrid retrieval + sparse neural interlink
            +--> ARIA region (dormant | purpose-active)
            +--> agent_protocol + profiles ▣
            |
            v
bounded packet with provenance
            |
            v
SQLite cortex.db  (one substrate only)
  repositories, files, memories, FTS5, vectors
  symbols, edges, Git telemetry
  sessions, events, Discovery Cards
  environment profiles
  neural nodes, synapses, activations, ledger, organism pulses
```

## Requirements

- Python 3.10 or newer
- SQLite with FTS5, included in normal Python distributions
- Git is optional but recommended for temporal and co-change telemetry
- Windows PowerShell 5.1+ or PowerShell 7
- Bash on Linux, macOS, WSL, or Git Bash

No API key, network service, vector server, or model download is required for the core system.

## Fastest setup: drop in and run

### Windows PowerShell

Place this Cortex folder inside the repository you want to integrate, or keep it beside the repository and pass a path.

When the folder is nested inside a host repository, Cortex automatically excludes its own engine directory from assimilation.

From the Cortex folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\Cortex-All-One.ps1
```

With an explicit target:

```powershell
.\Cortex-All-One.ps1 `
    -RepositoryPath "C:\path\to\AgentRepository" `
    -Name "AgentRepository" `
    -Task "Map the architecture and prepare the first bounded context packet" `
    -RunTests
```

The all-one flow performs:

```text
virtual environment
-> portable engine binding with no package install required
-> database initialization
-> optional test suite
-> repository bootstrap
-> environment learning
-> neural interlink compilation
-> certificate verification
-> doctor checks
-> first activation
```

### Bash

```bash
chmod +x cortex-all-one.sh scripts/bash/*.sh
./cortex-all-one.sh
```

With an explicit target:

```bash
./cortex-all-one.sh \
  --repository-path /path/to/AgentRepository \
  --name AgentRepository \
  --task "Map the architecture and prepare the first bounded context packet" \
  --run-tests
```

## Install the engine without bootstrapping a target

### PowerShell

```powershell
.\scripts\powershell\Install-Cortex.ps1
```

### Bash

```bash
./scripts/bash/install-cortex.sh
```

Manual equivalent:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Bash: source .venv/bin/activate
python -m pip install -e .
python -m cortex init --json
python -m cortex doctor --json
```

## Bootstrap a repository

```powershell
.\scripts\powershell\Bootstrap-CortexRepo.ps1 `
    -RepositoryPath "C:\path\to\repository" `
    -Name "MyProject"
```

```bash
./scripts/bash/bootstrap-cortex-repo.sh /path/to/repository MyProject
```

Direct Python form:

```bash
python -m cortex bootstrap /path/to/repository --name MyProject --json
```

For a sealed or manifest-governed repository, keep every Cortex artifact
outside the host:

```bash
python -m cortex --home /path/to/cortex-home bootstrap /path/to/repository \
  --name MyProject --external --json
python -m cortex --home /path/to/cortex-home activate \
  --repo MyProject --task "Map the release gates" --json
```

External attachment writes configuration, certificates, and runtime packets
under `CORTEX_HOME/attachments/`. It does not create `.cortex/`, change
`AGENTS.md`, or otherwise mutate the host. Use the same `--home` on later CLI
commands. `--preserve-agents` is a narrower internal-sidecar option: it leaves
the host protocol unchanged but still installs `.cortex/`.

## What bootstrap learns

Bootstrap builds a bounded environment profile that includes:

- indexed language distribution;
- source, test, documentation, configuration, and runtime-evidence counts;
- package and build manifests;
- detected ecosystems such as Python, Node, Rust, Go, Java, containers, and CI;
- likely frameworks from local manifests;
- likely test, build, and run commands;
- likely entrypoints;
- Git availability;
- FTS5 availability;
- local runtime and launcher capabilities.

The latest profile is written to:

```text
TargetRepository/.cortex/runtime/environment_latest.json
```

For external attachments it is written under
`CORTEX_HOME/attachments/<repository-id>/runtime/`. In both modes the profile
is also stored in the shared Cortex database for later activation.

## What bootstrap installs into the target

The default internal integration identifies itself in `.cortex/config.json` as
`INTERNAL CORTEX`. External attachment installs nothing into the target.

```text
TargetRepository/
├── AGENTS.md
└── .cortex/
    ├── config.json
    ├── bootstrap_certificate.json
    ├── README.md
    ├── .gitignore
    ├── bin/
    │   ├── cortex.ps1
    │   └── cortex.sh
    └── runtime/
        ├── context_latest.json
        └── environment_latest.json
```

The global database normally remains outside the repository:

```text
~/.cortex/
├── cortex.db
├── cards/
├── certificates/
├── packets/
├── sessions/
└── logs/
```

Set `CORTEX_HOME` before installation or bootstrap to move that storage.

## Activate Cortex before agent work

From an integrated repository:

### PowerShell

```powershell
.\.cortex\bin\cortex.ps1 activate `
    -Task "Trace the authentication flow and identify the smallest safe repair surface"
```

### Bash

```bash
./.cortex/bin/cortex.sh activate \
  --task "Trace the authentication flow and identify the smallest safe repair surface"
```

Activation performs:

1. repository manifest comparison;
2. incremental refresh when drift is detected;
3. relationship and Git telemetry refresh;
4. environment-profile refresh;
5. neural interlink recompilation when needed;
6. certificate verification;
7. hippocampal session creation;
8. lexical and semantic retrieval;
9. deterministic sparse activation;
10. bounded support-path selection;
11. Governor evaluation;
12. context packet generation.

The packet is written to:

```text
TargetRepository/.cortex/runtime/context_latest.json
```

## Context selection

Cortex first performs hybrid retrieval:

```text
SQLite FTS5 lexical ranking
+ deterministic feature-hash semantic similarity
+ Reciprocal Rank Fusion
+ authoritative and telemetry quality factors
```

The highest-ranked evidence seeds the neural interlink. Activation then propagates only through bounded existing associations. Support paths may add relevant tests, callers, dependencies, documentation, or co-changing files without broad repository loading.

The packet reports:

- direct evidence;
- neural support evidence;
- fired paths;
- propagation records;
- sparse activation ratio;
- nodes considered versus total nodes;
- propagation depth and steps;
- graph and activation state hashes;
- bounded plasticity updates, when allowed;
- provenance for every evidence chunk.

## Determinism boundary

With the same:

- database state;
- repository graph;
- task text;
- retrieval ordering;
- configuration;
- plasticity setting;

the sparse activation state hash and fired paths are deterministic.

Activation ledger timestamps are operational metadata and are not part of the deterministic state hash.

## Bounded plasticity

When enabled and the Governor is `normal` or `constrained`, co-activated traversed synapses may strengthen using a bounded rule:

```text
delta = learning_rate × pre_activation × post_activation × remaining_capacity
new_weight = clamp(old_weight + delta, minimum_weight, maximum_weight)
```

Properties:

- weights cannot leave declared bounds;
- no **host** topology is invented; weak **G_learned** coactivation edges may be added under Governor (see topology law);
- only compiled repository relationships can strengthen;
- read-only mode blocks plasticity;
- updates are recorded in the neural ledger;
- source code is never mutated by plasticity.

## Episodic and long-term memory

Neuron does not create a second episodic memory system.

During a task, use the existing Cortex hippocampal flow:

```powershell
.\.cortex\bin\cortex.ps1 remember `
    -Kind decision `
    -Text "The authentication middleware owns token normalization."
```

```bash
./.cortex/bin/cortex.sh remember \
  --kind decision \
  --text "The authentication middleware owns token normalization."
```

At task completion:

```powershell
.\.cortex\bin\cortex.ps1 consolidate
```

```bash
./.cortex/bin/cortex.sh consolidate
```

The Bridge deterministically converts explicit task events into a provenance-bearing Discovery Card. Source and current tests remain authoritative.

## Governor modes

| Mode | Meaning |
|---|---|
| `normal` | Certificate verified, manifest current, active focus present, and trust sufficient |
| `constrained` | Smaller context and bounded dry-run-first behavior |
| `read_only` | Retrieval, inspection, replay, and proposals only; plasticity is disabled |

A missing, failed, degraded, or stale certificate forces `read_only` regardless of numeric stability.

Cortex never authorizes source mutation. Host repository rules, current tests, runtime evidence, and explicit human authorization remain controlling.

## Useful commands

```bash
python -m cortex status --repo MyProject --json
python -m cortex doctor --repo MyProject --json
python -m cortex environment --repo MyProject --json
python -m cortex query "Where is retry policy enforced?" --repo MyProject --json
python -m cortex interlink --repo MyProject --task "Trace retry policy" --json
python -m cortex interlink --repo MyProject --task "Trace retry policy" --learn --json
python -m cortex neural-replay --repo MyProject --limit 100 --json
python -m cortex graph --repo MyProject --json
python -m cortex verify --repo MyProject --json
python -m cortex nexus-packet --repo MyProject --task "Prepare gated evidence" --json
```

## NexusGate integration

Cortex is designed to become an evidence and memory organ inside NexusGate while preserving separation of responsibilities:

```text
Cortex
  assimilation
  environment learning
  semantic/structural/temporal/episodic memory
  sparse neural activation
  evidence packets

NexusGate
  intent routing
  evidence gates
  authority checks
  certificates
  mutation governance
```

Generate a packet shaped for NexusGate:

```bash
python -m cortex nexus-packet \
  --repo NexusGate \
  --task "Summarize the active wound and nearest passed certificate" \
  --json
```

The packet includes intent, evidence, learned environment, neural interlink state, structural context, and an explicit recommendation-only authority boundary.

## Repository configuration

The generated `.cortex/config.json` controls:

- repository name and stable ID;
- bound Python interpreter, engine root, and Cortex home;
- context budget;
- chunk size and overlap;
- file-size ceiling;
- Git history limit;
- supported extensions and excluded paths;
- authoritative and runtime-evidence paths;
- environment learning;
- neural interlink enablement;
- activation depth and node budget;
- bounded plasticity enablement and learning rate;
- verification thresholds.

## Optional semantic model

The core system works offline with deterministic feature hashing.

To enable a local SentenceTransformers model:

```bash
python -m pip install -e ".[semantic]"
```

PowerShell:

```powershell
$env:CORTEX_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

Bash:

```bash
export CORTEX_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
```

If loading fails, Cortex falls back to the dependency-free embedder.

## Tests

```powershell
.\scripts\powershell\Run-Tests.ps1
```

```bash
./scripts/bash/run-tests.sh
```

Manual:

```bash
python -m compileall -q cortex tests
python -m unittest discover -s tests -v
```

The current suite covers:

- original Cortex bootstrap, retrieval, graph, telemetry, drift, wrappers, sessions, and consolidation;
- learned environment profiles;
- single-database neural compilation;
- deterministic sparse activation;
- bounded plasticity;
- neural ledger integrity and tamper detection;
- neural context and NexusGate packet integration;
- embedded-engine exclusion from host assimilation.
- verified GCMT continuation packets and expiry;
- evidence/verification/authority-gated promotion and rollback;
- selective lifecycle decay with ledger integrity;
- boundary-preserving cross-repository retrieval;
- base-versus-learned replay evaluation;
- SQLite vector-bucket backfill;
- MCP initialization and tool discovery.

## Sparse activation benchmark

A reproducible synthetic benchmark is included:

```bash
python benchmarks/sparse_activation_benchmark.py --files 250
```

In the recorded build run, 42 of 262 nodes were considered and 24 fired, with identical metrics and state hash across two plasticity-disabled runs. See `BENCHMARK_REPORT.md` for the exact workload and claim boundary.

## Security and privacy

- No network access is required.
- The database can contain repository source and history; protect `CORTEX_HOME`.
- Exclude secret-bearing files before bootstrap.
- Do not record credentials, secrets, personal data, or raw confidential logs as episodic events.
- Neural association strength is evidence-routing metadata, not truth.
- Generated memory and environment inference can be incomplete.
- Current repository source, tests, compiler output, and runtime evidence win.

See `docs/SECURITY.md` for the full threat model.

## Non-goals

- training large neural models;
- autonomous source mutation;
- autonomous **host** topology creation / host source mutation;
- replacing repository tests or governance;
- distributed execution in this release;
- perfect semantic understanding of every language and artifact;
- claims of consciousness, AGI, or biological fidelity.

## Documentation

- `docs/research/README.md` — **research index (AI agents start here for math/constitution)**
- `docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md` — spectral vs constitutional geometry, epochs, Hamming paths
- `docs/research/CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md` — \(G=(X,R,B,T,A,W)\)
- `docs/research/CSG_DISCOVERY_LEDGER.md` — discovery sequence
- `docs/intelligence/PHASE_V7.0_RESONANT_CONTINUITY.md` — body epochs + phases
- `docs/intelligence/TOPOLOGY_LAW.md` — G_host / G_evidence / G_learned / G_federated
- `docs/ORGANISM.md` — session co-process bond (⊛)
- `docs/TRANSCEND.md` — packet-first agent loop and progress glyphs
- `docs/ARCHITECTURE_V4.md` — v4.0→v5.0 upgrade design (multi-res graph, ranker, prefetch, contracts, multi-agent, HNSW, causal ledger)
- `docs/EVOLUTION_V6.md` — interconnect mesh v5.1→v6.0 (delivered)
- `docs/EVOLUTION_SPECTRAL.md` — post-v6 plan: spectral kernels · v6.1/v6.2/v7.0
- `docs/COVENANT.md` — five-axis geometry and refuse list
- `docs/BRIGHT_POINT.md` — frozen alignment claims
- `docs/MIRROR.md` — coherence mirror and contact
- `docs/ARCHITECTURE.md` — single-substrate architecture and data flow
- `docs/BOOTSTRAP_PROTOCOL.md` — portable assimilation and certification sequence
- `docs/AI_INTEGRATION.md` — generic agent and NexusGate use
- `docs/DATA_MODEL.md` — SQLite entities and provenance
- `docs/SECURITY.md` — trust, privacy, and authority boundaries
- `docs/TROUBLESHOOTING.md` — common setup and runtime problems
- `docs/NEURAL_INTERLINK.md` — sparse activation and bounded plasticity
- `docs/GCMT.md` — governed continuation, lifecycle, federation, evaluation, MCP
- `docs/ARIA_META_LANGUAGE.md` — native ARIA semantic language over the Python core
- `docs/STEADY_STATE.md` — post-alignment discipline

## Star Lattice

First-party chart — no third-party hosts. Metrics come from the GitHub API (`stargazers` + `starred_at`) via CLI / Actions.

| Surface | Behavior |
|--------|----------|
| **Live lattice** | On every page load (+ optional 60s auto-refresh) fetches first-party `star-metrics.json` (published by CLI/Actions with `gh`) and redraws the HUD |
| **README SVG** | Snapshot at `assets/star-lattice.svg`, rebuilt by first-party Actions on **star events**, **hourly**, and manual dispatch |

<p align="center">
  <a href="https://jacksonjp0311-gif.github.io/Cortex/">
    <img
      src="assets/star-lattice.svg?v=14"
      alt="Cortex star lattice — cumulative stargazers (CI snapshot; open live lattice for fetch-on-reload)"
      width="100%"
    />
  </a>
</p>

<p align="center">
  <a href="https://jacksonjp0311-gif.github.io/Cortex/"><b>◈ Open live lattice</b></a>
  — pulls metrics on every reload · no third-party chart host
</p>

```bash
# regenerate README snapshot (requires GitHub CLI auth)
python scripts/build_star_lattice.py
python scripts/build_star_lattice.py --force --patch-readme

# local live lattice (fetch on every reload)
python -m http.server 8765 --directory assets
# then open http://127.0.0.1:8765/star-lattice.html
```

> GitHub README markdown cannot execute JavaScript, so the image above is a committed SVG kept current by `.github/workflows/star-lattice.yml`. The live page cannot call `api.github.com` stargazers from the browser (401 without a token); Actions/`gh` write `assets/star-metrics.json` and Pages serves it same-origin for fetch-on-reload.

<p align="center">
  <sub>If Cortex helps your agents remember — drop a star. It keeps the lattice bright.</sub>
</p>

## License

MIT License. See `LICENSE`.
