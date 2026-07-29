# Cortex Next Evolution — Interconnect Mesh · v5.1 → v6.0

**Status:** Plan (design record; execute in phases)  
**Baseline:** Cortex **v5.0.0** governed local cognition substrate  
**Posture:** Local-first · recommend-only · one SQLite body · covenant-aligned  
**Companion:** `docs/ARCHITECTURE_V4.md` (v4→v5 delivered) · `docs/intelligence/INTERCONNECT.md`

---

## 0. Do not forget (spine that must survive)

```text
v3.5 organism ⊛ / breathe ∽ / ritual ⟳
v3.5.x immune ⚠ / packet block / OPERATOR
v3.6 connect ⧉ gather → metric graph → distill
v5.0 seven capabilities (multi-res · HNSW · ranker · prefetch · contract · agent · causal)
GCMT operational | evidence | canonical
ARIA wake-gated, never executed
Relevance NEVER becomes mutation rights
```

**Sacred law (unchanged):**

```text
One substrate. One Governor. One packet language.
Agent = temporary working cortex.
Cortex = durable body.
Host + human = authority.
```

---

## 1. Thesis: from *organs present* to *organs coupled*

v5.0 **installed** seven advanced organs. They are not yet a single **interconnect mesh**.

| Today (v5.0) | Gap | Next motion |
|---|---|---|
| Connect pass gathers metrics | Ranker/HNSW/prefetch/causal fields partial | Full v5 vector in every connect_pass |
| Ranker trains on outcomes | Promote/rollback of weights not GCMT-first-class | Ranker snapshot receipts |
| Prefetch proposes paths | Precision not fed into causal/ranker features | Closed prefetch→causal→ranker loop |
| Contracts on continuation | Ritual seal / promote not fail-closed on strict | Contract gates on seal + promote |
| Multi-res graph compiles | Activation seeds mostly file-level | Resolution-aware seed + rollup |
| HNSW optional | Not auto-built after bootstrap; no incremental | Bootstrap opt-in + delta insert |
| Causal episodes ad-hoc | Not tied to connect_pass / transcend | Episode per N connects + CI gate |
| Agents register/mint | MCP/remember not token-enforced by default | Optional multi-agent mode flag |
| Organism nervous body | Thin on v5 surfaces | Nervous reports ranker/HNSW/prefetch/causal |

**Design verb for this era: INTERCONNECT** — wire existing organs so each connect pass *strengthens the whole body*, not just one table.

---

## 2. Target interconnect mesh

```text
                    ┌──────────────────────────────┐
                    │   Host + Human Authority     │
                    └──────────────▲───────────────┘
                                   │ never granted by Cortex
                    ┌──────────────┴───────────────┐
                    │  Governor + immune ⚠ + contract│
                    └──────┬───────────┬───────────┘
           ┌───────────────┼───────────┼───────────────┐
           ▼               ▼           ▼               ▼
      Thalamus        Ranker ⇅     Prefetch ⇢     Multi-agent
      (inhibit)     (verified)    (propose)       (tokens)
           │               │           │               │
           └───────┬───────┴─────┬─────┴───────┬───────┘
                   ▼             ▼             ▼
            ┌──────────────────────────────────────────┐
            │   Multi-res graph + HNSW ▦ + FTS + LSH   │
            │   (evidence plane only)                  │
            └──────────────────┬───────────────────────┘
                               ▼
            ┌──────────────────────────────────────────┐
            │  Connect ⧉  → metric_graph → distill     │
            │  Organism ⊛ pulse · Causal ↻ episodes    │
            └──────────────────┬───────────────────────┘
                               ▼
            ┌──────────────────────────────────────────┐
            │  GCMT: operational → evidence → canonical│
            │  promote / rollback / receipt            │
            └──────────────────────────────────────────┘
```

### Coupling contracts (must hold)

| Edge | Rule |
|---|---|
| Prefetch → Thalamus | May only boost lanes already weighted > ε |
| Ranker → Retrieval | Reorders within inhibited set; cannot resurrect hard-inhibited |
| HNSW → Retrieval | Semantic lane only; FTS remains primary for exact tokens |
| Multi-res → Neural fire | Seed at hit resolution; rollup to file for token budget |
| Connect → Causal | Every Kth pass opens/closes micro-episode |
| Causal → Ranker | `regressed` recommends freeze/rollback candidate (not auto) |
| Contract → Ritual/Promote | Strict fail-closed; default warn |
| Token → MCP | When multi-agent mode on, scope ∩ Governor |
| Immune → All | `block: true` freezes ranker train, plasticity, seal, promote |
| Organism → Packet | Nervous/metabolism expose v5 rollups for agent read-first |

