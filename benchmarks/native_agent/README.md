# Native Agent Benchmarks

The Alpha 1 runner measures the executable `Agent + Cortex context` mechanism:
wall latency, event count, model turns, tool calls, and canonical verification.
It uses a deterministic adapter, so its result is structural—not empirical
agent competence.

```powershell
python benchmarks/native_agent/run.py --runs 5
```

The remaining preregistered arms stay explicit and unmeasured until their
feature gates exist:

- Agent shell only — HELD (no Cortex projection bypass in Alpha 1)
- Agent + Cortex memory — HELD (memory is already governed within context; no isolated ablation yet)
- Agent + Cortex competence — HELD
- Full Cortex — HELD

No opaque composite score is produced.
