# Cortex v3.1.0 Test Report

**Release validation date:** July 28, 2026

## Constitutional homeostasis / GCMT v1.5 validation

- `python -m pytest tests -q`: 47 passed
- `python -m ruff check cortex tests`: passed
- `python -m cortex benchmark --verify --json`: passed all five controlled
  thresholds
- ARIA strict doctor: passed; system ready
- ARIA full conformance: 512/512 gates coherent
- Constitutional ARIA lattice: 12/12 gates coherent
- Bundled ARIA manifest: 301/301 files verified
- Source distribution and wheel build: passed
- Real ARIA execution verified all five glyph lowerings through ordinary typed
  functions and existing `CALL` bytecode; no privileged opcode or capability
  was introduced
- Continuation protocol 1.1 verified that imported packets are metadata-only,
  authority is rebound locally, and source packets grant no authority
- Promotion tests verified that authority growth requires a content-addressed
  external grant and that rollback admits only a staged, verified recovery
  candidate
- Deferred ARIA substrate: non-anchor vendor files remain `substrate_deferred`
  through verified bootstrap; ARIA-active query materializes them once
- Fluency corpus expansion: false-friend cases (semver, glyph icon, bridge
  modules, etc.) stay dormant; multi-token ARIA cues still wake correctly

The new checks establish the declared repository-local invariants. They do not
prove general intelligence, universal safety, or correctness outside the
tested workloads.

The v3.0 report below is retained as release lineage.

# Cortex v3.0.0 Test Report

**Release validation date:** July 28, 2026

## v3.0 release validation

- `python -m unittest discover -s tests -q`: 43 passed
- `python -m ruff check cortex thalamus tests`: passed
- Python compilation: passed
- Source distribution and wheel build: passed
- Existing controlled-workload benchmark thresholds: passed
- Nested-clone self-host lifecycle: verified certificate, ready activation,
  explicitly labeled internal engine excluded, source/engine commit parity
  verified, nested tests passed
- Sealed-host external attachment: zero host writes, Aria Git tree clean,
  Aria strict doctor passed, Cortex certificate verified
- Aria native surfaces: `.aria` and `.cmd` indexed; supported inventory
  increased from 238 to 292 files
- ARIA meta-language boundary: Python implementation/execution retained,
  automatic ARIA execution disabled, context and continuation propagation
  verified
- INTERNAL ARIA snapshot: 298 tracked files vendored as a squashed subtree;
  no submodule or external runtime repository dependency
- Bundled ARIA native manifest: 297/297 verified
- Bundled ARIA handshake, strict doctor, and full conformance suite: passed
- Clean-wheel bundle verification: 297 entries checked, zero failures
- Host-local ARIA integration remains available and takes precedence when
  Cortex is explicitly operating on such a repository
- Native-region routing: INTERNAL ARIA remains known but contributes zero
  eligible nodes to unrelated tasks; semantic and continuity signals activate
  the region deterministically
- Dormant-region retrieval: internal ARIA paths are excluded at lexical and
  vector candidate selection rather than discarded after scoring
- Typed fluency: 7 purposes and 19 immutable core cues; reviewed verified
  outcome admits a bounded learned cue, and negative verified evidence can
  lower it below the deterministic 0.65 wake threshold without changing
  authority
- Fluency corpus: 20/20 passed with zero false wakes, missed wakes, or purpose
  misses
- Fluent-runtime nested self-host: verified certificate, ready activation,
  commit-current internal engine, nested tests passed
- Bootstrap probe hardening: ambiguous duplicate symbols excluded and exact
  heading evidence accepted when a specialized document outranks README
- Real Cortex repository smoke: manifest current, database integrity true,
  dashboard version 3.0.0, replay corpus non-regression true, boundary gate true,
  persisted continuation packet valid

The new suite covers GCMT state-plane separation, continuation packet integrity
and expiry, evidence/verification/authority promotion gates, hash-chained
receipts, rollback fidelity, selective learned-association decay, neural ledger
integrity, cross-repository boundary preservation, vector-bucket migration,
base-versus-learned replay evaluation, external sealed-host attachment,
internal-engine identity/freshness, native `.aria`/batch indexing, fused
reranking, bundled and host-local ARIA language discovery, INTERNAL ARIA
identity, manifest verification, namespace compilation, dormant routing,
semantic wake-up, and MCP
initialization/tool discovery.

