# Phase v7.3.0 — Resonant Frames

**Tagline:** Distributed activity becomes useful when it forms a differentiated, evidence-aligned frame.

## Placement

```
fusion ticks → channel samples → bounded frame → temporal metrics
  → deterministic classification → advisory retrieval/regime policy
  → constitutional gate remains controlling
```

## Surfaces

| Surface | Behavior |
|---------|----------|
| `cortex field report/trace/latest/verify/baseline/policy` | Observation-only |
| `cortex field close` | Persist frame; never seals epoch |
| `cortex field calibrate --shadow` | Candidate only |
| `cortex field cleanup` | Dry-run default; field keys only |
| Fusion injection | `resonant_frame` compact + advisory instruction |
| Activation advanced | Seeds field; policy only if `CORTEX_FIELD_ADVISORY=1` |
| Activation evidence_baseline | Read-only latest receipt; no adaptive append |
| Coherence | Separate `temporal_field` panel; score unchanged |
| Claim receipts | May reference frame_id/hash as **supporting context only** |

## Public demo + holdout

```bash
# STALE_ECHO vs COHERENT_DIFFERENTIATED (TEMP paths only; symbolic host/body display)
python scripts/demo_resonant_frames_public.py
# optional real public tree:
python scripts/demo_resonant_frames_public.py --with-flask

# Advisory width holdout (N=20 synthetic tasks)
python scripts/experiment_field_advisory_holdout.py --n 20 --base-k 5
```

Artifacts: `work/demo_resonant_frames_report.json`, `work/demo_resonant_frames_screenshot.txt`,
`work/field_advisory_holdout.json`.

## Warmup messaging

`cortex field report --json` includes:

```json
"baseline_frames_display": "3/16",
"baseline_warmup": {
  "baseline_frames_seen": 3,
  "baseline_frames_target": 16,
  "baseline_ready": false,
  "baseline_message": "baseline warming (3/16 frames; need 16 ...)"
}
```

`N_F` stays **null** until ≥3 channel baselines exist — never a fake midpoint.

## Disable / rollback

- `CORTEX_FIELD=0` disables collection (v7.2 behavior).
- `field cleanup --apply` removes `field_*` settings keys only.

## Claim boundary

Resonant Frames are bounded temporal telemetry. They do not grant authority, witness, epoch, evidence axis satisfaction, or host mutation permission.
