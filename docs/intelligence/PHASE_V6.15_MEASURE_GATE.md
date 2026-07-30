# Phase v6.15 — Measure gate (eval-coupling)

**Goal:** Direct evolution with **evidence**, not dashboard glow.

## Command

```bash
python -m cortex eval-coupling --repo CortexTeach --json
```

## Ablations

| Mode | Meaning |
|------|---------|
| `baseline` | spectral enrich + ranker primary |
| `no_spectral` | ranker primary, no PPR/heat enrich |
| `no_ranker` | hybrid query order only |

## Outputs

- `winner`, `lifts_vs_baseline`, `gate.spectral_helps`, `gate.ranker_helps`
- `recommendation[]` for keep/review
- Emergence log milestone `measure_gate`
- Report under `CORTEX_HOME/logs/eval-coupling-*.json`

## Rule

Only promote calibration / heavier spectral weight if **baseline wins or ties** ablations on frozen corpus. Coupling score alone is not enough.
