# Data Model

Cortex uses **one** SQLite database, normally `~/.cortex/cortex.db` (v6.1+ lattice).

## Core invariant

```text
one repository identity · one SQLite body · one Governor · one consolidation path
```

## Repository assimilation

- `repositories`: stable target identity, path, manifest, and bootstrap status.
- `files`: complete visible inventory and status (incl. `substrate_deferred` for ARIA bulk).
- `memories`: indexed chunks with line ranges, hashes, vectors, and metadata.
- `memories_fts`: FTS5 lexical index.
- `memory_vector_buckets`: deterministic LSH semantic candidate sketches (fallback lane).
- `symbols`: extracted symbols and signatures.
- `edges`: structural/temporal relations (`imports`, `resolves_to`, `tested_by`, `calls`,
  `dataflow_use`, `documents`, `co_changed`, …).
- `git_commits` / `file_telemetry`: bounded Git churn and co-change.

## Episodic and consolidated memory

- `sessions` / `events`: focus and append-only working memory.
- Discovery Cards: indexed memories with session provenance (**retain** kernel class).

## Environment

- `environment_profiles`: deterministic host profile JSON per repository.

## Neural interlink (multi-resolution)

- `neural_nodes`: file / symbol / basic_block nodes; columns
  `resolution`, `parent_node_id`, `span_start`, `span_end`, `fingerprint`.
- `neural_synapses`: bounded weights; metadata may include
  `kernel_class` ∈ {`reset`,`integrate`,`retain`}, `hierarchical`.
- `neural_activations` / `neural_ledger`: activation packets and hash-chained events
  (`connect_pass`, `organism_pulse`, `graph_pruned`, `ranker_*`, …).

## Governed continuation (GCMT)

- `continuation_packets`, `canonical_states`, `continuation_receipts`.

## v5–v6 substrate tables (same DB)

| Table | Role |
|---|---|
| `coverage_facts` | Optional test→target coverage edges |
| `ranker_models` / `ranker_examples` | Local online ranker (verified outcomes) |
| `prediction_traces` / `prediction_outcomes` | Prefetch proposals + precision |
| `contract_checks` | Machine-checkable continuation/seal contracts |
| `agent_principals` / `capability_tokens` | Multi-agent identity + scopes (no host.mutate) |
| `memory_conflicts` / `shared_locks` | Conflict receipts + locks |
| `vector_indices` / `vector_index_nodes` | Local deterministic HNSW |
| `causal_episodes` / `causal_links` | Closed-loop outcome ledger |

## Settings keys (selected)

| Key | Purpose |
|---|---|
| `metric_graph:{repo}` | Connect rollups, co-activations, retention_by_class |
| `kernel_profile:{repo}` | Spectral δ/ρ per reset/integrate/retain |
| `ranker_frozen:{repo}` | Freeze train after unsafe/block/causal |
| `ranker_canonical:{repo}` | Last promoted ranker snapshot (fallback) |
| `multi_agent:{repo}` | `{enabled: bool}` — token required when on |
| `organism_pulse:{repo}` | Prior pulse chain |
| `prune:{repo}` | Last prune receipt |
| `aria_cue_profile:{repo}` | Learned ARIA cues (wake only) |

## Spectral classes (not tables — metadata)

| Class | Typical surfaces | Prune bias |
|---|---|---|
| `reset` | weak unused synapses | prune/decay first |
| `integrate` | calls, ranker, prefetch, connect | moderate |
| `retain` | hierarchy, cards, tested_by/docs | protected |

## Provenance

Evidence keeps path, line range, kind, content hash, embedding model, selection source.
Neural/kernel metadata never replaces source authority.

## Claim boundary

Schema is local operational structure. It grants no host mutation rights.
