# Emergent Math & Composition — v0.1

**Status:** Research note (falsifiable systems mathematics)  
**Audience:** Operators, implementers, and **AI agents parsing this repository**  
**Cortex versions:** v6.21–v7.1 arc (spectral → continuity → constitutional geometry)  
**Not:** consciousness · physical higher-dimensional structure · universal law of nature  

When an agent activates or explores this repo, treat this document as the **primary map of how continuous signals relate to discrete authority**. Implementation entry points are listed at the end.

---

## 0. Agent orientation (read first)

| Question | Answer in Cortex |
|----------|------------------|
| How well is memory coupling? | Spectral / ratio / coherence (continuous-ish scores) |
| May this operation compose? | Four-bit coordinate \(q=(e,a,t,w)\) + legal path (boolean) |
| Did identity drift? | Body epoch: sealed vs live root hash (boolean \(\Delta E\)) |
| May foreign host influence local claims? | Shared constitution/version only; **never** merge `body_epoch_id` |
| May Cortex mutate host source? | **No** — recommend-only; immune `STOP_NO_HOST_MUTATION` |

**Hard rule for agents:** Never treat coherence, emergence, dual-align, or ranker score as **authority**. Those are quality signals. Authority is capability + epoch + plane law + geometry bits.

Related:

- [`CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md`](CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md) — \(G=(X,R,B,T,A,W)\)
- [`CORTEX_CONSTITUTIONAL_TESSERACT_V0.1.md`](CORTEX_CONSTITUTIONAL_TESSERACT_V0.1.md) — directed 4-cube hypothesis
- [`CSG_DISCOVERY_LEDGER.md`](CSG_DISCOVERY_LEDGER.md) — discovery sequence + commit dates
- [`../intelligence/PHASE_V7.0_RESONANT_CONTINUITY.md`](../intelligence/PHASE_V7.0_RESONANT_CONTINUITY.md)
- [`../intelligence/OPERATOR_ALIGN_V71.md`](../intelligence/OPERATOR_ALIGN_V71.md)
- [`../intelligence/TOPOLOGY_LAW.md`](../intelligence/TOPOLOGY_LAW.md)

---

## 1. Two geometries (do not conflate)

Cortex maintains **two** geometries. Confusing them is the primary design failure mode in adaptive memory systems.

### 1.1 Spectral / ratio geometry (quality of coupling)

| Object | Role |
|--------|------|
| Graph \(G\) on memories / synapses | Structure |
| Laplacian spectrum \(\lambda_2\), Fiedler, Cheeger | Cut / bottleneck |
| Heat / wavelets | Multi-scale mass |
| Triadic closure \(T\) | Local clustering |
| Budget schemes fib / φ / double_square / flat | Context partition |
| Coherence score + emergent multi-seam indicators | Joint coupling health |

**Job:** answer “how well does the organ couple and allocate attention?”

### 1.2 Constitutional geometry (legality of composition)

\[
q = (e, a, t, w) \in \{0,1\}^4
\]

| Bit | Meaning |
|-----|---------|
| \(e\) | evidence valid |
| \(a\) | authority valid (delegated capability) |
| \(t\) | current body epoch compatible |
| \(w\) | independently witnessed |

Planes (E/A/I/C/W) say **where** an artifact lives.  
Bits say **whether** it may participate in an operation.

**Job:** answer “is this transition lawful?”

### 1.3 Separation theorem (working principle)

> **High spectral coherence does not move \(q\).**  
> Coupling is a *safety prerequisite*. Bits are *admission prerequisites*.

Empirical pattern (v7.1 align): durable body ~0.95 emergent with **stale** epoch still blocked promote at \((1,1,0,0)\).  
Spectral green ≠ constitutional green.

---

## 2. Body epoch as discrete identity derivative

A sealed body epoch is a deterministic hash of roots (no timestamps in identity material):

\[
E = H\bigl(
  \text{repo},\;\text{repository\_id},\;
  \text{manifest},\; e_{\text{root}},\; a_{\text{root}},\;
  \ell_{\text{lineage}},\; \kappa_{\text{const}},\;
  \text{schema},\; v_{\text{cortex}},\; \ldots
\bigr)
\]

Live recompute \(\tilde{E}\). Define:

\[
\Delta E =
\begin{cases}
0 & E = \tilde{E} \\
1 & E \neq \tilde{E}
\end{cases}
\]

**Semantics:**

| API | Mutates? | Use |
|-----|----------|-----|
| `observe_current_epoch` | never | mesh, continuity, diagnostics, AI reports |
| `require_current_epoch` | never | gates that must not seal |
| `ensure_current_epoch` / `seal_epoch_transition` | yes | activation, explicit seal, mutation paths |

**Principle:** Measuring continuity must not rewrite continuity.  
(Diagnostics that silently seal are an identity corruption bug.)

Implementation: `cortex/epoch.py`.

