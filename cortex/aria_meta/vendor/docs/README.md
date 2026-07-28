# ARIA Documentation Index

The documents in this directory define the language, its bootstrap implementation, and the research decisions behind it.

## Normative core

- [`00-charter.md`](00-charter.md) — project principles and non-goals
- [`01-language-spec.md`](01-language-spec.md) — bootstrap syntax and semantics
- [`02-mathematical-model.md`](02-mathematical-model.md) — graph, machine-state, authority, and transition model
- [`03-glyph-alphabet.md`](03-glyph-alphabet.md) — glyph invariants and registry
- [`04-bytecode-and-container.md`](04-bytecode-and-container.md) — opcodes and `.ariac` binary envelope
- [`05-vm-and-memory.md`](05-vm-and-memory.md) — runtime and durable memory
- [`06-capability-security.md`](06-capability-security.md) — authority and host-effect confinement
- [`07-compiler-gates.md`](07-compiler-gates.md) — compilation, integrity, and release gates
- [`08-ai-bridge.md`](08-ai-bridge.md) — deterministic boundary for AI proposals
- [`09-versioning-and-compatibility.md`](09-versioning-and-compatibility.md) — compiler/spec/container version policy
- [`10-repository-operations.md`](10-repository-operations.md) — local development and release workflow
- [`11-roadmap.md`](11-roadmap.md) — staged evolution beyond the bootstrap
- [`47-verified-map-alpha7.md`](47-verified-map-alpha7.md) — verified typed transformation and iteration evidence
- [`48-verified-filter-alpha8.md`](48-verified-filter-alpha8.md) — verified stable selection and count evidence
- [`49-verified-reduce-alpha9.md`](49-verified-reduce-alpha9.md) — verified exact left fold and accumulator evidence
- [`50-per-card-execution-evidence-alpha10.md`](50-per-card-execution-evidence-alpha10.md) — bounded receipts joining cards, artifacts, policy, and terminal events
- [`51-semantic-proposal-bundles-alpha11.md`](51-semantic-proposal-bundles-alpha11.md) — canonical non-mutating language-change proposals
- [`52-consent-admission-receipts-alpha12.md`](52-consent-admission-receipts-alpha12.md) — independent human consent and deterministic admission
- [`53-agent-semantic-handshake-alpha13.md`](53-agent-semantic-handshake-alpha13.md) — content-addressed AI discovery, shared vocabulary, and authority-free synchronization
- [`54-deterministic-semantic-replay-alpha14.md`](54-deterministic-semantic-replay-alpha14.md) — verify-only semantic reconstruction and first-drift evidence
- [`55-portable-session-handoff-alpha15.md`](55-portable-session-handoff-alpha15.md) — privacy-bounded continuity between distinct AI participants
- [`56-provider-bridge-membrane-alpha16.md`](56-provider-bridge-membrane-alpha16.md) — provider-neutral eligibility below an explicit capability ceiling
- [`57-cooperative-agent-mesh-alpha17.md`](57-cooperative-agent-mesh-alpha17.md) — producer, critic, and human coordination without consensus or authority aggregation

## Algorithms

The [`algorithms/`](algorithms/) folder records implementation invariants for parsing, glyph normalization, capability resolution, memory, reproducible builds, container integrity, compiler stages, and bytecode verification.

## Research and discoveries

The [`research/`](research/) folder maps compiler theory, formal semantics, security, reproducibility, Unicode, memory systems, HCI, AI agents, information theory, and distributed systems into concrete ARIA decisions.

## Architecture decisions

The [`adr/`](adr/) folder records why ARIA uses a PowerShell bootstrap, a
deterministic core, glyph aliases, memory outside executable artifacts, and
explicit verifier-visible sequence algorithm instructions.

## Validation

- [`VALIDATION.md`](VALIDATION.md) — executable and static validation commands
- [`references.md`](references.md) — primary specifications and technical references
- [`MIGRATION_FROM_AEL.md`](MIGRATION_FROM_AEL.md) — relationship to the earlier AEL laboratory prototype

- [`15-coreflow.md`](15-coreflow.md) — typed expressions, functions, lexical control flow, loops, modules, and dispatch.
- [`algorithms/expression-evaluation.md`](algorithms/expression-evaluation.md) — host-independent typed expression parsing and lowering.
- [`algorithms/lexical-scope-and-functions.md`](algorithms/lexical-scope-and-functions.md) — scope stacks, frames, and authority isolation.
- [`algorithms/structured-control-verification.md`](algorithms/structured-control-verification.md) — nested branch and loop verification.
- [`research/coreflow-discoveries.md`](research/coreflow-discoveries.md) — cross-domain findings behind Coreflow.
- [`adr/0005-structured-control-bytecode.md`](adr/0005-structured-control-bytecode.md) — rationale for structured control bytecode.

- [`16-connectflow.md`](16-connectflow.md) — human intent, agent proposal, explicit consent, and deterministic connection closure.
