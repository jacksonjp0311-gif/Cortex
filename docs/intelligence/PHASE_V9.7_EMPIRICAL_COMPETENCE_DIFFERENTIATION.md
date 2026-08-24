# Cortex v9.7 — Empirical Competence Differentiation

## Purpose

v9.6 proved that a host-registered live model can circulate through Cortex and
produce a canonical, independently witnessed outcome. Its first A-E transfer
trial did not prove competence benefit because every arm passed.

v9.7 makes that experimental ambiguity mechanically visible. It asks:

```text
Does the frozen competence produce a reproducible paired improvement over
matched controls on tasks capable of distinguishing the arms?
```

This is a causal-differentiation surface, not a model selector and not a new
controller.

## Provider-neutral lock

The evaluator accepts only:

- repository and competence identity;
- canonical transfer trial IDs;
- a bounded statistical policy; and
- an experimenter-supplied cohort nonce.

It does not accept a model, model family, provider, endpoint, credential, or
adapter. Unknown policy fields fail closed. The optional live v9.6 scripts also
no longer contain default model names or families; the host must supply those
values explicitly at execution time.

Model identity remains preserved in each underlying invocation receipt as
provenance. It is not copied into a differentiation receipt and is not used in
scoring, threshold selection, or promotion.

## Canonical path

```text
competence
  -> canonical v9.2 A-E trial IDs
  -> independent trial verification
  -> exact trial receipt bindings
  -> frozen evaluator scores
  -> paired case effects
  -> discriminability gates
  -> immutable advisory differentiation receipt
```

A caller cannot supply arm scores or claim that a trial was valid. Cortex
reloads each immutable trial and reconstructs its canonical task-evaluation
score.

## Primary effects

For each case `i`:

```text
continuity_i   = score(D_i) - score(A_i)
distillation_i = score(D_i) - score(B_i)
governance_i   = score(D_i) - score(C_i)
credit_i       = score(E_i) - score(D_i)
```

For every panel Cortex records:

- sample count;
- paired mean;
- sample standard deviation;
- standard error;
- declared-z lower and upper confidence bounds; and
- positive, zero, and negative case counts.

The primary score is the canonical frozen task evaluator's success value.
Composite utility remains recorded as a secondary diagnostic for cost and
quality. This separation prevents small latency or token differences from
appearing as causal competence lift.

## Discriminability

The cohort reports:

- baseline mean;
- competence-arm mean;
- A/D dynamic range;
- ceiling detection;
- floor detection; and
- negative-transfer rate.

An easy task on which baseline already saturates is not evidence against the
competence. It is an uninformative experiment. Likewise, a task that neither
baseline nor competence can solve is a floor, not a transfer result.

## Noncompensatory gates

Promotion requires every declared gate:

```text
canonical trials
AND minimum cases
AND no baseline ceiling
AND no competence floor
AND sufficient dynamic range
AND lower paired bounds above the minimum effect
AND bounded negative-transfer rate
AND compatible epoch/cohort
AND required evidence class
```

No mean score, provider reputation, model identity, coherence value, or utility
aggregate can compensate for a failed gate.

## Evidence class

The evidence boundary is reconstructed independently from the canonical origin
and five arm invocation classes. A transfer outcome may remain unresolved while
all invocations are still correctly classified as live empirical evidence.
Outcome status does not define evidence class, and evidence class does not
define outcome success.

Synthetic cohorts may establish only `STRUCTURAL_DIFFERENTIATION_PASS` under an
explicit structural policy. They cannot satisfy the default live-empirical
gate.

## First live receipt

The preserved v9.6 trial was evaluated without another model call:

- cases: 1;
- baseline mean: 1.0;
- competence mean: 1.0;
- dynamic range: 0.0;
- every paired effect: 0.0;
- result: `DIFFERENTIATION_HELD`.

The failed gates are minimum cases, ceiling, dynamic range, and paired effect.
The invocation evidence itself is live empirical. No distribution or revision
was attempted.

## Legacy handling

One pre-finalization v9.7 draft receipt used the v9.2 aggregate transfer class,
which is outcome-dependent. It remains immutable and inspectable as
`cortex-competence-differentiation/1.0`, is treated as legacy partial, and can
never promote. Current receipts use schema `1.1` and reconstruct evidence class
from the origin plus all five invocation arms.

## Tests

The adversarial suite proves:

- a saturated cohort is detected and held;
- paired structural differentiation can be reconstructed;
- synthetic evidence cannot satisfy an empirical policy;
- model/provider/endpoint policy fields are rejected;
- changing provider-shaped labels does not change effect or gate semantics;
- negative transfer remains visible and blocks promotion;
- immutable receipts independently reconstruct; and
- every authority flag remains false.

## Claim boundary

v9.7 measures within-cohort paired differentiation. It does not establish
universal transfer, model intelligence, consciousness, agency, execution
authority, or distribution authority.

The next empirical requirement is a preregistered live cohort containing tasks
whose baseline does not saturate, followed by replication across fresh model
instances and capability classes.
