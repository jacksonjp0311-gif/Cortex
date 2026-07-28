# Cross-Domain Research Map

ARIA combines ideas from programming-language design, virtual machines, graph systems, security, human-computer interaction, memory systems, and AI tool protocols. This document separates established lessons from ARIA-specific decisions.

## Compiler construction and multi-level IR

**Established lesson:** syntax, semantic validation, intermediate representation, optimization/lowering, binary representation, and execution are separate concerns. WebAssembly specifies text, binary, validation, and execution layers; MLIR demonstrates progressive conversion between dialects and abstraction levels.

**ARIA decision:** glyph and text notation normalize into one semantic IR. The bootstrap compiler lowers only the entry flow to stack bytecode while retaining graph metadata. Future targets may lower through typed ARIA dialects before WebAssembly or native backends.

## Virtual machines and bytecode verification

**Established lesson:** a portable bytecode boundary can isolate source notation from host implementation, but container integrity is not semantic validity.

**ARIA decision:** `.ariac` uses a bounded, checksummed, compressed envelope. The bytecode verifier independently proves reference validity, stack safety, compatibility, effect activation, and termination shape before the VM executes.

## Formal semantics and rewriting logic

**Established lesson:** language meaning can be represented as explicit state transitions and guarded rewrite rules rather than prose alone.

**ARIA decision:** define sequential VM transitions first. Add graph rewriting only after deterministic flow semantics and conformance fixtures stabilize.

## Capability security

**Established lesson:** authority should be conveyed explicitly and minimized; possession of authority is distinct from merely naming an operation.

**ARIA decision:** host effects require declaration, policy approval, runtime activation, and target confinement. Unknown effects are denied. ARIA exposes a narrow opcode set rather than forwarding arbitrary PowerShell.

## Secure software development

**Established lesson:** security must be integrated into development and release workflows, not added after implementation.

**ARIA decision:** compiler gates, manifest integrity, tests, deny-by-default policy, bounded decoding, and provenance are part of the repository contract and CI.

## Reproducible builds and supply-chain provenance

**Established lesson:** reproducibility requires the same source, build environment, and instructions to recreate bit-identical artifacts; provenance records how an artifact was produced.

**ARIA decision:** the gate serializes twice and compares artifact hashes. Time, mutable memory, and machine paths are excluded from `.ariac`. Timestamped provenance is emitted separately.

## Unicode, semiotics, and accessibility

**Established lesson:** Unicode syntax requires normalization and identifier profiles. Visual symbols vary by font, input system, and accessibility technology.

**ARIA decision:** glyphs are aliases over stable semantic identifiers with textual and spoken equivalents. Bootstrap identifiers use a deliberately narrow ASCII profile while the glyph registry is evaluated separately.

## Graph theory and visual programming

**Established lesson:** graph structure can encode dependency, authority, dataflow, and transformation, but visual layout itself is not a reliable semantic identity.

**ARIA decision:** canonical graphs exclude screen coordinates. Meaning resides in named nodes, typed relationships, attributes, and rewrite rules. Animation and visual effects must reveal runtime state rather than decorate it.

## Databases, event sourcing, and memory

**Established lesson:** mutable operational state and immutable executable definitions have different lifecycle, privacy, and reproducibility requirements.

**ARIA decision:** memory declarations and defaults compile; live memory remains repository-local and outside artifacts. The roadmap moves toward event-sourced facts, provenance, expiration, redaction, and rollback.

## Concurrency and distributed systems

**Established lesson:** parallel actions require explicit communication and conflict models; nondeterministic scheduling complicates replay and verification.

**ARIA decision:** version 0.1 is sequential. Future concurrency must declare read/write sets or equivalent effects, support deterministic replay profiles, and make conflicts visible in the semantic graph.

## AI agents and tool protocols

**Established lesson:** AI tool ecosystems separate model-generated requests from tools and resources, with authorization handled at a protocol or host boundary.

**ARIA decision:** AI systems will emit typed proposals or ARIA source. ARIA policy and compiler rules remain authoritative. Interoperability protocols may transport context and tool requests, but they cannot bypass ARIA capability checks.

## Human-computer interaction

**Established lesson:** direct manipulation can improve comprehension when users can inspect state, causality, and reversibility. Decorative complexity increases cognitive load.

**ARIA decision:** the future glyph studio must show authority boundaries, active flows, memory changes, failures, provenance, simulation, and rollback. Every visual operation must have a lossless textual representation.
