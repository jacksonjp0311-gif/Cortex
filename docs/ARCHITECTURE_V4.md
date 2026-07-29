# Cortex Architecture Upgrade — v4.0 → v5.0

**Status:** Design record (not yet implemented)  
**Baseline:** Cortex **v3.6.0** (living organism ⊛, immune ⚠, connect pass ⧉, teach ☰, GCMT v1.5)  
**Author posture:** Local-first, governed, recommend-only  
**Supersession:** Argues *with* `docs/COVENANT.md`; does not walk around it.

---

## 0. What we already are (do not forget)

Cortex today is **not** a blank slate. Any v4+ design must preserve and extend:

| Surface | Role (v3.x) | Invariant |
|---|---|---|
| One SQLite substrate | inventory, FTS, vectors, graph, neural, sessions, GCMT | No second DB |
| Thalamus | deterministic lane weights + inhibition | Advisory only |
| Neural interlink | file-level sparse graph + bounded Hebbian plasticity | Topology from edges only |
| Governor | normal / constrained / read_only | Never self-expands |
| control_error + immune_action | STOP codes agents cannot miss | `block` ≠ mutation grant |
| Organism ⊛ / breathe ∽ | session co-process pulse chain | Not consciousness |
| Connect pass ⧉ | gather → metric graph → distill | Telemetry, not authority |
| GCMT planes | operational / evidence / canonical | Non-interchangeable |
| ARIA | deferred substrate, wake-gated, never executed | Language ≠ capability |
| Ritual ⟳ / teach ☰ | remember → consolidate; packet seed | Explicit events only |
| Certificates + promote/rollback | hash-chained receipts | Recoverable provenance |

**Sacred law (unchanged):**

```text
Relevance never becomes mutation rights.
Learned never outranks source/tests/runtime.
Packet never becomes authorization.
Promotion never edits host source.
```

---

## 1. Design thesis

Elevate Cortex from **selective memory organ** to **governed local cognition substrate** by adding:

1. **Multi-resolution structure** (where code *is*)
2. **Outcome-gated ranking** (what *helped* under verification)
3. **Proactive evidence** (what will *likely* be needed next)
4. **Formal continuation contracts** (what *must* be true to continue)
5. **Shared multi-agent memory** (who may *read/write* what)
6. **Scalable local vectors** (how to *find* at size)
7. **Causal closed loop** (whether memory *actually* improved agents)

…without cloud, without unauthorized mutation, without non-deterministic core, without second authority.

### System topology (target)

```text
                         ┌─────────────────────────────┐
                         │   Host + Human Authority    │
                         │   (only mutation rights)    │
                         └──────────────▲──────────────┘
                                        │ never granted by Cortex
┌───────────────────────────────────────┴───────────────────────────────────────┐
│                              Governor + immune ⚠                               │
│                     (modes · block · STOP · certificates)                      │
└───────────┬─────────────────────┬─────────────────────┬───────────────────────┘
            │                     │                     │
   ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
   │ Thalamus (det.) │   │ Ranking model   │   │ Contract engine │
   │ lanes + inhibit │   │ (outcome-gated) │   │ (checkable)     │
   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
            │                     │                     │
   ┌────────▼─────────────────────▼─────────────────────▼────────┐
   │              Multi-resolution neural graph + HNSW            │
   │     file → symbol → AST → BB · call · dataflow · coverage     │
   └────────┬─────────────────────┬─────────────────────┬────────┘
            │                     │                     │
   ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
   │ Proactive pre-  │   │ Shared agent    │   │ Causal outcome  │
   │ activation (op) │   │ capability mem  │   │ ledger (closed) │
   └─────────────────┘   └─────────────────┘   └─────────────────┘
            │                     │                     │
            └─────────────────────┴─────────────────────┘
                                  │
                    GCMT: operational | evidence | canonical
                    Connect ⧉ metric graph + organism ⊛ pulse
```

---

## 2. Capability 1 — Hierarchical multi-resolution neural graph

### Intent

Today: **file-level** nodes + edges compiled from structural/Git relations.  
Target: **resolution pyramid** so activation can fire precise basic-blocks while still rolling up to files for packet budgets.

### Data model changes

