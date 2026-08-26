# Cortex v9.8.5 — Latent-Cause Discrimination Forge

## Purpose

Test whether nonzero residual causal ambiguity and exact downstream evidence can
create informative development tasks after additive length and state coupling
largely saturated.

## Architecture

The existing discriminative forge now emits four latent-cause families:

- a hidden faulty module inferred from end-to-end checksums;
- a hidden recurrence patch inferred from training traces and applied to a fresh input;
- a hidden eligibility policy inferred from historical state panels;
- a hidden dependency edge inferred from weighted build schedules.

Every candidate is locally plausible. The generator computes the evidence
signature for every hypothesis and rejects observational collisions. Each case
binds:

- hypothesis count;
- `H(H|L)` under the declared uniform local candidate set;
- posterior hypothesis count;
- resolved information;
- one hash per hypothesis evidence signature;
- exact public evaluator and answer hash.

All 128 generated development cases had unique case identities, unique evidence
signatures, posterior count one, and prior entropy between 2.807 and 4 bits.

## Resumable commissioning

The canonical runner now reloads previously completed observations from the
immutable circulation ledger and re-verifies each one against its exact case.
It also resolves an existing immutable adapter registration instead of trying to
reclassify the same implementation/profile under a new principal.

Bounded adapter failure is reported separately and never becomes success or a
canonical outcome. One unsealed level-4 repair attempt exceeded 180 seconds. A
later run under the unchanged budget succeeded. This establishes runtime
variance, not a canonical timeout rate; the sealed artifact reports zero
execution failures and does not include the unsealed attempt in calibration.

## Live development result

The completed panel contains 48 unique canonical observations: 20 independently
reconstructed from the interrupted run and 28 newly executed.

| Family | Levels | Result |
|---|---|---|
| Bug localization | 2, 3, 4 | 4/4 at every level; ceiling |
| Multi-step repair | 2, 3, 4 | 4/4, 4/4, 7/8; ceiling |
| Stale-state detection | 2, 3 | 4/4, then 5/8; calibrated |
| Architecture reconstruction | 2, then 1 | 0/4 and 0/4; floor |

Stale-state level 3 has `p=.625` and Rasch-style item information
`I=.237654321`. The commissioning receipt selected only that family. Overall
status remains `CALIBRATION_HELD`; confirmatory eligibility is false.

## Emerging geometry

Let `H` be causal hypotheses, `L` local evidence, `O` downstream observations,
and `C` measured inference cost:

```text
A_local    = H(H | L)
R_evidence = I(H; O | L)
η_evidence = R_evidence / C
```

v9.8.5 measures the first two structural quantities. It does not yet calibrate
`C` or `η_evidence`. The empirical panel shows that equal hypothesis entropy can
produce a ceiling, an informative middle, or a floor depending on evidence
factorization, required transfer, and decoding structure. A scalar difficulty
ladder is therefore an incomplete task ontology.

## Claim boundary

This release verifies a latent-cause development forge and one canonical
frontier calibration panel. It does not establish competence lift, causal model
improvement, universal task difficulty, confirmatory evidence, cognition,
consciousness, agency, or authority. Hidden reasoning and raw provider envelopes
were not persisted. Host mutation, execution, memory admission, policy effect,
and update authority remained false.

## Next bounded phase

The next phase should be **v9.8.6 — Cost-Calibrated Evidence Entanglement**.
It should preserve repeated latency/token observations, distinguish factorized
from entangled evidence structures, estimate information resolved per bounded
cost, and repair the architecture family’s floor before any held-out trial is
sealed. It must not tune on confirmatory outcomes or convert timeout metadata
into task success.
