# Phase v7.5.0 — Self-Sensing Field

**Tagline:** Measure Cortex’s own operating regime against a verified baseline — report residual, never self-authorize.

**Not:** consciousness · autonomous self-modification · authority geometry

## Live structures this phase answers

| Structure | Observer response |
|-----------|-------------------|
| Bimodal integrate/retain mass | Exposed in spectral panel; not “emergence” |
| Six-seam coupling / high C | Enters \(C_t\) in \(z_t\); not capability |
| Local coherence + phase unbound | Hard gate → **UNBOUND** (never false healthy) |
| Temporal field cold (0/16) | **COLD** until frames + observer baseline warm |
| Sparse activation / weak causal | Out of scope for v7.5 authority; telemetry only |

## Observer state

\[
z_t=[C_t,N_t,I_t,L_t,D_t,H_t,G_t,Q_t,\eta_E,\eta_M,T_t,\Delta E_t,U_t]
\]

Baseline (EMA): \(\mu_t=(1-\alpha)\mu_{t-1}+\alpha z_t\) (updates only when epoch current + evidence valid).

Residual (diagonal Mahalanobis):

\[
r_t=\sqrt{(z_t-\mu_t)^\top(\mathrm{diag}(\sigma^2)+\lambda I)^{-1}(z_t-\mu_t)}
\]

Field health (engineering GM; diversity uses \(D_t\) as positive term; literal \(1-D\) kept as `F_spec_literal` for audit):

\[
F_t=\mathrm{GM}(C_t,N_t,Q_t,D_t,1-U_t)
\]

## Hard gates

Before **NOMINAL**:

- observer / field baseline warm
- body epoch current (verified)
- phase binding present
- evidence/bootstrap valid

If epoch or phase unbound → **UNBOUND** always (no false healthy).

## Architecture

```text
Field channels + coherence + epoch/phase
        ↓
sample z_t
        ↓
EMA baseline (gated)
        ↓
residual r_t + F_t
        ↓
classification (COLD|UNBOUND|NOMINAL|DRIFT|STRESSED|INDETERMINATE)
        ↓
advisory recommendations only
```

## CLI

```bash
python -m cortex sense observe --repo MyProject --json
python -m cortex sense report --repo MyProject --json
python -m cortex sense replay --repo MyProject --json
python -m cortex sense milestone --repo MyProject --json
python -m cortex sense observe --repo MyProject --no-update --json
```

## First milestone

> Warm 16 verified temporal / observer updates across ≥3 channel families, then reproduce the same self-sensing classification on holdout/replay without changing any authority state.

Success:

- baseline ready 16/16 (observer and/or field)
- ≥3 channel baselines (field)
- deterministic replay classification
- no constitutional bit changes
- no host writes
- no automatic ARIA materialization
- no NOMINAL when epoch binding missing

## Claim boundary

Self-Sensing Field residual means “different from recent verified regime,” not “authorized to change itself.” Host source, tests, epoch, capability, constitutional path, and witness remain controlling.
