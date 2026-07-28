# Validation Record

## Authoritative executable gates

Run these commands in Windows PowerShell 5.1 or PowerShell 7:

```powershell
.\aria.ps1 doctor -Strict
.\aria.ps1 test
.\aria.ps1 gate .\examples\hello.aria -Strict
.\aria.ps1 run .\examples\hello.aria -Strict
.\aria.ps1 inspect .\.aria\build\HelloARIA-0.1.0.ariac
```

The GitHub Actions workflow repeats the compiler and VM gates on:

- Windows PowerShell 5.1;
- PowerShell 7 on Windows;
- PowerShell 7 on Linux.

## Gate coverage

The test suite covers:

- machine-readable glyph registry;
- source parsing and graph validation;
- deterministic container generation;
- strict repository-manifest validation;
- container digest round-trip;
- VM output and persistent memory;
- default denial of filesystem writes;
- path traversal rejection;
- rejection of checksummed but structurally invalid bytecode;
- rejection of container header-length mismatch;
- rejection of mismatched glyph semantics;
- execution-time policy revalidation;
- proof that read-only programs do not create memory state.

## Packaging-environment validation

The artifact-assembly environment did not provide a PowerShell runtime. Therefore it did not claim to execute the PowerShell test suite locally. Static packaging checks performed here include:

- strict UTF-8 decoding for every text file;
- JSON parsing for policy, lock, registries, and schemas;
- JSON Schema validation where supported;
- source-tree and reference inspection;
- manifest regeneration and independent SHA-256 comparison;
- balanced delimiter and PowerShell surface screening;
- ZIP integrity, file-count, and checksum verification.

The repository remains gated on the executable commands above and CI before release.

## Operator renderer validation

The `0.1.0-alpha.2` operator-renderer pass adds only presentation and Windows PowerShell compatibility changes around the existing deterministic compiler core. The previously installed `0.1.0-alpha.1` engine passed all 21 executable conformance tests on Windows PowerShell 5.1. The refreshed source tree received UTF-8 BOM verification, balanced delimiter screening, test-count verification, manifest regeneration, and archive integrity checks in the packaging environment. Re-run `aria test` and `aria doctor -Strict` after applying the upgrade; the upgrade script performs both automatically and preserves the prior files under `.aria/backups`.
