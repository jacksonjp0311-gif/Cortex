# Native Interface Architecture

Alpha.2 is a local-first web application served by Cortex on loopback. It uses
no provider SDK and no frontend package manager.

```text
browser UI
  -> narrow JSON/SSE service
  -> CortexChatService
  -> NativeAgentRuntime
  -> CortexRuntimeBridge
  -> provider fabric / bounded tools
  -> immutable native_agent_trajectory
```

The interface is an event consumer. It cannot construct Cortex context,
execute a tool, call a provider, or declare a trajectory valid. Static assets
ship in `cortex.ui`; `cortex ui` serves them from `127.0.0.1` and opens the
browser. Remote binding is rejected in alpha.2.

## Service surface

- `GET /v1/status`, `/v1/providers`, `/v1/settings`
- `POST /v1/providers/{provider}/credential|validate|models`
- `GET /v1/providers/{provider}/models`
- `POST|GET /v1/sessions`
- `GET /v1/sessions/{id}`
- `POST /v1/sessions/{id}/messages|interrupt|model|archive`
- `GET /v1/sessions/{id}/context|evidence|trajectory|telemetry`
- `GET /v1/events?session_id=...` (SSE)

The service uses one serialized UI Store connection and a separate Store
connection for each active model turn. Both address the same canonical Cortex
database; this is concurrency isolation, not a second memory system.

## Frontend

The standards-based HTML/CSS/JavaScript client is split by concern through
service endpoints, UI regions, and the versioned event vocabulary. A future
native shell can embed the exact same loopback contract.

The main view is a three-rail instrument layout: measured call telemetry,
Cortex core/chat, and intelligence state. The optional operator surface is a
collapsed drawer rather than a permanent bottom rail. Canvas sparklines and
the plasma core are event consumers; they do not create synthetic runtime
state.
