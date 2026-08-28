# Native Agent Runtime Architecture

## Decision

The v10 runtime is an additive narrow waist. It does not replace v9 model
circulation. The older circulation remains the scientific path for frozen task
contracts, independent outcomes, witnesses, and competence experiments. The
new runtime owns multi-turn model/tool orchestration and emits a public
trajectory that later evaluators may inspect.

## Components

```text
CLI / future UI
      |
NativeAgentRuntime ---- AgentEventSink
      |                       |
      |                       +-- live UI/event consumers (observational)
      |
      +-- AgentModelAdapter (replaceable)
      |
      +-- ToolRegistry -- CapabilityGrant -- host process/filesystem
      |
      +-- CortexRuntimeBridge
              +-- open_symbiotic_session()
              +-- bounded Cortex context projection
              +-- symbiotic immutable receipt ledger
              +-- trajectory verification
```

## Ownership

- Cortex owns repository identity, context projection, session identity,
  immutable receipt persistence, and verification.
- The adapter owns provider transport only. Provider-native material is removed
  at the boundary.
- The runtime owns turn ordering, tool-call pairing, iteration limits, and
  finalization.
- The host owns capability grants. A model may request a tool but cannot grant
  it.
- Tools own bounded side effects and return explicitly untrusted observations.

## Trust planes

| Plane | Trusted fact | Non-authorizing input |
|---|---|---|
| Context | canonical Cortex projection/hash | model restatement |
| Provider | host-constructed adapter identity | response metadata |
| Tool | host capability grant + registry | model request |
| Result | tool executor status/output | model interpretation |
| Trajectory | receipt hash, event chain, request/response bindings | success claim |

## Persistence

Alpha 1 reuses the existing immutable symbiotic receipt ledger. One
`native_agent_trajectory` receipt embeds the ordered, hash-linked event stream.
This avoids a second database and preserves legacy schema compatibility.
Additional per-event tables may be added later only if measured query pressure
justifies them.

## Deferred surfaces

Streaming transport, interrupt/resume, compaction, MCP, delegation, skills,
scheduling, gateway channels, and UI are protocol-compatible future work. They
are not silently stubbed into the authority boundary.
