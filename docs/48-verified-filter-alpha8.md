# Verified Filter alpha.8

Verified Filter activates ARIA's second bounded sequence algorithm:

```aria
let selected: Sequence<Number> = ⫰(values, IsPositive)
```

The operator and the machine instruction share one contract:

```text
Sequence<T> × PureFunction<T,Bool> → Sequence<T>
```

## Why Filter follows Map

Sequence Core established finite immutable values and resource ceilings.
Effect Graph established deterministic transitive purity. Verified Map proved
that ARIA can bind a compile-time function identity through source, semantics,
bytecode, independent verification, VM calls, and Event Spine evidence. Filter
reuses those contracts while adding controlled variable cardinality.

## Compiler contract

The parser creates a dedicated `filter` AST node. Semantic analysis rejects the
program unless:

- `algorithm.filter` has a valid verified card;
- the first operand has type `Sequence<T>`;
- the predicate exists and has exactly one parameter;
- the parameter type is exactly `T`;
- the return type is exactly `Bool`;
- the predicate's transitive effect summary is proven `pure`.

The compiler emits:

```text
FILTER predicate=<name> sequenceType=Sequence<T>
```

The bytecode verifier reconstructs these obligations independently. Editing a
predicate name, type, return contract, or purity summary causes artifact
rejection even when the modified JSON remains syntactically valid.

## Runtime contract

The VM invokes the established verified function body exactly once per input
element in source order. A `true` result retains the original immutable value;
a `false` result omits it. The input is never changed. The result is created
through `New-AriaSequenceValue`, so the established 256-element and 65,536-byte
ceilings remain authoritative.

Empty input produces a typed empty result and no invented iteration. Filter is
sequential and deterministic. Closures, capture, mutation, coercion, nested
sequences, and parallel selection remain outside this evolution.

## Shared event projection

The human display and machine journal consume the same Event Spine records:

```text
algorithm.filter.start      ACTIVE
algorithm.filter.iteration  INFO × completed predicates
algorithm.filter.complete   PASS
```

If predicate execution fractures:

```text
algorithm.filter.fracture   FAIL
```

Records contain predicate identity, input count, completed count, selected
count, measured duration when available, source line, operation identity, and
event digest. They do not contain input or selected element values. A completion
seal means the declared filter contract passed; it does not grant authority or
claim universal correctness.

## Admission evidence

The dedicated 24-gate lattice proves:

- sealed card identity and canonical AST;
- type preservation and `FILTER` metadata;
- unknown, arity, input-type, Boolean-return, and purity diagnostics;
- bytecode tamper rejection independent of source semantics;
- effect-graph predicate visibility;
- stable some, zero, all, and empty selections;
- source order and input immutability;
- measured count continuity and value-free evidence;
- bounded fracture publication;
- deterministic compilation and execution;
- explicit composition with Verified Map;
- no capability or policy expansion;
- the alpha.8 boundary where `algorithm.reduce` was still inactive.

Aggregate conformance at alpha.8 was `368/368`; the current baseline is
recorded in `AGENTS.md`.

## Next boundary

Verified Reduce alpha.9 subsequently admitted the explicit initial
accumulator, exact pure binary reducer, deterministic left-fold order,
accumulator continuity, and bounded value-free evidence described in
`docs/49-verified-reduce-alpha9.md`.
