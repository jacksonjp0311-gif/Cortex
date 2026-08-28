# Provider Secret Storage

Provider keys are host secrets. Cortex resolves them in this order:

1. `OPENAI_API_KEY`, `XAI_API_KEY`, or `OPENROUTER_API_KEY` in the current
   process environment;
2. the operating-system credential vault through Python `keyring`.

The service returns only configuration state, source class, and a masked tail.
It never returns a key. Keys are excluded from:

- Cortex settings and SQLite evidence;
- model-catalog caches;
- requests exposed to the model;
- UI event payloads;
- trajectory receipts;
- access and exception logs.

The process-only `MemorySecretStore` exists solely for deterministic tests. It
is not a production fallback. If the OS vault is unavailable, Cortex reports
that state instead of writing a key into ordinary configuration.
