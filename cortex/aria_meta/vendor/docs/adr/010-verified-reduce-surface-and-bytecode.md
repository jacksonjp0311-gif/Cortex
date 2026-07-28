# ADR-010: Admit `Σ` with an explicit verified REDUCE instruction

## Status

Accepted for Verified Reduce alpha.9 implementation.

## Context

ARIA has bounded immutable `Sequence<T>`, a transitive purity proof, verified
function invocation, and explicit `MAP` and `FILTER` instructions. Reduce adds
an accumulator whose value and type must remain continuous across every
iteration. Ordinary calls cannot expose that invariant to the bytecode
verifier, and neither existing sequence opcode expresses a left fold.

## Decision

The exact source form is:

```aria
Σ(sequence, Reducer, initial)
```

It creates:

```text
reduce(sequence=<expression>, reducer=<identifier>, initial=<expression>)
```

The semantic contract is:

```text
Sequence<T> × PureFunction<A,T,A> × A → A
```

`Reducer` is resolved at compile time and is never a runtime function value.
ARIA requires:

- an input `Sequence<T>`;
- an explicit initial value with declared type `A`;
- exactly two reducer parameters ordered `(A, T)`;
- an exact reducer return type `A`;
- a verified transitive `pure` effect summary.

The compiler emits:

```text
REDUCE reducer=<name> sequenceType=Sequence<T> accumulatorType=A
```

The compiler pushes the sequence and initial value in source order. `REDUCE`
pops the initial value, then the sequence, and pushes one value of type `A`.
The verifier independently reconstructs function identity, arity, parameter
order, exact types, return continuity, and purity.

The VM performs a deterministic left fold:

```text
accumulator = initial
for element in sequence, from first to last:
    accumulator = Reducer(accumulator, element)
return accumulator
```

Empty input returns the explicit initial value without invoking the reducer.
ARIA never infers an identity value.

## Evidence contract

One operation projects:

```text
algorithm.reduce.start      ACTIVE
algorithm.reduce.iteration  INFO, after each completed reducer call
algorithm.reduce.complete   PASS
algorithm.reduce.fracture   FAIL
```

Evidence may contain reducer identity, input count, completed count, measured
duration, source line, and event identities. It must not contain elements,
initial values, or accumulator values.

The maximum 256-element sequence must be benchmarked before admission. If
individual persistence is too expensive, optimization must preserve each
semantic event, ordering, digest, and transition identity; it may not replace
real progress with an estimated percentage.

## Boundaries

- Execution is sequential and strictly left to right.
- No implicit identity, coercion, closure, capture, mutation, or parallel fold
  is introduced.
- `REDUCE` grants no capability or policy permission.
- The card becomes verified only after its dedicated lattice and complete
  regression lattice pass.
