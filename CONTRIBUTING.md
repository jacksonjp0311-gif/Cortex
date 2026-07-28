# Contributing to ARIA

ARIA accepts contributions to the specification, compiler, VM, glyph system, tests, documentation, and research archive.

## Required workflow

1. Create or update a test before changing semantics.
2. Update the normative specification when behavior changes.
3. Run `./aria.ps1 test`.
4. Run `./aria.ps1 gate examples/hello.aria`.
5. Record significant design choices as an ADR under `docs/adr`.
6. Add a changelog entry for user-visible changes.
7. Regenerate `MANIFEST.sha256` only after reviewing the final tree.
8. Run `./aria.ps1 doctor -Strict` before opening a release pull request.

A semantic change is incomplete unless the parser, validator, bytecode compiler, VM, disassembler, tests, and documentation agree.

## Design rule

AI may propose ARIA, but only the deterministic compiler defines whether a program is valid.
