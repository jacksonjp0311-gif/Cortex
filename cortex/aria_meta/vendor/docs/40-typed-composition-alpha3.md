# Typed Composition alpha.3

## Intent

Typed Composition alpha.3 activates the verified meaning of `≫` without
introducing a composition opcode or any new runtime authority.

The governing law is:

> Composition may reorganize established pure calls; it may not bypass their
> types, effects, policy, or verification.

## Source law

```aria
value ≫ StageA ≫ StageB
```

lowers left-to-right into:

```aria
StageB(StageA(value))
```

Each stage is a function identifier. The stage receives exactly one value: the
result accumulated from the left side of the pipeline.

## Type law

ARIA lowers the pipeline before semantic analysis. Existing call verification
therefore proves the full chain:

```text
type(value) -> input(StageA)
output(StageA) -> input(StageB)
```

Unknown stages, non-unary stages, and incompatible intermediate types use the
same diagnostics as their explicit nested-call equivalents.

## Precedence

`≫` has lower precedence than ARIA's existing logical and arithmetic operators:

```aria
1 + 2 ≫ Double
```

means:

```aria
Double(1 + 2)
```

## Identity and provenance

The glyph and nested-call forms share:

- the same canonical call AST;
- the same semantic IR hash;
- the same constants, functions, and instruction stream;
- the same runtime result and diagnostics.

They retain different source hashes and final provenance-bearing containers.

## Authority boundary

Alpha.3 adds no opcode, capability, policy effect, or VM path. The established
`CALL` machinery remains authoritative. The `composition.pipe` card advances
from `specified` to `verified` only after the dedicated admission lattice passes.

The algorithm cards remain bounded:

- `⨯` map — specified;
- `⫰` filter — specified;
- `Σ` reduce — specified.

## Admission lattice

`tests/Run-CompositionTests.ps1` proves fifteen contracts covering:

1. card and alias alignment;
2. left-to-right nested lowering;
3. precedence;
4. invoke-glyph interoperability;
5. semantic IR parity;
6. executable bytecode parity;
7. CALL ordering;
8. provenance separation;
9. runtime output;
10. unknown-stage diagnostics;
11. type continuity;
12. stage arity;
13. malformed syntax rejection;
14. opcode and capability non-expansion;
15. verified activation with algorithm containment.

## Next bounded evolution

After remote attestation, alpha.4 may implement `⨯` map as the first verified
sequence primitive. That evolution requires a real sequence type and cannot be
simulated through scalar composition.
