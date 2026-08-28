# Agent Protocol

The protocol has four immutable public objects: `AgentMessage`,
`AgentModelRequest`, `AgentModelResponse`, and `AgentEvent`.

Events use schema `cortex-agent-event/1.0` and are monotonically sequenced.
Each event hash covers the prior event hash, creating a per-trajectory chain.
Required Alpha 1 ordering is:

```text
session.started
context.prepared
model.requested
model.responded
[tool.requested -> tool.completed -> model.requested -> model.responded]*
answer.final
trajectory.sealed
```

A model response must bind the exact request hash. A tool result must bind the
exact tool-call ID. Duplicate call IDs, missing pairs, malformed arguments,
context hash drift, and response replay fail closed.

Terminal capability hashes cover exact argument vectors. A model cannot retain
an executable grant while substituting different arguments.

Only public answer text, public rationale, tool intents, usage, and bounded
tool observations are canonical. Hidden reasoning and provider-native payloads
are neither requested nor persisted.
