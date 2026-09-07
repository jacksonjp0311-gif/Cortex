# GSI-II.1 — cumulative loop closure

September 7, 2026. Product remains `10.0.0a39`. Zero provider calls.
Public HEAD at implementation start: `3863ad5490e5a13e2a721e2aee14472fcead25a1`.
Exact-head CI for that commit was still in progress at documentation time and
must not be treated as passed from this file.

GSI-II added the coordinator. This pass closes the existing loop. It does not
replace source-improvement v1, tournament promotion, or GSO-IIb.

## Closed loop

```
G0 -> measured deficiency -> G1 candidate
   -> frozen development + withheld measurement
   -> verified result
   -> authenticated canary/apply/rollback
   -> post-promotion remeasurement
   -> G1 state
   -> next measured deficiency -> G2 candidate
   -> fresh withheld partition
   -> verified result
   -> generation ledger
```

with `AuthorityLeakage = 0` and
`cumulative_self_improvement_established = false`.

## Laws implemented

- Development gain is not withheld gain. Both `delta_dev` and `delta_holdout`
  are recorded. Strong improvement requires both deltas to meet frozen
  epsilons; withheld degradation beyond frozen tolerance is not improvement.
- `ATTESTED -> PASS`, `PARTIALLY_ATTESTED -> HELD`, `INVALID -> FAIL`.
  UNKNOWN never becomes PASS.
- Workload correctness is not constitutional validity. Those gates are
  separate and noncompensatory.
- Repository revision change is not automatic forgetting. Constraints persist
  by subject/dependency/instrument identity. Changed identity is
  `REVALIDATION_REQUIRED`.
- Constraint awareness is not constraint enforcement. Machine-checkable
  predicates can reject a candidate before evaluation.
- Candidate worktree success is not promoted-state success. Promotion composes
  existing isolated canary, apply, and rollback, then remeasures the live tree.
- One positive generation is not cumulative self-improvement.
- Two synthetic adjacent generations may verify mechanics only.

## Deterministic result

A two-target ranking fixture can produce G0 -> G1 -> G2 with independently
measured withheld partitions, post-promotion remeasurement, and a reconstructable
cumulative delta from canonical generation records.

Flags:

- `cumulative_generation_mechanics_verified = true` in that fixture
- `cumulative_self_improvement_established = false`

No live provider trial. Storm generation is not invoked. Tournament promotion
schema `cortex-policy-promotion/1.0` is unchanged; GSI promotion is a composing
adapter.

## Claim ceiling

Two-generation governed self-improvement mechanics verified in deterministic
controls.

Not claimed: cumulative real-world self-improvement, recursive
self-improvement, intelligence acceleration, general self-improvement,
production-safe autonomous mutation, superintelligence, or consciousness.

## Remaining unknowns

OS isolation, process-tree completeness, and full environment applicability
remain UNKNOWN / UNENFORCED / DECLARATIVE_ONLY. Live provider GSI-III remains
unauthorized.
