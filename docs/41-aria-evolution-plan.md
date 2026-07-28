# ARIA Evolution Plan v1.0

**Canonical repository:** `jacksonjp0311-gif/ARIA`
**Baseline commit:** `b628fc79258b87d806be2884dec2afb2e2b67ba1`
**Baseline state:** Glyph Memory alpha.1, Glyph Lowering alpha.2, and Typed Composition alpha.3 remotely attested
**Proposed repository path:** `docs/41-aria-evolution-plan.md`

---

## 1. North Star

ARIA will become a governed, glyph-native, AI-native local execution language in
which every executable symbol carries:

1. a stable semantic identity;
2. an explicit type and effect contract;
3. a canonical lowering path;
4. deterministic implementation evidence;
5. a bounded authority surface;
6. replayable admission history.

ARIA is not optimized for maximum syntax density alone. It is optimized for
**meaning that remains inspectable under evolution**.

The defining objective is:

> A language that can evolve with machine assistance without allowing meaning,
> authority, or provenance to drift silently.

---

## 2. Canonical Laws

Every future evolution must preserve these laws.

### Law 1 — Meaning before execution

No glyph becomes executable before its semantic card exists, verifies, and
declares its lowering target.

### Law 2 — Syntax does not grant authority

A source surface may select or compose established behavior. It may not create a
capability, policy permission, effect, or merge authority.

### Law 3 — Lowering before opcode

Prefer canonical lowering into existing verified semantics. A new opcode is
admitted only when the language introduces a genuinely new runtime value or
operation that cannot be represented faithfully through existing machinery.

### Law 4 — Equivalence with provenance

Equivalent source surfaces must produce equal semantic IR and equal executable
behavior while retaining distinct source identity.

### Law 5 — Evidence before activation

A semantic card advances from `specified` to `verified` only after its dedicated
admission lattice passes locally and remotely.

### Law 6 — Proposal is not consent

An AI may propose syntax, cards, compositions, tests, or changes. It may not
approve its own proposal, grant itself authority, or merge its own evolution.

### Law 7 — Boundedness before scale

Every collection, recursion path, payload, call depth, artifact, and replay
surface must have explicit deterministic limits.

### Law 8 — Migration by equivalence

A native implementation may replace a bootstrap component only after
differential tests prove semantic and artifact equivalence.

### Law 9 — No invisible semantic drift

Any change to grammar, types, cards, lowering, opcodes, diagnostics, policy,
bytecode, or runtime behavior must be explicit in the evolution contract and
manifest.

### Law 10 — Necessary structure

ARIA does not gain a feature merely because other languages have it. A feature
enters because an established contract requires it or because a new governing
contract is explicitly proposed and admitted.

---

## 3. Current Proven Foundation

| Evolution | State | Established result |
|---|---:|---|
| Glyph Memory alpha.1 | Complete | Content-addressed semantic cards and activation memory |
| Glyph Lowering alpha.2 | Complete | `▷` and `↩` lower to existing `CALL` and `RETURN` |
| Typed Composition alpha.3 | Complete | `≫` lowers left-to-right into typed nested calls |
| Verified Map alpha.7 | Complete | `⨯` applies a compile-time unary pure transform with measured iteration evidence |
| Verified Filter alpha.8 | Complete | `⫰` performs stable typed selection with measured count evidence |
| Verified Reduce alpha.9 | Complete | `Σ` performs an exact pure left fold from an explicit initial accumulator |
| Per-Card Execution Evidence alpha.10 | Complete | Verified sequence-card exercises emit bounded observational receipts |
| Semantic Proposal Bundles alpha.11 | Complete | Canonical non-mutating contracts preserve semantic scope, rollback, evidence, and approval separation |
| Consent and Admission Receipts alpha.12 | Complete | Exact independent consent deterministically admits or rejects without granting repository authority |
| Core conformance | Complete | 202-test established language lattice |
| Cross-platform attestation | Complete | Windows PowerShell 5.1, PowerShell 7 Windows, PowerShell 7 Linux |

Verified executable cards:

```text
▷  function.invoke
↩  function.return
≫  composition.pipe
```

