# ADR-006: Semantic projections are event-bound and content-addressed

## Status

Accepted for Semantic Projection Core alpha.6.

## Decision

ARIA will not let a renderer independently infer the meaning of an event.
`aria.event` version 2 introduced a deterministic `aria.semantic-projection/1`
derived from the event state and the sealed semantic cue registry.

The projection includes the cue identity, glyph, motion and rhythm contracts,
bounded record, measured-only metrics, transition delta, explanation,
interpretation boundary, static/reduced-motion equivalent, engagement contract,
and digest. The event digest covers that projection.

## Consequences

- Human output and machine journals name the same cue identity.
- Cue drift or projection drift invalidates the event.
- Rendering profiles may omit temporal frames but may not omit semantics.
- Motion may express a recorded event transition; it may not imply evidence or
  progress absent from the event.
- Color is supplementary.
- Semantic cues remain observational and grant no authority.
- Legacy `aria.event` version 1 ledgers remain verifiable and render with their
  established fallback. ADR-007 later advances new events to version 3 while
  retaining the projection contract.
