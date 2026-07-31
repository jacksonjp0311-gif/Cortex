# Phase v7.1.2 — Claim Receipts

**Tagline:** Green gate is not the claim. The stamp is the claim.

## What

When promotion is evaluated with a bound store+repo, Cortex issues a **claim receipt**:

| Field | Meaning |
|-------|---------|
| `claim_id` | `claim_` + hash prefix |
| `body_epoch_id` | Epoch the claim is valid for |
| `gate_bits` | Live-eligible geometry bits |
| `axis_truth` | Per-axis truth_source + gate_eligible |
| `phase_binding` | BOUND status panel |
| `utility.*_digest` | Holdout / foreign / witness digests |
| `receipt_hash` | SHA256 of identity material (no wall-clock in ID) |

Denied promotes still stamp a `status: denied` receipt for audit.

## CLI

```bash
python -m cortex claim --repo CortexTeach --json
python -m cortex claim verify --repo CortexTeach --json
python -m cortex claim latest --repo CortexTeach --json
```

## Verify

`verify_claim_receipt` recomputes the hash and checks the body epoch is still present+verified and matches the receipt. Drift after issue → verify fails (expected).

## Claim boundary

> Claim receipts are falsifiable stamps of gate decisions under measured geometry. They do not authorize host mutation or establish consciousness.