All three bounded sequence-algorithm cards are verified after alpha.9.

The present architecture proves this lifecycle:

```text
intent
→ semantic card
→ cryptographic identity
→ source syntax
→ canonical AST
→ typed semantics
→ deterministic bytecode
→ verified VM execution
→ remote attestation
```

---

# 4. Evolution Epochs

## Epoch I — Semantic Identity and Scalar Composition

**State: complete**

### alpha.1 — Glyph Memory Kernel

- Create canonical glyph-card registry.
- Hash every card and registry.
- Separate `specified` from `verified`.
- Add local content-addressed activation memory.
- Reject symbol collisions and tampering.

### alpha.2 — Function Glyph Lowering

- Activate `▷ function.invoke`.
- Activate `↩ function.return`.
- Preserve textual/glyph semantic parity.
- Preserve distinct source provenance.
- Add no opcode or capability.

### alpha.3 — Typed Composition

- Activate `≫ composition.pipe`.
- Lower pipelines into left-folded nested calls.
- Reuse existing function type diagnostics.
- Preserve source-order execution.
- Add no composition opcode.

---

## Epoch II — Immutable Data and Pure Algorithms

**Objective:** establish real typed sequence semantics before activating the
algorithm glyphs.

### alpha.4 — Sequence Core

Introduce a bounded immutable sequence value.

Candidate source:

```aria
let values: Sequence<Number> = [1, 2, 3, 4]
let empty: Sequence<Text> = []
```

Required work:

- Extend the type parser from scalar names to parameterized `Sequence<T>`.
- Support immutable homogeneous sequence literals.
- Require an explicit declared type for empty sequences.
- Initially restrict sequence elements to established scalar value types.
- Reject mixed element types without implicit coercion.
- Define deterministic sequence equality.
- Define canonical container serialization and hashing.
- Define bytecode-verifier stack contracts for sequence values.
- Define VM representation with explicit element and byte limits.
- Add policy/lockfile resource ceilings without granting a new capability.
- Preserve flat sequences first; nested sequences remain out of scope until a separate bounded-depth contract exists.
- Keep `⨯`, `⫰`, and `Σ` specified and inactive.

Mandatory design decision before implementation:

```text
ADR-004: sequence bytecode representation
A. immutable structured constant through existing PUSH_CONST
B. explicit sequence-construction opcode with typed verifier contract
```

The decision must prioritize verifier clarity, deterministic encoding, and
cross-platform equivalence—not minimum opcode count alone.

Exit gates:

- literal and declared-type agreement;
- heterogeneous literal rejection;
- empty-sequence type requirement;
- deterministic serialization;
- artifact round-trip;
- equality and provenance tests;
- resource-limit rejection;
- no algorithm activation;
- full existing regression lattice.

### alpha.5 — Effect and Purity Core

Sequence algorithms cannot honestly claim purity until ARIA can summarize the
functions they execute.

Required work:

- Infer a function effect summary from its statements.
- Include transitive effects from called functions.
- Produce a deterministic call graph.
- Reject unresolved purity caused by unsupported cycles.
- Classify functions as `pure` or `effectful`.
- Record required capabilities and effects in semantic IR.
- Preserve current policy decisions and diagnostics.
- Expose purity summaries to glyph-card admission tests.
- Do not add function closures or ambient function values.

Exit gates:

- direct effect inference;
- transitive effect inference;
- pure-call-chain proof;
- effectful-chain detection;
- deterministic call-graph ordering;
- recursive-cycle handling;
- capability-summary parity;
- no policy expansion.

### alpha.6 — Semantic Projection Core

Interposed by the governing human semantic-interface intent after Integration
Closure alpha.5.1.

- Bind glyph, motion/rhythm, machine record, and explanation to one verified
  event state.
- Give every cue a stable identity, digest, meaning, and non-meaning boundary.
- Record actual transition deltas and measured-only timing.
- Preserve reduced-motion and static semantic equivalence.
- Bound and redact event-journal detail before persistence.
- Prohibit false progress and manipulative engagement mechanics.
- Make the cue vocabulary self-teaching through the CLI.
- Add no capability, policy permission, opcode, or execution authority.

