# Provider Interface

`AgentModelAdapter.invoke_agent(request) -> mapping` is provider-neutral.
Adapters expose identity fields but identity is provenance, not authority.

Canonical response fields are limited to:

- `request_hash`
- `public_output.text`
- `tool_calls[]` with `id`, `name`, and JSON-compatible `arguments`
- `finish_reason`
- `rationale_public`
- `declared_uncertainty`
- `token_usage`
- `cost`

Unknown fields are discarded. Credential-shaped configuration is rejected.
Alpha 1 includes a deterministic scripted adapter for tests and a host-selected
JSON subprocess adapter. The subprocess contract uses stdin/stdout JSON,
executes no shell, and contains no provider or model default.

Two different adapters can drive the same runtime without changing Cortex core
semantics. Provider streaming is deferred behind the event protocol.
