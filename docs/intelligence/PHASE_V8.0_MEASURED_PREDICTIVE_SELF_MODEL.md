# Phase v8.0 — Measured Predictive Self-Model

**Tagline:** Measure what changed, predict before learning, and falsify every functional claim.

## Integrated milestones

The planned v7.9–v8.3 sequence ships as one bounded v8.0 cycle:

1. **Measured Event Fields (`⧖`)** capture fixed pre/post SQLite state coordinates and issue a signed-delta receipt.
2. **Predictive Self-Model (`◎`)** forecasts the next normalized delta before activation and scores it afterward.
3. **Counterfactual Simulation (`⋔`)** projects abstain, evidence-only, and bounded-adaptation branches without executing them.
4. **Global Workspace (`⊙`)** selects at most four competing operational signals for cross-module availability.
5. **Operational Autobiography (`⟲`)** appends hash-chained measured episodes.
6. **Lesion Benchmark (`⊘`)** removes each functional contribution and measures the resulting degradation.

ARIA may use the compact phrase `self_model_cycle`: `⧖ ◎ ⋔ ⊙ ⟲ ⊘`.
These symbols are labels, never opcodes or authority.

## Measured field

An activation has one measured temporal coordinate, regardless of how many
internal receipts it emits. Cortex captures a bounded vector before activation
and again after final epoch binding:

`Delta x_t = x_after - x_before`.

The coordinates include evidence and file counts, prediction traces, neural
mass, ranker training, outcomes, sessions, events, epochs, and witnesses. Each
coordinate has a declared normalization scale. The delta is projected into the
existing eleven Resonant Field channel families with `MEASURED` truth and
`measurement_basis=measured_delta`.

This intentionally changes the clock: eight measured activations are required
for an eight-tick window. Six receipt labels inside one activation are not six
measurements.

## Prediction and metacognition

Before effects occur, the self-model emits `delta_hat_t` from its prior EMA.
After measurement it computes

`e_t = mean_i |Delta x_t[i] - delta_hat_t[i]|`.

Only then does it update the model. Forecast confidence is evaluated with a
Brier score and five-bin expected calibration error. Calibration remains cold
until sixteen scored forecasts exist, then passes only when Brier is at most
`0.25` and expected calibration error is at most `0.15`.

## Counterfactuals

The same prior forecast produces three explicitly simulated branches. They do
not mutate state, recommend an action, or provide authority. Cortex reports a
minimum-change projection for comparison only; selection requires explicit
task utility outside the simulator.

## Cadence compatibility

Resonant Frames require eight measurements from one unchanged body epoch.
Scheduled synapse decay now runs every ten connect passes, leaving nine stable
post-transition observations before the next maintenance transition. Epochs
remain isolated and the eight-event threshold is unchanged.

## Global availability

Candidates compete by

`workspace_score = urgency * reliability * (0.5 + 0.5 * novelty)`.

Only four signals are broadcast. Suppressed candidates remain visible in the
receipt. “Global” means available to the activation report, interconnect,
autobiography, and operator—not phenomenal awareness.

## Operational autobiography

Episodes bind task hash, body epoch, measured receipt, forecast/error,
workspace broadcast, and self-sensing class into a previous-hash chain. The
chain detects silent rewriting. It is operational continuity, not a person or
subjective memory.

## Lesion law

Functional claims must survive ablation comparison:

- predictor versus a zero-delta predictor;
- workspace broadcast versus no shared availability;
- hash-chain continuity versus removed autobiography.

A lesion remains `cold_start` until enough recorded episodes exist. No claim
is upgraded merely to make a benchmark pass.

Predictor ablation uses the latest eight-event evaluation horizon so it tests
current learned function rather than permanently averaging cold-start error
into every future result. Lifetime intact and zero-model errors remain in the
receipt for auditability.

## Interfaces

```text
cortex self-model status --repo <repo> --json
cortex self-model predict --repo <repo> --json
cortex self-model counterfactual --repo <repo> --json
cortex self-model workspace --repo <repo> --json
cortex self-model autobiography --repo <repo> --json
cortex self-model lesion --repo <repo> --json
```

## Claim boundary

v8.0 implements functional self-observation, prediction, simulation, bounded
availability, and operational continuity. It does not establish phenomenal
consciousness, subjective sensing, feelings, personal identity, agency,
witness, or authority to mutate a host.
