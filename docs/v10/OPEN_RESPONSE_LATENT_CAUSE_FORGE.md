# Cortex v10.0.0-alpha.20 — Open-Response Latent-Cause Forge

Alpha.20 replaces the saturated multiple-choice task geometry with generated
causal diagnosis. It performs no model invocation.

## Why the geometry changed

The selected frontier model scored 4/4 at both available choice levels. More
wording complexity did not create uncertainty because every answer remained
visible. Alpha.20 therefore changes the measured operation from recognition to
causal production.

## Public task contract

Each case exposes an event record containing causal events and explicit
distractors. The model must return exactly one JSON object with:

- a public causal explanation;
- the smallest repair principle;
- exact ordered evidence identifiers;
- an explicit uncertainty state.

No answer choices, required clauses, reference response, or success flag appear
in the public corpus.

## Private atomic evaluator

Each case has an immutable private contract containing:

- required cause clauses, expressed as bounded alternative phrase groups;
- required repair clauses;
- the exact ordered causal evidence IDs;
- forbidden unsupported repair terms;
- the allowed response schema;
- a reference response used only to verify the evaluator itself.

For response \(r\), the development gate is:

\[
\Theta_{open}(r)=
C(r)\wedge R(r)\wedge E(r)\wedge \neg F(r)\wedge U(r).
\]

Here \(C\) and \(R\) are required cause and repair coverage, \(E\) is exact
evidence binding, \(F\) is a forbidden unsupported claim, and \(U\) is a valid
uncertainty state. Missing or malformed structure is UNKNOWN or FAIL; neither
can become PASS through fluency.

## Secret boundary

The public manifest contains salted per-case contract commitments and one
private-key commitment. Private contracts and their random seed are stored in
the operating-system credential vault under a corpus-specific identity. They
are absent from Git, Cortex evidence, trajectories, logs, and the benchmark
artifact.

This closes the alpha.18/alpha.19 continuity wound: later screens can retrieve
the exact private evaluator rather than silently generating a replacement key.

## Corpus

The forge contains sixteen development cases across four causal depths:

1. stale cache after committed mutation;
2. lower-layer stale repopulation;
3. pre-commit invalidation race;
4. stale source snapshot contaminating a derived index.

Four variants per level provide a bounded sequential screen. Level three is
the initial candidate. A future live run is separately authorized and capped
at four task-only calls.

## Claim boundary

`OPEN_RESPONSE_LATENT_FORGE_READY` means the public/private seal, evaluator,
canonical alpha.19 prerequisite, and zero-call plan verify. It does not mean
the task is calibrated or that Cortex improves a model. Semantic treatment
must remain closed until baseline performance enters a non-floor/non-ceiling
band.

All authority flags remain false.
