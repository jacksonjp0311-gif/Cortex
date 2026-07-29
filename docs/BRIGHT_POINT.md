# Bright Point — frozen alignment

**Release:** Cortex v3.2.3 (Bright Point + Transcend packet surfaces)  
**Scope:** This repository only. No external host contact unless the operator names a path.

## What is frozen as true

| Claim | Evidence surface |
|---|---|
| Geometry latched | `geometry.zero_point` on context packets |
| ARIA deferred economics | bootstrap inventory ≠ full index; wake materializes once |
| Probe quarantine | verify cannot erase deferred bulk |
| Fluency | adversarial corpus; 0 false / 0 missed wakes on CI |
| Synthetic contact | foreign matrix import-safe; CI green |
| Session ritual | `activate → remember → consolidate` via `cortex ritual` |
| Authority | packet never authorizes mutation |

## Agent-facing packet (no lore required)

Read these fields in order:

1. `instructions` — numbered steps  
2. `agent_protocol.steps` — commands  
3. `agent_protocol.state` — governor / ARIA / deferred  
4. `evidence` — path:line ranges  
5. `aria_materialization` — dormant/active + materialized_this_turn  
6. `geometry` — interlock map  
7. `claim_boundary` / refuse lists — hard stops  

## Self-host only

Allowed verification on this tree:

```bash
python -m pytest tests -q
python -m cortex mirror --json
python -m cortex contact --json
python -m cortex self-test --json
```

Do not bootstrap arbitrary Desktop repositories.

## Refuse list (operational)

- new regions / second DBs  
- auto-ARIA execution  
- glow-chasing  
- treating packets as authorization  

## Claim boundary

This document freezes repository-local alignment. It does not prove universal
production readiness or grant rights over any other repository.
