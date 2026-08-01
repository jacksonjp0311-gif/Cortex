# Phase v7.6.0 — Verified Operating Regime (Warm-In Closure)

**Tagline:** Close the self-sensing milestone: warm baselines, replay-stable classification, hashed readiness — still not autonomy.

**Built on:** v7.5 Self-Sensing · v7.4 Continuity Realignment · v7.3 Resonant Frames

## Why

v7.5 defined the observer. Live bodies still reported:

- field baseline cold (`0/16`)
- observer EMA cold
- epoch/phase unbound → **UNBOUND** (correct)

v7.6 is the **protocol that warms the regime** under operator control, then stamps a **milestone receipt**.

## Flow

```text
warm-in status          (observe readiness)
        ↓
warm-in run
  ├─ if epoch stale → realign apply (only with --i-authorize-realign)
  ├─ field warm ticks + field close rounds
  ├─ self-sensing observe updates (EMA when epoch current)
  ├─ replay stability check
  └─ warm-in receipt (hashed)
        ↓
warm-in verify
```

## CLI

```bash
python -m cortex warm-in status --repo MyProject
python -m cortex warm-in run --repo MyProject --rounds 3 --field-ticks 4 --sense-updates 4
# if continuity stale:
python -m cortex warm-in run --repo MyProject --i-authorize-realign
python -m cortex warm-in verify --repo MyProject --json
```

## Success criteria (milestone)

| Check | Meaning |
|-------|---------|
| epoch current | no `needs_realign` |
| field ≥16/16 or field ready | temporal baseline |
| ≥3 channel baselines | field distributions |
| observer ≥16 updates | self-sensing EMA |
| replay stable | same classification twice |
| no false NOMINAL if unbound | hard gate |
| advisory only | no authority |

## Non-negotiables

- No host mutation  
- No silent epoch seal  
- No constitutional bit write  
- No capability / promote / auto ARIA  
- No consciousness claim  

## Claim boundary

A Verified Operating Regime is warm, replay-stable self-sensing under current epoch and phase binding. Milestone pass is **telemetry readiness**, not authority.
