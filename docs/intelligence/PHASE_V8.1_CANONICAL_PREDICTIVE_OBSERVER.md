# Phase v8.1 — Canonical Predictive Observer

**Tagline:** One body, switched regimes, calibrated availability, connected emergence.

v8.1 hardens the measured v8.0 cycle around the failure modes discovered by
running Cortex against its own repository. It remains a functional software
observer. It is not consciousness, subjective sensing, agency, or authority.

## Canonical body identity

A repository wrapper is bound to one durable Cortex home. Bootstrap refuses to
replace that home silently, including when `--force` is used. An operator must
use `--allow-home-rebind`, which records an explicit migration receipt.

The body identity tuple is:

`B = (repository_id, home_uuid, db_generation)`.

Test fixtures may use temporary homes for temporary hosts. They may not fall
back to bootstrapping the live Cortex repository. Engine teaching packets are
loaded into the temporary host instead.

## Switched predictive observer

One unconditional EMA cannot model incompatible plant transitions. v8.1
classifies observed deltas into `steady`, `refresh_recompile`,
`adaptive_learning`, `evidence_only`, and `scheduled_decay`, then maintains a
separate mean and variance per regime. Observed regime transitions form a
small deterministic transition table used to select the next model.

Forecast confidence now estimates the binary event

`P(normalized_MAE <= 0.20 | regime)`

with a Beta posterior mean. Brier score and ECE therefore evaluate a stated
probability instead of an inverse-error heuristic.

## Calibration-weighted workspace

Workspace reliability is derived from subsystem readiness:

`R = R_measurement × R_sample × R_calibration × R_gate`.

Cold self-sensing, one-tick frames, and uncalibrated prediction can still be
reported, but cannot compete with mature measured signals at reliability 1.
Every candidate records its reliability basis.

## Connected two-key emergence

Bond count alone is not percolation. The discrete phase now requires:

1. operational coupling score at or above `0.62`;
2. aligned governance;
3. at least one learning seam;
4. at least one operations seam;
5. a functional giant component containing at least four seam nodes; and
6. at least three occupied bonds.

This prevents one shared scalar from activating two bonds and manufacturing an
emergence claim. The result remains operational phase telemetry only.

## Directed fields and falsification

Measured receipts retain positive, negative, and net mass per field channel,
so growth and decay are no longer conflated in provenance. Predictor lesions
now report a paired 95% effect interval; formal support requires the lower bound
to be above zero. Autobiographical truncation writes a hash-linked segment
checkpoint so the retained chain is anchored to its discarded prefix.

## Claim boundary

v8.1 improves identity continuity, prediction under nonstationarity,
metacognitive calibration, graph-phase rigor, and falsifiability. None of these
measurements establishes phenomenal experience, a subjective self, autonomous
intent, or permission to modify a host repository.