```sql
-- Extend, do not replace, neural_nodes
ALTER TABLE neural_nodes ADD COLUMN resolution TEXT NOT NULL DEFAULT 'file';
  -- 'file' | 'symbol' | 'ast' | 'basic_block'
ALTER TABLE neural_nodes ADD COLUMN parent_node_id TEXT;
ALTER TABLE neural_nodes ADD COLUMN span_start INTEGER;  -- line or byte
ALTER TABLE neural_nodes ADD COLUMN span_end INTEGER;
ALTER TABLE neural_nodes ADD COLUMN language TEXT;
ALTER TABLE neural_nodes ADD COLUMN fingerprint TEXT;   -- content-addressed span hash

-- Edge kinds (edges.relation / neural_synapses.relation)
-- existing: imports, resolves_to, tested_by, documents, cochange, call (partial)
-- new:
--   calls, called_by, dataflow_def, dataflow_use, covers, covered_by,
--   contains, child_of, next_bb, dominates

CREATE TABLE IF NOT EXISTS coverage_facts(
  repo TEXT NOT NULL,
  test_node_id TEXT NOT NULL,
  target_node_id TEXT NOT NULL,
  coverage_kind TEXT NOT NULL,  -- line | branch | path
  weight REAL NOT NULL,
  source TEXT NOT NULL,         -- e.g. coverage.json path hash
  observed_at REAL NOT NULL,
  PRIMARY KEY(repo, test_node_id, target_node_id, coverage_kind)
);
```

**Node ID scheme (deterministic):**

```text
file:{path_hash}
symbol:{path_hash}:{qualname_hash}
ast:{path_hash}:{node_type}:{span_start}:{span_end}:{body_hash8}
bb:{path_hash}:{fn_qual}:{bb_index}:{body_hash8}
```

### Integration

| System | Integration |
|---|---|
| **Thalamus** | New lanes: `symbol`, `callgraph`, `dataflow`, `coverage`. Intent classifiers map “fix X fails” → coverage+call lanes first. |
| **Governor** | Multi-res expand only when mode ≠ read_only for *plasticity*; read/query always allowed. Budget caps by resolution (BB ≤ symbol ≤ file). |
| **GCMT** | Evidence plane gains span-addressable refs (`path:line-line` + node_id). Canonical may promote *topology receipts*, never host AST edits. |
| **Connect ⧉** | Metrics: `nodes_by_resolution`, `call_edges_fired`, `coverage_hits`. |
| **Organism** | Nervous body reports resolution mix; does not invent topology. |

### CLI / MCP

```bash
cortex graph resolve --repo R --resolution symbol|ast|bb --json
cortex graph neighborhood --repo R --node <id> --depth 2 --json
cortex compile-interlink --repo R --resolutions file,symbol --json
cortex coverage ingest --repo R --from path/to/coverage.json --json
```

```text
MCP: cortex_graph_neighborhood, cortex_compile_interlink
(not MCP: coverage ingest write paths that alter settings beyond evidence)
```

### Safety invariants

1. **Compile-from-evidence only** — no synthetic edges without parser/Git/coverage provenance.
2. **Contains edges are hierarchical only** — child cannot outrank parent for authority.
3. **Coverage is evidence, not truth** — missing coverage ≠ authorization to skip tests.
4. **Plasticity bounded per resolution** — BB synapses have lower max weight ceiling than file.
5. **Packet still path:line first** — agents cite source spans, not opaque node IDs alone.

### Implementation sketch

- Pure Python: `ast` + `tokenize` for Python; tree-sitter optional native for multi-lang.
- Basic blocks: CFG from AST for Python functions (no SSA required in v4.0).
- Call graph: resolve local defs via existing `symbols` + import graph; mark unresolved.
- Compiler: bottom-up build children, emit `contains` synapses; reuse `sync_neural_graph`.
- Activation: seed at highest resolution hit, **rollup** to file for token budget, **drill** one level if confidence low.

### Complexity / risk

| | |
|---|---|
| Complexity | **High** (parsers, CFG, ID stability) |
| Risk | Medium-high — ID churn breaks ledger continuity |
| Mitigation | Content-addressed fingerprints; soft-delete obsolete nodes; migration recipe |

---

## 3. Capability 2 — Tiny local online ranking model

### Intent

Replace pure hand-tuned score fusion with a **tiny, local, online** ranker that updates **only** from **verified outcomes** under GCMT promotion gates. Relevance scores never become rights.

### Data model changes

