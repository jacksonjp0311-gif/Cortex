# Signal Integrity Closure alpha.6.1

Signal Integrity Closure applies Semantic Projection Core to ARIA's persistent
history, live process surface, VM, and governance CLI.

## Governing law

```text
temporal cue
→ verified event, measured value, or live bounded predicate
```

Static layout may explain computation, but it does not animate or claim
evidence. Syntax may request a signal, but it cannot manufacture verification.

The evolution was declared first in executable ARIA:

```text
plans/signal-integrity-closure-alpha6-1.aria
```

## Event Spine v3

Every new event adds:

```text
sequence
operationId
operationSequence
previousDigest
```

`sequence` is the physical one-based position in the workspace ledger and
resumes across CLI processes. `operationSequence` starts at one for each
operation. `previousDigest` binds the complete prior event.

Initialization and replay revalidate every existing record. Appending opens the
ledger with exclusive file sharing, compares its exact bytes with the identity
established by that validation, verifies the tail and next sequence, rejects
changed or stale state, and then appends one UTF-8 record. This keeps repeated
semantic events bounded by one initial history validation rather than reparsing
the complete ledger for every event.

Replay rejects:

- event-content tampering;
- reordering;
- deletion;
- duplication;
- chain splicing;
- stale writers;
- cross-session sequence reset.

Event versions 1 and 2 remain individually verifiable. Version 3 begins chained
history without rewriting old evidence.

## Operation-local meaning

The ledger chain spans operations, but semantic transition comparison resets
when a new operation begins. A compiler transition is therefore not falsely
described as a transition from an unrelated Git or doctor command.

Operation identity belongs to the evidence record. It does not alter the
content-addressed semantic cue identity.

## Truthful Bufferflow

The old timer selected four phase names with `tick % 16`. Those labels did not
prove that the underlying subprocess had meshed, transmitted, aligned, or
verified anything.

Bufferflow now exposes only:

```text
pending while process.HasExited == false
```

Its rhythm communicates liveness and measured elapsed time. Completion removes
the pending frame and emits a projected receipt with duration, byte counts,
exit code, heartbeat count, and outcome.

## VM bridge

VM output, source-authored signals, agent dispatch, and connection lifecycle
events now receive Event Spine identities and semantic projections in execution
order.

A source statement such as:

```aria
signal pass "ready"
```

is recorded as an observation. It does not become `verification.seal`, because
source syntax is not verification evidence.

Runtime-evaluated withheld consent becomes rejection evidence. Connection
closure becomes bounded closure evidence.

## Static versus semantic output

Legacy banners, trees, summaries, and direct signals are static renderers. They
do not advance event history and no longer animate on their own.

Temporal glyph motion is reserved for:

- rendering a verified semantic projection;
- a live Bufferflow heartbeat tied to an active process.

## CLI governance adoption

The CLI now records semantic outcomes for:

- evolution proposal, authorization, and closure;
- intent verdicts;
- doctor closure;
- repository verification and manifest sealing;
- aggregate conformance closure;
- pipeline fractures.

Detailed diagnostic trees remain static explanations around those records.

## Admission

The dedicated 26-gate lattice proves history continuity, chain fractures,
legacy replay, truthful waiting, reduced-motion parity, receipt privacy,
VM identities, consent rejection, static/evidence separation, and inactive
algorithm cards.

Aggregate conformance at alpha.6.1 admission was `322/322`; the current
aggregate is recorded in the README and runtime test command.

## Authority boundary

This evolution adds no opcode, capability, policy permission, or active
algorithm card. Event records observe decisions; they do not make them.

## Next boundary

Verified Map, Filter, and Reduce now use this substrate as iterable language
operations whose start, measured iteration, completion, fracture, and evidence
history share the same human/machine semantic spine. Reduce alpha.9 added
bounded 32-record persistence batches that preserve every event identity while
avoiding one full append transaction per iteration. Per-Card Execution Evidence
alpha.10 is the next bounded language boundary.
