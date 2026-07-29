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
# work under host/human authority only when immune_action allows
python -m cortex remember --repo Cortex --kind discovery --text "durable fact" --json
python -m cortex breathe --repo Cortex --json
python -m cortex ritual --repo Cortex --task "seal" --remember-text "lesson" --json
python -m cortex transcend-check --json
python -m cortex mirror --json
```

## Read order every activate

1. `cortex immune` / `control_error.immune_action` (if `block: true` → stop host edits)  
2. `instructions`  
3. `agent_protocol.state`  
4. `organism` pulse  
5. `evidence` path:line  

## Refuse

Second DB · auto-ARIA · packet-as-authorization · glow-chasing · unsolicited foreign scans
