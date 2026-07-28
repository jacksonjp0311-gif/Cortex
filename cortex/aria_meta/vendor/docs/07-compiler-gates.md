# Compiler Gates

The gate is a release and execution boundary, not a cosmetic status panel.

## Per-program gate

`aria.ps1 run` performs:

1. source normalization and size check;
2. parse diagnostics;
3. semantic validation;
4. exact compiler and language compatibility with `aria.lock.json`;
5. capability-policy validation;
6. bytecode generation;
7. bytecode verification for opcode, stack, references, effects, and termination;
8. two independent container serializations;
9. byte-for-byte build hash comparison;
10. container decompression and embedded digest verification;
11. source-hash identity verification.

## Repository gate

`aria.ps1 test` verifies parsing, glyph graphs, deterministic compilation, bytecode stack discipline, container round-trip, corruption detection, VM execution, version locking, policy denial, path confinement, and repository-manifest integrity.

`Release-Aria.ps1` runs doctor, tests, a real example compile, and packaging. CI repeats the gate on Windows and Linux PowerShell.

## Provenance

A `.aria-provenance.json` file records compiler, source, IR, policy, and artifact hashes. It is separate from the executable because timestamps make provenance intentionally non-reproducible while the executable must remain reproducible.


## Strict repository mode

`-Strict` adds a compiler-repository integrity gate using `MANIFEST.sha256`. Normal development may run without it while files are changing; CI, packaging, and release workflows use strict mode. Update the manifest deliberately with `scripts/Update-Manifest.ps1` after reviewing a compiler change.