```sql
CREATE TABLE IF NOT EXISTS ranker_models(
  repo TEXT NOT NULL,
  model_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,   -- cortex-ranker/1.0
  feature_names_json TEXT NOT NULL,
  weights_blob BLOB NOT NULL,     -- float32 little-endian vector
  bias REAL NOT NULL,
  train_count INTEGER NOT NULL,
  last_outcome_id TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  PRIMARY KEY(repo, model_id)
);

CREATE TABLE IF NOT EXISTS ranker_examples(
  example_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  outcome_id TEXT NOT NULL,
  activation_id TEXT NOT NULL,
  feature_vector BLOB NOT NULL,
  label REAL NOT NULL,            -- +1 helpful, -1 harmful, 0 neutral
  verification_type TEXT NOT NULL,
  created_at REAL NOT NULL,
  FOREIGN KEY(outcome_id) REFERENCES task_outcomes(outcome_id)
);
```

**Features (fixed, deterministic, ~16–32 dims):**

```text
thalamus_lane_score, fts_rank, vector_sim, neural_support,
path_depth, recency, cochange, is_test, is_doc, is_aria_deferred,
resolution_level, call_distance, coverage_weight, governor_mode_oh*,
retrieval_confidence, surprise_ratio, prior_credit, immune_block
```

### Integration

| System | Integration |
|---|---|
| **Thalamus** | Ranker reorders *within* inhibited candidate set; cannot restore inhibited-out lanes above Governor floor. |
| **Governor** | Training disabled in read_only; inference always OK. Constrained → lower learning rate. |
| **GCMT** | Weights live in **operational** plane until `cortex promote` of a **ranker snapshot receipt** into canonical. Rollback restores prior weights blob. |
| **Outcomes** | Only `status in {verified, helpful}` with verification payload may train; `unsafe` freezes ranker. |

### CLI / MCP

```bash
cortex ranker status --repo R --json
cortex ranker train --repo R --outcome-id out_... --json   # usually auto from outcome
cortex ranker evaluate --repo R --corpus path.json --json
cortex ranker promote --repo R --model-id m_... --json     # GCMT gate
cortex ranker rollback --repo R --receipt-id r_... --json
```

```text
MCP: cortex_ranker_status (read)
CLI-only: promote / rollback (same as current canonical promotion policy)
```

### Safety invariants

1. **Verified-only learning** — no train on raw activate or fluent chat.
2. **Monotone authority** — ranker cannot change Governor mode or immune `block`.
3. **Bounded weights** — L2 clip + per-feature clamps; no NaN.
4. **Promotion required for canonical** — hot weights are operational; crash recovery may reload last *promoted* snapshot.
5. **Feature set frozen per schema_version** — no silent dim change.

### Implementation sketch

- Pure Python logistic regression or tiny two-layer MLP (numpy optional; pure list math OK).
- Online update: SGD / passive-aggressive on single example after `cortex outcome`.
- Seed from current hand-tuned linear combination (v3 fusion as initial weights).
- Determinism: fixed seed, fixed feature order, float32 round-to-even.

### Complexity / risk

| | |
|---|---|
| Complexity | **Medium** |
| Risk | Medium — reward hacking / spurious correlations |
| Mitigation | Evaluation corpus gate; promote only if non-regression on controlled benchmarks |

---

## 4. Capability 3 — Proactive / predictive context engine

### Intent

Pre-activate **likely** evidence *before* the agent asks, using history + graph + connect-pass metric graph — still recommend-only, still budgeted.

### Data model changes

```sql
CREATE TABLE IF NOT EXISTS prediction_traces(
  trace_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  session_id TEXT,
  task_hash TEXT NOT NULL,
  predicted_node_ids_json TEXT NOT NULL,
  predicted_paths_json TEXT NOT NULL,
  scores_json TEXT NOT NULL,
  materialize_cost INTEGER NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_outcomes(
  trace_id TEXT NOT NULL,
  used_count INTEGER NOT NULL,      -- how many predicted paths entered final packet
  unused_count INTEGER NOT NULL,
  precision REAL NOT NULL,
  outcome_id TEXT,
  PRIMARY KEY(trace_id)
);
```

**Reuse:** `metric_graph:{repo}` path co-activations (v3.6) as prior for co-prefetch.

### Integration

| System | Integration |
|---|---|
| **Thalamus** | Prediction runs *after* route plan; may only boost lanes already weighted > ε. |
| **Governor** | Prefetch depth 0 in read_only (metadata only); constrained = smaller budget. |
| **GCMT** | Predictions are **operational**; never auto-promoted to canonical. |
| **ARIA** | Prefetch **cannot** materialize ARIA bulk unless wake classification already active. |
| **Organism** | Metabolism reports `prefetch_hit_rate`; conscience flags low precision. |

### CLI / MCP

```bash
cortex predict --repo R --task "..." --budget 200 --json
cortex activate --repo R --task "..." --prefetch auto|off|aggressive --json
```

