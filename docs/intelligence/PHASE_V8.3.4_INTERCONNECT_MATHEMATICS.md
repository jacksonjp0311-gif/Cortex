# Phase v8.3.4 — Interconnect Mathematics Alignment

## Purpose

v8.3.3 closed independent activation-measurement conformance. v8.3.4 makes the
cross-module mathematics explicit and consistent:

> Cortex is a gated, sheaf-like network of typed operators observed through a
> redundant tight frame, with null-preserving observability and noncompensatory
> composition.

This is a research-architecture alignment release. It does not claim improved
cognition, task utility, consciousness, or authority.

## What landed

### 1. Null-preserving observability (activation ↔ echo)

The geometric-echo law and activation metrology now share the same rule:

```text
silenced because unmeasured  ≠  measured and equal to zero
```

- Activation coordinates retain `null` with `valid=false` and a typed failure
  reason when unavailable.
- Geometric-echo axes carry an explicit gate mask `D_g = diag(g_E, g_G, g_T, g_I)`.
- Echoes observe the gated state `y = P D_g x`.
- Report fields separate `silent_unmeasured_axes` from `silent_zero_axes`.
- Signed channel mass only includes schema-backed channels; empty families do
  not appear as measured zeros.

### 2. Eight-probe 2-tight frame

The fixed orthogonal + tetrahedral probes satisfy:

```text
Pᵀ P = 2 I₄
```

so under ideal independent equal-variance noise the least-squares reconstruction
halves coordinate variance relative to a single orthonormal basis. Live reports
expose the tight-frame residual and reconstruction of the masked state.

### 3. Active-subspace fragility χ_A

The existing 19-orientation rotation orbit now reports:

```text
χ_A(x; A) = max_R α_R(x; A) − min_R α_R(x; A)
```

High identity alignment with high fragility is labeled
`coordinate_artifact_risk`. This is a bounded orbit probe, not a full O(4)
invariance theorem.

### 4. Noncompensatory composition law

Shared composition module:

```text
Φ = Γ · (∏ x_i^{w_i}) · (∏ (1 − d_j))
```

with equivalent defect potential `𝒟` when `Γ = 1`. Typed residual energy remains
a direct sum:

```text
ℛ = ℛ_self ⊕ ℛ_prediction ⊕ ℛ_operator ⊕ ℛ_temporal ⊕ ℛ_outcome
```

Residual types cannot impersonate each other and cannot authorize policy.

### 5. Activation conformance (from v8.3.3, hardened)

Independent recomputation remains the known-output reference for activation
observation. Gate B still requires structured invariants, a MEASUREMENT witness,
epoch/cohort currency, and the exactly-once hash-chained ledger. Gate C stays
cold until 16 compatible same-epoch production receipts exist.

## Claim boundary

```text
Local coherence may suggest composition, but only compatible, independently
witnessed closure permits governed adaptation.

Δθ_t ≠ 0  ⇒  Γ_t · Ξ_t · W_t · O_t · S_t = 1
Γ_t Ξ_t W_t O_t S_t = 0  ⇒  Δθ_t = 0
```

No measurement, residual, cohort, fragility score, tight-frame residual, or
composition score can move a constitutional bit or automatically change
retrieval ranking, routing, cadence, training, plasticity, promotion, host
source, execution authority, or policy.