### alpha.6.1 — Signal Integrity Closure

- Resume Event Spine sequence identity across CLI processes.
- Hash-chain every new event to the prior workspace event.
- Separate workspace ledger order from operation-local transition order.
- Replace timer-generated Bufferflow phases with live pending state.
- Project measured process receipts without raw stdout or stderr.
- Bind VM signals, agent dispatch, and connection lifecycle to semantic events.
- Prevent source-authored pass/fail signals from manufacturing verifier verdicts.
- Keep static layout non-temporal and outside evidence history.
- Add no opcode, capability, policy permission, or algorithm activation.

### alpha.7 — Verified Map

Activate `⨯ algorithm.map` as the first sequence algorithm.

**State: complete.** The admitted surface, bytecode, verifier, runtime, signal
history, and evidence are specified by ADR-008 and
`docs/47-verified-map-alpha7.md`.

Candidate surface:

```aria
let doubled: Sequence<Number> = ⨯(values, Double)
```

The exact surface must be locked in an ADR before implementation. The semantic
contract is fixed regardless of spelling:

```text
Sequence<T> × PureFunction<T,U> → Sequence<U>
```

Required behavior:

- Transform function is identified at compile time.
- Transform must be unary and pure.
- Input type must match the sequence element type.
- Output order and length are preserved.
- Execution is deterministic and bounded.
- No closure capture or ambient mutation.
- The map card advances to `verified` only after remote admission.

Preferred runtime direction:

- use a dedicated verified sequence-map operation or a generic sequence iteration IR;
- invoke the established function body for each element;
- never bypass existing argument and return verification.

### alpha.8 — Verified Filter

Activate `⫰ algorithm.filter`.

Candidate surface:

```aria
let positive: Sequence<Number> = ⫰(values, IsPositive)
```

Contract:

```text
Sequence<T> × PureFunction<T,Bool> → Sequence<T>
```

Required behavior:

- stable source order;
- unary pure predicate;
- predicate return type exactly `Bool`;
- deterministic cardinality;
- bounded allocation;
- no mutation of the input sequence.

### alpha.9 — Verified Reduce

Activate `Σ algorithm.reduce`.

Candidate surface:

```aria
let total: Number = Σ(values, Add, 0)
```

Contract:

```text
Sequence<T> × PureFunction<A,T,A> × A → A
```

Required behavior:

- explicit initial accumulator;
- deterministic left fold;
- binary pure reducer;
- accumulator continuity at every step;
- empty sequence returns the explicit initial value;
- no implicit identity inference;
- bounded execution.

### Epoch II closure

At closure, ARIA must support:

```text
scalar values
immutable typed sequences
pure function summaries
typed composition
ordered map
stable filter
deterministic reduce
```

No algorithm may use a semantic shortcut unavailable to its textual equivalent.

---

## Epoch III — Execution Evidence and Governed Semantic Proposals

**Objective:** allow ARIA to remember not only what a card means, but where and
under what evidence it executed.

### alpha.10 — Per-Card Execution Evidence

**Status: Complete.** Implemented as `aria.card-execution-evidence/1` with a
dedicated 20-gate lattice and exact Event Spine plus SignalSubset linkage.

Emit a bounded evidence event whenever a verified card is exercised.

Evidence should include:

- card ID and digest;
- compiler and runtime version;
- source hash;
- semantic IR hash;
- build hash;
- policy digest;
- relevant test-receipt digest;
- event state and deterministic timestamp/sequence identity;
- aggregate counts rather than sensitive runtime payloads by default.

Integrate evidence through Event Spine and SignalSubset.

Evidence is observational. It grants no authority.

### alpha.11 — Semantic Proposal Bundles

Introduce `aria.semantic-proposal/1`.

A proposal bundle may contain:

- human intent reference;
- proposed card or card revision;
- grammar and lowering changes;
- affected types, effects, opcodes, and policies;
- exact changed-path allowlist;
- proof obligations;
- generated test plan;
- compatibility and migration analysis;
- rollback or reversal strategy;
- proposer identity.

