# Cortex v10.0.0-alpha.12 — Governed Autonomy Differential

## Purpose

Alpha.12 measures a narrower question than “can Cortex improve itself?”:

> Holding the model, source, evaluator, tools, authority, and budgets fixed,
> does Cortex-governed context change matched task outcomes relative to a
> task-only control?

The release creates the canonical experiment needed to answer that question.
It does not claim a positive empirical answer.

## Frozen comparison

Each preregistration commits before execution to:

- one repository and Git source commit;
- a fixed set of case and task-evaluation contracts;
- model identity, adapter implementation, and host-derived evidence class;
- the tool catalog and capability-grant profile;
- a committed randomization seed;
- token, time, cost, tool-call, and iteration budgets;
- effect, significance, regression, and discordance thresholds;
- an exact matched-binary power plan with declared expected discordance and
  target power;
- efficiency weights and normalizers.

Every case runs the same `NativeAgentRuntime` twice in randomized order:

```text
task-only control                  Cortex-governed
-----------------                  ----------------
task                               task
same model                         same model
same tools and grant               same tools and grant
same evaluator                     same evaluator
constitutional restrictions        verified Cortex projection
no memory/evidence/competence       governed context surfaces
```

The control remains Cortex-observed so provenance and verification are not a
confound. Its request is canonically marked `task_only_control`, and deep
trajectory verification requires the evidence, memory, competence, and
contradiction collections to be empty.

## Independent outcome law

Neither the model nor the caller supplies success. Cortex reloads each sealed
trajectory and evaluates its public final answer with the evaluator committed
in the frozen case contract. A model field such as `success=true` or
`verified=true` is inert.

```text
model response
  → immutable trajectory
  → canonical reconstruction
  → frozen evaluator
  → observed outcome
```

## Matched mathematics

Let `Yᶜᵢ` be control success and `Yᵍᵢ` governed success for matched case `i`.
The primary effect is:

```text
G_C = (1/n) Σᵢ (Yᵍᵢ - Yᶜᵢ) = (b - c) / n
```

where `b` counts control-fail/governed-pass pairs and `c` counts
control-pass/governed-fail pairs. Only `b + c` pairs contain causal contrast.
The primary binary significance calculation is the exact two-sided
conditional-binomial matched-pairs test. A deterministic paired bootstrap
reports descriptive uncertainty without replacing that exact gate.

Resource use remains separate from correctness. When tokens, latency, and cost
are all measured, the normalized descriptive efficiency is:

```text
η_C = G_C / (wτ·tokens/τ₀ + wt·latency/t₀ + w$·cost/$₀)
```

Unavailable usage remains unavailable. It is never converted to zero.

## Noncompensatory promotion geometry

An empirical advantage requires every hard plane to pass:

```text
Θ_autonomy = min(
  canonical reconstruction,
  complete frozen panel,
  preregistered power sufficiency,
  live-empirical evidence,
  minimum discordance,
  minimum paired effect,
  exact significance,
  regression ceiling,
  observed resource budgets
)
```

under `FAIL < UNKNOWN < PASS`. No utility, confidence, consensus, or efficiency
score can compensate for a failed or unknown hard gate.

## Synthetic boundary

`ScriptedAgentAdapter` carries an intrinsic fixture-lineage marker. Host-side
adapter provenance is derived from that marker across its class lineage, so a
subclass cannot become empirical by changing provider family, model ID,
adapter ID, or response metadata.

The included benchmark intentionally creates a synthetic contrast. It may
return `STRUCTURAL_DIFFERENTIAL_MEASURED`; it cannot return empirical autonomy
verification. Historical evidence without a trustworthy evidence class remains
legacy or unknown for empirical use.

## Authority

Both arms preserve:

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
```

The differential is an observation surface. It cannot authorize source
integration, policy change, memory admission, or another experiment.

## Current evidence

The deterministic eight-case benchmark verifies the paired machinery,
treatment isolation, reconstruction, analysis, and claim boundary. It does not
cross a live external model boundary and does not establish `G_C > 0` for a
frontier model.

Current empirical disposition:

```text
EMPIRICAL_AUTONOMY_ADVANTAGE: NOT EXECUTED / NOT ESTABLISHED
```

The next legitimate step is a preregistered, sufficiently powered live trial on
discriminative tasks. Its policy must be frozen before model execution, and a
positive result must survive replication before Cortex describes it as a
general advantage.