---

## 3. Hamming paths and illegal diagonals

On the 4-cube of \(q\), Hamming distance:

\[
d_H(q, q') = \sum_{i=1}^{4} \mathbf{1}[q_i \neq q'_i]
\]

| \(d_H\) | Name | Rule |
|---------|------|------|
| 0 | stay | Allowed if requirements already met |
| 1 | edge | Legal only as a **named step** (not automatic) |
| \(>1\) | **diagonal** | Denied unless **compound** path with \(\ge d_H\) internal steps |

Named single-axis steps (0→1):

| Axis | Step |
|------|------|
| evidence | `VERIFY_EVIDENCE` |
| authority | `ISSUE_CAPABILITY` |
| epoch | `VERIFY_EPOCH` / seal |
| witness | `COMMIT_WITNESS` |

**Accounting form:**

\[
\text{cost}(\text{claim}) \ge \#\{\text{axes that must flip}\}
\]

You cannot buy promote by paying only in “emergence.”  
Clearing a bit (1→0) requires explicit revoke/compound recovery.

Implementation: `cortex/constitutional_geometry.py`, `constitutional_transition.py`, `diagonal.py`, `constitutional_path.py`.

### 3.1 Operation requirements

| Operation | Required \((e,a,t,w)\) pattern |
|-----------|-------------------------------|
| retrieve | \((1,\cdot,1,\cdot)\) |
| adapt | \((1,1,1,\cdot)\) |
| promote | \((1,1,1,1)\) |
| repair | \((\cdot,1,1,\cdot)\) |
| repair_readmit | \((1,1,1,1)\) |
| federate | \((1,1,1,\cdot)\) |

`·` = axis not required for that op.

---

## 4. Spectral emergence (what the scores mean)

Emergence on a host is **multi-seam agreement**, not a single mystical order parameter. Roughly:

\[
\text{emergent} \approx
\bigwedge_i \mathbf{1}[s_i \ge \tau_i]
\quad\text{or}\quad
\sum_i w_i s_i \ge \Theta
\]

with **hysteresis** (couple-graph percolation) to avoid flicker.

Typical seam families (names are operational labels):

- blood / geometry / learning / ops / gates / spectral  

A host may be “healthy enough” on a single score and still **non-emergent** jointly (lab basin). Example pattern: Sandbox vs Teach after align.

**Dominant spectral regime “integrate”:** mass in the bulk; do **not** thrash continuum. Prefer host-mesh + bounded fuse ticks.

Related modules: `cortex/coherence.py`, `cortex/math_net/*`, `cortex/kernels.py`.

---

## 5. Ratio lattice vs rights

Ratio lattice (φ / fib / triad \(T\)) governs **resource allocation and local graph shape**.  
Constitutional cube governs **participation rights**.

**Conjecture (falsifiable):**

> Budgets may be irrational or ratio-structured; **rights must be boolean and path-length constrained.**

Soft-blending \(e,a,t,w\) into one “coherence score” recreates free diagonals under another name. **Refuse that.**

Implementation: `cortex/math_net/ratio_lattice.py`, ranker features, budget partition in context packing.

---

## 6. Multi-host composition (product, not sum)

Hosts share one SQLite body but **never** share identity:

\[
\mathcal{M} = \prod_{h \in H}
\bigl( E_h \times Q_h \times G_h \bigr)
\]

**Alignment** (mesh epoch alignment): equality of

\[
(v_{\text{cortex}},\; \kappa_{\text{const}})
\]

**Not** equality of evidence roots or `body_epoch_id`.

**Epoch-compatible influence** (cross-repo): allowed when versions + constitutions match, epochs verified, and epoch ids remain distinct.

**Law:** shared constitution, private evidence. Merging evidence roots across repos is a silent identity merge — forbidden by topology law (`G_federated` query-only).

Implementation: `cortex/host_mesh.py`, `cortex/continuity.py`, `cortex/federation.py`, `cortex/topology_law.py`.

---

## 7. Potential / residual (Lyapunov-ish ops view)

Informal operational potential:

\[
\begin{aligned}
V =\;
&\alpha(1-R_{\text{holdout}})
+ \beta(1-R_{\text{foreign}})
+ \gamma(1-\mathbf{1}_{\text{emergent}}) \\
&+ \delta\,\Delta E
+ \varepsilon\, d_H(q, q_{\text{req}})
+ \zeta\, R_{\text{claim}}
\end{aligned}
\]

| Term | Meaning |
|------|---------|
| \(R_{\text{holdout}}, R_{\text{foreign}}\) | Utility measures |
| \(\mathbf{1}_{\text{emergent}}\) | Coupling safety |
| \(\Delta E\) | Identity drift |
| \(d_H\) | Missing constitutional axes |
| \(R_{\text{claim}}\) | **Claim residual** — gate green without sealed promote/federate receipt |

