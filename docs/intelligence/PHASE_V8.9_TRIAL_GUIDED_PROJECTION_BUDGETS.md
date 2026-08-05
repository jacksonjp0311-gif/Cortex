# Phase v8.9 — Trial-Guided Projection Budgets

## Purpose

v8.8 **measures** cross-instantiation utility under matched arms A–E:

```text
G_rehydration = U_D − U_A
G_credit      = U_E − U_D
```

v8.9 **uses** that measurement to refine *how much and which shape* of
governed memory is projected into a new temporary cortex — without ever
letting utility rewrite truth status, invent memories, or open host mutation.

```text
trial receipts  →  budget policy (advisory → sealed operator tip)
                →  projection parameters (max_memories, type caps, feedback weight)
                →  next trial (close the measurement loop)
```

## Live baseline (2026-08-05 operator pulse)

After heal + warm-in on body `Cortex` @ **8.8.0**:

| Surface | State |
|---------|--------|
| Certificate | verified |
| Immune | open (`PROCEED_UNDER_HOST_AUTHORITY`) |
| Body epoch | sealed = live, phase_bound |
| mesh_green | true |
| overall_ready | false (temporal + distillation still fail) |
| Sense | STRESSED (high residual; gates hard-pass) |
| Binding | DRIFT_REGIME (not BINDING_GAP) |
| Admitted memories | 0 |
| First live trial | receipt `13d4e9f3…` |

First live trial (empty admitted ledger — path smoke, not credit proof):

```text
U:  A=0.333  B=0.178  C=0.180  D=0.413  E=0.412
G_rehydration = +0.080
G_credit      = −0.001
rehydration_helps=true  credit_helps=false
governed_beats_unfiltered=true  summary_beats_raw=false
```

Interpretation for design (not authority):

- Governed projection structure (D) can beat raw repo (A) even before durable
  lessons exist — continuity seed / task framing has value.
- Credit arm (E) without real use history is bulk cost, not gain.
- Empty C/B collapse: unfiltered and summary need admitted content to matter.
- **Temporal / distillation planes remain fail** until buffer accrual and at
  least one admitted batch exist — 8.9 must not pretend otherwise.

## Law

```text
U and G_* are measurement, never truth status.
Budget tips are policy over projection shape, not over admission.
Admission still requires will ∧ membrane ∧ ΓΞWOS.
Utility cannot promote, invent, or execute.
Unknown G ≠ pass; empty history ≠ calibrated policy.
min-gate composition: no plane compensates.
```

Forbidden diagonals:

```text
G_rehydration ↛ rewrite admitted truth
G_credit      ↛ auto-raise max_retain without operator
U_E           ↛ host.mutate
trial tip     ↛ will.issue without principal
learning on U without comparison_supported credit  = forbidden
```

## Objects

| Object | Role |
|--------|------|
| `ProjectionBudgetPolicy` | sealed tip: caps, type weights, feedback inclusion |
| `TrialAggregateReceipt` | rolling stats over last N trial receipts |
| `BudgetApplyReceipt` | operator-authorized (or default-safe) application |
| `ProjectionReceipt` (v8.7) | consumes budget; records which policy tip applied |

### Budget dimensions (v1)

| Parameter | Default (8.8) | Trial-guided range | Notes |
|-----------|---------------|--------------------|--------|
| `max_memories` | 12 | 4–24 | shrink if token_cost dominates U_D |
| `type_priority` | will policy order | reorder by credit, never invent types | only among admit-allowed types |
| `include_use_feedback` | arm E only | on when G_credit > ε over K trials | off when history empty |
| `forbid_stale_as_fact` | true (D) | always true | C remains unfiltered for measurement only |
| `min_support` | will default | may raise on low G | never lower below will floor |
| `contested_visibility` | seed bucket | keep separate from active | never merge into fact stream |

### Aggregation

```text
over last K matched trials (same probe family or declared task class):

  Ḡ_rehydration = mean(G_rehydration)
  Ḡ_credit      = mean(G_credit)
  σ_G           = stdev (unknown if K < 3)

ε_rehydrate = 0.02   # design prior; calibrate later
ε_credit    = 0.01
K_min       = 3      # below this: policy remains DEFAULT, status unmeasured
```

