# Phase v7.4.0 — Continuity Realignment

**Tagline:** When the seal lags the living tree, realign explicitly — never silently.

**Built on:** v7.3 Resonant Frames · v7.2 Hermetic Attach · v7.1 constitutional geometry · v7.0 body epochs

## Why this phase

Interconnect after v7.3 showed a living body that was **coupled but not current**:

- sealed epoch version lagged live engine (`7.1.2` vs `7.3.x+`)
- `epoch_stale_or_mismatched` bottleneck
- Resonant Frame baseline cold (`0/16`)
- mesh amber, not green

v7.4 turns that diagnosis into an **operator path**, not a silent fix.

## Canonical statement

> Cortex may report drift freely. Cortex may seal a new body epoch only when the operator authorizes realign. No silent seal on interconnect, activate, or import.

## Flow

```
interconnect / realign diagnose  (observe-only)
        ↓
realign plan                     (still observe-only)
        ↓
realign apply --i-authorize-realign
        ↓
seal_epoch_transition + phase QUIESCENT
        ↓
optional field warm seeds
        ↓
realign receipt (hashed)
        ↓
re-check epoch_verified → mesh path
```

## CLI

```bash
python -m cortex realign diagnose --repo MyProject --json
python -m cortex realign plan --repo MyProject --json
python -m cortex realign apply --repo MyProject --i-authorize-realign --json
python -m cortex realign warm --repo MyProject --warm-ticks 3 --json
python -m cortex realign status --repo MyProject --json
```

| Action | Seals epoch? | Host mutate? |
|--------|--------------|--------------|
| diagnose / plan / status | No | No |
| warm | No | No |
| apply (no flag) | No — errors `authorization_required` | No |
| apply `--i-authorize-realign` | Yes if drift | No |

## Interconnect

Mesh report includes:

```json
"realign": {
  "needed": true,
  "command": "python -m cortex realign apply --repo X --i-authorize-realign",
  "diagnose": "python -m cortex realign diagnose --repo X --json"
}
```

## What this phase does **not** do

- Silent epoch seal on import, activate, or interconnect
- Host source mutation
- Auto-clear of `STOP_NO_HOST_MUTATION` (that is correct immune posture)
- Full field calibration to 16/16 in one apply (warm seeds only)
- Consciousness claims

## Claim boundary

Continuity Realignment is operator-authorized rebind of body epoch and optional field warm-in after version or constitutional config drift. Not host mutation authority. Not automatic promotion. Not consciousness.

## Module map

| Path | Role |
|------|------|
| `cortex/realign.py` | diagnose · plan · apply · warm · receipt |
| `cortex/cli.py` | `realign` subcommand |
| `cortex/interconnect.py` | `realign` advice block |
| `tests/test_realign.py` | auth + observe-only gates |
| `scripts/ci/release_receipt_v740.py` | hard CI gate |
