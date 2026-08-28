# Multi-Provider Model Fabric

`ProviderFabric` extends the alpha.1 `AgentModelAdapter` seam. Cortex core sees
only normalized model descriptors and provider-neutral agent requests/results.

Implemented providers:

| Provider | Discovery | Inference |
|---|---|---|
| OpenAI | live `GET /v1/models` | streaming chat completions, `store=false` |
| xAI / Grok | live `GET /v1/language-models`, `/v1/models` fallback | streaming OpenAI-compatible chat completions |
| OpenRouter | live `GET /api/v1/models` | streaming OpenAI-compatible chat completions |

Provider identity is provenance, never authority. Model output cannot mark
itself successful, witnessed, admitted to memory, or authorized to execute.

`CortexModelDescriptor` preserves unknown capability values instead of
inventing them. OpenAI's basic model list does not provide complete capability
metadata, so obvious non-chat families are closed and otherwise compatibility
remains `UNKNOWN`. xAI and OpenRouter richer metadata is normalized when
present.

The transport parses public streamed text, tool-call fragments, token usage,
and supported finish states. Provider-native and hidden reasoning fields never
enter the canonical response.