```text
MCP: cortex_predict (read-only proposal)
activate gains optional prefetch flag (default auto under normal mode)
```

### Safety invariants

1. **Prefetch ≠ permission** — pre-activated evidence never implies edit rights.
2. **No ARIA surprise wake** — same wake gates as activate.
3. **Hard token budget** — prefetch shares context budget; cannot exceed.
4. **Audit trail** — every prefetch writes `prediction_traces`.
5. **Precision debt** — repeated unused prefetch raises Governor pressure toward constrained (telemetry only, explicit policy).

### Implementation sketch

```text
score(node) =
  α · P(path | prior tasks co-activation)
+ β · callgraph distance from seed hits
+ γ · ranker score
+ δ · recency / cochange
- ε · deferred_aria_penalty
```

- Pure Python; uses connect-pass graph + neural neighborhood.
- Materialize only spans already indexed (no new file IO beyond existing).

### Complexity / risk

| | |
|---|---|
| Complexity | **Medium** |
| Risk | Medium — noise bloat / false confidence |
| Mitigation | Default conservative; measure precision in causal ledger |

---

## 5. Capability 4 — Machine-checkable formal contracts on continuation packets

### Intent

Every continuation packet carries a **checkable contract** (not natural language alone). Lightweight differential verification proves the next state still satisfies the contract or emits a machine-readable break.

### Data model changes

```sql
-- continuation_packets.payload gains contract block (JSON schema cortex-contract/1.0)
-- Also first-class table for receipts:

CREATE TABLE IF NOT EXISTS contract_checks(
  check_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  packet_id TEXT NOT NULL,
  contract_hash TEXT NOT NULL,
  result TEXT NOT NULL,           -- pass | fail | inconclusive
  breaks_json TEXT NOT NULL,
  differential_json TEXT NOT NULL, -- what changed vs prior packet
  checked_at REAL NOT NULL
);
```

**Contract shape (`cortex-contract/1.0`):**

```json
{
  "schema_version": "cortex-contract/1.0",
  "requires": {
    "governor_modes_allowed": ["normal", "constrained"],
    "immune_block": false,
    "manifest_current": true,
    "certificate_status_in": ["verified"],
    "min_evidence_paths": 1,
    "evidence_must_include_any": ["tests/", "test_"],
    "forbidden_actions": ["edit_host", "ignore_immune_block"],
    "max_scope": ["cortex.canonical.read"],
    "geometry_zero_point": true
  },
  "promises": {
    "claim_boundary_present": true,
    "no_mutation_authority": true,
    "packet_is_not_authorization": true
  },
  "differential": {
    "compare_to_packet_id": "vcp_...",
    "allowed_drift_fields": ["task", "evidence", "operational"],
    "forbidden_drift_fields": ["authority", "grants", "scope_effective"]
  }
}
```

### Integration

| System | Integration |
|---|---|
| **Thalamus** | Contract may require certain evidence kinds; Thalamus routes to satisfy. |
| **Governor** | Contract check is an input to mode; fail → read_only or block consolidate. |
| **GCMT** | Contract is part of verify → authorize → promote chain; fail blocks promote. |
| **Immune** | `immune_block true` always fails contracts that require `immune_block: false`. |

### CLI / MCP

```bash
cortex continuation --repo R --task "..." --contract default|strict|path.json --json
cortex continuation-verify --packet-id vcp_... --json
cortex contract check --packet-id vcp_... --json
cortex contract diff --from vcp_a --to vcp_b --json
```

```text
MCP: cortex_continuation (includes contract), cortex_contract_check (read)
```

### Safety invariants

1. **Fail-closed on promote** — cannot promote if contract fails.
2. **Authority fields immutable under differential** without external grant record.
3. **Contracts cannot grant rights** — they only *constrain*.
4. **Deterministic checkers** — pure functions of packet + repo evidence hashes.
5. **Human-readable breaks** — every fail has code + message + path.

### Implementation sketch

- Pure Python JSON Schema + custom predicates (manifest hash, governor mode, evidence counts).
- Differential: deep-diff of allowed paths; hash equality for forbidden paths.
- Default contract library ships in-repo: `contracts/default.json`, `contracts/strict.json`.

### Complexity / risk

| | |
|---|---|
| Complexity | **Medium** |
| Risk | Low-medium — overly strict contracts block workflows |
| Mitigation | Profiles (default/strict); force only with explicit human flag + receipt |

---

