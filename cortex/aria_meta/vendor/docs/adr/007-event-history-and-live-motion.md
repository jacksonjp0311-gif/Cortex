# ADR-007: Chain event history and bind waiting motion to liveness

## Status

Accepted for Signal Integrity Closure alpha.6.1.

## Context

Event Spine v2 verified records independently but reset sequence numbers for
each CLI process. Bufferflow advanced named phases according to a timer. Both
behaviors were incompatible with a shared semantic language: order was not
continuous and motion could claim transitions that had not occurred.

## Decision

New events use `aria.event` version 3 with a workspace ledger sequence,
operation identity, operation sequence, and previous-event digest. A process
fully validates history once, retains its exact byte identity, and appends only
when the locked ledger still has that identity and a valid tail. Replay always
performs full validation.

Bufferflow exposes one live `pending` state. Its heartbeat is allowed only while
the underlying process remains alive. Richer phase names require explicit
producer events.

Static renderers do not animate. Source-authored signal states are observations,
not verifier verdicts.

## Consequences

- History deletion, reorder, duplication, splice, and stale append are detected.
- Independent CLI invocations share one ordered workspace history.
- Operation-local transition meaning does not leak across unrelated commands.
- Waiting remains visibly alive without a false percentage or phase.
- Final duration and volume come from measured receipts.
- Version 1 and 2 evidence remains readable.
- No authority is added by event or display identity.
