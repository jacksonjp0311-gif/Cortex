# ADR-009: Admit `⫰` with an explicit verified FILTER instruction

## Status

Accepted for Verified Filter alpha.8 implementation.

## Context

Sequence Core supplies bounded immutable `Sequence<T>` values. The effect graph
proves transitive function purity. Verified Map established compile-time
function identity, explicit algorithm bytecode, bounded function invocation,
and value-free Event Spine iteration evidence. The `algorithm.filter` card is
specified but inactive.

Filter changes sequence cardinality according to runtime predicate results.
That selection contract cannot be represented faithfully as ordinary calls or
as `MAP`, so the verifier needs to see it explicitly.

## Decision

The exact source form is:

```aria
⫰(sequence, Predicate)
```

It produces a dedicated canonical AST node:

```text
filter(sequence=<expression>, predicate=<identifier>)
```

The semantic contract is:

```text
Sequence<T> × PureFunction<T,Bool> → Sequence<T>
```

`Predicate` is an identifier resolved at compile time. It is not a function
value and creates no closure or capture.

The compiler emits:

```text
FILTER predicate=<name> sequenceType=Sequence<T>
```

`FILTER` pops one sequence and pushes one sequence of the same type. The
verifier independently requires:

- a valid input sequence type equal to the operand-stack type;
- an existing unary predicate;
- exact predicate parameter agreement with `T`;
- an exact `Bool` return type;
- a verified pure effect summary.

The VM evaluates the predicate exactly once per input element in source order.
It retains an element only when the verified result is `true`, never mutates the
input, and constructs the result through the established bounded sequence
constructor.

## Evidence contract

One Event Spine operation projects:

```text
algorithm.filter.start      ACTIVE
algorithm.filter.iteration  INFO, after each completed predicate
algorithm.filter.complete   PASS
algorithm.filter.fracture   FAIL
```

Evidence may contain predicate identity, input count, completed count, selected
count, measured duration, and source line. It must not contain input or selected
element values. Completion means the declared filter contract passed; it does
not imply universal correctness or grant authority.

## Boundaries

- Filter is sequential; parallel selection is out of scope.
- Nested sequences, closures, capture, mutation, and implicit coercion remain
  out of scope.
- `FILTER` is pure computation and grants no capability or policy permission.
- `algorithm.filter` may become `verified` only after its dedicated lattice and
  the complete regression lattice pass.
- `algorithm.reduce` remains specified and inactive.
