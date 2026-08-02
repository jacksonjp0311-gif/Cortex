# Phase v6.22 — Foreign Geometry

**Law under foreign load + close dark couples.** Builds on Ratio Lattice (v6.21).

## What shipped

| Piece | Behavior |
|-------|----------|
| Foreign IR routes | Concept routes + score damp for `src/*.rs` over cards on PulseFlow-style queries |
| Bounded prune | `max_prune` + `protect_triads` (default on); CLI `--max-prune` / `--no-protect-triads` |
| Dual-align band | Historical v6.22 heuristic peaked near ratio ~6. v8.1.1 supersedes it with complete structural counts and an order-one compiled-layer band. |
| Advice | `bounded_integrate_soft_prune_cap_protect_triads`, `dual_align_check_neural_structural_ratio_band` |

## CLI

```bash
python -m cortex prune --repo CortexTeach --policy integrate_soft --max-prune 60 --json
python -m cortex eval-coupling --repo PulseFlow --suite foreign --json
python -m cortex coherence --repo CortexTeach --json
```

## Success criteria

- Foreign recall thickens (path tokens hit policy/storage/server)
- Teach prune hygiene improves under **capped** apply (no thrash)
- dual_align no longer permanently dark when both layers healthy
- promote gate still holdout+foreign+emergent

## Claim boundary

Telemetry and memory-graph hygiene only. Not host mutation. Not consciousness.
Foreign utility only via measure suite — never train body ranker from foreign holdout.
