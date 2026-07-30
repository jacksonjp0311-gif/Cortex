# Phase v6.23 — Foreign Emergence

**Thicken host phase** so foreign/cold hosts can reach **emergent coupling** without merging identities.

## Why

After v6.22, foreign *suite* recall can be 1.0 while PulseFlow stays **non-emergent** because:

- `ranker_warm = train_count / 15` needs **≥7** trains for couple active (0.45)
- `fusion_coupling` is **0.32** when fuse closed; **≥0.55** when open

Suite utility ≠ host phase. This phase closes that gap.

## Operators

| Piece | Module |
|-------|--------|
| `thicken_host_phase` | `foreign_emerge.py` — fuse open + ticks + path-token ranker warm + activate |
| `thicken_mesh_cold_hosts` | mesh-wide non-emergent foreign (optional cold engine) |
| CLI `foreign-emerge` | single host |
| CLI `host-mesh --thicken` | observe then thicken |
| self-org hook | after foreign measure, thicken if not emergent |

## CLI

```bash
python -m cortex foreign-emerge --repo PulseFlow --fuse-ticks 4 --target-trains 8 --json
python -m cortex host-mesh --thicken --thicken-foreign-only --json
```

## Claim boundary

Per-host memory phase only. **Not** host source mutation. **Not** identity merge. **Not** consciousness.
Primary body ranker still warms only from **train** split; foreign path tokens warm **that host’s** ranker.
