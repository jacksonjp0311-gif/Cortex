# Phase v8.3.1 — Operator Residual Evidence (shadow)

## Goal

Measure the unresolved part of a typed transition without conflating it with
Cortex's self-sensing residual, prediction error, or ranker score. v8.3.1 now
implements the receipt and gate machinery, but remains a shadow-only review
path: no residual is learned and no policy is changed.

For a known operator `T_k` and observed output `y_k`, the receipt computes a
bounded residual burden:

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
reported as unmeasured, never silently learned. Use:

```powershell
python -m cortex ostt residual --repo CortexTeach --json
```

Before an activation observation, the live repository reports
`status=unmeasured`. After activation v8.3.2 may report `status=observed_shadow`:
the measured output exists and is typed, but the known operator output is still
undeclared. Both states are deliberate safe results, not missing fallbacks.

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
are measured and reviewed. The implementation exposes `policy_effect=false`,
`advisory_only=true`, and `update_authorized=false` in every report.

## Verification

```powershell
python -m pytest tests/test_ostt.py tests/test_ostt_residuals.py -q
python benchmarks/ostt_residual_benchmark.py
```

The benchmark covers exact operator output, bounded residual perturbation,
untyped output refusal, invariant-failure injection, and comparison-mode
disclosure. It is deterministic and synthetic; it validates the receipt
machinery, not general transformation performance.
