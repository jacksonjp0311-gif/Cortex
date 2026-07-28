# ADR-011: Derive bounded execution receipts from terminal card events

## Status

Accepted for Per-Card Execution Evidence alpha.10.

## Context

ARIA already verifies semantic cards, deterministic source and IR identities,
artifact bytes, whole-program effects, policy, and hash-chained runtime events.
These identities remain separate during execution. A completion cue proves its
own event integrity but does not identify the exact card and artifact that
produced it.

## Decision

Every completed or fractured `MAP`, `FILTER`, and `REDUCE` exercise derives one
`aria.card-execution-evidence/1` receipt after its terminal algorithm event.
The receipt binds:

- verified card ID, symbol, and digest;
- compiler and runtime versions;
- source, semantic IR, artifact, and effect-graph identities;
- exact policy-byte digest;
- a deterministic admission-test-contract digest derived from the card;
- operation kind, target, source line, outcome, and bounded aggregate counts;
- terminal Event Spine operation, sequence, time, state, and digest;
- a verified SignalSubset containing only terminal-event identity fields;
- an explicit observational, zero-authority classification.

The VM independently verifies the completed receipt before returning it and
then emits one `evidence.card.execution` Event Spine event containing only
receipt linkage. Receipts are returned under `executionEvidence`.

## Determinism boundary

Given identical receipt inputs, canonical identity is deterministic. Runtime
wall-clock timestamps and measured event sequence positions are observations,
not replay-invariant constants. They are bound exactly rather than invented or
normalized away.

## Privacy boundary

Receipts contain aggregate counts but no sequence elements, mapped values,
filter payloads, initial values, accumulators, output text, event data, or
semantic projection payload. SignalSubset records both the allowlist and the
excluded source fields.

## Authority boundary

Execution evidence is observational. It cannot issue a capability, alter a
policy decision, admit a card, approve an interpretation, or authorize another
execution. Any receipt claiming authority fails verification.

## Test-receipt boundary

`admissionTestReceiptDigest` identifies the verified card's canonical admission
test contract and lifecycle state. It does not claim that the current execution
reran the complete repository suite. Release and CI results remain separate
closure evidence.
