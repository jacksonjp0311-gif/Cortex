# Cortex v9.8.1 — Discriminative Task Forge & Information-Powered Trial

## Purpose

v9.8.1 converts two saturated measurements into a stricter experimental design
boundary. A runtime-selected frontier-model calibration solved 8/8 disposable
tasks. A fresh 250-file Thalamus rerun placed the target at rank 1 in both the
baseline and routed arms. These are functioning mechanisms observed through
uninformative experiments—not evidence of causal improvement.

No model or provider is encoded in Cortex ontology. The preserved frontier run
records model identity only as external experiment provenance. Hidden reasoning
and raw provider-native envelopes were not persisted.

## Emerging measurement law

For a binary task outcome `Y` with success probability `p`:

```text
H(Y) = -p log2(p) - (1-p) log2(1-p)
```

At a floor (`p=0`) or ceiling (`p=1`), entropy is zero. For matched treatment
and control pairs:

```text
b = count(control=0, treatment=1)
c = count(control=1, treatment=0)
d = b + c
```

`d`, not raw `n`, is the effective causal sample used by the exact matched
binary test. When `d=0`, Cortex reports measurement collapse.

## Evidence geometry

Research readiness is a noncompensatory triad:

```text
E = semantic evidence
D = experimental discriminability
I = independent replication

Theta = min(E, D, I), under fail < unknown < pass
```

A geometric mean may be exposed as a diagnostic only. It cannot open a gate.
This geometry describes evidence readiness, not consciousness, cognition,
subjective sensing, or execution authority.

## Development task forge

`cortex/discriminative_forge.py` deterministically generates disposable exact-
evaluator cases across:

- repository bug localization;
- multi-step code repair;
- stale-state detection;
- API migration;
- architecture reconstruction.

The generated corpus is marked `development_only=true`, `held_out=false`, and
`confirmatory_eligible=false`. Changing prose, model identity, or provider
labels cannot change those boundaries.

`benchmarks/discriminative_forge_benchmark.py` creates the corpus or scores an
external observation file. It does not invoke or select a model. A runtime may
be attached outside Cortex and its public exact outputs returned as development
observations.

## Calibration boundary

The default development target is baseline success between 30% and 70% with at
least four observations per family. Above the range is a ceiling; below it is a
floor; insufficient samples remain unknown. Only informative families are
candidates for a separately generated held-out corpus.

Development cases must never be reused for confirmation. Confirmation still
requires frozen unseen cases, independent evaluation, canonical trial binding,
live empirical evidence, exact inference, negative-transfer control, and
replication.

## Power and uncertainty

`cortex/causal_trial.py` now includes:

- exact unconditional matched-binary power planning from a minimum interesting
  effect and expected discordance;
- deterministic case-level paired bootstrap intervals;
- explicit effective-causal-sample and discordance-rate reporting;
- a required power-analysis gate;
- a development-calibration binding gate.

An arbitrary `n=8` is no longer a confirmatory design. Planned sample size must
meet the declared power assumptions after multiplicity allocation.

## Runtime evidence

The preserved development frontier calibration is:

```text
task count                 8
successes                  8
success rate               1.0
entropy                    0 bits
classification             ceiling
confirmatory eligible      false
```

The fresh routing rerun is:

```text
baseline target rank       1
routed target rank         1
rank contrast              0
baseline Recall@3          1.0
routed Recall@3            1.0
```

The deferred/eager harness was repaired so every timing sample uses a fresh
host and fresh Cortex home. The fresh controlled result reduced median
bootstrap time from 0.555 s eager to 0.394 s deferred (about 29%), while leaving
30 deferred materialization operations. It establishes bootstrap deferral, not
total lifecycle savings.

The two-run self-host benchmark completed after the interactive wait was
stopped. Its output is complete, but the roughly one-minute activation times
show that it is a heavy system benchmark and should not be placed on an
interactive critical path.

## Claim boundary

v9.8.1 implements information diagnostics and a task-generation surface. It
does not demonstrate positive competence lift, general transfer, production
portability, independent replication, or cognition. All authority flags remain
false.

## Next evidence

1. Run development-only frontier calibration on the forged task families.
2. Retain only families whose baseline lies inside the preregistered information
   window.
3. Estimate matched discordance and calculate exact sample size.
4. Generate a disjoint held-out corpus and freeze its hash, evaluators, arms,
   negative controls, budgets, exclusions, and stopping rule.
5. Run fresh runtime-selected models through canonical circulation.
6. Replicate across a later runtime cohort and an additional capability class
   before making any transfer claim.
