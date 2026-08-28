# Live Telemetry

Cortex alpha.2 exposes human-facing telemetry through the same versioned event
stream used by the native agent runtime. The frontend does not poll a provider,
invent activity, or interpret animation as evidence.

## Measurement classes

Every metric is presented as one of:

- **measured** — derived from local monotonic clocks or counted runtime events;
- **provider-reported** — returned by the selected provider, such as token
  usage or explicit cost;
- **estimated** — a declared approximation, such as streamed character count
  divided by four before final provider token usage arrives;
- **unavailable** — no defensible signal exists.

Unavailable values remain `—`. Cortex does not manufacture confidence,
reasoning depth, GPU utilization, context percentage, or cost.

## Runtime signals

The native runtime emits measured context-projection duration, first public
delta latency, model latency, streamed character count, tool duration, and
total turn latency. Provider token usage and cost remain separately typed as
provider-reported. `GET /v1/sessions/{id}/telemetry` reconstructs the latest
truthful summary from current events or the sealed trajectory.

## Visual binding

The plasma core reacts to real states:

```text
message accepted -> thinking
session/context events -> context field
model requested -> thinking
model delta -> streaming pulse
tool started -> tool pulse
interrupt -> cancelled field
trajectory sealed -> idle/sealed
failure -> bounded error field
```

Canvas sparklines retain only bounded in-browser display history. They are not
a second evidence ledger and grant no authority. The canonical trajectory
continues to own persisted runtime provenance.
