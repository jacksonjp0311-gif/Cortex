# Cortex v10 — Native Agent Runtime

Version target: `10.0.0-alpha.2`

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

Alpha.2 adds a loopback-only Cortex graphical interface, persistent
conversations, live OpenAI/xAI/OpenRouter model discovery, OS-vault-backed
credentials, streamed public output, and real cancellation while preserving
the alpha.1 circulation and evidence boundary. It does not add a second memory
system, autonomous memory admission, skills, delegation, cron, remote gateway
channels, or browser-control authority.

## Documents

- [Architecture](ARCHITECTURE.md)
- [Hermes extraction audit](HERMES_EXTRACTION_AUDIT.md)
- [Agent protocol](AGENT_PROTOCOL.md)
- [Tool security](TOOL_SECURITY.md)
- [Provider interface](PROVIDER_INTERFACE.md)
- [Cortex runtime bridge](CORTEX_RUNTIME_BRIDGE.md)
- [UI design language](UI_DESIGN_LANGUAGE.md)
- [Native interface plan](NATIVE_INTERFACE_PLAN.md)
- [UI architecture](UI_ARCHITECTURE.md)
- [Provider fabric](PROVIDER_FABRIC.md)
- [Secret storage](SECRET_STORAGE.md)
- [Model discovery](MODEL_DISCOVERY.md)
- [Cortex chat](CORTEX_CHAT.md)
- [Benchmark plan](BENCHMARK_PLAN.md)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)

## Claim boundary

Alpha.2 proves that the local interface and provider-neutral runtime path are
executable and auditable with deterministic provider fixtures. It does not
prove cognition, consciousness, competence improvement, autonomous authority,
safe execution of arbitrary tools, or live cross-provider model quality.