## 6. Capability 5 — Governed multi-agent shared memory

### Intent

Multiple agents may share Cortex memory for one repo under **capability tokens** and **conflict-resolution receipts**. No agent receives host mutation rights from Cortex.

### Data model changes

```sql
CREATE TABLE IF NOT EXISTS agent_principals(
  repo TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  public_key_or_hmac TEXT NOT NULL,  -- local secret reference, not cloud IAM
  created_at REAL NOT NULL,
  PRIMARY KEY(repo, agent_id)
);

CREATE TABLE IF NOT EXISTS capability_tokens(
  token_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  scope_json TEXT NOT NULL,     -- ["memory.read", "memory.remember", "packet.activate"]
  not_before REAL NOT NULL,
  not_after REAL NOT NULL,
  issued_by TEXT NOT NULL,      -- human|bootstrap|rebind
  token_hash TEXT NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memory_conflicts(
  conflict_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  session_a TEXT NOT NULL,
  session_b TEXT NOT NULL,
  path_or_claim TEXT NOT NULL,
  resolution TEXT NOT NULL,     -- keep_a | keep_b | merge | defer_human
  receipt_hash TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS shared_locks(
  repo TEXT NOT NULL,
  resource_key TEXT NOT NULL,   -- e.g. session:canonical:claim_id
  holder_agent_id TEXT NOT NULL,
  token_id TEXT NOT NULL,
  expires_at REAL NOT NULL,
  PRIMARY KEY(repo, resource_key)
);
```

**Capability vocabulary (closed set):**

```text
memory.read
memory.remember
memory.consolidate   -- still subject to Governor + contract
packet.activate
packet.predict
ranker.infer
graph.read
metrics.read
canonical.read
canonical.propose    -- never auto-promote
# NEVER: host.mutate, source.edit, deploy, token.mint_self
```

### Integration

| System | Integration |
|---|---|
| **Governor** | Token scope ∩ Governor mode; tighter wins. |
| **GCMT** | Shared operational memory; canonical still single-writer via promote receipts. |
| **Organism** | Optional multi-agent bond: organism lists `agents[]` but one pulse chain per session resource. |
| **Immune** | Token cannot clear `block`. |

### CLI / MCP

```bash
cortex agent register --repo R --agent-id a1 --name "Codex" --json
cortex token mint --repo R --agent-id a1 --scope memory.read,memory.remember --ttl 8h --json
cortex token revoke --repo R --token-id t_... --json
cortex remember --repo R --agent-id a1 --token t_... --kind discovery --text "..." --json
cortex conflict list --repo R --json
cortex conflict resolve --repo R --conflict-id c_... --resolution keep_a --json
```

```text
MCP: tools require token in arguments when multi-agent mode enabled
cortex_activate, cortex_remember, cortex_ritual (+ token_id)
```

### Safety invariants

1. **No self-mint of broader scope** — only human/bootstrap path mints; rebind can only narrow.
2. **No host.mutate capability exists** in vocabulary.
3. **Conflict receipts hash-chained** like neural ledger / continuation receipts.
4. **Single canonical writer** — concurrent propose OK; promote serializes.
5. **Default single-agent** — multi-agent off unless registered (backward compatible).

### Implementation sketch

- HMAC tokens local to `CORTEX_HOME` secrets file (0600); pure Python `hmac` + `hashlib`.
- Optimistic concurrency on remember: claim fingerprint conflict → `memory_conflicts` row.
- Resolution is explicit CLI; no automatic “majority vote becomes truth.”

### Complexity / risk

| | |
|---|---|
| Complexity | **High** |
| Risk | High — confused deputy / token leakage |
| Mitigation | Short TTL, narrow scopes, audit all mint/revoke, refuse token in logs |

---

## 7. Capability 6 — Fully local deterministic scalable vector index

### Intent

Graduate from LSH buckets + brute candidates to **HNSW (or equivalent)** stored in SQLite (or sidecar mmap under `CORTEX_HOME`), deterministic build order, multi-vector nodes (e.g. summary + chunk + symbol).

### Data model changes

