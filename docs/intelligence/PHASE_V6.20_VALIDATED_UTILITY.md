# Phase v6.20 — Validated utility & bottleneck action

Full spine from the post-6.19 map: **prove foreign utility**, **gate promotion**, **act on named math** (attention only).

## A. Utility law

| Piece | Behavior |
|-------|----------|
| Holdout freeze | `HOLDOUT_FREEZE_ID` — bump on intentional suite change |
| Foreign suite | `eval-coupling --suite foreign --repo PulseFlow` |
| Promotion gate | `promote_gate.evaluate_promotion` — holdout + foreign + emergent |
| Self-org | Warms ranker on **train** only; promote/calibrate only if gate allows |

```bash
python -m cortex eval-coupling --repo CortexTeach --suite holdout --json
python -m cortex eval-coupling --repo PulseFlow --suite foreign --json
python -m cortex self-org --repo CortexTeach --json
```

## B. Bottleneck action

| Piece | Behavior |
|-------|----------|
| Cheeger → prune preview | `prune` policy preview includes `bottleneck_attention` |
| Percolation → advice | `couple_bottleneck:<id>` on coherence.advice |
| Lyapunov drift | emergence `lyapunov_drift` when ΔV > 0.05 |

Still **dry-run / recommend-only** for prune. Never host mutation.

## C. Fisher skeleton

Ranker SGD uses per-feature `lr / (1+I_ii)` when Fisher examples exist.

## D. CI receipt

```bash
python scripts/ci/release_receipt.py
```

Writes version, holdout freeze id, OCI, holdout/foreign recalls, promotion decision.

## Claim boundary

Telemetry and evaluation policy only. Not consciousness. Not host authority.
Promotion is not “the system is smarter forever” — only that **this gate passed**.
