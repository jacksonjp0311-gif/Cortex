# Phase v6.25 — Constitutional Immunity

**Tagline:** A digital organism must be able to enter a sterile state, trace a wound, quarantine its descendants, heal selectively, and prove that it remained itself.

## Lifecycle

```text
DETECT → TRACE → QUARANTINE → PLAN → SNAPSHOT → REPAIR → VERIFY → READMIT|ROLLBACK
```

No stage silently authorizes the next.

## Modules

| Module | Role |
|--------|------|
| `evidence_kernel.py` | Separate trusted retrieval (no adaptive path) |
| `controller_scope.py` | Adaptive write firewall |
| `lineage.py` | Causal lineage graph |
| `quarantine.py` | Quarantine envelopes |
| `unlearning.py` | Plan / apply / rollback |
| `immunity.py` | Orchestration |
| `witness.py` | Independent sealed evaluation |
| `promote_gate.py` | Coupling = safety only; development transfer labeled |

## CLI

```bash
python -m cortex evidence-kernel --repo CortexTeach --task "authority" --json
python -m cortex immunity scan --repo CortexTeach --json
python -m cortex immunity quarantine --repo CortexTeach --artifact-id syn_x --json
python -m cortex immunity plan-repair --repo CortexTeach --wound-id mw_… --json
python -m cortex immunity apply-repair --repo CortexTeach --plan-id up_… --authorize --json
python -m cortex witness run --repo PulseFlow --json
```

## Claim boundary

> Cortex Immunology provides provenance-directed quarantine, selective unlearning, repair verification, and trusted evidence fallback for an adaptive repository-memory runtime. It does not establish biological life, consciousness, autonomous host authority, or perfect protection from adversarial memory.