These checks establish implementation and repository-local benchmark evidence.
They do not establish universal answer-quality improvement, biological
fidelity, cross-domain robustness, or independent reproduction.

The v2.0 report below is retained as release lineage.

# Cortex v2.0.0 Test Report

**Release validation date:** July 14, 2026

## v2.0 release validation

- `python -m pytest`: 26 passed
- Python compilation: passed
- `ruff check cortex tests`: passed
- Outcome learning: activation is observational; a verified outcome receives bounded credit, passes the replay gate, updates only in an allowed Governor mode, and appends to the hash-chained ledger.
- Context protocol: `cortex protocol` exposes `cortex-context/1.0` with an explicit authority boundary.

The v1.3.1 report below is retained as release lineage.

# Cortex Neural Interlink v1.3.1 Test Report

**Test date:** July 11, 2026  
**Primary validation environment:** Linux, CPython 3.13, SQLite with FTS5

## Automated suite

## Current release addendum (July 12, 2026)

- Python compilation: passed
- `python -m unittest discover -s tests -q`: 26 passed
- Ruff: passed
- `cortex benchmark --verify --json`: passed

The historic v1.1.0 validation details below are retained as lineage, not as the current release claim.

Commands:

```bash
python -m compileall -q cortex tests
python -m unittest discover -s tests -v
bash -n cortex.sh cortex-all-one.sh scripts/bash/*.sh
```

Result:

```text
Ran 17 tests
OK
```

The suite covers all original Cortex behavior plus the neural integration:

- managed `AGENTS.md` and repository-local wrapper installation;
- bootstrap certificate issuance and manifest integrity;
- supported-content indexing and unsupported-surface reporting;
- hybrid retrieval with path, line, hash, type, and score provenance;
- structural graph resolution and source-to-test relationships;
- bounded Git history and co-change telemetry;
- repository drift detection and incremental refresh;
- read-only fallback when refresh is disabled;
- active sessions, episodic events, and Discovery Card consolidation;
- repository identity reuse without stale-memory contamination;
- CLI and generated Bash wrapper execution, including protection from inherited Cortex-home and Python-engine redirection;
- learned environment profiles;
- single-database neural node and synapse compilation;
- deterministic sparse activation with plasticity disabled;
- explicit structural propagation from a retrieved seed into a non-retrieved support file;
- bounded Hebbian plasticity;
- neural event-ledger integrity and tamper detection;
- neural context and NexusGate packet integration;
- embedded engine exclusion from host assimilation.

## Portable nested-folder smoke test

A clean copy of Cortex was placed at:

```text
HostRepo/CortexEngine/
```

The command below was run without installing the package into the virtual environment:

```bash
./cortex-all-one.sh \
  --name HostRepo \
  --task "Find the host entrypoint" \
  --run-tests
```

Observed outcome:

- engine virtual environment created;
- 17 tests passed;
- parent host repository inferred;
- `CortexEngine` automatically added to host exclusions;
- repository bootstrap completed;
- environment profile written;
- neural interlink compiled;
- bootstrap certificate status: `verified`;
- doctor database check: passed;
- neural ledger check: passed;
- first context packet written.

## Wheel validation

A wheel was built and installed into a clean virtual environment:

```text
cortex_memory-1.1.0-py3-none-any.whl
```

A separate sample repository completed:

```text
wheel install -> bootstrap -> environment learning -> neural compilation
-> verified certificate -> activation -> doctor
```

Observed checks:

```json
{
  "certificate": "verified",
  "environment_ecosystems": ["python"],
  "neural_node_coverage": 1.0,
  "database_integrity": true,
  "neural_ledger_integrity": true
}
```

## Deterministic benchmark validation

The 250-module sparse benchmark was run twice. Activation metrics and state hash were identical across runs when plasticity was disabled.

See `BENCHMARK_REPORT.md`.

## PowerShell validation boundary

The build environment does not contain Windows PowerShell or `pwsh`. PowerShell files were reviewed for Windows PowerShell 5.1-compatible syntax and kept free of PowerShell 7-only constructs. The GitHub Actions matrix includes Windows launcher execution for repository-hosted validation.

## Claim boundary

These results validate the implemented assimilation, environment learning, graph compilation, retrieval, sparse activation, bounded plasticity, consolidation, integration, drift refresh, packaging, and integrity behavior. They do not prove target-repository correctness, security, semantic completeness, biological fidelity, or authority to mutate source.
