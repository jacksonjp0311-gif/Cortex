# Live Model Discovery

Catalogs are credential-specific live provider responses normalized into
`CortexModelDescriptor`. Cortex does not maintain a provider roster.

The metadata-only cache has a five-minute default freshness window. Opening a
selector returns fresh cached data immediately when eligible; `REFRESH MODELS`
bypasses the cache. Provider errors may fall back to a visibly stale catalog.
Credentials never enter the cache.

OpenRouter free status is derived from the live ID/variant and pricing fields:

- `openrouter/free` is the documented dynamic Free Models Router;
- a live `:free` variant is free;
- a model whose declared prompt, completion, and request prices are all zero
  is free.

The special router is placed first. Specific free variants remain individually
selectable. Search, free/tools/vision/reasoning filters, provider-side popular,
newest, context, and price sorts use only metadata the provider exposes.
Missing values render as `—` or `UNKNOWN`.
