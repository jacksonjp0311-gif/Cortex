# Public demos (v7.3 Resonant Frames)

No personal machine paths. Symbolic display only: `./your-project`, `~/.cortex`.

## Resonant Frames classification demo

```bash
python scripts/demo_resonant_frames_public.py
# optional:
python scripts/demo_resonant_frames_public.py --with-flask
```

| Artifact | Description |
|----------|-------------|
| [`demo_resonant_frames_screenshot.txt`](demo_resonant_frames_screenshot.txt) | Terminal “screenshot” |
| [`demo_resonant_frames_report.json`](demo_resonant_frames_report.json) | `field report --json` style payload |

**Scenario A:** `STALE_ECHO` — memory-dominant, weak verified evidence  
**Scenario B:** `COHERENT_DIFFERENTIATED` — differentiated + evidence-aligned  
**Warmup:** `baseline_frames_seen: 3/16`

## Advisory holdout (N=20)

```bash
python scripts/experiment_field_advisory_holdout.py --n 20 --base-k 5
```

| Artifact | Description |
|----------|-------------|
| [`field_advisory_holdout.json`](field_advisory_holdout.json) | hit@k off vs on + lift |

Synthetic gold ranks — **not** production retrieval proof. Advisory-only.

## Claim

Frames are bounded temporal telemetry. No temporal metric can move a constitutional bit.
