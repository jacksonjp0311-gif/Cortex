# Phase v8.6 — Will-Bound Admitted Memory Ledger

## Purpose

v8.5 admitted candidates under will ∧ ΓΞWOS but left “durable write” as flags
on receipts.

v8.6 closes that gap:

```text
trajectory candidates
  → membrane admit (retain=true)
  → immutable AdmittedMemory rows
```

## Law

```text
chat text ↛ admitted memory
invented ↛ commit
will alone ↛ commit
gates closed ↛ commit
admission ≠ host mutation
admission ≠ execution
exactly-once(candidate_id)
```

## Receipt

`AdmittedMemory` (`cortex-admitted-memory/1.0`) binds:

```text
memory_id, candidate_id, candidate_type, summary, support_level
source.{prior_frame, next_frame, transition, outcome, proposal, ...}
will_receipt_hash, membrane_receipt_hash
body_epoch_id, session_id, turn_id
host_mutate_authorized=false
execution_authorized=false
from_chat_text=false
invented=false
```

Table: `admitted_memories` (immutable, unique per repository/candidate).

## Integration

- `consolidate_session(..., will=, will_secret=)` runs membrane then
  `commit_admitted_memories`.
- `cortex admitted status|list|verify`
- Next-session brief includes admitted memories.

## Claim boundary

```text
durable_memory ≠ host source edit
retain ≠ auto-execute
lesson ≠ fluency
```

## Sequence

```text
8.4.3  heartbeat
8.4.4  trajectory
8.4.5  candidates
8.5    will + membrane
8.6    admitted memory ledger
```
