# Cortex operator path (this repo)

Forward path only. No outside repos unless you name one.

```bash
pip install -e .
python -m cortex init --json
python -m cortex bootstrap . --name Cortex --json
python -m cortex teach --seed --path . --repo Cortex --json
# lean loop (v6.2 — fewer tokens)
python -m cortex immune --repo Cortex --json
python -m cortex interconnect --repo Cortex --json
python -m cortex kernels --repo Cortex --json
python -m cortex activate --repo Cortex --task "heal lattice" --budget 800 --profile agent --json
python -m cortex remember --repo Cortex --kind discovery --text "fact" --json
python -m cortex ritual --repo Cortex --task "seal" --remember-text "lesson" --contract default --json
python -m cortex distill --repo Cortex --json
python -m cortex dashboard --repo Cortex --mesh --json
```

## v5 surfaces (additive)

| Command | Purpose |
|---|---|
| `vectors build\|status\|query` | Local HNSW index |
| `ranker status` | Verified-only ranking model |
| `predict` | Prefetch proposal (not rights) |
| `contract check\|diff` | Continuation contracts |
| `agent register\|list` | Multi-agent principals |
| `token mint\|revoke\|validate` | Capability scopes (no host.mutate) |
| `causal report\|evaluate` | Closed-loop memory effect ledger |
| `compile-interlink` | Multi-res neural compile |

## v6 mesh + gates

```bash
python -m cortex interconnect --repo Cortex --json
python -m cortex prune --repo Cortex --dry-run --json
python -m cortex prune --repo Cortex --decay --json
python -m cortex ritual --repo Cortex --task "seal" --contract default --json
# --contract strict fails closed without --force when contract breaks
```

| Command | Purpose |
|---|---|
| `interconnect` | Mesh health, bottlenecks, gates, glyph map |
| `prune` | Drop weak unused synapses; optional weight decay |
| `ritual --contract` | default \| strict \| off seal gates |

Mesh law: high ranker score, bright prefetch, or causal “improved” still never
equals host edit rights. Glyphs are our medium — labels, never opcodes.

## v6.1 spectral

```bash
python -m cortex kernels --repo Cortex --annotate --json
python -m cortex dashboard --repo Cortex --mesh --json
python -m cortex ranker promote --repo Cortex --authorize-promote --json
python -m cortex ranker rollback --repo Cortex --json
```

| Release | Theme | Status |
|---|---|---|
| **v6.1** | Kernel spectrum + closed loops + mesh dashboard | **shipped** |
| **v6.2** | Fold + lean packets + multi-agent tokens | **shipped** |
| **v7.0** | AST/CFG when IDs stable | planned |

### Multi-agent (opt-in)

```bash
python -m cortex agent register --repo Cortex --agent-id a1 --name "Agent" --json
python -m cortex agent mode --repo Cortex --on --json
python -m cortex token mint --repo Cortex --agent-id a1 --scope memory.remember --scope packet.activate --json
python -m cortex remember --repo Cortex --kind discovery --text "x" --token <token_id> --json
python -m cortex agent mode --repo Cortex --off --json
```

Principle: **distributed retention kernels**, not one memory scalar.

## Read order every activate

1. `cortex immune` / `control_error.immune_action` (if `block: true` → stop host edits)  
2. `instructions`  
3. `agent_protocol.state`  
4. `organism` pulse  
5. `evidence` path:line  

## Refuse

Second DB · auto-ARIA · packet-as-authorization · glow-chasing · unsolicited foreign scans
