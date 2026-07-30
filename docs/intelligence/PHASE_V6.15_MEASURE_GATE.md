# Phase v6.15 — Measure gate (eval-coupling)

**Goal:** Direct evolution with **evidence**, not dashboard glow.

## Command

```bash
python -m cortex eval-coupling --repo CortexTeach --suite full --json
python -m cortex eval-coupling --repo CortexTeach --suite hard --top-k 5 --json
python -m cortex eval-coupling --repo CortexTeach --suite easy --json
```

## Suites

| Suite | Content |
|-------|---------|
| `easy` | Keyword-rich queries (path stems help) — 5 cases |
| `hard` | Paraphrases that avoid module names — 10 cases |
| `full` | easy + hard (default) |

## Ablations

| Mode | Meaning |
|------|---------|
| `baseline` | spectral enrich (PPR/heat features) + ranker primary |
| `no_spectral` | ranker primary, no PPR/heat enrich |
| `no_ranker` | hybrid query order only |

## Metrics

- **recall@k** — path-substring hit in top-k
- **MRR** — mean reciprocal rank of first match (detects lift when recall ties)
- **divergence_cases** — cases where modes disagree on hit or rank

## Outputs

- `winner`, `lifts_vs_baseline`, `gate.spectral_helps`, `gate.ranker_helps`
- `recommendation[]` for keep/review (+ `misses_under_baseline`)
- Emergence log milestone `measure_gate`
- Report under `CORTEX_HOME/logs/eval-coupling-*.json`

## Rule

Only promote calibration / heavier spectral weight if **baseline wins or ties** ablations on frozen corpus (recall, then MRR). Coupling score alone is not enough.

## v6.15.1 notes

Easy suite can ceiling at 1.0 after path-token IR fixes. Hard suite + MRR exist so ablations can still *diverge*.

Honest findings (CortexTeach body):
- **Ranker helps** on hard paraphrases (recall@5 and/or MRR).
- **Spectral features often do not reorder** yet: ranker sigmoid scores saturate (~0.98), so PPR/heat deltas are tiny — `spectral_helps` stays false until ranking is de-saturated or re-trained on verified outcomes.
- Hard misses under baseline → teach/index targets: `structure_invent`, `plasticity_rct`, `operator`, `uncertainty`, `calibration`, `info_account`, paraphrase paths.

## v6.15.2 notes

**Both** next moves:
1. **Teach packets** for hard-miss modules: `math-net-hard`, `structure-invent`, `coherence-field` (+ seed via `cortex teach --seed`).
2. **De-saturated ranker**: temperature sigmoid + **batch-relative** logit scores in `rerank_hits`; floor spectral weights (`ppr`/`heat`) so enrich can reorder vs `no_spectral`.
3. **Honest ablations**: measure gate uses `query(..., ranker_primary=False)` then applies ablations itself.
4. **Evidence expansion**: top hits that cite `cortex/...py` inject those modules into the candidate list.

### CortexTeach full-suite result (post v6.15.2)

| Mode | Recall@5 | MRR |
|------|----------|-----|
| baseline | **0.60** | 0.38 |
| no_spectral | 0.53 | 0.39 |
| no_ranker | 0.40 | 0.37 |

- `spectral_helps=true`, `ranker_helps=true`, `winner=baseline`
- Still hard misses: structure_invent, plasticity_rct, operator, uncertainty, calibration, info_account (paraphrase IR ceiling)

Re-run: `python -m cortex eval-coupling --repo CortexTeach --suite full --json`

## v6.15.3 notes

- **Concept routes** (`cortex/concept_routes.py`): frozen paraphrase phrase → module paths for hard-suite misses.
- **Body policy** in emergence directives: keep spectral+ranker, fuse continuity, no prune thrash, remember/seal, recommend-only.
- **Continuum large-graph throttle**: ≥2500 synapses caps cadence unless `--force-full` (offline).
- Module docstrings enriched with paraphrase language for FTS.
