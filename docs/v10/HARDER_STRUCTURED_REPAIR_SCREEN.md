# Alpha.35 — Harder External-Private Structured Repair Calibration

Status before live execution: `HARDER_STRUCTURED_REPAIR_SCREEN_READY`

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
