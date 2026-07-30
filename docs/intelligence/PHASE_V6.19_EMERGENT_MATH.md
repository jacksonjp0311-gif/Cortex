# Phase v6.19 — Emergent math made explicit

Name the high-value operators already inside the body. Every scalar carries a claim boundary.

## Operators

| ID | Formula / object | Module |
|----|------------------|--------|
| M7 η, Π | ΔU/log(1+T), max(0,ΔU)·F·R | `info_account` |
| M7 F proxy | F ≈ U + complexity | `info_account.free_energy_proxy` |
| M4 underuse | (1+10h)⁻¹(1+5w)⁻¹ · {1,0.4} | `spectral` |
| M4 Cheeger | Fiedler sign cut → h_approx | `spectral.cheeger` |
| M4 wavelet | e^{-t₁L}−e^{-t₂L} | `spectral.heat_wavelet_top` |
| OCI / couples | S≥0.62 ∧ #bonds≥3 | `coherence` |
| Percolation | cut bonds, hysteresis | `coherence.couple_percolation` |
| Lyapunov V | (1−S)+α(1−c)+βU | `coherence.lyapunov` |
| M9 δ | mass distortion multi-scale | `multiscale.mass_conservation` |
| Fisher I_ii | p(1−p)x_i² mean | `ranker.fisher` |
| Topology | G_host/evidence/learned/federated | `topology_law` |

## Claim boundary (absolute)

Telemetry for Governor and agents. **Not** consciousness, thermodynamic criticality,
FEP ideology, Shannon bits from the environment, or host authority. **Holdout / foreign
eval** for utility claims.

## CLI

```bash
python -m cortex coherence --repo CortexTeach --json
# couple_percolation, lyapunov, operational_coupling_index

python -m cortex eval-coupling --repo CortexTeach --suite holdout --json
```
