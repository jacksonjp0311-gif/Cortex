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
