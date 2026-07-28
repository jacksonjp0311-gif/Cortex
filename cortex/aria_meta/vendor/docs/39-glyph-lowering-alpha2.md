# Glyph Lowering alpha.2

## Intent

Glyph Memory Kernel alpha.1 established stable identities for `▷` and `↩`.
Alpha.2 makes those already-verified meanings available in ARIA source without
adding execution authority.

The governing law remains:

> A glyph may select an established semantic path; it may not invent a new
> runtime privilege.

## Source equivalence

```aria
▷ Add(20, 22)
↩ left + right
```

lowers canonically to:

```aria
Add(20, 22)
return left + right
```

The glyph surface does not survive as a distinct AST operation. Both forms
produce the same call and return nodes, the same semantic IR hash, and the same
executable instruction stream.

## Provenance boundary

Source provenance remains exact:

- glyph and textual source have different `sourceHash` values;
- their semantic `irHash` values are equal;
- their executable constants, functions, and instructions are equal;
- their final containers differ because the source identity is embedded.

This preserves both equivalence and authorship evidence.

## Runtime boundary

Alpha.2 adds no opcode. The existing verified operations remain authoritative:

- `▷` lowers to `CALL`;
- `↩` lowers to `RETURN`.

The opcode registry remains unchanged.

## Diagnostics

Because lowering occurs before semantic analysis, glyph and textual forms retain
the same diagnostics for:

- unknown functions;
- argument count and type errors;
- return type errors;
- return outside a function;
- all existing policy and capability checks.

## Admission gates

`tests/Run-GlyphLoweringTests.ps1` proves:

1. alias and semantic-card alignment;
2. canonical call lowering;
3. adjacent and nested invocation;
4. canonical return lowering;
5. semantic IR equality;
6. executable bytecode equality;
7. distinct source provenance;
8. no opcode expansion;
9. expected runtime values;
10. runtime behavioral parity;
11. unknown-function diagnostic parity;
12. type and return-authority diagnostic parity.

The established 202-test core lattice and the Glyph Memory 8-test lattice remain
mandatory.

## Next bounded evolution

Alpha.3 may introduce `≫` as typed composition syntax. It should lower into
nested established calls first, before any sequence primitive or new runtime
operation is admitted.
