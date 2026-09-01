# Alpha.35 — Harder External-Private Structured Repair Calibration

Status: `HARDER_STRUCTURED_REPAIR_SCREEN_RECONSTRUCTED — INTERPRETATION_HELD`

## Causal prerequisite

Alpha.35 does not trust a caller's `move_harder` flag. Before freezing any new
call it reconstructs the canonical alpha.34 result, all four case receipts,
their native trajectories, and the aggregate screen. The prior result must be
a live-empirical `4/4` screening ceiling under the identical model identity.

```text
canonical alpha.34 ceiling
  ∧ same model identity
  ∧ live adapter provenance
  ∧ fresh external-private forge
  → alpha.35 screen may freeze
```

Unknown, malformed, different-model, floor, or caller-described prerequisites
cannot open the gate.

## Difficulty transition

The response and evaluation interface remains fixed. Only task semantics move
harder. Four development cases exercise:

1. monotonically fenced lease state across expiry and release;
2. atomic batches with stable observer snapshots;
3. deterministic dependency waves with cycle/unknown rejection;
4. per-key optimistic conflicts with stable MVCC snapshots.

The unchanged implementation must fail each host-private evaluator and a
separately authored host reference repair must pass before the live screen is
eligible. Specifications originate outside Git, and the private bundle remains
in the host credential vault.

## Frozen screen

- Provider/model: runtime selected, but must equal alpha.34 identity.
- Context: task-only control.
- Output: `cortex-edit-intent/1.0`.
- Tools: none.
- Calls: exactly four, no retries.
- Evaluator: unchanged baseline versus isolated candidate under the same
  withheld executable test.

```text
0–1 / 4 → floor; forge easier under a new seal
2 / 4   → calibrated; freeze sham/relevant treatment separately
3–4 / 4 → ceiling; forge harder under a new seal
```

No result in this phase establishes semantic transfer, broad model
improvement, autonomous self-improvement, or mutation authority.

## Observed result

The same `OpenAI / gpt-5.6-sol` identity executed exactly four calls against
implementation commit `2601517b3df1979569ea6b60a2b1dd39d4d6cc6c`.

| Case | Intent compiled | Withheld evaluator |
|---|---:|---:|
| Fenced lease tokens | yes | PASS |
| Atomic observer batch | yes | PASS |
| Stable dependency waves | yes | PASS |
| Per-key MVCC conflicts | yes | FAIL |

The immutable raw score is `3/4`; canonical reconstruction passed. By the
prospective numeric policy this is a ceiling.

## Zero-call instrument audit

The single failure is interpretation-confounded. The public MVCC contract said
that `begin` returns an **opaque snapshot**. The model implemented an opaque
identity handle whose data and per-key versions remain internal to the store.
The private evaluator nevertheless indexed the snapshot as if its internal
`data` mapping were public. That representation assumption was not authorized
by the public contract.

Therefore:

```text
raw score                         3 / 4  (immutable)
structured transport failures    0 / 4
public/private contract mismatch 1 / 4
baseline interpretation          HELD
additional model calls           0
```

The audit does not rescore the failed case or establish that its implementation
is otherwise correct. It establishes only that the evaluator cannot cleanly
attribute this failure to repair reasoning. A new external-private panel must
align every observable assertion with the public contract before more calls.
