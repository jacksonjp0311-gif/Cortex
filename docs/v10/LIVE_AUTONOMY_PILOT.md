# Cortex v10.0.0-alpha.13 — Lightweight Live Autonomy Pilot

Alpha.13 is an execution pulse, not another autonomy architecture.

It reuses the alpha.12 preregistration, native runtime, canonical trajectory
verifier, independent evaluator, exact matched-pairs analysis, and authority
closure. The only new operational surface is a bounded commissioning runner:

```powershell
python benchmarks/live_autonomy_pilot.py
python benchmarks/live_autonomy_pilot.py --execute --register-live-boundary
```

The first command is read-only and prints the plan. The second explicitly
authorizes at most four provider calls for the default two-case panel. Provider
and model come from explicit arguments or the Cortex UI selection. Neither is
encoded into the runner.

```text
same runtime-selected model
  ├─ task-only control
  └─ Cortex-governed context
        ↓
canonical trajectories
        ↓
frozen independent evaluator
        ↓
exact matched result
```

The corpus is intentionally small to control cost and latency. Consequently,
its exact power gate is unresolved. Even a positive observed difference cannot
produce `EMPIRICAL_AUTONOMY_ADVANTAGE_VERIFIED`.

The live adapter classification is derived from an explicit host-side
registration of the exact provider-fabric implementation and runtime profile.
Provider/model labels and response metadata cannot upgrade evidence. Where the
provider supplies no cryptographic attestation, Cortex records
`provider_attestation = not_available`.

Authority remains closed:

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
```

The pilot answers only whether the live paired measurement path executed. A
larger preregistered panel, adequate power, discriminative task families, and
replication remain necessary before any Cortex-advantage claim.
