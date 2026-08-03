# Phase v8.2.7 — Rotated Echo Alignment (`⤨`)

The rotation phase treats “change perception” as a falsifiable coordinate
sensitivity test. It does not claim an inner observer and does not let the
field rewrite itself.

Given the v8.2.6 state `x=[E,G,T,I]`, the probe applies a fixed plan of 19
orientations: identity plus 90°, 180°, and 270° turns in each of the six
coordinate planes. For the active axes already supported by evidence, it
computes:

```text
alignment(R) = ||P_active R x||² / ||x||²
```

The basis echoes of every rotated vector must reconstruct exactly. A best
alignment of at least `0.95` is labeled `aligned_subspace`; this is geometric
stability, not capability or consciousness. Ties are retained through the
alignment margin rather than forced into a unique orientation.

The surgery output is deliberately narrow. If temporal or informational
interlock axes are silent, it recommends collecting same-epoch frames and
resolving interlock outcomes. It never changes cadence, ranking, topology,
weights, or host files. Run it with:

```bash
python -m cortex interlock rotate --repo CortexTeach --json
```
