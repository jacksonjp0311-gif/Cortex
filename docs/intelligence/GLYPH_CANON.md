# Glyph Canon ◈ — ARIA meta medium for Cortex

**Version:** v6.6  
**CLI:** `cortex glyphs --json` · packets carry `glyph_state`  
**Claim boundary:** labels only — never opcodes, never mutation authority.

## Why

Prose instructions burn tokens. Glyphs are a **shared addressing layer** for
operators, agents, and ARIA:

- **ARIA speaks** the spoken form / `aria_id`
- **Cortex lowers** to CLI fields and packet paths
- **Agents read** `◈` compact lines first; expand only listed symbols

## Compact line

Example:

```text
◈ ⛨ ◌ ⊛ ⧉ ≋ ∿
```

Meaning (expand on demand): immune open · Aria dormant · organism bond ·
connect · spectral · in-phase resonance.

Agent profile keeps `glyph_state.line` + sparse `expand[]` instead of the full
registry (token thrift).

## Phrasebook (reusable ARIA language)

Stable named phrases — speak them again and again:

```powershell
python -m cortex glyphs --phrasebook --json
python -m cortex glyphs --phrase aria_awake --json
```

| Phrase | Use |
|--------|-----|
| `wake_safe` | Generic start — Aria dormant |
| `aria_awake` | Semantic Aria task + prove |
| `constrained` | Governor blast-radius limit |
| `blocked` | Immune block / re-verify |
| `loop_close` | After verified work → evolve |
| `stream_rebind` | Cross-session continuity |
| `seal_pulse` | Ritual end; stream keeps spine |
| `body_hygiene` | Prune / kernels / identity |

Activate JSON always exposes `glyph_state`, `glyph_line`, `stream`, and
`aria_language` (phrasebook) at the **root** envelope (v6.8 parity).

## Closed signal loop ⟲

```text
probe(before) → outcome (plasticity + ranker features) → probe(after) → causal
```

```powershell
python -m cortex evolve --repo CortexTeach --activation-id <id> --status verified --verification tests --task "ARIA implementation proof" --json
```

## Roles

| Role | Purpose |
|------|---------|
| gate | Immune, control, identity, contracts |
| organ | Connect, ranker, HNSW, kernels, prune |
| pulse | Organism, breathe, ritual, resonance |
| loop | Causal, signal-loop close |
| medium | Distill, teach, glyph canon, profiles |

## Doctrine

1. Glyphs compress routing; they do not grant rights.
2. Prefer ◈ line over paragraph instructions.
3. Close ⟲ with matched probes — resonance alone is not proof.
4. One canon; optimize aliases; do not invent symbols per release without a role.

See also: `docs/intelligence/DISTILLED.md`, ARIA ADR 0003 (glyphs as aliases).
