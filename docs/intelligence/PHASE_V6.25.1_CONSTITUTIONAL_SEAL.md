# Phase v6.25.1 — Constitutional Seal

**Tagline:** Every adaptive change must cross an explicit boundary, carry authority, commit atomically, preserve its ancestry, and prove it can be reversed.

## Planes

```text
E — evidence
A — adaptation
C — constitutional control
W — independent witness
```

Forbidden: `A ↛ E`, `A ↛ authorize C`, `A ↛ inspect W` before evaluation.

## Core modules

| Module | Role |
|--------|------|
| `capabilities.py` | Immutable ExecutionCapability; operation registry; fail-closed |
| `state_transition.py` | Atomic transitions + controller_audit_events |
| `influence_policy.py` | Runtime quarantine exclusion |
| `activation.py` | Controller-first; sterile baseline early return |
| `ranker/model.py` | Training event ledger + deterministic rebuild |
| `unlearning.py` | Full SQLite backup snapshot + rollback |
| `witness.py` | Commit-before-reveal chronology |

## Claim boundary

> Cortex v6.25.1 enforces capability-scoped adaptive writes, sterile evidence-only activation, runtime quarantine exclusion, atomic repair transactions, deterministic ranker reconstruction, exact database recovery, and commit-before-reveal witness verification. These mechanisms provide bounded computational continuity; they do not establish biological life, consciousness, autonomous host authority, or perfect adversarial security.
