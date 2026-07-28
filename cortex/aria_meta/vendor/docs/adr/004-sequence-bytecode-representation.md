# ADR-004: Sequence Bytecode Representation

- **Status:** Accepted for alpha.4
- **Decision:** Structured immutable constant through `PUSH_CONST`
- **Baseline:** Typed Composition alpha.3
- **Scope:** Flat scalar `Sequence<T>` values only

## Context

ARIA needs a real sequence substrate before map, filter, or reduce can be
implemented honestly. Two representations were considered:

1. encode a complete immutable sequence as a typed constant and reuse
   `PUSH_CONST`;
2. introduce a sequence-construction opcode that consumes element values from
   the operand stack.

Alpha.4 permits only scalar literals inside sequence literals. Every element is
therefore known, typed, bounded, and serializable during compilation.

## Decision

Use an immutable structured constant:

```json
{
  "format": "aria.sequence",
  "version": 1,
  "elementType": "Number",
  "values": [1, 2, 3]
}
```

Compilation interns the complete value in the constant pool and emits the
existing `PUSH_CONST` instruction. The bytecode verifier independently validates
the structure, element type, homogeneity, count ceiling, and encoded-byte
ceiling.

## Reasons

- no new runtime control path is required;
- no partial or malformed sequence can remain on the operand stack;
- constant identity is deterministic and content-addressable;
- container round-trip is direct;
- the existing stack verifier remains simple;
- alpha.4 contains no dynamic sequence construction.

## Consequences

Positive:

- opcode registry remains unchanged;
- source and runtime values share one canonical representation;
- empty sequences are representable without an identity element;
- values are immutable because ARIA exposes no mutation operation.

Boundaries:

- sequence elements must be compile-time scalar literals;
- nested sequences are rejected;
- dynamic construction is deferred;
- map, filter, and reduce may later require a verified iteration primitive or
  dedicated bounded opcodes.

## Revisit trigger

Revisit this decision only when a verified evolution requires dynamic sequence
construction. That evolution must prove stack behavior, allocation bounds,
effect preservation, and artifact determinism independently.
