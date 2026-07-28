# ARIA Security Policy

ARIA is an experimental language runtime with local execution authority. Treat source programs as code.

## Bootstrap threat model

The specification 0.4.0 VM supports typed local execution, functions, bounded structured control flow, console output, explicit memory, graph metadata, deterministic agent-dispatch events, verified connection lifecycles, assertions, and policy-gated filesystem access. It deliberately does **not** implement network access, subprocess execution, dynamic module loading, native calls, or arbitrary PowerShell evaluation.

## Security invariants

1. Host effects are denied unless declared by an ARIA capability and allowed by `aria.policy.json`.
2. Paths are canonicalized and confined to both the repository root and capability scope.
3. The compiler never invokes `Invoke-Expression` or evaluates ARIA source as PowerShell.
4. Compiled artifacts contain no mutable runtime memory and no build timestamp.
5. Container decoding enforces fixed-header, encoded-size, decompression-size, reserved-field, UTF-8, JSON, and SHA-256 checks.
6. The VM independently verifies bytecode compatibility, opcodes, references, stack safety, capability activation, and termination before execution.
7. A program cannot acquire authority through AI confidence, graph position, or glyph appearance.

## Reporting

Do not publish a suspected vulnerability before maintainers have had a reasonable opportunity to investigate. Include the affected version, minimal reproduction, expected invariant, and observed behavior.

## Alpha limitations

Path confinement is lexical and canonical but does not yet provide a complete defense against malicious filesystem reparse points, junctions, or symbolic-link layouts. Do not run untrusted repositories with host capabilities enabled. The default build has no process or network opcode, treats agent dispatch as data rather than model execution, and denies filesystem writes.

- Effect payloads are bounded by policy-defined `maxBytes` limits.
