# Primary-Source Research Notes

Research review date: 2026-07-21.

## Portable instruction formats

The WebAssembly core specification separates structure, instructions, validation, execution, binary encoding, and text encoding. ARIA adopts the architectural separation, not WebAssembly's instruction set. ARIA keeps a higher-level graph and capability model and uses a verified container around its alpha bytecode.

Source: https://webassembly.github.io/spec/

## Executable semantics

K describes language semantics through configurations and rewrite rules. ARIA uses this as evidence that language meaning can be specified as explicit state transitions. ARIA 0.1 implements a sequential stack machine first; guarded graph rewriting remains a later semantic layer.

Sources:

- https://kframework.org/
- https://kframework.org/k-distribution/k-tutorial/1_basic/13_rewrite_rules/

## Unicode and glyph safety

Unicode UAX #31 distinguishes identifier syntax from general Unicode presentation and supports profiles. ARIA therefore keeps bootstrap identifiers in a narrow ASCII profile while treating glyphs as validated aliases over stable semantic names. A font shape never grants meaning or authority.

Source: https://www.unicode.org/reports/tr31/

## Secure development and least authority

NIST SP 800-218 recommends integrating security practices into the development lifecycle. ARIA applies this through deny-by-default policy, explicit capabilities, path confinement, compiler gates, hostile-bytecode verification, tests, and release checks.

Source: https://csrc.nist.gov/pubs/sp/800/218/final

## Reproducible artifacts

The reproducible-builds project defines a reproducible build as one where the same source, environment, and instructions recreate bit-for-bit identical outputs. ARIA's alpha gate compiles twice in the same locked bootstrap environment and compares bytes. Mutable memory and timestamps are excluded from `.ariac` and stored in separate state and provenance files.

Sources:

- https://reproducible-builds.org/docs/
- https://reproducible-builds.org/docs/definition/

## Provenance

SLSA describes provenance as verifiable information tracing artifacts through a build process to their inputs. ARIA emits a sidecar provenance record with compiler, source, IR, policy, and artifact hashes. This alpha record is informative rather than a signed SLSA attestation.

Source: https://slsa.dev/spec/v1.2/provenance

## Version contracts

Semantic Versioning provides a disciplined vocabulary for compatible and incompatible changes. ARIA separately versions the compiler, language specification, program, and binary container. During alpha, the compiler gate requires exact specification compatibility with `aria.lock.json`.

Source: https://semver.org/

## PowerShell bootstrap constraints

Windows PowerShell 5.1 supports JSON serialization and deserialization through `ConvertTo-Json` and `ConvertFrom-Json`. ARIA uses only built-in .NET and PowerShell facilities so the bootstrap can execute on a standard Windows installation without fetching packages.

Source: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertto-json?view=powershell-5.1
