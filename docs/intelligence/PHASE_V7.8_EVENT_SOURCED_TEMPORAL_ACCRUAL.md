# Phase v7.8 — Event-Sourced Temporal Accrual

**Tagline:** Time advances only when a distinct runtime event is observed.

## The missing dimension

v7.7.2 made every activation boundary epoch-atomic, but it also closed every
activation as a one-tick frame. The identity was trustworthy; the temporal
support could not grow during ordinary stable operation.

v7.8 separates an atomic boundary from a duplicated snapshot. One advanced
activation already produces an ordered sequence of durable runtime receipts:
neural activation, session begin, organism pulse, packet hash, stream frames,
prediction trace when available, connect pass, and controller receipt. Cortex
observes those distinct events in the final epoch. Sparse sequences remain
open on a stable epoch; a first or changed epoch closes its available sequence
as an atomic current-epoch boundary.

## Observation coordinate

Each admitted observation has the coordinate

`o_i = (body_epoch_id, event_id, tick, timestamp, channel_vector)`.

Admission requires both:

1. `event_id` has not previously entered the activation-observation cursor;
2. every sample in the open window names the same body epoch.

Durable IDs come from their native receipt surfaces. The event ID is stored in
`source_ids` for provenance. `event_key` stores only a bounded event kind such
as `stream_breathe` or `connect_pass`, preventing unique IDs from inflating
differentiation.

Each event kind also applies a bounded participation mask to the live channel
snapshot (for example, `connect_pass` marks runtime, structure, federation,
and operations as salient). This prevents a real multi-event sequence from
collapsing into ten identical vectors. The mask describes which Cortex
subsystem emitted the receipt; it does not invent an event or elevate truth.

## Close law

For activation observations:

- no previous frame → close one honest initial receipt sequence;
- `epoch_changed=true` → close one honest successor receipt sequence;
- stable epoch and `W < W_min` → keep accruing;
- stable epoch reaching `W_min` → close `temporal_window_ready`;
- duplicate event ID → skip without advancing the tick.

Fusion ticks retain their existing transition-pressure and `W_max` cadence.

## What emerges mathematically

The new object is an event-sourced, epoch-partitioned sequence rather than a
repeated snapshot. It supports three falsifiable quantities:

- **event novelty:** `|unique(event_id)| / |attempted observations|`;
- **temporal support:** the number of distinct ticks in one epoch;
- **epoch survival length:** how many admitted events occur before identity
  changes.

These quantities can distinguish a stable operating regime from repeated
polling without manufacturing warmth. They do not establish consciousness,
intent, biological hunger, correctness, witness, capability, or permission to
mutate a host.

## Implementation

- `cortex/field_channels.py` binds event provenance to channel samples.
- `cortex/resonant_frame.py` enforces exactly-once admission and `W_min` close.
- `cortex/activation.py` preserves stable windows and exposes
  `temporal_accrual`.
- `tests/test_resonant_frame_integration.py` proves duplicate rejection and an
  eight-event close.

## Claim boundary

Event-sourced temporal accrual is bounded operational telemetry. It remains
advisory and cannot move a constitutional bit or execute ARIA.
