# Cortex v9.8.4 — Coupled Dependency Task Geometry

## Purpose

Test whether genuine state dependence, rather than a longer list of independent
subproblems, creates an informative development calibration for a runtime-selected
frontier model.

## Change

Four families that saturated in v9.8.3 now use coupled mechanisms:

- state-dependent invariant violation for bug localization;
- recurrent branch coupling for multi-step repair;
- recursive lineage eligibility for stale-state detection;
- checksum-coupled topological scheduling for architecture reconstruction.

API migration remains the previously calibrated control and was not rerun.
Every case has an exact public evaluator, deterministic corpus identity, declared
dependency depth, no model identity in its ontology, and development-only status.
The runner binds `coupled` into adapter provenance so these observations cannot be
silently mixed with the additive cohort.

## Empirical result

The run used 52 fresh canonical `live_empirical` model circulations selected at
runtime. Results were:

| Family | Level 2 | Level 3 | Level 4 | Decision |
|---|---:|---:|---:|---|
| Bug localization | 4/4 | 4/4 | 4/4 | ceiling |
| Multi-step repair | 4/4 | 4/4 | 7/8 | ceiling |
| Stale-state detection | 4/4 | 4/4 | 4/4 | ceiling |
| Architecture reconstruction | 4/4 | 4/4 | 4/4 | ceiling |

No family entered the declared `.30 ≤ p ≤ .70` window. The canonical result is
`CALIBRATION_HELD`; `selected` is empty and confirmatory eligibility is false.

## Emergent measurement law

Dependency depth is not an adequate difficulty coordinate by itself. These tasks
were computationally coupled, but their relevant cause often remained locally
obvious. Let `H` denote plausible causes, `L` locally visible evidence, and `O`
downstream observations:

```text
A_local = H(H | L)
R_evidence = I(H; O | L) = H(H | L) - H(H | L,O)
```

An informative causal task needs nonzero local ambiguity and observations that
reduce it. When `H(H | L)=0`, adding more deterministic transitions increases
work without increasing causal discrimination.

This is an inference from the observed ceiling pattern, not a general theorem
about model capability.

## Claim boundary

v9.8.4 demonstrates a model-neutral coupled-task forge and one canonically
measured development run. It does not establish competence lift, general model
ability, confirmatory evidence, cognition, consciousness, agency, or authority.
No hidden reasoning was requested or persisted. Host mutation, execution, memory
admission, policy effect, and update authority remained false.

## Next phase

The next bounded phase should be **v9.8.5 — Latent-Cause Discrimination Forge**.
It should create matched hypotheses with indistinguishable local evidence,
release bounded downstream observations, quantify residual hypothesis entropy,
and retain cases only when the public evidence—not answer leakage—produces a
non-ceiling exact-evaluator task. It must remain development-only until a new
held-out seal is frozen.