An AI may construct this bundle but may not mark it approved.

### alpha.12 — Consent and Admission Receipts

Bind proposal admission to:

```text
intent
→ proposal
→ verifier result
→ human consent
→ deterministic apply
→ local gates
→ remote attestation
→ closure receipt
```

Requirements:

- consent references an exact proposal digest;
- apply rejects proposal drift;
- approval and implementation identities remain distinct;
- no self-approval;
- no hidden path changes;
- no force push;
- remote failure uses a normal reversal commit.

### alpha.13 — Deterministic Semantic Replay

Given the same baseline commit, proposal bundle, consent receipt, toolchain lock,
source inputs, policy, and test evidence, ARIA should reproduce the same admitted
semantic state or explain the exact drift boundary.

Epoch III closure establishes a machine-auditable memory of language evolution.

---

## Epoch IV — Native Core Migration

**Objective:** move beyond the PowerShell bootstrap without discarding it as
evidence.

The PowerShell implementation becomes a frozen reference oracle. It is not
deleted during migration.

### beta.1 — Native Front End

Implement in Rust:

- UTF-8 source normalization;
- lexer;
- parser;
- canonical AST;
- type parser;
- semantic diagnostics;
- semantic-card loading and verification.

Run every source fixture through both implementations.

Required result:

```text
PowerShell AST/diagnostics == Rust AST/diagnostics
```

### beta.2 — Native Bytecode, Verifier, and VM

Implement:

- canonical IR;
- deterministic container writer/reader;
- bytecode verifier;
- capability and policy enforcement;
- VM;
- sequence runtime;
- event/evidence emission.

Required result:

```text
PowerShell executable projection == Rust executable projection
PowerShell runtime output          == Rust runtime output
```

Byte-for-byte container equality is preferred. Where platform-independent
metadata prevents it, the differing field must be isolated and explicitly
specified.

### beta.3 — Differential Equivalence and Bootstrap Freeze

- Execute the complete fixture corpus through both implementations.
- Fuzz parser and verifier boundaries.
- Compare diagnostics, IR, bytecode, output, effects, and failure modes.
- Freeze the PowerShell bootstrap as the historical oracle.
- Reject native-only semantics until formally admitted.

### beta.4 — One Binary Operator Experience

Deliver:

```text
aria.exe
aria
```

with the established Grok-build surface:

```text
◆ staged execution
◈ active operation
◇ bounded information
⬗ explicit fracture
```

Raw compiler and VM detail remains behind verbose/debug mode.

The native core must remain local-first and usable without an AI provider.

---

## Epoch V — Language Completeness

These features begin only after the native core is equivalence-proven.

### beta.5 — Records and Tagged Variants

- immutable records;
- named fields;
- tagged variants;
- deterministic field ordering;
- structural type identity;
- bounded nesting.

### beta.6 — Option, Result, and Pattern Matching

- explicit absence and failure values;
- exhaustive matching;
- no exception-shaped hidden control flow;
- typed propagation operator only after Result semantics are verified.

### beta.7 — Modules and Visibility

- explicit exports;
- qualified imports;
- no ambient symbol injection;
- deterministic module graph;
- import-cycle diagnostics;
- content-addressed module identity.

### beta.8 — Package and Dependency Integrity

- content-addressed package manifests;
- locked dependency graph;
- reproducible fetch/build;
- signatures as optional additional evidence, not a replacement for hashes;
- offline cache;
- no install-time execution by default.

### beta.9 — Standard Library v0

Initial bounded modules:

```text
core
text
number
sequence
result
memory
graph
event
```

Every standard-library operation receives the same card, type, effect, test, and
provenance treatment as language primitives.

---

## Epoch VI — AI-Native Composition

**Objective:** make AI a governed semantic collaborator rather than an
unbounded code emitter.

### rc.1 — Composition Planner

An AI may propose:

- function compositions;
- graph structures;
- semantic-card candidates;
- test obligations;
- refactor plans.

Output is a proposal artifact, never an automatic mutation.

### rc.2 — Constraint-Grounded Synthesis

The planner receives:

