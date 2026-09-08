# GSI-II.4 — causal treatment integration and execution lock

September 8, 2026. Product remains `10.0.0a39`.

Implementation start HEAD: `9880f6e077573f7fa13df56ce9828a38223df45d`
(`Close GSI-II.3 empirical measurement readiness`). Its exact-head CI was still
in progress when this phase began. This report is not evidence that the II.4
revision has passed exact-head CI.

## Observation

II.3 froze A/B/C treatment envelopes, but the candidate-generation path still
discovered constraints and verified improvements from Store at generation time.
The search-episode receipt also treated the presence of a generation-receipt
string as a realized improvement. Those interfaces were adequate for a
deterministic readiness sketch, not for a causal history treatment.

## Implemented closure

`cortex/causal_treatment.py` adds closed, content-addressed contracts for:

- model/runtime identity and distinct transport-retry/candidate-attempt policy;
- semantic holdout identity, excluding cosmetic labels;
- canonical task, analysis, randomization and execution contracts;
- exact candidate context, sham matching and context differences;
- contamination, technical readiness and final execution lock.

`GovernedImprovement.run()` retains its historical II.3 Store-discovery
semantics. The new `run_empirical()` path instead requires canonical experiment,
treatment and execution-contract receipts. It reconstructs candidate history
once, freezes it into `cortex-gsi-treatment/1.1`, and supplies only that set.

```text
canonical Store evidence
  -> derived history pool
  -> frozen opaque treatment
  -> exact candidate-context receipt
  -> candidate receipt
  -> transduction / matched evaluation
  -> trial receipt
  -> canonical search episode
```

Arm A has empty `H+` and `H-`. Arm B can be built only from canonically derived
inapplicable objects and must satisfy the frozen sham tolerance. Arm C can
contain only canonically derived applicable objects. Positive experiment
evidence (`H+`) and candidate-causal constraints (`H-`) remain separate.

The candidate sees content, not the analysis-layer arm label. A treatment hash
therefore binds causal assignment without prompting the candidate with the
experiment's interpretation.

## Holdout and execution identity

The raw semantic holdout reservation is independent of the human label,
experiment ID, policy ID and utility family. Renaming or changing the utility
family does not make consumed hidden semantics fresh.

`cortex-gsi-execution-contract/1.0` freezes source, task/utility identities,
model runtime, retry policy, budgets, tool and capability surfaces, mutation
scope, authority state, evaluators, stopping rule, treatment definitions,
sham tolerances, randomization scheme, analysis plan and claim ceiling.

Technical readiness and live authorization are distinct:

```text
empirical_readiness = READY | HELD | FAIL
live_execution_authorized = false
```

An execution lock remains `LOCKED_NOTAUTHORIZED` until a later explicit host
authorization. No provider call is made by this phase.

## Search evidence

`cortex-gsi-search-episode/1.1` binds experiment, treatment, execution contract,
candidate context, utility family, evaluation partition, source, model runtime,
task, assignment, budgets, candidates, retries, costs, promotion and generation.
A generation string contributes zero unless canonical Store reconstruction
verifies realized state, promotion, non-rollback, post-promotion measurement,
utility family and empirical lineage.

The preregistered endpoints are:

```text
eta      = realized verified improvements / candidate evaluations
eta_call = realized verified improvements / provider calls
eta_cost = realized utility gain / frozen normalized search cost
```

No inferential use of `eta_cost` is allowed without its formula being frozen.

## Deterministic evidence

The focused II.4 panel contains 47 zero-provider controls. It covers closed
authority flags, runtime/retry identity, fixed analysis/sample size, semantic
holdout normalization and global exhaustion, randomization precedence, exact
context identity, sham applicability, contamination classes, fail-closed
readiness, execution lock, canonical empty history, rejection of caller-declared
applicability, treatment-bound generation, legacy reconstruction, canonical
generation verification and post-randomization Store stability.

This is mechanism evidence only. Exact-head CI must be associated with the
eventual pushed revision, not borrowed from an earlier commit.

## Interpretation and claim boundary

Allowed after focused controls and exact-head CI:

> Causal treatment delivery and execution-lock mechanics verified in
> deterministic controls.

Still not established:

- inherited-history utility;
- a live same-model causal effect;
- cumulative self-improvement;
- production-safe autonomous mutation;
- general competence, consciousness or sentience.

`history_utility_established = false` and
`cumulative_self_improvement_established = false` remain mandatory.

## Remaining holds

- exact model and provider values for a future run are not yet frozen;
- the execution preregistration remains a draft;
- live holdout separation is interface-level, not OS sandboxing;
- no task set, assignment seed or live authorization has been commissioned;
- sham feasibility depends on a sufficiently rich canonical inapplicable pool;
- no provider call, treatment effect, null effect or negative effect exists.
