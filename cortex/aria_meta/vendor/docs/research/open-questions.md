# Open Research and Engineering Questions

These are intentionally unresolved. Each decision requires an ADR, specification update, and conformance tests.

## Semantic graph

- Are graph nodes values, declarations, runtime objects, or distinct categories?
- Which relationships are executable and which are descriptive metadata?
- How are graph identities preserved across refactoring and source-control merges?

## Glyph system

- Should multi-glyph compositions use spatial grammar, linear grammar, or both?
- Which Unicode symbols are stable across common fonts and input methods?
- When should ARIA use a private icon registry rather than Unicode characters?
- How will screen readers and voice systems round-trip every visual expression?

## Type and effect system

- Nominal versus structural types.
- Algebraic effects versus a closed effect enumeration.
- Linear or affine capability tokens for single-use approval.
- Units, dimensions, and physical constraints as types.

## Memory

- Event sourcing versus snapshot-plus-log persistence.
- Fact confidence and contradiction without allowing confidence to grant authority.
- Retention, redaction, encryption, and selective disclosure.
- Deterministic replay when external observations are involved.

## Concurrency

- Actor model, dataflow, process calculus, or explicit transaction graph.
- Deterministic scheduling profile versus performance-oriented scheduling.
- Conflict detection and rollback across repository, network, and device effects.

## AI bridge

- Provider-neutral proposal envelope and evidence model.
- Context selection without hidden authority or prompt-derived permissions.
- Tool protocol interoperability while keeping ARIA policy authoritative.
- How to distinguish generated content from compiler-established truth.

## Compilation targets

- Keep the ARIA VM as the portable authority boundary.
- Lower typed ARIA IR to WebAssembly for portability.
- Use MLIR/LLVM only as optional backends after semantics stabilize.
- Define a dense binary encoding without sacrificing inspectability or verifier simplicity.