- type environment;
- effect summaries;
- capability policy;
- active semantic-card registry;
- resource limits;
- approved dependency graph.

Generated programs must pass the same compiler and verifier as human-authored
programs.

### rc.3 — Governed Evolution Workbench

Provide an operator surface showing:

```text
intent
proposal
semantic diff
authority diff
proof obligations
local evidence
remote evidence
consent state
reversal plan
```

The human remains the final admission authority.

---

# 5. Definition of ARIA 1.0

ARIA reaches 1.0 only when all of the following are true.

## Language

- stable grammar and semantic versioning;
- scalar, sequence, record, variant, Option, and Result types;
- typed functions and composition;
- map, filter, and reduce;
- deterministic module and package graph;
- explicit effect and capability summaries.

## Runtime

- native Rust compiler, verifier, and VM;
- deterministic artifacts;
- reproducible builds;
- bounded memory, sequence, recursion, and payload behavior;
- Windows and Linux support;
- no mandatory cloud dependency.

## Governance

- content-addressed semantic cards;
- proposal, consent, admission, and closure receipts;
- replayable semantic history;
- exact authority diffs;
- AI proposal without AI approval authority.

## Tooling

- formatter;
- language server;
- diagnostics with stable codes;
- package lock;
- test runner;
- artifact inspection;
- semantic-card inspection;
- trace and evidence inspection;
- operator-friendly CLI with verbose/debug escape hatch.

## Trust

- public specification;
- conformance suite;
- reproducible release artifacts;
- migration documentation;
- security model and threat analysis;
- no claims beyond verified implementation.

---

# 6. Anti-Goals

ARIA will not:

- use glyphs as decorative aliases without semantic contracts;
- treat AI output as intrinsically trusted;
- grant execution authority through syntax;
- hide effects behind apparently pure operators;
- add unbounded collections or recursion;
- adopt first-class closures before effect and capture semantics exist;
- rewrite the compiler wholesale without differential evidence;
- force a cloud model into the runtime;
- sacrifice provenance to make equivalent sources hash identically;
- use force pushes to erase failed evolution history;
- claim self-awareness, consciousness, or autonomous understanding.

---

# 7. Mandatory Evolution Transaction

Every direct-main evolution follows this transaction:

```text
resolve exact main SHA
→ require clean main
→ verify remote identity
→ apply bounded mutation
→ enforce exact changed-path allowlist
→ reseal semantic registries
→ reseal MANIFEST.sha256
→ parse authored scripts
→ run dedicated evolution lattice
→ run all prior lattices
→ run strict doctor
→ run full conformance
→ execute canonical example
→ commit directly to main
→ push without force
→ await exact push-triggered remote attestation
→ accept green closure or create a normal reversal commit
```

No pull request is created unless explicitly requested.

Each evolution must contain:

- `docs/<evolution>.md`;
- `plans/<evolution>.aria`;
- executable examples;
- dedicated tests;
- CI integration;
- manifest updates;
- explicit next bounded evolution.

---

# 8. Immediate Execution Order

The next canonical sequence is:

```text
alpha.4  Sequence Core
alpha.5  Effect and Purity Core
alpha.6  Semantic Projection Core
alpha.6.1 Signal Integrity Closure
alpha.7  Verified Map
alpha.8  Verified Filter
alpha.9  Verified Reduce
alpha.10 Per-Card Execution Evidence
alpha.11 Semantic Proposal Bundles
alpha.12 Consent and Admission Receipts
alpha.13 Deterministic Semantic Replay
beta.1   Native Rust Front End
beta.2   Native Bytecode, Verifier, and VM
beta.3   Differential Equivalence and Bootstrap Freeze
beta.4   One Binary Operator Experience
```

This order is architectural, not cosmetic:

```text
data substrate
→ purity proof
→ algorithms
→ execution evidence
→ governed proposals
→ replay
→ native migration
```

---

# 9. Immediate Next Evolution Contract

## Semantic Continuity Epoch alpha.14–17

### Intent

Carry the same admitted semantic state through replay, private handoff,
provider eligibility, and multi-agent cooperation—or identify the exact drift,
privacy, capability, disagreement, or authority boundary.

