# Conformance and Bootstrap Trust

## Language identity

ARIA is defined by the specification, grammar, bytecode contract, conformance fixtures, and observable execution behavior. The PowerShell modules are the first reference implementation; they are not the language definition.

## Bootstrap chain

```text
Windows PowerShell 5.1 or PowerShell 7
        ↓ hosts
ARIA reference compiler and VM
        ↓ compiles
ARIA bytecode containers (.ariac)
        ↓ execute under
ARIA semantic and capability rules
```

A future implementation in another host language is conforming when it accepts and rejects the same fixtures and produces semantically equivalent results. Byte-for-byte artifact identity is required only for implementations claiming compatibility with the same canonical encoder and compiler lock.

## Conformance levels

### Parser conformance

- accepts normative grammar fixtures;
- emits stable diagnostic codes for invalid fixtures;
- normalizes UTF-8 and line endings as specified.

### Compiler conformance

- produces valid ARIA IR and bytecode;
- enforces reference, glyph, memory, and capability rules;
- emits deterministic canonical payloads.

### VM conformance

- verifies containers and bytecode before execution;
- implements opcode transition rules;
- applies deny-by-default policy and path confinement;
- keeps mutable memory outside executable artifacts.

### Full implementation conformance

- passes parser, compiler, verifier, VM, security, and reproducibility fixtures;
- reports implementation and specification versions;
- does not add ambient host authority under an existing opcode.

## Trust boundary

The bootstrap host is trusted to execute the reference implementation faithfully. ARIA narrows that host through a deliberately small opcode set. There is no opcode for arbitrary PowerShell evaluation, process launch, network access, dynamic modules, or native calls in version 0.1.

## Self-hosting

Self-hosting is not required for ARIA to be a real language. It becomes useful only after the type system, verifier, module model, and conformance suite are mature enough to detect bootstrap divergence.
