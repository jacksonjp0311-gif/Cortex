# ARIA as an Optional Cortex Meta-Language

Cortex remains implemented and executed in Python. ARIA is an optional
meta-language for repositories that use it to represent intent, semantic
plans, governance contracts, verified continuation, and cooperative agent
coordination.

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
- `role: meta_language`;
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

For sealed ARIA repositories, use external attachment so no Cortex files enter
the host:

```bash
cortex --home /path/to/cortex-home bootstrap /path/to/aria \
  --name aria-language --external --json
cortex --home /path/to/cortex-home meta-language \
  --repo aria-language --json
```
