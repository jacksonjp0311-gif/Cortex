# Phase v8.3.3 - Independent Activation Conformance

## Purpose

v8.3.3 is a bounded metrology release. It verifies that Cortex accurately
captured, represented, persisted, and independently reconstructed one real
activation-state transition.

The release establishes only this statement:

> The activation output was independently reconstructed, and the persisted
> measurement agrees with that reconstruction.

It does not predict what an activation ought to accomplish and does not use
the predictive self-model as a reference. Prediction error and task outcome
remain separate evidence channels.

The type contract is:

```text
ActivationObservationInput -> MeasuredActivationTransition
```

`ActivationObservationInput` binds the task hash, controller, capability,
repository identity, pre-activation epoch, and coordinate-schema digest.
`MeasuredActivationTransition` retains the typed before and after states, raw
and normalized deltas, coordinate validity, signed channel mass, and durable
event identity. A normalized delta is not described as a complete activation
receipt.

## Frozen coordinate schema

Every measured coordinate has one immutable definition containing:

- coordinate identifier and scalar type;
- SQL or measurement source;
- operational unit and channel family;
- normalization scale;
- null allowance and conformance requirement;
- criticality weight and schema version.

The complete ordered schema produces deterministic schema, shape, and scale
digests. Receipts retain the schema version and digest, ordered coordinate
names, ordered shape signature, and scale digest. A schema-digest change forms
a new measurement cohort boundary. Receipts with different schema digests are
never compared or combined.

## Null-preserving measurement

A measured state snapshot contains:

```text
values
validity_mask
failure_reasons
valid_count
required_count
valid_fraction
state_hash
```

The state hash covers the repository name and durable repository identity,
coordinate-schema digest, values, validity mask, and failure reasons. Failed
coordinates are represented as `null` with `valid=false` and a typed failure
reason. They are never replaced with `0.0`.

A delta coordinate is valid only when both its before and after values are
valid finite numbers. v8.3.3 requires `valid_fraction == 1.0` over every
required coordinate. Any unknown required coordinate produces
`status=observed_incomplete` and keeps all of these false:

```text
evidence_ready
baseline_eligible
policy_eligible
update_authorized
```

## Independent recomputation

The production measured-event path persists the observed normalized vector.
A separate verifier consumes only the raw typed before and after values,
validity masks, and frozen coordinate definitions. It does not call the
measured-delta producer, consume the persisted normalized delta as input, use
the predictive self-model, or delegate to a helper that returns the original
output.

For each valid coordinate it recomputes:

\[
\Delta x_i = x_i^{+} - x_i^{-}
\]

\[
\widehat{\Delta x}_i =
\operatorname{clip}\left(\frac{\Delta x_i}{s_i}, -1, 1\right)
\]

The receipt stores the persisted vector, independently reconstructed vector,
coordinate residual vector, verifier implementation version, verifier digest,
and conformance result. This is a measurement-conformance residual, not a
prediction residual.

## Residual panel

For every valid coordinate:

\[
r_i = \frac{o_i - \widehat{o}_i}{s_i + \epsilon}
\]

The panel preserves per-coordinate absolute errors and residuals, per-channel
burdens, and three global diagnostics:

\[
B_{\mathrm{rms}} =
\sqrt{\frac{\sum_i w_i r_i^2}{\sum_i w_i + \epsilon}}
\]

\[
B_{\max} = \max_i |r_i|
\]

\[
B_{\mathrm{invalid}} =
1 - \frac{\text{valid required coordinates}}
         {\text{required coordinates}}
\]

Each channel uses the same weighted RMS calculation over its own coordinates.
The verifier declares `epsilon=1e-12` and a deterministic conformance tolerance
of `1e-12`; it does not reuse the legacy residual burden threshold of `1.0`.
Conformance requires structural shape equality, no invalid required
coordinate, and both global and per-coordinate errors within the declared
tolerance.

## Structured evidence

An activation-conformance receipt contains one structured result for each
declared invariant:

