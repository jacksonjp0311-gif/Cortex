# Phase v8.2.1 — Geometric Bridge Field

## Purpose

The complete graph audit in v8.2 found a dense-core/sparse-periphery topology: a small top-degree projection contains almost every triangle and substantially overstates whole-graph closure. v8.2.1 separates useful connectivity from density by measuring bridge potential.

This is shadow telemetry. It does not change retrieval scores, reorder evidence, invent topology, grant authority, or establish consciousness.

## Bridge operator

For node \(v\):

\[
B_v = (O_v R_v D_v N_v)^{1/4}
\]

- \(O_v=1-C_v\): open-wedge mass from local closure.
- \(R_v=\log(1+d_v)/\log(1+d_{max})\): enough reach to connect regions without raw-degree domination.
- \(D_v\): the larger normalized entropy of neighboring path domains and edge relations.
- \(N_v=1-\min(0.95,d_v/d_{max})\): explicit non-hub factor.

Leaves fail the diversity/reach balance; closed clique nodes fail openness; dominant hubs lose non-hub mass. Cross-region connectors can remain bright.

## Surfaces

```bash
python -m cortex interlock bridges --repo MyProject --json
python -m cortex interlock status --repo MyProject --json
python -m cortex interconnect --repo MyProject --json
```

ARIA uses `⟠` (`GeometricBridge`). MCP accepts `cortex_interlock` with `bridges: true`.

The explicit bridge command refreshes a bounded cache. Retrieval may attach `geometric_bridge_shadow` after ranking. Tests assert that path order and scores remain byte-for-byte unchanged.

## Promotion gate

No promotion occurs in v8.2.1. A later release must run a matched holdout comparing the existing winner with a bounded bridge reserve and demonstrate:

- recall loss no worse than 2 percentage points;
- MRR regression no worse than 0.01;
- lower top-decile route concentration;
- more distinct path/domain coverage;
- p95 retrieval latency increase no worse than 10%;
- no constitutional, witness, or evidence-floor regression.

Until then, `policy_effect=false` is an invariant.

## Live starting observation

At phase start, the Cortex graph contained 2,283 nodes and 5,273 edges. The top degree decile held 73.32% of degree mass and the maximum degree was 312. The strongest shadow candidates included test, constitutional, capability, resonant-frame, and retrieval paths that connect several relation/domain neighborhoods while retaining open wedges.

## Claim boundary

Bridge potential is a structural hypothesis about routing coverage. It is not causal utility until a holdout supports it, and it is never mutation authority or subjective sensing.
