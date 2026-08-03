# Phase v8.3.1 — Operator Residual Evidence (planned)

## Goal

Measure the unresolved part of a typed transition without conflating it with
Cortex's self-sensing residual, prediction error, or ranker score. This phase
is a design gate, not an enabled learning path.

For a known operator `T_k` and observed output `y_k`, define a bounded residual
burden only after a receipt exists:

\[
B^R_k = \frac{\mathbb{E}\lVert y_k - T_k(x_k)\rVert}
              {\mathbb{E}\lVert T_k(x_k)\rVert + \epsilon}.
\]

The implementation must disclose the norm, sample cohort, uncertainty, and
epsilon. A scalar is not treated as a covariance or a proof of generalization.

## Required receipt

Every future residual observation must carry the operator id, input and output
types, known output, residual output, invariant projection, uncertainty rule,
validation result, epoch/cohort identity, and an independent outcome witness.
Exact and approximate paths must be distinguishable. An untyped residual is
reported as unmeasured, never silently learned.

## Gates before any update

1. Typed domain/codomain compatibility and current epoch binding.
2. Residual bound plus invariant projection with no silent overwrite.
3. Calibrated uncertainty and exact/approximation disclosure.
4. Comparisons against black-box, operator-only, residual-only, untyped, and
   OSTT variants on the same cohort.
5. Failure injection that localizes domain, invariant, routing, and evidence
   failures.
6. Repeated runs with no host mutation and independently witnessed outcomes.

No routing, cadence, plasticity, promotion, or policy change is authorized by
this phase. A later proposal may open a bounded update only after these gates
are measured and reviewed.
