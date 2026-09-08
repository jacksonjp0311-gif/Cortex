# GSI-III preregistration — same-model history utility

September 8, 2026. Product remains `10.0.0a39`.

**This document freezes an unrun experiment. Zero live provider calls.**

Do not tune tasks, treatments, utility, stopping rules, or significance
rules after seeing live treatment outcomes.

## Conditions

| Arm | History |
|---|---|
| A | `NO_HISTORY` — no inherited GSI experiment evidence beyond a neutral baseline |
| B | `SHAM_HISTORY` — equal-sized history-shaped context that is applicability-invalid |
| C | `APPLICABLE_HISTORY` — applicable verified Cortex experiment evidence and candidate-causal constraints |

Primary contrast is `C - B`. B controls for extra text, formatting, priming, and tokens. A is a no-history reference.

## Frozen equalities

`Model`, `ProviderConfig`, `CandidateBudget`, `ToolSurface`, and `UtilityFamily`
are identical across A/B/C. Only treatment history varies.

Exact model ID, provider, sampling, tool access, budgets, mutation scope,
evaluator, promotion policy, authority envelope, randomization, and analysis
plan must be filled before the first live treatment call. They are not filled
here because this phase does not authorize those calls.

## Primary endpoint

```text
eta = RealizedVerifiedImprovements / CandidateEvaluations
HistoryEfficiencyGain = eta_C - eta_B
```

Do not change this endpoint after observing results.

## Hypotheses

- H0: `eta_C <= eta_B`
- H1: `eta_C > eta_B`

Secondary: `U_C` versus `U_B` under the frozen utility family.

A positive result may support only:

> Applicable inherited Cortex evidence improved same-model improvement-search
> performance within the declared workload.

It would not establish general intelligence, recursive self-improvement, or
production-safe autonomy.

## Contamination

A/B/C must not share mutable learning state. Each arm is a fresh experiment
envelope with its own holdout partition and no cross-arm Store leakage of
treatment outcomes.

## Execution status

`live_execution_authorized = false`
`provider_calls = 0`
`history_utility_established = false`

Authorization of GSI-III is a separate host decision after GSI-II.3 exact-head
CI and an explicit live-experiment request.
