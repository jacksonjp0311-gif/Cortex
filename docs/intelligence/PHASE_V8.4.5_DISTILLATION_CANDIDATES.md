# Phase v8.4.5 — Distillation Candidate Extraction

## Purpose

v8.4.4 verified the pulse wave between turns.

v8.4.5 extracts durable **lessons as candidates** from that wave:

```text
(F_k, T_k, O_k, F_{k+1}) → D_k
```

Candidates are typed proposals for what *might* later be retained. They are
**not** durable memory and do **not** authorize learning.

## Why this comes before authenticated will

The future unified membrane must not distill arbitrary chat text. It should
distill **measured change linked to an outcome**. Authenticated principal intent
(v8.5.0) may later prioritize which candidates matter; it must never invent
facts that the trajectory did not measure.

## Candidate types

```text
verified_fact
successful_procedure
failed_hypothesis
counterevidence
useful_route
persistent_constraint
regime_warning
unresolved_ambiguity
```

## Extraction rules (summary)

1. Trajectory links must verify:
   `T.prior = F_k.hash` and `T.next = F_{k+1}.hash`.
2. Regime / constraint candidates may fire from transition class and validity
   planes without full causal credit.
3. Outcome-linked types (`successful_procedure`, `verified_fact`,
   `failed_hypothesis`, `counterevidence`, `useful_route`) require
   `causal_status ∈ {outcome_bound, comparison_supported}`.
4. Every candidate sets `retain=false`, `memory_write_authorized=false`,
   `durable_write_authorized=false`, `policy_effect=false`.

## Receipt

`DistillationCandidateBatch` (`cortex-distillation-candidates/1.0`) includes:

```text
extraction_status   # extracted | blocked | empty
trajectory_verified
candidates[]
by_type
support_ceiling
source.{prior_frame_hash, next_frame_hash, transition_hash, outcome_hash, ...}
```

Ledger table: `distillation_candidate_batches` (immutable, exactly-once per
session/turn).

## Integration

- Built on each multi-turn symbiotic propose when a transition exists.
- Flattened into consolidation *input* when callers do not supply candidates;
  ΓΞWOS still blocks retention until gates open.
- Next-session brief surfaces candidates and support ceiling for the model.

## Claim boundary

```text
candidate ≠ memory
support ≠ causality proof
extraction ≠ authorization
```

## Next

v8.5.0 — authenticated principal will / direction.  
v8.5.1 — will-bound unified distillation membrane.
