# References

ARIA uses primary specifications and established technical sources as design inputs. These references do not define ARIA; the repository specification, ADRs, and tests do.

## Languages, IR, and virtual machines

- W3C WebAssembly Core Specification 2.0: https://www.w3.org/TR/wasm-core-2/
- WebAssembly specification index: https://webassembly.github.io/spec/
- MLIR Language Reference: https://mlir.llvm.org/docs/LangRef/
- MLIR Dialect Conversion: https://mlir.llvm.org/docs/DialectConversion/
- LLVM Language Reference: https://llvm.org/docs/LangRef.html
- K Framework documentation: https://kframework.org/docs/user_manual/
- K Framework project: https://kframework.org/

## Security and authority

- NIST SP 800-218 Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- Capability Myths Demolished, Miller, Yee, Shapiro: https://papers.agoric.com/assets/pdf/papers/capability-myths-demolished.pdf
- Model Context Protocol specification: https://modelcontextprotocol.io/specification/

## Unicode and notation

- Unicode Standard Annex #31, Unicode Identifiers and Syntax: https://www.unicode.org/reports/tr31/
- Unicode Standard Annex #15, Unicode Normalization Forms: https://www.unicode.org/reports/tr15/

## Reproducibility and provenance

- Reproducible Builds formal definition: https://reproducible-builds.org/docs/formal-definition/
- SLSA v1.2 specification: https://slsa.dev/spec/v1.2/
- SLSA provenance: https://slsa.dev/spec/v1.2/provenance
- Semantic Versioning 2.0.0: https://semver.org/

## ARIA conclusions derived from the research

- Keep notation, IR, validation, binary encoding, and execution distinct.
- Treat glyphs as accessible semantic aliases rather than visual opcodes.
- Verify bytecode independently from artifact checksums.
- Deny ambient authority and require explicit activation of host effects.
- Separate reproducible executables from timestamped provenance and mutable memory.
- Keep AI proposals outside the deterministic trust boundary.
