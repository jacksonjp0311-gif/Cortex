# Phase v8.9.1 — Epoch-Converged Interconnect Telemetry

## Purpose

v8.9.1 closes the seams exposed by the v8.9.0 runtime audit. It makes the
interconnect status surface observationally honest without adding a controller,
learning path, routing mechanism, or new geometry.

## Changes

- `cortex interconnect` does not persist a binding-field projection while
  reporting status.
- A measured frame is complete only when its coordinate schema and measurement
  cohort are both present. Unknown is not complete.
- Temporal readiness fails closed for cold, indeterminate, transitional, and
  candidate-only telemetry. A stable peak remains a separate measured gate.
- Frozen ranker state remains visible as an operational bottleneck but does not
  make the constitutional plane false. Host mutation is still forbidden.
- Cached resonance, geometric-echo, rotated-echo, and interlock panels expose
  their declared epoch against the live report epoch. Stale panels are marked
  and remain advisory.
- Self-sensing retains the legacy `residual_r` field while adding
  `regime_deviation_r`, valid residual axes, and excluded unknown coordinates.

## Claim boundary

This phase improves telemetry conformance and failure closure. It does not
establish task utility, prediction accuracy, cognition, consciousness,
subjective sensing, agency, or authority. No report can change routing,
learning, cadence, policy, plasticity, promotion, or host source.

## Remaining evidence

The interlock cohort still requires genuine same-epoch observations, resolved
structured outcomes, and replicated task families. The source-admission trial
remains shadow-only until calibration and the missing replication context are
complete. A frozen ranker requires explicit operator review before any unfreeze.
