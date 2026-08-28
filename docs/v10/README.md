# Cortex v10 — Native Agent Runtime

Version target: `10.0.0-alpha.1`

Cortex v10 closes one bounded operational loop:

```text
human task
  -> verified Cortex context
  -> replaceable model adapter
  -> structured tool request
  -> host-approved tool execution
  -> untrusted tool result
  -> model continuation
  -> public final answer
  -> immutable Cortex trajectory
```

The model supplies temporary cognition. Cortex supplies durable context,
identity, evidence, ordering, and audit. The host supplies authority. None of
those roles may impersonate another.

Alpha 1 is deliberately headless and narrow. It supports provider-neutral
model turns, bounded filesystem reads and shell-free terminal processes,
versioned public events, and a reconstructable trajectory. It does not add a
second memory system, autonomous memory admission, skills, delegation, cron,
gateway channels, browser control, or a graphical interface.

## Documents

- [Architecture](ARCHITECTURE.md)
- [Hermes extraction audit](HERMES_EXTRACTION_AUDIT.md)
- [Agent protocol](AGENT_PROTOCOL.md)
- [Tool security](TOOL_SECURITY.md)
- [Provider interface](PROVIDER_INTERFACE.md)
- [Cortex runtime bridge](CORTEX_RUNTIME_BRIDGE.md)
- [UI design language](UI_DESIGN_LANGUAGE.md)
- [Benchmark plan](BENCHMARK_PLAN.md)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)

## Claim boundary

Alpha 1 proves that the runtime path is executable and auditable. It does not
prove cognition, consciousness, competence improvement, autonomous authority,
or safe execution of arbitrary tools.
