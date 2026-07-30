# Phase v6.13 — Calibrated spectral memory end-to-end

**Goal:** Move from *theory ↔ surface alignment* (M0–M10 probes) to a **live path** where activate/retrieve actually run unified \(U\), \(\Lambda_g\), diffusion features, ranker-primary, and optional live calibration.

## Live path

```text
activate / query
    → spectral_memory_pulse (U, Λ_g, regime δ schedule, dual graph, λ₂ sample)
    → enrich hits with PPR/heat
    → ranker-primary score (0.82 model + 0.18 prior)
    → Governor uses live coeffs when promoted
    → control_error / constitutional consume U
```

## CLI

```bash
python -m cortex math-net pulse --repo R --json
python -m cortex math-net promote-calibration --repo R --force --json
python -m cortex activate --repo R --task "..." --json   # includes spectral_memory
```

## What “end-to-end” means here

| Piece | Live |
|-------|------|
| Unified \(U\) | Yes — activate + Governor + control_error |
| \(\Lambda_g\) pulse | Yes — connect + activate pulse |
| Diffusion in ranking | Yes — enrich_hits_with_diffusion → features |
| Ranker-primary | Yes — 0.82/0.18 blend |
| \(\delta_g\) from data | Scheduled from mass/activity (not full MLE) |
| Calibration live | After promote (auto at n≥8 or CLI force) |
| True \(L,\lambda_2\) | On pulse/spectral probe; feeds underuse telemetry |

## Claim boundary

Still recommend-only. Promotion of calibration is explicit (auto threshold or `--force`).  
Spectral \(\lambda_2\) remains approximate power method.  
Not a claim of biological fidelity or host authority.
