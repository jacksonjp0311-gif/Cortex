# Bytecode Verification Algorithm

Container integrity and bytecode validity are separate gates.

## Inputs

- decoded ARIA bytecode model;
- `aria.lock.json` compatibility contract;
- opcode table and stack effects.

## Algorithm

1. Verify format, compiler, specification, and container versions.
2. Validate program identity, semantic version, entry name, and SHA-256 fields.
3. Bound the constant pool and instruction count.
4. Index memory and capability declarations; reject duplicates.
5. Walk instructions in order while maintaining:
   - abstract stack depth;
   - maximum stack depth;
   - declared local bindings;
   - active effect set;
   - termination state.
6. For every instruction:
   - validate the opcode;
   - validate all operands and references;
   - apply its abstract stack effect;
   - reject underflow;
   - record definitions and activated effects;
   - reject instructions after `HALT`.
7. Require at least one `HALT` and a final stack depth of zero.
8. Return all verifier errors rather than only the first.

## Invariants

- No constant index leaves the constant pool.
- No variable is loaded before definition.
- No memory instruction references undeclared memory.
- No filesystem instruction appears before activation of a matching capability.
- No unsupported opcode reaches the VM.
- Verified sequential bytecode has a statically bounded operand stack.

## Security observation

A malicious actor can construct a new container and compute a correct checksum. Therefore, SHA-256 validation cannot replace bytecode verification. `Invoke-AriaArtifact` verifies both before execution.