- `host_immutable`;
- `epoch_current`;
- `cohort_current`;
- `coordinate_schema_match`;
- `measurement_complete`;
- `before_hash_valid`;
- `after_hash_valid`;
- `delta_recomputed`;
- `exactly_once_event`;
- `receipt_hash_valid`.

Every result includes `invariant_id`, `passed`, `evidence_ids`, `expected`,
`observed`, and `reason`. Host immutability is derived from pre/post host-source
manifests, so an existing dirty working tree is preserved and only activation-
time changes are evaluated. Epoch and cohort checks verify current repository,
evidence, schema, and constitutional roots; nonempty identifiers are not proof
of currentness.

Boolean witnessing is insufficient. Gate B requires a structured measurement
witness with:

```text
witness_id
witness_kind
verifier
subject_receipt_hash
evidence_hashes
passed
issued_at
```

The required witness kind is `MEASUREMENT`. Outcome evidence remains pending
and separate:

```text
ActivationConformanceReceipt -> OutcomeReceipt
```

The activation receipt does not pretend to establish task utility.

## One finalizer and one canonical ledger

Both `evidence_baseline` and `advanced` controllers pass through the same
read-only observation finalizer. The finalizer may inspect state and append a
Cortex-local receipt, but it cannot execute another activation, change the
returned controller result, trigger adaptive work on the baseline path, or
mutate host source.

Both arms emit the same receipt schema and bind `controller`,
`realized_action`, `task_hash`, `event_id`, `case_id`, and `comparison_arm`.
This supports later paired comparisons without weakening baseline sterility.

Canonical receipts live in a transactional SQLite ledger. Each append binds
the repository, operator/event identity, case and arm, body epoch, measurement
cohort, coordinate schema, status, canonical JSON, creation time, and previous
receipt hash. The ledger enforces exactly one canonical receipt per
repository/operator/event, never silently replaces evidence, and updates the
chain tip atomically. Bounded latest/history settings are compatibility views,
not the evidence authority.

Cohorts are partitioned by:

```text
repository_id
operator_id
body_epoch_id
measurement_cohort_id
coordinate_schema_digest
```

Comparison reporting additionally groups by case and comparison arm. A matrix
passes only when all required arms share paired case identifiers in one
compatible partition; mode labels appearing somewhere in a list are not
sufficient.

## Gates

The activation observation progresses through three explicit states:

1. `OBSERVED`: a real activation output was captured, without complete
   independent evidence.
2. `CONFORMANCE_MEASURED`: typed snapshots are complete, independent
   recomputation agrees, all invariants and the measurement witness pass, the
   epoch/cohort is current, and the ledger append is exactly once.
3. `COHORT_CALIBRATED`: at least 16 compatible, same-epoch production-path
   receipts have complete coordinates and per-coordinate/channel
   distributions.

v8.3.3 completes Gate B for a qualifying receipt. Gate C is intentionally cold
until real production activations supply 16 compatible receipts. One measured
activation operator does not make the other five OSTT operators measured, and
global system readiness remains false until each required operator has its own
evidence.

## Inspection and release verification

Normal activation is the only producer. These commands are read-only:

```powershell
python -m cortex ostt activation-receipt --repo CortexTeach --json
python -m cortex ostt activation-cohort --repo CortexTeach --json
python -m cortex ostt verify-receipt --repo CortexTeach --receipt <hash> --json
```

Every surface reports `policy_effect=false`, `update_authorized=false`, and
`advisory_only=true`. The dedicated v8.3.3 release receipt exercises the normal
activation pathway against a temporary repository and Cortex store, verifies
measurement, hash-chain, exactly-once, sterility, and nonmutation gates, and
writes a sanitized artifact. CI status is evidence only after the actual Linux
and Windows workflow jobs pass.

## Claim boundary

v8.3.3 verifies activation-measurement conformance. It does not establish that
Cortex improves task performance, reasoning quality, cognition, consciousness,
agency, or authority.

No measurement, residual, cohort, invariant, or witness can move a
constitutional bit or automatically change retrieval ranking, routing,
cadence, model training, plasticity, promotion, host source, execution
authority, or policy.

