# ADR 0005: Use Structured Control Bytecode in the Bootstrap VM

## Status

Accepted for ARIA specification 0.3.0.

## Decision

Represent conditionals and bounded loops as opcodes containing nested instruction arrays rather than relative or absolute jump offsets.

## Rationale

Structured control exposes topology to the verifier, preserves lexical scope boundaries, avoids invalid jump targets, and maps directly to glyphic execution trees. It also keeps the alpha disassembler and canonical JSON artifact understandable.

## Consequences

The format is less compact than native-style branch bytecode and requires recursive verification and execution. A future lowering stage may translate verified structured control into denser jumps or native IR without changing source semantics.
