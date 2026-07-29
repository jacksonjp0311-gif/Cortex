# Transcend — run Cortex from the packet alone

Operational definition:

> A capable agent can run Cortex **from the packet alone**, close a session
> with **ritual**, and keep the **mirror bright** — without new organs and
> without leaving this repository unless the operator names a path.

## One language, every door

| Door | How the agent gets `agent_protocol` |
|---|---|
| CLI `activate` | Full context packet fields |
| CLI `context` / `protocol` / `nexus-packet` | Same `instructions` + `agent_protocol` |
| CLI `ritual` | Closed loop activate→remember→consolidate |
| MCP `cortex_activate` | Full activate result |
| MCP `cortex_context` | `cortex-context/1.1` with protocol |
| MCP `cortex_ritual` | Same ritual as CLI |
| Wrappers `.cortex/bin/cortex.ps1\|.sh` | `activate`, `ritual`, remember, consolidate |

If a door does not speak this language, it is a bug.

## Agent loop (no lore)

```text
1. activate / cortex_context / cortex_activate
2. READ: instructions, agent_protocol.state, evidence path:line
3. OBEY governor_mode:
     read_only   → diagnose only; no host edits
     constrained → minimal reversible edits only
     normal      → work under host/human authority
4. remember durable facts
5. consolidate OR ritual to close
```

## Forced red modes

Packets **prefix** hard STOP instructions when governor is `read_only` or
`constrained`. `agent_protocol.state.work_allowed` and `allowed_actions` make
this machine-checkable.

## Refuse (everywhere)

- second memory database  
- auto-execute ARIA  
- treat packet as authorization  
- glow-chasing without gates  
- unsolicited foreign repo scan  

## Progress glyphs (ARIA labels → Cortex surfaces)

| Glyph | Spoken | Maps to |
|---|---|---|
| ⟡ | transcend check | `cortex transcend-check` |
| ▣ | packet profile | `cortex activate --profile agent\|debug\|minimal` |
| ⚠ | control error | `packet.control_error` (read first) |
| ⌖ | retrieval gate | `cortex evaluate --mode retrieval` |
| ⟳ | ritual idempotent | `cortex ritual` |
| Δ | incremental surprise | `packet.efficiency.surprise` |
| ☰ | teach surface | `cortex teach` |

Capability-free. Never auto-execute. Never authorize mutation.

## Self-host checks (this tree)

```bash
python -m pytest tests -q
python -m cortex transcend-check --json
python -m cortex mirror --json
python -m cortex contact --json
python -m cortex teach
```

## Claim boundary

Transcendence here is instrument usability, not consciousness or universal
production certification.