---

## 3. Capability depth map (honest v5.0 → target)

| Cap | v5.0 depth | v5.1 target | v5.2 target | v6.0 target |
|---|---|---|---|---|
| **1 Multi-res** | file+symbol+BB proxy | symbol seed in activate | AST spans (Python) | CFG/dataflow edges |
| **2 Ranker** | linear SGD | features from connect/prefetch | promote/rollback snapshot | optional 2-layer MLP |
| **3 Prefetch** | coact+hits | precision→causal | ranker feature `prefetch_hit` | budget adaptive |
| **4 Contract** | continuation default | seal gate optional | promote fail-closed strict | differential suite CI |
| **5 Agents** | register/mint | remember token opt-in | MCP token mode | locks + conflict CLI complete |
| **6 HNSW** | full rebuild | bootstrap `--hnsw` | incremental insert | native optional |
| **7 Causal** | episode + recall Δ | connect-linked episodes | transcend gate | auto rollback *candidates* |

---

## 4. Phased roadmap

### **v5.1 — Interconnect spine** (tight coupling, low myth)

**Theme:** *Make every connect teach the whole body*

| Work | Detail | Evidence |
|---|---|---|
| **I1** | Expand `gather_connect_metrics` with ranker_score, hnsw_hit, prefetch_precision, contract_result, agent_id, multi_res counts | connect_pass payload + tests |
| **I2** | Organism nervous/metabolism surfaces v5 rollups | organism packet fields |
| **I3** | Prefetch outcome auto-record when activate evidence overlaps prediction | prediction_outcomes rows |
| **I4** | Causal micro-episode every N connect passes (N=3 default) | causal_episodes + settings |
| **I5** | Ranker features: `prefetch_hit`, `hnsw_lane`, `coact_strength` | FEATURE_NAMES bump schema 1.1 |
| **I6** | Memory packet `interconnect-mesh.packet.json` + teach seed | retrieval of mesh law |
| **I7** | `cortex interconnect --repo R --json` status surface (read-only mesh health) | CLI/MCP |
| **I8** | CI `smoke_interconnect_mesh.py` | workflow |

**Exit criteria:** activate → metrics shows v5 fields; organism carries them; mesh smoke green; workflow unbroken.

**Risk:** Low–medium (schema/feature dim freeze discipline).

---

### **v5.2 — Gates and govern** (safety edges of the mesh)

**Theme:** *Couple conscience to the new organs*

| Work | Detail | Evidence |
|---|---|---|
| **G1** | Ritual seal: optional `--contract strict` fail-closed | session_ritual |
| **G2** | Promote: reject if strict contract fails or immune block | continuation.promote |
| **G3** | Ranker promote/rollback via GCMT receipt (`canonical_states` key `ranker:linear_v1`) | promote/rollback CLI |
| **G4** | Causal `regressed` → ranker freeze flag in settings | outcomes path |
| **G5** | Multi-agent mode `settings multi_agent:{repo}=on` enforces token on remember/activate MCP | agents |
| **G6** | HNSW build hook after bootstrap when `config.hnsw_on_bootstrap` | bootstrap |
| **G7** | Transcend-check 2.1: mesh coupling assertions | transcend |
| **G8** | OPERATOR.md mesh read order | docs |

**Exit criteria:** cannot promote under immune block; ranker snapshot recoverable; multi-agent default still off.

**Risk:** Medium (workflow friction from contracts — default stays soft).

---

### **v6.0 — Deep structure + closed loop** (advanced, still local)

**Theme:** *Structure that earns its keep; loops that falsify themselves*

| Work | Detail | Evidence |
|---|---|---|
| **D1** | Python AST multi-res (ast nodes optional resolution) | compiler |
| **D2** | Call-graph resolve across files from symbols+imports | edges |
| **D3** | Dataflow_def/use lightweight (name-based) | edges |
| **D4** | HNSW incremental insert on index refresh | vectors |
| **D5** | Prefetch precision closed into ranker + causal CI corpus | benchmarks |
| **D6** | Coverage ingest → covers edges (optional file) | coverage_facts live |
| **D7** | Dashboard 2.0: mesh health one screen | dashboard |
| **D8** | Foreign-host matrix still 3/3; no outside auto-scan | CI |
| **D9** | Transcend 3.0: falsify full mesh + causal non-regression | transcend |

