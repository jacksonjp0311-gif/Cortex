# Cortex v9.8.6 — Cost-Calibrated Evidence Entanglement

## Purpose

Measure two axes discarded by earlier task calibration: how evidence coordinates
separate latent hypotheses, and what verified model inference actually costs.
Both remain advisory development telemetry.

## Prior wound

v9.8.5 observed ceiling, calibrated, and floor regimes at similar hypothesis
entropy. It declared information efficiency but did not retain a canonical cost
panel. It also knew only that complete signatures were unique—not whether one
coordinate or many coordinates were needed to resolve them.

## Structural evidence geometry

For a uniform latent hypothesis `H` and evidence coordinate `O_j`:

```text
E_entangle = mean_j H(H | O_j) / H(H)
R_min      = min |J| such that O_J uniquely separates every H
```

The corpus additionally binds mean pairwise coordinate collision and the
fraction of available coordinates needed for resolution. These quantities are
computed before invocation and never use model identity or model outcomes.

`E_entangle = 0` means every coordinate independently resolves the hypothesis.
Higher values mean single coordinates retain more ambiguity. It is not a
universal difficulty score: transfer burden, presentation, and inference cost
remain separate.

## Canonical cost reconstruction

The calibration verifier reloads the immutable `model_invocation` receipt and
derives:

- request-to-completion latency;
- normalized input, output, reasoning, and total token coordinates when present;
- monetary amount and currency when present;
- resolved information bits per observed second.

Missing or invalid values remain null with a false validity bit. They never
become zero. Cross-case panels report median, p95, median absolute deviation,
minimum, and maximum.

The panel is explicitly `cross_case_observational`. It does not establish
repeat-run variance because each case was invoked once.

## Bounded rebalance

Two interventions were preregistered as development strata:

1. `multi_step_code_repair`, level 4: double the held-input recurrence depth;
2. `architecture_reconstruction`, level 1: expose the exact candidate signature
   table while retaining a fresh target schedule.

The runner's `--target FAMILY=LEVEL` option prevents already mapped strata from
being rerun merely to reach the interventions.

## Live result

The host selected a frontier model at runtime. Cortex core retained only the
provider-neutral adapter contract and canonical public receipts.

| Family | Cases | Success | State | Median latency | Median total tokens | Median cost |
|---|---:|---:|---|---:|---:|---:|
| Multi-step repair L4 | 4 | 4/4 | screening ceiling | 120.810141 s | 24,560 | USD 0.014460 |
| Architecture reconstruction L1 | 4 | 4/4 | screening ceiling | 122.214857 s | 19,215.5 | USD 0.008477 |

Repair's doubled transfer burden did not leave the ceiling. Complete signature
support moved architecture from the v9.8.5 `0/4` floor to a `4/4` ceiling.
Overall status remains `CALIBRATION_HELD`; bug localization and stale-state were
not rerun in this targeted panel.

## Falsified hypotheses

- More recurrence steps alone are sufficient to calibrate repair: **not
  supported**.
- Architecture's floor is explained by hypothesis entropy alone: **falsified by
  the support intervention**.
- Complete evidence disclosure provides the desired calibration: **falsified;
  it overshot to ceiling**.

## Remaining evidence

The next experiment should expose a deterministic fraction of the minimum
resolving signature set, retain the undeclared coordinates behind a commitment,
and search for a 30–70% success region. Repeated independent invocations per
identical case are still required before runtime variance or stable information
efficiency can be claimed.

## Claim boundary

v9.8.6 measures development evidence geometry and observational invocation cost.
It does not establish model improvement, competence transfer, repeatability,
cognition, consciousness, agency, authority, or permission to modify host
source, policy, memory admission, or execution scope.