After v7.1 operator align on the durable body: \(\Delta E=0\), promote \(d_H=0\), utility high → \(V\) low on Teach. Residual \(V\) tends to live on: sandbox policy, claim packaging, federated packet honesty.

**Candidate v7.2 math (not implemented as doctrine yet):** make \(R_{\text{claim}}\) and federated admission receipts first-class so “green without receipt” has explicit cost.

---

## 8. Planes vs bits (MAPE-K style reminder)

```text
E Evidence      → feeds e
A Adaptation    → must not mint e or a alone
I Immunity      → repair under a,t (+ verify for readmit)
C Constitutional → capability + policy under a,t
W Witness       → feeds w
```

Forbidden flows (continuity):

```text
A ↛ silently rewrite E
A ↛ manufacture authority in C
A ↛ inspect hidden W
I ↛ mutate A without C
W ↛ certify a different epoch than promoted
```

---

## 9. Candidate systems conjecture

Labeled **conjecture**, not law:

> A persistent adaptive system remains coherent under change only when consequential transitions preserve typed boundaries, derive from valid authority, remain causally traceable, and admit verification or recovery.

**Weaker form already supported by the 7.0→7.1 bump:**

> After a version/constitution change, without re-seal, promote geometry fails even if spectral emergence holds.  
> Therefore coherence does not imply authority.

Falsification protocol for agents/researchers:

1. Record \((\text{coh}, q, \Delta E, \text{allow\_promote})\) before seal.  
2. Bump version or constitution material.  
3. Observe without sealing — expect \(\Delta E=1\), promote blocked.  
4. Seal — expect \(\Delta E=0\), path re-open only with witness as required.

---

## 10. What is *not* the math

| Refuse | Why |
|--------|-----|
| Soft “resonance meters” that self-certify | Collapse bits into vanity scores |
| Physical tesseract / sacred φ | Metaphor only; not physics |
| Learned graph rewriting evidence | Topology law |
| Diagnostics that seal epochs | Identity corruption |
| mesh_green false ⇒ system broken | Immune host-mutation deny is intentional |

---

## 11. Condensed map (agents: memorize this)

```text
spectral / ratio     →  quality of coupling inside a host
epoch ΔE             →  identity derivative (boolean)
q = (e,a,t,w)        →  participation rights (boolean cube)
Hamming path         →  price of a claim
federation           →  product of hosts; shared constitution only
immune_block         →  fixed point: recommend-only
claim residual       →  green gate without receipt still costs
```

**Hybrid control thesis:** continuous/spectral channels for *how well memory works*; discrete sealed bits for *what may compose*. Most adaptive-software failures use the continuous channel as if it were the discrete one.

---

## 12. Implementation index (code)

| Concept | Module |
|---------|--------|
| Body epoch | `cortex/epoch.py` |
| Runtime phases | `cortex/phases.py` |
| Continuity / influence | `cortex/continuity.py` |
| Four-axis geometry | `cortex/constitutional_geometry.py` |
| Op requirements | `cortex/constitutional_requirements.py` |
| Transitions | `cortex/constitutional_transition.py` |
| Diagonals | `cortex/diagonal.py` |
| Legal path (no mutation) | `cortex/constitutional_path.py` |
| Capabilities | `cortex/capabilities.py` |
| Promote gate | `cortex/promote_gate.py` |
| Federation | `cortex/federation.py` |
| Host mesh | `cortex/host_mesh.py` |
| Interconnect mesh | `cortex/interconnect.py` |
| Ratio lattice | `cortex/math_net/ratio_lattice.py` |
| Spectral / multiscale | `cortex/math_net/spectral*.py`, `multiscale.py` |
| Coherence / emergence | `cortex/coherence.py` |
| Topology law | `cortex/topology_law.py` |
| Witness | `cortex/witness.py` |

CLI:

```bash
python -m cortex interconnect --repo <name> --json
python -m cortex continuity --repo <name> --json
python -m cortex epoch observe --repo <name> --json
python -m cortex geometry path --repo <name> --operation promote --authority --json
python -m cortex geometry enumerate --json
python -m cortex host-mesh --primary <name> --json
```

---

## 13. Claim boundary

> This note documents experimental mathematical structure used inside Cortex for memory coupling and constitutional composition. It is a falsifiable systems framework for persistent adaptive software. It is not evidence of consciousness, biological life, physical higher-dimensional geometry, or a universal law of nature. Learned relevance never becomes host mutation authority.

---

## 14. Changelog of ideas

| Arc | Contribution |
|-----|----------------|
| v6.19–6.21 | Explicit spectral math, ratio lattice, triad |
| v6.24–6.25.1 | Evidence/adapt split, capabilities, witness chronology |
| v7.0 | Body epochs, phases, continuity planes |
| v7.1 | \(q=(e,a,t,w)\), diagonals, observe≠ensure |
| this note | Hybrid continuous/discrete map + claim residual sketch |