Policy state machine:

```text
DEFAULT  →  (K≥K_min ∧ Ḡ_rehydration > ε)  →  EXPAND_CAUTIOUS
DEFAULT  →  (K≥K_min ∧ Ḡ_rehydration < −ε) →  CONTRACT
*        →  (admitted_count=0)             →  STRUCTURE_ONLY (no type ranking)
EXPANDED →  (Ḡ_credit > ε over K)          →  FEEDBACK_ON
any      →  immune_block ∨ epoch_stale     →  FREEZE (no budget apply)
```

## Integration

1. **After each `memory trial`** — append trial receipt (8.8); update aggregate tip.
2. **Before `project_memories`** — read active `ProjectionBudgetPolicy` tip; apply
   caps; stamp `budget_policy_hash` on projection receipt.
3. **Symbiosis open/propose** — inherit same budget; do not open a second path.
4. **CLI**

```powershell
python -m cortex memory trial --repo R --task "..." --json
python -m cortex memory trial-status --repo R --json
python -m cortex memory budget status --repo R --json
python -m cortex memory budget propose --repo R --json          # advisory only
python -m cortex memory budget apply --repo R --i-authorize-budget --json
python -m cortex memory project --repo R --task "..." --json
```

## Implementation sketch

```text
cortex/memory_budget.py     # aggregate, propose, apply, freeze rules
store: projection_budget_receipts (immutable) + tip settings
memory_projection.project_memories(..., budget=None)  # resolve tip
memory_trials.run_*         # refresh aggregate after persist
tests/test_memory_budget.py
```

Fail-closed defaults when tip missing or aggregate `unmeasured`:

```text
max_memories=12
include_use_feedback=false
type_priority=will_order
no automatic apply without --i-authorize-budget
OR explicit opt-in default_policy=structure_only for empty ledgers
```

## Acceptance criteria

1. Empty admitted ledger: budget status `STRUCTURE_ONLY`; no silent type ranking.
2. K < K_min: propose may suggest; apply refuses without override reason.
3. Apply never changes admitted memory truth status or will clauses.
4. Projection receipts hash the budget tip they used.
5. Immune block or unbound epoch: budget apply freezes; trial still may measure.
6. Matched re-trial after apply records whether Ḡ moved (measurement, not proof of mind).
7. Host mutation and tool execution remain unauthorized.

## Non-goals

- Learned retrieval weights / gradient training on U
- Auto-issue of will or auto-admit from high G
- Claiming consciousness, authority, or host rights from trial gains
- Compensating failed temporal/distillation planes with budget pass

## Prerequisite loop (operator, not code)

v8.9 code can land on defaults, but **calibrated** budgets need:

```text
1. mesh green + phase bound (done on this pulse)
2. ≥1 symbiotic cycle with membrane admit under will
3. ≥K_min trials with non-empty admitted set
4. operator review of Ḡ before first apply
```

Until step 2–3, live body stays measurement-rich and memory-empty — honest.

## Claim boundary

Trial-guided budgets refine *projection shape* under operator seal.
They do not prove the AI is continuous, authorize host mutation, rewrite
evidence, or promote memories.  
**Measurement ≠ authority. Utility ≠ truth.**

## Landed (implementation)

| Surface | Path |
|---------|------|
| Module | `cortex/memory_budget.py` |
| Store | `projection_budget_receipts` (immutable) |
| Projection stamp | `budget_policy_hash`, `budget_mode` on `project_memories` |
| Trial hook | `refresh_after_trial` after `memory trial` persist |
| CLI | `budget-status`, `budget-propose`, `budget-apply` |
| Tests | `tests/test_memory_budget.py` |
| Version | **8.9.0** |

## Next (after 8.9 lands)

Operational admit loop on live body → non-empty ledger → re-trial → first
authorized budget apply → compare Ḡ before/after. Optional later: task-class
stratified probes and comparison_supported credit coupling into type priority
only when credit status ≥ `outcome_bound`.