```sql
CREATE TABLE IF NOT EXISTS vector_indices(
  repo TEXT NOT NULL,
  index_id TEXT NOT NULL,
  algorithm TEXT NOT NULL,        -- hnsw_v1
  dim INTEGER NOT NULL,
  metric TEXT NOT NULL,           -- cosine
  params_json TEXT NOT NULL,      -- M, efConstruction, efSearch
  build_fingerprint TEXT NOT NULL,
  created_at REAL NOT NULL,
  PRIMARY KEY(repo, index_id)
);

CREATE TABLE IF NOT EXISTS vector_index_nodes(
  repo TEXT NOT NULL,
  index_id TEXT NOT NULL,
  node_key TEXT NOT NULL,         -- memory_id or multi-vector key
  vector_kind TEXT NOT NULL,      -- chunk | summary | symbol | node
  layer INTEGER NOT NULL,
  neighbors_json TEXT NOT NULL,   -- deterministic sorted ids
  vector_blob BLOB NOT NULL,      -- float32
  PRIMARY KEY(repo, index_id, node_key, vector_kind)
);

-- memories gain optional multi-vector refs
-- memory_vector_buckets retained as fallback / hybrid lane
```

### Integration

| System | Integration |
|---|---|
| **Thalamus** | Semantic lane uses HNSW; FTS lane unchanged; hybrid fusion via ranker. |
| **Governor** | Rebuild allowed always (read path); large rebuild may set constrained recommendation. |
| **GCMT** | Index is evidence infrastructure; not canonical “knowledge.” |
| **Multi-res graph** | Symbol/AST nodes may carry their own vectors. |

### CLI / MCP

```bash
cortex vectors build --repo R --algorithm hnsw_v1 --json
cortex vectors status --repo R --json
cortex vectors query --repo R --text "..." --k 12 --json
cortex migrate-vectors --repo R --to hnsw_v1 --json
```

```text
MCP: cortex_vectors_query (read)
CLI: build / migrate
```

### Safety invariants

1. **Deterministic build** — sorted insert order by `node_key`; fixed RNG seed from repo+manifest.
2. **Local only** — no remote embedding API required; existing local embedder only.
3. **Fallback path** — if HNSW corrupt, degrade to FTS + LSH buckets with certificate note.
4. **No mutation of source** during build.
5. **efSearch bounds** — hard caps to prevent pathological latency as “work proxy.”

### Implementation sketch

- Pure Python HNSW first (`cortex/vectors/hnsw.py`); optional Cython/Rust extension later behind same API.
- Multi-vector: query against kind set; fuse with max or learned ranker features.
- Persist layers as JSON neighbor lists (acceptable to 100k nodes; mmap optional v5).

### Complexity / risk

| | |
|---|---|
| Complexity | **High** |
| Risk | Medium — correctness vs brute force; rebuild cost |
| Mitigation | Property tests vs brute on small repos; incremental insert API |

---

## 8. Capability 7 — Closed-loop causal outcome ledger

### Intent

Measure whether **memory changes** (ranker, plasticity, distill, prefetch, cards) **cause** better future agent performance — not vanity glow.

### Data model changes

```sql
CREATE TABLE IF NOT EXISTS causal_episodes(
  episode_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  task_family TEXT NOT NULL,       -- normalized task class
  baseline_fingerprint TEXT NOT NULL,  -- memory+ranker+graph hash before
  treatment_json TEXT NOT NULL,    -- what changed
  metrics_before_json TEXT NOT NULL,
  metrics_after_json TEXT NOT NULL,
  delta_json TEXT NOT NULL,
  verdict TEXT NOT NULL,           -- improved | regressed | inconclusive
  confounds_json TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS causal_links(
  episode_id TEXT NOT NULL,
  cause_kind TEXT NOT NULL,       -- ranker_update | synapse_plasticity | distill | prefetch | card
  cause_id TEXT NOT NULL,
  effect_metric TEXT NOT NULL,    -- recall_at_k | steps_to_fix | packet_token_efficiency
  effect_delta REAL NOT NULL,
  PRIMARY KEY(episode_id, cause_kind, cause_id, effect_metric)
);
```

**Metrics (local, deterministic proxies):**

```text
retrieval recall@k on fixed corpus
packet token efficiency (useful evidence / tokens)
prefetch precision
time-to-green on recorded test commands (optional, host-invoked only)
immune false-block rate (should stay ~0 on healthy certs)
connect_pass surprise trend
```

### Integration

| System | Integration |
|---|---|
| **Connect ⧉** | Each pass can open/close micro-episodes. |
| **GCMT** | Causal verdicts inform promote/rollback recommendations; never auto-promote. |
| **Governor** | Sustained regression → recommend constrained + ranker rollback candidate. |
| **Mirror / transcend** | Include causal non-regression gate. |

### CLI / MCP

```bash
cortex causal status --repo R --json
cortex causal evaluate --repo R --corpus benchmarks/corpora/cortex_retrieval.json --json
cortex causal report --repo R --since 7d --json
cortex outcome --repo R ... --link-episode auto   # existing outcome extended
```