**Exit criteria:** controlled corpus non-regression vs v5.0; mesh dashboard; still offline core path.

**Risk:** High on AST/callgraph ID stability — content-addressed fingerprints mandatory.

---

## 5. New CLI / MCP (planned)

### v5.1

```bash
cortex interconnect --repo R --json
# mesh health: connect averages, hnsw, ranker train_count, causal counts,
# contract last check, agent mode, immune block
```

```text
MCP: cortex_interconnect (read-only)
```

### v5.2

```bash
cortex ranker promote --repo R --json
cortex ranker rollback --repo R --receipt-id r_... --json
cortex ritual ... --contract default|strict|off
cortex agent mode --repo R --on|--off --json
```

### v6.0

```bash
cortex coverage ingest --repo R --from coverage.json --json
cortex graph resolve --repo R --resolution ast --node <id> --json
cortex dashboard --repo R --mesh --json
```

---

## 6. Data model deltas (additive only)

```sql
-- v5.1: no new tables required if settings + existing tables suffice
-- optional:
CREATE TABLE IF NOT EXISTS interconnect_snapshots(
  repo TEXT NOT NULL,
  taken_at REAL NOT NULL,
  mesh_json TEXT NOT NULL,
  mesh_hash TEXT NOT NULL,
  PRIMARY KEY(repo, taken_at)
);

-- v5.2:
-- ranker snapshots already via canonical_states + continuation_receipts
-- settings: ranker_frozen:{repo}, multi_agent:{repo}

-- v6.0:
-- reuse coverage_facts; expand neural_nodes.resolution = 'ast'
```

**Invariant:** still one `cortex.db`; no second authority store.

---

## 7. Safety invariants (mesh-era)

| ID | Invariant |
|---|---|
| M0 | Interconnect status is telemetry; never authorization |
| M1 | Mesh coupling cannot clear immune `block` |
| M2 | Causal “improved” cannot auto-promote or auto-edit host |
| M3 | Ranker promote uses GCMT locks; operational weights may roll back |
| M4 | Prefetch cannot materialize ARIA without wake |
| M5 | Multi-agent tokens cannot include host.mutate (static + runtime) |
| M6 | Contract profiles constrain only; never grant scope |
| M7 | bootstrap/activate/organism/ritual path remains default-compatible |
| M8 | claim_boundary on interconnect and dashboard mesh surfaces |
| M9 | Deterministic core: same repo+task+manifest → same Thalamus + contract check |

---

## 8. First execution slice (when implementing v5.1)

Ordered for maximum interconnect leverage:

1. **`cortex/interconnect.py`** — `mesh_status(store, repo)` folds immune, metrics, hnsw, ranker, causal, agents, last contract.
2. **Wire connect_pass** — attach ranker/hnsw/prefetch/v5 counts already partially present; fill real values from context.
3. **Prefetch outcome** — on activate return, if prediction.trace_id and evidence paths: `record_prediction_outcome`.
4. **Causal every 3 connects** — in `persist_connect_pass` when pass_count % 3 == 0.
5. **Organism nervous** — include mesh snippet (not full dumps).
6. **CLI/MCP + smoke + teach packet**.
7. Version **5.1.0**, CHANGELOG, OPERATOR mesh section.

Estimated effort: **1 focused climb** (same style as v3.6 / v5.0 spikes).

---

## 9. What we refuse

- Cloud vector/ranker APIs as core dependency  
- Auto host mutation from any mesh signal  
- Second database or shadow ledger of record  
- ARIA plan execution  
- Glow metrics without causal/connect falsification  
- Unsolicited foreign-repo scans  
- “Agent majority vote” as truth  

---

## 10. Success picture (v6.0)

An operator on this repo alone can:

```text
bootstrap → immune → organism → (work) → breathe → metrics
                ↓
         interconnect (mesh green)
                ↓
    vectors + ranker + predict couple into each activate
                ↓
         ritual seal under contract
                ↓
    outcome → ranker train → causal verdict
                ↓
         transcend 3.0 passes
```

…and at no point does a high ranker score, bright prefetch, or improved causal verdict become a right to edit the host.

---

## Claim boundary

This document is a **repository-local evolution plan**. It does not claim the mesh is fully implemented, conscious, autonomously self-improving, or authorized to mutate hosts. Human and host authority remain controlling.
