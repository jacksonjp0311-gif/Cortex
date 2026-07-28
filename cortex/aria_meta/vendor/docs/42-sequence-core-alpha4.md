# Sequence Core alpha.4

## Intent

Sequence Core alpha.4 gives ARIA its first bounded structured value without
activating map, filter, reduce, mutation, iteration, or any new authority.

The governing law is:

> Structure must become deterministic and bounded before algorithms are allowed
> to transform it.

## Type surface

Alpha.4 introduces flat immutable sequences of established scalar values:

```aria
let values: Sequence<Number> = [1, 2, 3, 4]
let names: Sequence<Text> = ["Ada", "Grace"]
let empty: Sequence<Text> = []
```

The declared element types are:

```text
Text
Number
Bool
Null
```

`Sequence<Any>`, nested sequences, implicit coercion, and mutable collections are
not part of alpha.4.

## Literal law

A sequence literal:

- contains only scalar literals;
- is homogeneous;
- preserves authored order;
- has no mutable surface;
- contains at most 256 elements;
- has a canonical encoded size of at most 65,536 UTF-8 bytes.

A non-empty literal infers its element type. An empty literal has the internal
type `Sequence<Empty>` and requires a declared or expected concrete sequence
type.

## Representation decision

ADR-004 selects a structured immutable constant represented through the existing
`PUSH_CONST` instruction.

The canonical runtime value is:

```json
{
  "format": "aria.sequence",
  "version": 1,
  "elementType": "Number",
  "values": [1, 2, 3, 4]
}
```

This introduces a new value category but no new opcode. The verifier derives
`Sequence<T>` from the sealed constant itself rather than trusting source text.

## Type and runtime law

Sequence types cross:

- local variable stores and sets;
- function parameters and returns;
- memory defaults and persisted memory validation;
- equality and inequality;
- deterministic container serialization;
- deterministic console rendering.

Runtime rendering uses the canonical value list:

```text
[1,2,3,4]
[]
```

No indexing, append, removal, mutation, or iteration operation exists in
alpha.4.

## Authority boundary

Sequence values introduce:

- no capability;
- no policy permission;
- no side effect;
- no executable glyph alias;
- no map, filter, or reduce activation.

The opcode registry remains unchanged. Existing `PUSH_CONST`, `STORE`, `LOAD`,
`CALL`, `RETURN`, `EQ`, `NE`, and effect operations remain authoritative.

## Admission lattice

`tests/Run-SequenceCoreTests.ps1` proves fifteen contracts:

1. parameterized type parsing;
2. homogeneous canonical AST;
3. typed empty-sequence admission;
4. untyped empty-sequence rejection;
5. mixed-element rejection;
6. non-literal element rejection;
7. element-count ceiling;
8. encoded-byte ceiling;
9. deterministic semantic and build identities;
10. structured constants with no opcode expansion;
11. verified container round-trip;
12. deterministic runtime rendering;
13. function-boundary type preservation;
14. memory-default bytecode projection;
15. algorithm containment and scalar regression.

All previous lattices remain mandatory.

## Next bounded evolution

Alpha.5 should implement deterministic function effect and purity summaries.
`⨯ map` remains inactive until ARIA can prove that a transform function and its
transitive call graph are pure.