```text
MCP: cortex_causal_status, cortex_causal_report (read)
```

### Safety invariants

1. **No self-congratulation** — glow intensity ≠ causal improvement.
2. **Counterfactual humility** — mark `inconclusive` when confounds dominate.
3. **Treatments recorded** — every plasticity/ranker/distill write cites episode or creates one.
4. **Human-visible regressions** — report lists cause_ids to roll back.
5. **Does not authorize** — even “improved” cannot edit host.

### Implementation sketch

- Before/after hash of (ranker weights, synapse weight sample, card set, metric graph averages).
- Run controlled corpora (already in CI) as effect measures.
- Simple difference-in-differences per task_family; no Bayesian cloud service.

### Complexity / risk

| | |
|---|---|
| Complexity | **Medium-high** |
| Risk | Medium — false causal claims |
| Mitigation | Prefer `inconclusive`; require repeated episodes for promote recommendations |

---

## 9. Cross-cutting safety architecture

### Invariants that must hold on every release

| ID | Invariant |
|---|---|
| S0 | One SQLite substrate (sidecars under CORTEX_HOME OK; not second authority DB) |
| S1 | Recommend-only: no path from relevance/rank/prefetch/contract-pass → host mutation |
| S2 | Governor + immune_action remain hard gates on ritual seal and promote |
| S3 | GCMT planes non-interchangeable; promote/rollback hash-chained |
| S4 | ARIA never auto-executed; wake-gated materialization only |
| S5 | Deterministic core: same repo+task+manifest → same route plan & contract check |
| S6 | Local-only: no network dependency for core activate/predict/rank/vectors |
| S7 | Capability tokens cannot mint host.mutate (vocabulary exclusion) |
| S8 | Verified outcomes only train ranker / admit ARIA cues / causal “improved” |
| S9 | Existing CLI workflow preserved: `init → bootstrap → activate → organism → ritual` |
| S10 | claim_boundary on every new supervisory surface |

### Authority lattice (unchanged topology)

```text
Human / host repo policy
        ▲
        │ only external grants expand scope
Governor modes + immune block
        ▲
GCMT promote / rollback
        ▲
Contracts (constrain only)
        ▲
Ranker / neural / prefetch / multi-agent memory
        ▲
Raw retrieval relevance
```

---

## 10. Integration with existing v3.6 workflow

**Must not break:**

```bash
python -m cortex init --json
python -m cortex bootstrap . --name Cortex --json
python -m cortex immune --repo Cortex --json
python -m cortex organism --repo Cortex --task "..." --json
python -m cortex metrics --repo Cortex --json
python -m cortex remember --repo Cortex --kind discovery --text "..." --json
python -m cortex breathe --repo Cortex --json
python -m cortex ritual --repo Cortex --task "..." --remember-text "..." --json
python -m cortex teach --seed --repo Cortex --json
python -m cortex transcend-check --json
```

**Additive defaults:**

| Flag | Default | Notes |
|---|---|---|
| `--prefetch` | `auto` | off if read_only |
| `--resolution` | `file,symbol` | bb opt-in |
| `--ranker` | `on` if model exists else `legacy` |
| `--contract` | `default` on continuation | activate unaffected |
| multi-agent | off | until `agent register` |

Connect pass ⧉ remains the **telemetry spine**: every new subsystem emits fields into `gather_connect_metrics` so metric graphs keep growing.

---

## 11. Phased roadmap

### Release **v4.0** — Structure + Vectors foundation  
**Theme:** *See finer, find faster — still safe*  
**Target capabilities:** **1** (multi-res graph file+symbol), **6** (HNSW v1)

| Work | Detail |
|---|---|
| Graph | Symbol resolution nodes + contains/calls edges; coverage ingest optional |
| Vectors | Pure-Python HNSW; migrate-vectors path; hybrid with FTS |
| Thalamus | Lanes for symbol + callgraph |
| Connect ⧉ | Resolution + vector latency metrics |
| CI | Multi-res compile smoke; HNSW recall≥brute on tiny fixture |
| Docs | DATA_MODEL + ARCHITECTURE update |

**Exit criteria:** bootstrap/activate/organism green; file-only mode still works; certificate notes vector algorithm.

**Risk focus:** node ID stability, rebuild time.

---

### Release **v4.1** — Learning + contracts + prefetch  
**Theme:** *Learn only from proof; continue only under contract*  
**Target capabilities:** **2** (ranker), **3** (prefetch), **4** (contracts)

