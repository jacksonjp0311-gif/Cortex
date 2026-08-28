# Cortex v10 Native Interface Plan

Target: `10.0.0-alpha.2`

## Existing seam

Alpha.1 already owns the authoritative circulation:

```text
CortexRuntimeBridge -> NativeAgentRuntime -> AgentModelAdapter -> tools
                   \-> immutable native_agent_trajectory
```

`AgentEventStream` is the only live-observation boundary the interface needs.
The UI must consume those events; it must not reproduce context projection,
tool execution, trajectory persistence, or provider invocation.

## Implementation map

1. **Provider fabric** — extend the existing `AgentModelAdapter` contract with
   optional streaming and cancellation. Add host-controlled OpenAI, xAI, and
   OpenRouter adapters, normalized live model discovery, compatibility states,
   and a bounded metadata-only cache.
2. **Host secrets** — resolve keys from environment variables or the operating
   system credential store. Keep secrets out of settings, events, model
   requests, exceptions, logs, receipts, and model-catalog cache entries.
3. **Cortex chat service** — add a loopback-only HTTP/SSE service that owns
   provider settings, persistent Cortex conversation projections, model
   switching provenance, active-run cancellation, and narrow read-only
   context/evidence/trajectory views.
4. **Native interface** — ship a responsive dependency-light web console as
   Cortex package data. It includes provider setup, live model browsing,
   streaming Cortex chat, a truthful event-driven plasma core and telemetry,
   evidence/context
   panels, and operator drawers.
5. **Launch** — `cortex ui` starts the service on loopback, chooses a safe port,
   opens the system browser by default, and never enables remote exposure
   implicitly.
6. **Verification** — fixture providers exercise discovery, streaming, tools,
   interruption, model switching, secret redaction, API routing, persistence,
   responsive UI assets, and the complete local E2E path without paid calls.

## Persistence boundary

Conversation projections reuse Cortex's existing repository session/event
store. Non-secret UI preferences use the existing settings surface. Provider
keys use only the host credential store or process environment. Chat messages
are session history, not admitted memory, competence, evidence truth, or
authority.

## Frontend decision

Alpha.2 uses standards-based HTML, CSS, and JavaScript served by Python's
loopback HTTP runtime. This avoids a second package manager and large framework
dependency while preserving component boundaries in modules and a versioned
JSON/SSE protocol. A future Tauri, Electron, or richer web renderer can consume
the same service contract without replacing Cortex core.

## Release boundary

The version remains alpha.1 during implementation. It advances to alpha.2 only
after the graphical interface, three live provider adapters, dynamic catalogs,
OpenRouter free routing, streaming, cancellation, sessions, secrets isolation,
native trajectory sealing, focused E2E tests, and compatibility verification
all pass. Live paid inference is opt-in and is never required by CI.