### Explicitly in scope

- canonical replay, handoff, bridge, and mesh records;
- exact baseline, proposal, consent, admission, toolchain, policy, and evidence identities;
- deterministic re-execution of admission obligations;
- first-difference drift classification;
- equivalent-state or bounded-fracture verdict;
- privacy-bounded transfer between distinct agents;
- provider capability ceilings without transport execution;
- independent producer, critic, and human mesh roles.

### Explicitly out of scope

- repository mutation during replay;
- hidden environment inputs;
- nondeterministic success assertions;
- treating equivalent replay as universal correctness;
- native compiler migration;
- live provider network calls;
- transferring consent or aggregating authority.

### Admission target

Four dedicated lattices must reproduce exact admitted state, preserve only
bounded references during handoff, reject excess provider capability, require
independent challenge and human conflict resolution, and remain non-mutating
and authority-free.

---

# 10. Canonical Summary

ARIA's evolution is governed by this progression:

```text
remember meaning
→ lower meaning
→ compose meaning
→ structure data
→ prove purity
→ verify algorithms
→ record evidence
→ govern proposals
→ replay evolution
→ migrate by equivalence
→ become native
```

The language should continue to feel discovered rather than arbitrarily
assembled because each new layer must be the necessary consequence of the
verified layers beneath it.
## 11. Attested implementation progress

- Sequence Core alpha.4 closed on `101a88f0316b7a0cb0110b73a1876bd2fa6efae1`.
- Effect Graph & Purity Core alpha.5 connects source semantics, call topology,
  bytecode metadata, independent verifier reconstruction, VM admission, glyph
  proof obligations, CI, and operator inspection.
- `⨯ algorithm.map` is verified through its dedicated 22-gate lattice.
- `⫰ algorithm.filter` is verified through its dedicated 24-gate lattice.
- `Σ algorithm.reduce` is verified through its dedicated 27-gate lattice.
- Semantic Projection Core alpha.6 interposes the governing human/machine
  projection contract before sequence algorithms.
- Signal Integrity Closure alpha.6.1 gives that contract continuous history,
  truthful live waiting, VM adoption, and governance adoption.
- Verified Map alpha.7 connects typed sequences, purity proofs, explicit MAP
  bytecode, deterministic VM iteration, and Event Spine evidence.
- Verified Filter alpha.8 connects stable selection, exact Boolean predicates,
  explicit FILTER bytecode, input immutability, and measured count evidence.
- Verified Reduce alpha.9 connects exact accumulator continuity, strict
  left-fold order, explicit REDUCE bytecode, full algorithm composition,
  content-addressed intent governance, and bounded event batching.
- Per-Card Execution Evidence alpha.10 binds each Map, Filter, and Reduce
  exercise to its card, artifact, effect graph, policy, admission-test
  contract, terminal Event Spine identity, and privacy-filtered aggregates.
- Semantic Proposal Bundles alpha.11 adds canonical, non-mutating, authority-free
  contracts with exact semantic deltas, path scope, obligations, compatibility,
  rollback, and optional execution-evidence references.
- Consent and Admission Receipts alpha.12 binds exact independent human consent
  to deterministic admission obligations while granting no repository authority.
- Agent Semantic Handshake alpha.13 makes repository identity, vocabulary,
  synchronization, health, and authority boundaries discoverable in one record.
- Deterministic Semantic Replay alpha.14 identifies the first exact causal drift
  without repeating external effects.
- Portable Session Handoff alpha.15 transfers bounded artifact references while
  excluding private conversation, consent, and authority.
- Provider Bridge Membrane alpha.16 verifies capability-bounded provider
  eligibility without network execution or payload transport.
- Cooperative Agent Mesh alpha.17 requires independent producer, critic, and
  human roles while prohibiting consensus claims and authority aggregation.
- The next bounded evolution is Capability-Gated Live Provider Adapter alpha.18.
- Integration Closure alpha.5.1 completes entry-flow effect coverage, derives
  intent authority from admitted artifacts, unifies all local lattices, and
  synchronizes release discovery before Semantic Projection Core alpha.6.
