# ARIA as Cortex's Native Semantic Language

Cortex remains implemented and executed in Python. It ships a self-contained,
Apache-2.0-licensed ARIA snapshot labeled `INTERNAL ARIA META-LANGUAGE`.
ARIA represents intent, semantic plans, governance contracts, verified
continuation, and cooperative agent coordination.

## Boundary

ARIA integration does not:

- replace or transpile Cortex's Python implementation;
- execute `.aria` artifacts automatically;
- authorize repository mutation;
- aggregate authority across agents;
- repeat external effects during continuation;
- make ARIA a competing memory database or execution substrate.

Repository source, current tests, host governance, and explicit human
authorization remain controlling.

## Discovery

Cortex detects ARIA from bounded repository evidence:

- `ARIA-RUNTIME.json`;
- `ARIA-CONNECT.json`;
- supported `.aria` artifacts.

Host-local ARIA evidence takes precedence when present. Otherwise Cortex uses
its bundled snapshot under `cortex/aria_meta/vendor/`. The bundle is a squashed
Git subtree, not a submodule, and has no runtime dependency on another
repository. Its native `MANIFEST.sha256` is verified by Cortex.

## Native-region activation

Bundled ARIA occupies the `internal_aria_substrate` neural namespace. Cortex
always knows the region's identity and verified manifest, but it does not scan
that region for ordinary implementation tasks.

- unrelated tasks: `mode: dormant`, zero eligible ARIA nodes;
- ARIA/semantic/governance/continuity tasks: `mode: active`;
- activation is deterministic and reported in
  `neural_interlink.metrics.aria_substrate`;
- activation exposes evidence only—it never executes ARIA or grants authority.

## Bootstrap-tiered substrate indexing

Internal ARIA is large enough that eager full indexing on every bootstrap taxes
host assimilation and nested self-host latency. Cortex therefore splits the
region into tiers:

| Tier | What | When |
|---|---|---|
| Inventory | Every vendored path + content hash | Always (manifest integrity) |
| Anchors | Runtime/policy/cue registry files | Fully indexed at bootstrap |
| Deferred bulk | Specs, plans, modules, deep docs | `substrate_deferred` until ARIA wake |
| Materialized | Deferred files after first active task | Indexed once, then incremental |

Work-proxy math (file-ops, not wall-clock):

```text
W_bootstrap ≈ |repo ∪ anchors| · c_index + |aria \ anchors| · c_inventory
W_wake_once ≈ remaining_deferred · c_index
savings_ratio ≈ 1 - W_deferred_units / W_eager_units
```

`index.aria_substrate.work_proxy` and certificate
`coverage.deferred_substrate_count` expose these counters. Set
`aria_substrate_indexing: "eager"` in repository config to restore legacy
full-index bootstrap (diagnostics only).

## Runtime fluency and adaptation

Cortex maps admitted cues into typed purposes:

- `language`;
- `intent`;
- `continuity`;
- `consent`;
- `governance`;
- `coordination`;
- `symbolic`.

The 26 core cues are immutable. Single-token common English is avoided; `aria`
is the only intentional single-token wake. Learned cues must be multi-token
(except `aria`), repository-scoped, inspectable through `cortex meta-language`,
limited to 32, and admitted at confidence 0.65 only when a verified outcome
carries an explicit human-reviewed proposal. Verification-backed outcomes may
adjust a matched learned cue between 0.35 and 0.90. Falling below 0.65 makes
that cue dormant. Core cues, Python execution, and authority are never modified.

The fluency corpus under `benchmarks/corpora/aria_fluency.json` is a regression
gate: false wakes and missed wakes must remain zero.

## Vendor snapshot bump ritual

Do not hand-edit `cortex/aria_meta/vendor` mixed into unrelated Cortex core
commits. Bump the snapshot deliberately:

```powershell
.\scripts\powershell\Bump-AriaSnapshot.ps1 `
  -Source C:\path\to\ARIA `
  -SourceCommit <sha> `
  -SourceRelease <label> `
  -EvolutionLabel <evolution-name>
```

```bash
./scripts/bash/bump-aria-snapshot.sh /path/to/ARIA <sha> <release> <evolution>
```

That script mirrors the source tree, regenerates `MANIFEST.sha256`, refreshes
`INTERNAL_ARIA.json`, and runs `verify_bundle()`. Prefer a dedicated
`chore: bump INTERNAL ARIA snapshot` commit before Cortex core work that depends
on the new language surface.

## Constitutional glyph vocabulary

The internal alpha.18 language adds five executable function aliases:

| Glyph | Function | Runtime meaning |
|---|---|---|
| `⋈` | `MemoryBalance` | Harmonic balance of preserved and adjacent context |
| `≋` | `ConstitutionalPotential` | Observational instability |
| `⌁` | `ReversibilityBurden` | Increasing proof burden |
| `↧` | `AuthorityAdmissible` | Monotonic authority admission |
| `↶` | `RecoveryAdmissible` | Verified staged recovery |

Every glyph lowers into an ordinary function call before semantic analysis.
The cards are pure, deterministic, capability-free, and covered by the same
bytecode verifier and VM as textual calls. They describe Cortex supervision but
do not execute Cortex or grant authority.

```bash
cortex outcome --repo MyProject --activation-id act_... \
  --status verified --verification human-review \
  --aria-cue "continuity=portable memory bridge" \
  --aria-cue-reviewed --json
```

The runtime also exposes ARIA's bundled `grammar/semantic-cues.json` identity,
cue IDs, digest, and engagement contract. Those display semantics inform
runtime meaning but cannot independently wake Cortex.

Evaluate false wakes, missed wakes, and purpose assignment:

```bash
cortex meta-language --repo MyProject \
  --corpus benchmarks/corpora/aria_fluency.json --json
python benchmarks/aria_fluency_evaluation.py
```

The hidden `.aria/` runtime and backup directory is excluded from
assimilation. The `.aria` file extension remains supported, so declared plans
under paths such as `plans/*.aria` and `examples/*.aria` are indexed.

Inspect the learned descriptor:

```bash
cortex meta-language --repo MyProject --json
```

The descriptor states:

- `cortex_implementation_language: python`;
- `cortex_execution_language: python`;
- `role: host_meta_language` or `native_semantic_language`;
- `knowledge_relationship: integrated_host_language` or
  `native_internal_language`;
- `automatic_execution: false`;
- `automatic_translation_to_core: false`;
- `grants_mutation_authority: false`.

## Context and continuation

When ARIA is detected, the descriptor appears in:

- learned environment profiles;
- Cortex context packets and the Context Protocol;
- NexusGate-shaped packets through their environment field;
- GCMT continuation operational state.

This makes the semantic layer portable without confusing semantic continuity
with executable authority.

## Native verification

Cortex reports ARIA's declared handshake, baseline, doctor, conformance,
replay, handoff, bridge, and mesh commands as recommendations. It does not run
them automatically. Agents may run them when authorized and useful, and their
outputs remain evidence subject to deterministic verification.

External attachment remains available when a host repository has its own ARIA
evolution and must remain sealed:

```bash
cortex --home /path/to/cortex-home bootstrap /path/to/aria \
  --name aria-language --external --json
cortex --home /path/to/cortex-home meta-language \
  --repo aria-language --json
```
