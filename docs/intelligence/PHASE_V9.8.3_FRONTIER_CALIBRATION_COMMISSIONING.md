# Cortex v9.8.3 — Frontier Calibration Commissioning

## Purpose

v9.8.3 turns the v9.8.2 difficulty ladder into an executable, fail-closed
development calibration protocol. It does not select or encode a model. A host
chooses a runtime adapter, and Cortex only accepts observations reconstructed
from a canonically verified `live_empirical` model circulation.

No frontier calibration was executed for this release. The committed structural
receipt therefore says `CALIBRATION_NOT_EXECUTED`.

## The discrete information wound

For `n` binary observations, the measurable success rates are not continuous:

```text
p = k / n,  k ∈ {0, 1, ..., n}
```

At `n=4`, the only rates are `0, .25, .50, .75, 1`. Under the declared
information band `.30 ≤ p ≤ .70`, only `2/4` passes. Four cases are consequently
a screen, not a calibration seal.

v9.8.3 uses two stages:

1. **Screening (`n=4`)** — zero successes moves easier, four moves harder, and
   any mixed result requests confirmation.
2. **Confirmation (`n=8`)** — only 3, 4, or 5 successes satisfy the declared
   band and allow that level to be selected.

The Rasch estimate and `I=p(1-p)` remain diagnostics. They cannot compensate
for a failed discrete gate.

## Canonical observation path

```text
runtime-selected adapter
  → canonical model circulation
  → immutable invocation/outcome/witness rows
  → independent public-output evaluation
  → development calibration observation
  → sequential family/level panel
```

The invocation configuration must bind the exact development prompt. The
circulation must independently verify, and its host-controlled adapter evidence
class must be `live_empirical`. A fixture, renamed fixture, caller Boolean, or
unrelated circulation cannot enter the accepted panel.

## Operational states

- `CALIBRATION_NOT_EXECUTED` — no admissible live observations exist.
- `CALIBRATION_HELD` — some observations exist, but at least one family is
  incomplete, ceiling, floor, or otherwise unready.
- `CALIBRATION_READY` — every declared family has a confirmed information-bearing
  level and no observation-integrity error exists.

All states are development-only and `confirmatory_eligible=false`.

## Running the structural seal

```powershell
python benchmarks/calibration_commissioning_v983.py
```

The command never invokes a model and therefore emits the honest unexecuted
state. A future host-controlled runner must pass a live `Store` to the Python
commissioning API; serialized observation mappings alone are deliberately
insufficient. Model and provider identity remain invocation provenance and
never participate in level selection.

## Claim boundary

v9.8.3 verifies the commissioning mechanics and discrete information law. It
does not establish positive competence lift, model superiority, cross-model
transfer, cognition, consciousness, agency, execution authority, memory
authority, or policy authority.

## Next evidence

1. Execute the development ladder with fresh runtime-selected frontier sessions.
2. Confirm informative levels with eight independent variants.
3. Run a separate development-only A/D discordance pilot.
4. Generate the secret-seeded held-out corpus only after calibration passes.
5. Preregister v9.9 before any confirmatory model invocation.
