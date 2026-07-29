# Phase plan — Continuum multi-lane evolution (v6.11)

**Authority:** recommend-only · one SQLite body · never host.mutate  
**Glyph:** ⟲ continuum · ❖ grow/seal · 〰 stream · ✂ prune · ▣ packs · ◈ ops  

---

## Theme

Wire the six evolution lanes into **one deliberate command** so operators stop thrashing isolated tools:

| Lane | Surface |
|------|---------|
| Use → teach → measure | activate + remember + signal loop + light ritual |
| Cadence | progress-logged observe/inject (bounded cycles) |
| Packs | install/index core intel + domain probe |
| Prune + graph | census + policy dry-run (apply opt-in) |
| Stream / glyphs | stream status + canon phrase / state encode |
| Ops surface | unified report + prove checklist |

---

## Deliverables

- `cortex continuum --repo R [--cycles 24] [--json]`
- `cortex/continuum.py` — `run_continuum(...)`
- Cadence `progress_every` + CLI `--progress` / `--progress-every`
- Report under `CORTEX_HOME/logs/continuum-*.json`
- Tests: `tests/test_continuum.py`

---

## Non-goals

- 1000-cycle thrash by default  
- Auto-ARIA execution  
- Silent aggressive prune  
- Pages / marketing work  

---

## Operator recipe

```bash
# Full multi-lane pass (default progress on stderr)
python -m cortex continuum --repo Cortex --cycles 24 --json

# Cadence only with live progress
python -m cortex cadence --repo Cortex --cycles 40 --progress --progress-every 5 --json

# Prove-style spot checks
python -m cortex packs list --json
python -m cortex graph --repo Cortex --stats --json
python -m cortex prune --repo Cortex --policy integrate_soft --dry-run --json
python -m cortex stream --repo Cortex --json
python -m cortex glyphs --phrase grow_seal --json
```

---

## Claim boundary

Continuum **orchestrates** existing organs. It does not add a second brain, grant mutation authority, or replace human judgment on prune apply.
