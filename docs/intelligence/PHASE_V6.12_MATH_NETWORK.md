# Phase v6.12 — Math/network spine (M0–M10)

**Authority:** recommend-only · one SQLite body · never host.mutate  
**Glyph:** ≋ regimes · U uncertainty · A operator · L spectral  

## Honesty (M0)

| Legacy name | Honest name |
|-------------|-------------|
| Spectral kernels | **Retention regimes** (prior \(\rho=e^{-\delta T}\)) |
| Kernel spectrum | Mass histogram by regime — **not** eigenvalues of \(L\) |
| True spectral | `cortex.math_net.spectral` (\(L\), \(\lambda_2\), heat) |

Fixed coefficients in Governor / constitutional are **priors** until shadow calibration promotes.

## Phases

| ID | Module | Status |
|----|--------|--------|
| M0 | `math_net.regimes` | regimes vs spectral claims |
| M1 | `math_net.uncertainty` | unified \(U\) → Governor, control_error, constitutional |
| M2 | `math_net.operator` | operator \(A\) + dual-graph report |
| M3 | `math_net.diffusion` | PPR + heat features |
| M4 | `math_net.spectral` | \(L\), \(\lambda_2\), heat, edge underuse |
| M5 | `math_net.calibration` | shadow fit of weights |
| M6 | `math_net.ranking` | ranker-primary + log-loss + ECE |
| M7 | `math_net.info_account` | \(\Delta U\) / promotion product gate |
| M8 | `math_net.plasticity_rct` | Hebbian on/off RCT |
| M9 | `math_net.multiscale` | multi-scale conservation check |
| M10 | `math_net.temporal_edges` | age × co-change × calls |

## CLI

```bash
python -m cortex math-net --repo R --json
python -m cortex math-net phases --repo R --json
python -m cortex math-net spectral --repo R --json
python -m cortex math-net diffusion --repo R --json
python -m cortex math-net dual --repo R --json
python -m cortex kernels --repo R --json   # regimes + Λ_g + not_spectral flag
```

## Claim boundary

Shadow calibration does not replace live priors until explicit promotion.  
Spectral estimates use projected power methods (approximate \(\lambda_2\)).  
Plasticity RCT is alternating-arm, not a randomized clinical trial.
