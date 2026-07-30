# Phase v6.21 — Ratio Lattice

**Law compression** from a multi-resolution ratio program (self-similar envelope, 1:2 cell, third-axis triad, path residual). Runtime name: **Ratio Lattice**. Internal analogy only: Giza exterior–interior ratio lattice — **not** sacred geometry, activation keys, or consciousness claims.

## Operators

| Operator | Formula / object | Module |
|----------|------------------|--------|
| Triadic closure \(T\) | \(3\Delta / \#\text{wedges}\); local clustering \(c_u\) | `math_net.ratio_lattice` |
| Ranker feature | `triadic_closure` ∈ FEATURE_NAMES | `ranker.model` + enrich stamp |
| Open-bridge attention | Edges with 0 triangles | `prune.policy_preview` → `triad_attention` |
| Budget partition | schemes: `fib` (default), `phi`, `double_square`, `flat` | `ratio_lattice.partition_budgets` → `context.budget_partition` |
| Residual pyramid | \(r_\ell\), \(\delta_\ell\), `envelope_cell_ok` | `math_net.multiscale` (M9 schema 1.1) |
| Rational tables | `RATIONAL_RATIOS` (fib, 1:2, quarter, …) | `ratio_lattice` |
| Couple phase history | `occupied_bonds`, `phase_emergent` on history points | `coherence` 1.2 |

## Lattice → Cortex map (analogy, labeled)

| Measurement structure | Operator | Landing |
|----------------------|----------|---------|
| Envelope constant-ratio band | Self-similar / Fib partition | Multi-res context budgets |
| Double-square floor | 1:2 base cell | `double_square` scheme |
| √5 height on 1:2 | Third-axis / triad | Triadic closure on synapses |
| Axis + expanding gallery | Path residual | M9 `residual_pyramid` |
| Envelope ↔ cell compatibility | Global must match local | `envelope_cell_ok` |

## CLI

```bash
python -m cortex activate --repo CortexTeach --task "ratio lattice" --budget 800 --budget-scheme fib --json
# packet.budget_partition

python -m cortex math-net --repo CortexTeach --json
# results.M9.residual_pyramid

# prune preview includes triad_attention + bottleneck_attention.triad_open_bridges
```

Budget schemes: `fib` | `phi` | `double_square` | `flat` (ablation = pre-6.21 single pool).

## Non-goals

- No Giza/sacred strings in runtime schemas
- No promote_gate change from triad/residual alone
- No auto-prune from open bridges (preview only)
- No new Cheeger/Fisher surface this phase

## Claim boundary

Telemetry and packing heuristics only. **Not** consciousness, sacred geometry, free energy ideology, or host mutation authority. Utility claims still require holdout/foreign suites.
