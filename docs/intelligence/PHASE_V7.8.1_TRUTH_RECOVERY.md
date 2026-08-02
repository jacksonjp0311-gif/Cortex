# Phase v7.8.1 — Truth Recovery

**Tagline:** Observe first, classify against yesterday, and learn only from a trustworthy regime.

## Why this phase exists

v7.8 introduced honest, exactly-once temporal support, but its event-category
participation masks were modeled salience rather than measured state changes.
Those masks produced useful shadow geometry, yet the same frames could enter
baselines and advisory retrieval policy. Separately, self-sensing updated its
EMA baseline before computing the current residual. That let an anomalous
sample pull its own reference toward itself. The Binding Field then accepted
`DRIFT` and `STRESSED` as a verified regime.

The result was a semantic contradiction: local binding could be healthy while
the observer reported drift, but the global label still said verified and the
drifting sample could be learned.

## Truth contract

Every field frame exposes three independent facts:

- `measurement_basis`: how channel activity was produced;
- `policy_eligible`: whether the frame may influence advisory retrieval;
- `baseline_eligible`: whether the frame may teach a temporal or observer baseline.

Activation event masks are `modeled_salience`. They remain visible and
receipted, but are shadow-only and false for both eligibility flags. Direct
snapshots retain the existing default eligibility. A future measured-delta
implementation will use `measured_delta` only after actual pre/post subsystem
state is captured.

## Observer law

For observation `z_t` and prior state `(mu_{t-1}, Sigma_{t-1})`, Cortex computes

`r_t = sqrt((z_t-mu_{t-1})^T (Sigma_{t-1}+lambda I)^-1 (z_t-mu_{t-1}))`

and classifies the sample before any update. Baseline learning is allowed only
when epoch, phase, evidence, measurement provenance, frame stability, and the
prior-regime classification permit it. Once warm, only `NOMINAL` observations
may update the observer. Cold start can still seed from an otherwise eligible
stable or direct observation.

## Binding regimes

`VERIFIED_REGIME` requires a warm bound field, a `NOMINAL` observer, and a
stable `QUIESCENT` or `COHERENT_DIFFERENTIATED` frame.

- a temporal transition becomes `TRANSITION_REGIME`;
- observer drift or stress becomes `DRIFT_REGIME`;
- modeled or otherwise unresolved frames remain `INDETERMINATE`.

These are telemetry labels, not authority states.

## Epoch attribution

Activation finalization reports changed epoch roots. New epoch records also
retain deterministic per-table adaptive digests, allowing a successor to name
which adaptive components changed. Legacy epochs remain valid; their first
comparison reports attribution unavailable instead of inventing detail.

## Next falsifiable phase

v7.9 should replace modeled event masks with measured event fields derived
from actual pre/post state deltas. Until then, modeled salience cannot train a
baseline or affect retrieval.

## Claim boundary

Truth Recovery improves telemetry provenance and update ordering. It grants no
capability, witness, constitutional authority, host mutation, ARIA execution,
or consciousness claim.
