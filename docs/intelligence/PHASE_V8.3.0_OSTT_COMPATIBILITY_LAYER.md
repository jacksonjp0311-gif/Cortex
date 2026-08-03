# Phase v8.3.0 — OSTT Compatibility Layer

## Purpose

Operator-Structured Transformation Theory (OSTT) is now represented inside
Cortex as a compatibility and audit layer. It describes transitions that
Cortex already knows how to observe; it is not a replacement execution engine.
The central discipline is **execute known operators, learn only bounded and
verified residuals**.

## Contract registry

The registry in `cortex/ostt/contracts.py` declares six existing boundaries:

| Operator | Domain → codomain | Admission signal |
| --- | --- | --- |
| `repository_assimilation` | `RepositorySource → EvidenceIndex` | Current manifest |
| `epoch_binding` | `EvidenceIndex → BodyEpoch` | Verified certificate and manifest |
| `activation_observation` | `TaskRequest → ActivationReceipt` | Current epoch and governor allowance |
| `temporal_resonance` | `EpochFrames → ResonanceReport` | Same-epoch frame coverage |
| `informational_interlock` | `ActivationReceipt → InterlockReport` | Current cohort and independent outcomes |
| `bounded_learning` | `VerifiedOutcome → BoundedUpdate` | Valid evidence, witness, and open learning gate |

Each trace names its preconditions, postconditions, invariants, uncertainty
rule, cost, and validation label. A held precondition is a measurement result,
not a failure of the invariant.

## Use

```powershell
python -m cortex ostt status --repo CortexTeach --json
python -m cortex interconnect --repo CortexTeach --json
python -m cortex dashboard --mesh --repo CortexTeach --json
```

The interconnect and dashboard responses include an `ostt` panel with:

- `operators`: one serializable trace per declared boundary;
- `facts`: the current evidence gates used for admission;
- `residuals.unresolved`: unmeasured or unsatisfied boundary pressure;
- `readiness`: next evidence actions already exposed by the interlock layer;
- `policy_effect: false` and `advisory_only: true`.

## Safety and claim boundary

OSTT is deliberately shadow-only. It does not execute operators, route tasks,
promote interlocks, train a model, mutate host files, overwrite memory, or
grant authority. It also does not imply subjective sensing or consciousness.
The current implementation is OSTT-D (architecture represented and wired to
telemetry, not benchmark-validated as a general transformation theory).

The residual names are intentionally conservative: Cortex's self-sensing
residual, predictive error, ranker score, and future OSTT residual burden are
separate quantities until they have an explicit shared receipt.

## Verification

```powershell
python -m pytest tests/test_ostt.py tests/test_interconnect_continuity.py -q
python -m ruff check cortex/ostt cortex/interconnect.py cortex/cli.py tests/test_ostt.py
python benchmarks/informational_interlock_benchmark.py
```

The layer is accepted only when traces serialize, held gates are visible, and
existing Cortex tests remain green. Performance or learning claims require the
next phase's independent residual evidence.
