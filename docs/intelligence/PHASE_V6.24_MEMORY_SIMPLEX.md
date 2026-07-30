# Phase v6.24 — Memory Simplex

**Cognitive runtime assurance for memory:** advanced adaptive controller vs trusted **EVIDENCE_BASELINE**.

## Controllers

| Controller | Behavior |
|------------|----------|
| **advanced** | Ranker-primary + spectral + concept routes + multi-res budget (`fib`) |
| **evidence_baseline** | Lexical hybrid only; no ranker, spectral, concept routes; budget `flat` |

Authority inequality (topology law):

```text
Authority(G_learned) < Authority(G_evidence)
```

Governor `read_only` → transfer to **EVIDENCE_BASELINE**.

## Measure gate

New ablation: `evidence_baseline` (alongside `baseline` / `no_spectral` / `no_ranker`).

Report fields:

- `memory_simplex` — lift of advanced (`baseline` mode) over trusted
- `gate.advanced_beats_evidence_baseline`

Naming note: eval mode **`baseline`** still means the **advanced** path (historical). Trusted controller is always **`evidence_baseline`**.

## CLI

```bash
python -m cortex activate --repo CortexTeach --task "..." --evidence-baseline --json
python -m cortex activate --repo CortexTeach --task "..." --memory-controller evidence_baseline --json
python -m cortex eval-coupling --repo CortexTeach --suite holdout --json
# → ablations.evidence_baseline + memory_simplex
```

## Lineage prep

Invented edges carry `ancestors` + `lineage_plane=G_learned` for future causal unlearning.

## Non-goals this phase

- Full Independent Witness crypto suite
- Causal unlearning apply
- PROV-O export

## Claim boundary

Runtime assurance for adaptive retrieval only. Not consciousness. Not host mutation.
