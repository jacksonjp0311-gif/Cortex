# Cortex v9.8 — Preregistered Causal Competence Trial

## Purpose

v9.8 responds directly to the August 24, 2026 independent engineering audit.
The audit verified Cortex's model-circulation, provenance, governance, routing,
and benchmark mechanisms, but found no positive causal competence effect. The
first live A–E cohort saturated at success in every arm (`n=1`, dynamic range
`0`, every measured gain `0`). v9.8 preserves that null and strengthens the
next experiment instead of adding another controller.

## Claim boundary

This release verifies evidence machinery. It does **not** establish that Cortex
improves models, that competence transfers generally, or that a distilled
abstraction is semantically complete.

```text
lineage validity ≠ semantic entailment
structural pass ≠ empirical effect
one observation ≠ estimable variance
```

Execution, host mutation, memory admission, distribution, and policy effect
remain unauthorized.

## Semantic identity repair

Legacy `cortex-competence/1.0` identity selected an explicit ID-like field from
a structured capability/outcome and could therefore ignore changed operational
siblings. New `cortex-competence/1.2` candidates bind both the identifier and
all non-prose operational material. Description, summary, rationale, prose, and
model identity remain outside semantic identity.

Legacy immutable receipts keep their original hash law. They are not rewritten
and continue to verify through schema dispatch.

## Independent distillation witness

`cortex/distillation_witness.py` creates an immutable claim panel from a
canonical competence and its verified origin circulation. Its deterministic
verifier reads only canonical public evaluation, outcome, and witness receipts.
It does not trust caller booleans, model self-evaluation, hidden reasoning, or
semantic similarity.

Each atomic claim is:

- `SUPPORTED` when exact normalized material is reconstructible from canonical
  public evidence;
- `UNKNOWN` when that support cannot be reconstructed;
- reserved for `CONTRADICTED` when a future verifier can establish an explicit
  canonical contradiction.

This verifier is intentionally narrow. It reports prerequisite completeness
and counterevidence completeness as `UNKNOWN`; exact support is not proof that
all omitted conditions were discovered. Generalization is never authorized by
this receipt.

## Immutable causal preregistration

Before bound trial execution, Cortex can freeze:

- task corpus and evaluation-contract hashes;
- competence and distillation-witness identity;
- A–E arms plus declared sham, irrelevant, corrupted, shuffled, and
  omitted-prerequisite controls;
- planned matched-case count;
- randomization-seed commitment;
- minimum interesting effects;
- stopping and exclusion rules;
- negative-transfer threshold;
- task-family and capability-class strata;
- exact test and Holm multiplicity policy.

Model IDs, provider families, adapter IDs, and endpoints are rejected from the
causal policy. They remain provenance, never scoring inputs.

## Exact matched-binary inference

For control arm `C` and treatment arm `T`, Cortex counts discordant pairs:

```text
b = count(C=0, T=1)
c = count(C=1, T=0)
G = (b-c)/n
```

The two-sided conditional-binomial probability over `b+c` discordant pairs is
used for the primary binary test. Continuity (`D-A`), distillation (`D-B`), and
governance (`D-C`) p-values receive Holm correction. Continuous utility remains
a secondary diagnostic.

At `n=1`, variance is explicitly `not_estimable`; Cortex does not report zero
variance as scientific certainty. A paired-binary confidence interval is not
implemented in v9.8 and is labeled accordingly rather than fabricated.

## Noncompensatory promotion

A v9.8 causal result can promote only if all required gates pass:

```text
preregistered before trials
∧ planned sample complete
∧ semantic distillation supported
∧ live empirical evidence
∧ discriminative cohort
∧ exact multiplicity-adjusted primary effects
∧ negative-transfer bound
```

Fixture/simulator results may test the mechanism but cannot open the empirical
gate. No score, model label, or provider label compensates for a failed gate.

## Benchmark and release manifests

The stale root v3 release manifest and benchmark narrative are superseded by
v9.8 surfaces. `benchmarks/results/MANIFEST.json` binds current quantitative
artifacts by SHA-256 and explicitly marks missing per-run metadata as
`legacy_partial`. This does not convert historical controlled results into a
current rerun.

## Tests

The v9.8 adversarial suite covers:

- operational sibling changes alter semantic identity;
- harmless prose and origin-model changes do not;
- exact canonical support can be reconstructed;
- unsupported generalization remains `UNKNOWN`;
- `n=1` variance is not estimable;
- exact discordance probabilities and Holm correction;
- model/provider fields cannot enter preregistration policy;
- fixture-only post-preregistered wins remain held;
- every authority flag remains false.

## Remaining evidence

No new live empirical model run was executed by this release. A confirmatory
study still needs a preregistered, non-ceiling corpus with an adequately powered
matched sample, multiple task families and model capability classes, negative
controls, a paired-binary confidence interval, fresh runtime cohorts, production
repository portability measurements, and independent external replication.

