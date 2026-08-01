# Phase v7.2 — Hermetic Attach

**Tagline:** The repository is no longer alone. Host remains sovereign.

## What

Zero-friction attach of Cortex to **any** repository using **external-home** isolation:

- Body: `CORTEX_HOME` / `~/.cortex` (never inside host by default)
- Host: unmodified (no `.cortex/` sidecar in external mode)
- Engine: installed package / uvx / pipx — not required as the host tree

## Ritual interface

Solar-lunar cadence with living 1.2s symbol pulse (TTY only). Peak interlock → pyramidion seal → `Returned to ROOT.`

Psychological design is **interface entrainment**, not a claim of consciousness or sacred authority over the host.

Disable: `CORTEX_ATTACH_RITUAL=0` or `--no-ritual` / `--json`.

## Commands

```bash
cortex-attach .
python -m cortex attach .
uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach .
```

## Claim boundary

> Hermetic attach is a governed interlock and re-integration ritual for local memory. It does not grant host mutation authority, claim AGI, or prove production readiness.
