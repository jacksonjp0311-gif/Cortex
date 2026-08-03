# Phase v8.2.2 — Query-Conditioned Bridge Trials

## Objective

Test whether the v8.2.1 structural bridge field improves query retrieval. This phase does not activate bridge routing. It constructs matched, fixed-cardinality counterfactual arms and refuses promotion without replicated task utility.

## Triadic eligibility

For query `q` and candidate `v`:

```text
T(q,v) = (R(q,v) × B(v) × N(q,v))^(1/3)
```

- `R` is normalized retrieval relevance.
- `B` is the v8.2.1 structural bridge potential.
- `N` is region and neighboring-region novelty relative to the visible baseline.

The geometric mean prevents one strong component from fully compensating for a missing component. Independent floors remain mandatory. The train-derived initial triadic floor is `0.80`; it reduced development selection from 90.3% to 9.7%.

## Matched arms

Every query produces four reports with identical cardinality:

1. existing baseline;
2. annotation-only baseline;
3. one-slot bridge reserve;
4. deterministic random eligible reserve.

The reserve may replace only the final visible slot. The returned live result is not modified. The random arm distinguishes geometric value from the generic effect of injecting another candidate.

## Surface

```bash
python -m cortex interlock trial --repo MyProject --suite all --limit 24 --top-k 5 --json
python -m cortex interlock trial --repo MyProject --suite bridge64 --limit 24 --top-k 5 --json
```

MCP exposes the same experiment through `cortex_interlock` with `trial_suite`.

## Promotion law

All gates must pass:

- at least 64 paired cases;
- non-inferior recall with a paired interval;
- positive paired MRR lift whose interval excludes zero;
- superiority to the deterministic random control;
- zero harmful replacements;
- selection rate between 5% and 35%;
- bounded p95 analysis overhead;
- fixed cardinality and `policy_effect=false` for every case.

## Initial live measurement

The 31-case development matrix produced:

- baseline: recall `30/31`, MRR `0.71612903`;
- bridge reserve: recall `31/31`, MRR `0.72258065`;
- random reserve: recall `29/31`, MRR `0.70967742`;
- selection: `3/31` (`9.677%`);
- helpful replacements: `1`;
- harmful replacements: `0`;
- p95 trial analysis overhead: approximately `1.8 ms`.

The bridge field is therefore promising but not promotion-ready. The sample count is below 64 and the paired MRR confidence interval still touches zero.

The separate `bridge64-v1-2026-08-02` corpus contains 64 evaluation-only cases spanning 32 Cortex subsystems. It is prohibited from ranker training, concept-route construction, and threshold selection. Editing it requires a new freeze id.

Its first sealed run measured baseline recall `23/64` and MRR `0.16588542`, bridge recall `24/64` and MRR `0.16901042`, and random-control recall `18/64` and MRR `0.15026042`. The bridge lane selected on `8/64` cases, added one hit, removed none, and cost approximately `1.1 ms` p95 after the graph cache. Promotion remained blocked because the paired MRR interval `[0, 0.009375]` did not exclude zero.

A repeat after final activation changed baseline and bridge recall to `19/64` with no lift. This exposed epoch sensitivity: the first directional gain did not survive graph/body refresh. Every receipt now binds the corpus hash, sealed body epoch, complete graph fingerprint, and trial parameters into a `trial_context_hash`; results from unlike structural contexts must not be pooled as replications.

The low baseline also exposes the next bottleneck: difficult implementation queries are often saturated by documentation and consolidated-card results before the relevant source module enters the 24-candidate pool. Bridge selection can recover a relevant source already in that pool, but it cannot yet create query relevance for an absent source candidate.

## Claim boundary

This phase measures counterfactual retrieval utility. It is not live routing, learning authority, self-directed mutation, consciousness, or subjective sensing.
