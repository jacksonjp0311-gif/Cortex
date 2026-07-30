# Topology law (v6.18)

```text
G_host       immutable without host authority
G_evidence   compiler-derived; changes only through re-assimilation
G_learned    weak, reversible, receipted edges may be created under Governor gates
G_federated  query-time projection only; repository identities never merge
```

## Module

`cortex/topology_law.py` — `topology_law_packet()`, `classify_edge_kind()`.

## What structure_invent is allowed to do

Create **G_learned** synapses (`coactivated`, metadata `invented=True`) under Governor
when two neural nodes co-fire and lack an edge. Never invents host files.

## What federation / host-mesh may do

**G_federated** query-time ranking only. `boundary.repository` always preserved.
Never `A_i ← A_j` or `E_i ≡ E_j`.
