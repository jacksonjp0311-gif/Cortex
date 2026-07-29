# Self-host contact log (Cortex tree only)

All contact here is **this repository**. No other paths.

## Commands

```bash
python -m pytest tests -q
python -m cortex mirror --json
python -m cortex contact --json
python -m cortex self-test --json
```

## Session ritual (Cortex as host after local bootstrap)

```bash
python -m cortex bootstrap . --name CortexBright --json
python -m cortex ritual --repo CortexBright --task "Close bright-point session loop" \
  --remember-kind discovery \
  --remember-text "Packet agent_protocol closes activate-remember-consolidate without a second DB" \
  --json
```

## Bright-point cut (v3.2.2, this tree only)

| Check | Result |
|---|---|
| `pytest` | 55 passed |
| `cortex mirror` | glow true, brightness bright, intensity ~0.92 |
| `cortex contact` | glow true, bright true, intensity ~0.94, synthetic matrix all_passed |
| Session ritual | unit-tested activate → remember → consolidate |

Re-run the commands above to refresh local telemetry. CI remains the public green signal.

## Claim boundary

Self-host proof only. Not multi-repo production certification.