| Work | Detail |
|---|---|
| Ranker | Online linear model; train on outcome; promote/rollback |
| Prefetch | Co-activation + callgraph predict; activate --prefetch |
| Contracts | cortex-contract/1.0; continuation default contract; check/diff CLI |
| GCMT | Ranker snapshot as promotable artifact |
| Causal prep | episode stubs around outcome + evaluate |
| CI | Ranker non-regression; contract fail-closed promote test |

**Exit criteria:** verified-only training tests; contract failure blocks promote; prefetch precision logged.

**Risk focus:** reward hacking, contract rigidity.

---

### Release **v4.2** — Multi-agent + causal closed loop  
**Theme:** *Share memory without sharing power; measure real improvement*  
**Target capabilities:** **5** (multi-agent), **7** (causal ledger); deepen **1** (AST optional)

| Work | Detail |
|---|---|
| Agents | principals, tokens, locks, conflict receipts |
| MCP | token-required mode |
| Causal | full episodes + report; mirror/transcend gate |
| AST | opt-in resolution for Python |
| Immune | token cannot clear block (test) |

**Exit criteria:** two-agent conflict receipt path; causal report on CI corpus; no host.mutate in vocabulary (static test).

**Risk focus:** confused deputy, false causal claims.

---

### Release **v5.0** — Advanced local cognition substrate  
**Theme:** *Unified governed local intelligence — still recommend-only*  
**Target capabilities:** all seven production-hardened

| Work | Detail |
|---|---|
| BB resolution | basic-block + dataflow for Python; optional tree-sitter |
| Ranker | tiny MLP optional; multi-vector features |
| HNSW | incremental insert; optional native accel |
| Prefetch | closed-loop with causal precision targets |
| Multi-agent | session co-process multi-principal organism view |
| Contracts | differential suite + strict profile for promote |
| Causal | automatic rollback *candidates* (human applies) |
| Transcend 2.0 | falsifies all seven capabilities’ safety invariants |

**Exit criteria:**

- Full controlled benchmark suite non-regression vs v3.6 baseline  
- transcend-check + causal + contract + immune all green  
- OPERATOR.md single path still works offline  
- Covenant axes unchanged in meaning  

---

## 12. Suggested package layout (additive)

```text
cortex/
  graph/           # existing + multi_res.py, coverage.py
  neuron/          # compiler gains resolution
  vectors/         # hnsw.py, index.py
  ranker/          # model.py, features.py, train.py
  predict/         # prefetch.py
  contract/        # schema.py, check.py, diff.py
  agents/          # tokens.py, conflict.py
  causal/          # episodes.py, report.py
  connect_pass.py  # extend gather fields only
  control_error.py # untouched authority semantics
  governor.py      # mode inputs only
```

---

## 13. Complexity summary

| Capability | Complexity | Risk | Phase |
|---|---|---|---|
| 1 Multi-res graph | High | Med-High | 4.0 → 5.0 |
| 2 Online ranker | Medium | Medium | 4.1 |
| 3 Prefetch | Medium | Medium | 4.1 |
| 4 Contracts | Medium | Low-Med | 4.1 |
| 5 Multi-agent | High | High | 4.2 |
| 6 HNSW vectors | High | Medium | 4.0 → 5.0 |
| 7 Causal ledger | Med-High | Medium | 4.2 → 5.0 |

---

## 14. Explicit non-goals (refuse)

- Cloud embeddings, remote vector DBs, multi-tenant SaaS control plane  
- Autonomous host editing, CI green-as-authority, “agent majority” mutation  
- Consciousness, biological fidelity, unrestricted Hebbian growth  
- Second memory database or shadow ledger of record  
- ARIA plan execution  
- Letting ranker/prefetch/contract-pass clear immune `block`  

---

## 15. First implementation spike (when executing)

1. **Symbol-level nodes + contains/calls** (no BB yet) behind `--resolution symbol`.  
2. **HNSW pure Python** with brute-force equivalence tests.  
3. Wire both into Thalamus lanes + connect_pass metrics.  
4. Keep file-only path default until certificate `graph_resolution: symbol` opted in.

That spike is the honest on-ramp to v4.0 without breaking the organism/immune/connect spine we already climbed.

---

## Claim boundary

This document is an **architecture plan** for repository-local evolution of Cortex. It does not assert that these systems are implemented, conscious, autonomously self-improving, or authorized to mutate host repositories. Human and host authority remain controlling at every stage.
