# Cortex operator path (this repo)

Forward path only. No outside repos unless you name one.

```bash
pip install -e .
python -m cortex init --json
python -m cortex bootstrap . --name Cortex --json
python -m cortex teach --seed --path . --repo Cortex --json
python -m cortex immune --repo Cortex --json
# if block: true → diagnose only; no host edits
python -m cortex organism --repo Cortex --task "interconnect immune first" --json
# each connect expands metric graph + may distill lessons into body
python -m cortex metrics --repo Cortex --json
# work under host/human authority only when immune_action allows
python -m cortex remember --repo Cortex --kind discovery --text "durable fact" --json
python -m cortex breathe --repo Cortex --json
python -m cortex ritual --repo Cortex --task "seal" --remember-text "lesson" --json
python -m cortex metrics --repo Cortex --json
python -m cortex vectors build --repo Cortex --json
python -m cortex ranker status --repo Cortex --json
python -m cortex predict --repo Cortex --task "interconnect" --json
python -m cortex compile-interlink --repo Cortex --resolutions file,symbol,basic_block --json
python -m cortex causal report --repo Cortex --json
python -m cortex transcend-check --json
python -m cortex mirror --json
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
| **v6.2** | Multi-agent under tokens | planned |
| **v7.0** | AST/CFG when IDs stable | planned |

Principle: **distributed retention kernels**, not one memory scalar.

## Read order every activate

1. `cortex immune` / `control_error.immune_action` (if `block: true` → stop host edits)  
2. `instructions`  
3. `agent_protocol.state`  
4. `organism` pulse  
5. `evidence` path:line  

## Refuse

Second DB · auto-ARIA · packet-as-authorization · glow-chasing · unsolicited foreign scans
