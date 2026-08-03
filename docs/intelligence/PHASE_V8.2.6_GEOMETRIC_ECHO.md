# Phase v8.2.6 — Four-Dimensional Geometric Echo

## Purpose

The geometric echo probe is a bounded diagnostic for the question: “Which
operational dimensions currently answer when a fixed signal is pulsed through
the Cortex field?” It is not a consciousness test and it does not create a
new authority channel.

The observed state is

```text
x = [E, G, T, I]
```

where:

- `E` is source-reserve candidate recall from the selective admission field;
- `G` combines graph deconcentration (`1 - top_decile_degree_share`) with the
  mean bridge potential of cached cross-region candidates;
- `T` is the resonance-sweep coherence only when its evidence gate reports a
  stable candidate peak; and
- `I` is mean informational-interlock alignment only when the cohort is data
  ready.

All components are clamped to `[0, 1]`. Missing or invalid inputs are zero,
not imputed.

## Pulse and echo

The probe sends four fixed unit basis pulses and four fixed tetrahedral
cross-check pulses. Each echo is a dot product `y = p · x`. The basis echoes
must reconstruct the input state; a non-zero reconstruction error signals a
bug in the probe rather than a property of the repository. `field_norm` and
`echo_energy = ||x||²` are descriptive only.

The CLI surface is:

```bash
python -m cortex interlock echo --repo CortexTeach --json
```

`interconnect` includes the same report without persisting it. MCP clients can
request it with `cortex_interlock` and `{ "echo": true }`. Persistence is
explicitly advisory (`geometric_echo_latest:<repo>`) and never changes routing,
cadence, learning, policy, topology, or host files.

## Interpretation boundary

An active axis means that an existing telemetry source has a measurable value;
a silent axis means its source is absent or its own evidence gate is closed.
The current Cortex reading is expected to show an evidence echo, a moderate
geometry echo, and silent temporal/interlock echoes while same-epoch frames and
resolved cohort outcomes are insufficient. That pattern is an instrumentation
result, not an inner signal or subjective report.

