# ADR-008: Admit `⨯` with an explicit verified MAP instruction

## Status

Accepted for Verified Map alpha.7.

## Context

ARIA already has immutable bounded `Sequence<T>` values, compile-time function
types, deterministic bytecode verification, whole-program purity summaries, and
Event Spine v3. The `algorithm.map` card is specified but inactive.

Map cannot be represented honestly as an ordinary source-level `repeat`:

- repeat has no result value;
- its verifier contract does not bind a transform identity;
- its body may contain effects;
- reconstructing a sequence through mutation would violate immutable sequence
  semantics.

## Decision

The only admitted source surface is:

```aria
let doubled: Sequence<Number> = ⨯(values, Double)
```

`⨯` is a prefix algorithm glyph. Its second argument is a function identifier
resolved at compile time, not a runtime function value or closure.

The semantic contract is:

```text
Sequence<T> × PureFunction<T,U> → Sequence<U>
```

where `T` and `U` are established scalar types.

The compiler emits:

```text
MAP transform=<name> inputType=Sequence<T> outputType=Sequence<U>
```

The operand stack contains only the input sequence. `MAP` pops that sequence
and pushes the output sequence.

The bytecode verifier independently requires:

- a declared transform;
- exactly one transform parameter;
- a pure verified effect summary;
- exact input element/parameter agreement;
- exact return/output element agreement;
- established sequence types;
- no capability or policy change.

The VM invokes the already verified function body once per element, in source
order, under the existing call-depth bound. It constructs the result through
`New-AriaSequenceValue`, reusing the existing 256-element and 65,536-byte
ceilings.

## Signal contract

Execution begins a new Event Spine operation and emits:

```text
algorithm.map.start      ACTIVE
algorithm.map.iteration  INFO, once after each completed transform
algorithm.map.complete   PASS
algorithm.map.fracture   FAIL
```

Records include transform identity, iteration counts, and measured duration.
They exclude input and output element values. No percentage is inferred.

## Consequences

- Map order and cardinality are deterministic and visible to the verifier.
- Transform purity is checked in source semantics, bytecode verification, and
  VM admission.
- Function values, closures, nested sequences, parallel execution, filter, and
  reduce remain unavailable.
- `MAP` is a new pure computational opcode, not a capability or authority.
- The `algorithm.map` card may become `verified` only with a green dedicated
  lattice and remote conformance.
