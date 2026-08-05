# Phase v8.7 — Governed Memory Rehydration and Revision

## Purpose

v8.6 closed the downward path into memory.

v8.7 closes the upward path back into cognition:

```text
AdmittedMemory ledger
  → deep lineage verification
  → current-state eligibility
  → task-bound MemoryProjection
  → CortexContextReceipt
  → AI proposal with memory citations
  → witnessed outcome
  → memory-use credit
  → challenge / reaffirm / supersede
```

## Law

```text
Admission establishes historical legitimacy.
Projection establishes current applicability.
Outcome establishes utility.
New evidence may supersede either.

Immutability of history ≠ permanence of applicability.
available ≠ cited ≠ useful.
will cannot erase historically valid counterevidence.
```

## Objects

| Receipt | Role |
|---------|------|
| `MemoryStateReceipt` | append-only state tip: active/contested/superseded/… |
| `MemoryEligibilityReceipt` | noncompensatory \(G_M\) gates |
| `MemoryProjectionReceipt` | bounded task rehydration + continuity seed |
| `MemoryUseReceipt` | projection → citation → outcome |
| `MemoryCreditReceipt` | utility credit (unmeasured…comparison_supported) |
| `MemoryChallengeReceipt` | conflict evidence → contested |
| `MemorySupersessionReceipt` | lineage replacement without deletion |

## CLI

```powershell
python -m cortex memory status --repo R --json
python -m cortex memory project --repo R --task "..." --json
python -m cortex memory inspect --repo R --memory mem_x --json
python -m cortex memory challenge --repo R --memory mem_x --candidate cand_y --json
python -m cortex memory supersede --repo R --old mem_x --new mem_y --authorize-supersede --json
python -m cortex memory verify --repo R --deep --json
```

## Integration

`open_symbiotic_session` and each proposal turn build a `MemoryProjectionReceipt`
into `CortexContextReceipt` predictions and memory episodes.

## Claim boundary

Projection never authorizes host mutation, tool execution, or learning.
Credit never rewrites truth status of an admitted memory.

## Next

v8.8 — cross-instantiation memory trials (matched arms A–E).
