# Phase v6.18 — Boundary Consolidation

Responds to the capability-vs-contract gap after v6.15–v6.17 velocity.

## Fixes

| Item | Change |
|------|--------|
| Self-org path slices | `(returned_paths or [])[:n]` |
| Governor fail-open | exception → **`read_only`** |
| Eval contamination | **train** vs **holdout** suites; warm only train |
| Promote calibration | not forced by perfect-recall ceiling |
| Topology law | `G_host` / `G_evidence` / `G_learned` / `G_federated` |
| Host roles | explicit `mesh_role` in repo metadata |
| Coherence naming | `operational_coupling_index` alias |
| Fuse proxy | restore WAL + busy_timeout; optional `CORTEX_FUSE_TOKEN` |

## Suites

```bash
python -m cortex eval-coupling --repo CortexTeach --suite train --json
python -m cortex eval-coupling --repo CortexTeach --suite holdout --json
python -m cortex self-org --repo CortexTeach --json   # trains on train; promotes on holdout
```

## Non-goals for this release

- No new major organ
- No live continuum expansion
- No host mutation

## Still open (next)

- Full fusion proxy auth + threaded server + batched ticks
- Automated CHANGELOG/test receipt from CI
- Foreign-host sealed transfer suite as promotion gate
