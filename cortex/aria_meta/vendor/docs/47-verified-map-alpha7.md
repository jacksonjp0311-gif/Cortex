# Verified Map alpha.7

Verified Map is ARIA's first admitted sequence algorithm and the first language
operation designed directly on top of Signal Integrity Closure.

## Source contract

```aria
function Double(value: Number) -> Number {
  ↩ value * 2
}

flow Main {
  let values: Sequence<Number> = [1, 2, 3, 4]
  let doubled: Sequence<Number> = ⨯(values, Double)
  emit doubled
  halt
}
```

The only admitted form is:

```text
⨯(sequence-expression, TransformIdentifier)
```

The transform identifier is resolved at compile time. Functions are not
first-class values and map does not introduce closures or capture.

## Type and purity law

```text
Sequence<T> × PureFunction<T,U> → Sequence<U>
```

The compiler rejects map unless:

- the input is an established flat `Sequence<T>`;
- the transform exists and has exactly one parameter;
- its parameter is exactly `T`;
- its return is an established scalar `U`;
- its transitive effect summary is `pure`.

These obligations are independently reconstructed from bytecode.

## Bytecode

```text
MAP
  transform=Double
  inputType=Sequence<Number>
  outputType=Sequence<Number>
```

`MAP` pops one sequence and pushes one sequence. Its transform metadata is
explicit and verifier-visible. It adds computation, not authority.

## Runtime

The VM:

1. revalidates the input sequence;
2. revalidates transform identity, arity, purity, and element type;
3. invokes the verified function body once per element in source order;
4. preserves cardinality;
5. constructs the result with `New-AriaSequenceValue`;
6. therefore reuses the 256-element and 65,536-byte ceilings.

Empty typed sequences produce typed empty results without inventing an
iteration.

## Shared signal history

A real execution emits:

```text
algorithm.map.start      ACTIVE
algorithm.map.iteration  INFO × completed iterations
algorithm.map.complete   PASS
```

If a transform fails:

```text
algorithm.map.fracture   FAIL
```

Evidence contains transform identity, completed and total iteration counts,
measured duration, cue identity, projection identity, operation identity, and
event digest. It excludes sequence and element values. Iteration signals occur
only after the corresponding transform invocation completes.

## Event Spine use-driven closure

Running map against a real accumulated event journal exposed an append-cost
gap. Event Spine now fully validates history at initialization and replay, then
retains the exact validated ledger-byte identity. Each subsequent append:

- takes an exclusive file lock;
- rejects changed ledger bytes;
- validates the tail identity and next sequence;
- extends the chain and cached byte identity.

This preserves tamper and stale-writer rejection without reparsing the entire
history for every map iteration.

## Admission evidence

The dedicated 22-gate lattice covers:

- card identity and activation;
- canonical AST and `MAP` metadata;
- unknown, non-unary, mismatched, non-scalar, direct-effect, and
  transitive-effect rejection;
- independent verifier rejection of transform and purity tampering;
- order, length, output type, empty sequence, nested map, and determinism;
- measured event order, value privacy, and runtime fracture evidence;
- unchanged capability and policy authority;
- the alpha.7 boundary where filter and reduce were still inactive.

Aggregate conformance at alpha.7 was `344/344`; the current repository baseline
is recorded in `AGENTS.md` and `ARIA-RUNTIME.json`.

## Next boundary

Verified Filter alpha.8 subsequently reused the compile-time pure-function and
iteration-evidence architecture while adding a distinct stable-cardinality
contract. Its admitted contract is recorded in
`docs/48-verified-filter-alpha8.md`.
