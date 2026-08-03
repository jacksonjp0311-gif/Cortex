# Phase v8.3.2 — Typed Activation Observations

## Purpose

The existing activation transaction already produces a measured event field
with a normalized vector, event hash, before/after state hashes, and local
measurement basis. v8.3.2 captures that output as a typed OSTT observation:

`TaskRequest → ActivationReceipt`

The adapter is deliberately an **observed** receipt, not a measured residual.
It records what happened without inventing what a known operator should have
produced.

## Receipt contents

Each activation observation includes:

- `cortex-measured-event-field/1.1` schema and event/receipt hash;
- normalized measured output vector;
- body epoch and measurement cohort identity;
- host-immutability and advisory-only assertions;
- explicit `known_output_declared=false`;
- bounded history in `ostt_residual_history:<repo>` for later cohort analysis.

Inspect the latest report with:

```powershell
python -m cortex ostt residual --repo CortexTeach --json
```

## Why the residual gate remains closed

Residual burden requires both a known output `T_k(x_k)` and an observed output
`y_k`. v8.3.2 supplies `y_k` only. The `known_output_declared` gate therefore
remains false, and `policy_effect`, `update_authorized`, routing, cadence, and
learning remain unchanged.

## Next gate

Declare the known activation operator output from an independently specified
contract, then compare it against the stored observed cohort. Require current
epoch identity, calibrated uncertainty, invariant projections, independent
witnesses, and the full comparison matrix before any review of residual burden.

This phase is telemetry and provenance, not consciousness, agency, or proof of
general transformation performance.
