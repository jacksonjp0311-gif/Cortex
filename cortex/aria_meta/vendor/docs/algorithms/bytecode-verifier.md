# Bytecode Verification

The ARIA VM treats every `.ariac` payload as untrusted, even when its SHA-256 digest is valid. A digest proves integrity relative to the container; it does not prove that the instructions are safe or well formed.

## Verification state

For an instruction stream `I`, the verifier tracks:

- current stack depth `d`;
- maximum stack depth `d_max`;
- defined local variables `L`;
- declared memories `M`;
- declared capabilities `C`;
- effects activated by `REQUIRE_CAP`;
- whether `HALT` has been observed.

Each opcode has a stack transfer function. For example:

```text
PUSH_CONST: d' = d + 1
STORE:      require d >= 1; d' = d - 1
ASSERT_EQ:  require d >= 2; d' = d - 2
FS_WRITE:   require d >= 2 and active(fs.write); d' = d - 2
```

The verifier rejects:

- unknown opcodes;
- stack underflow;
- constants outside the pool;
- loads of undefined locals;
- references to undeclared memory or capabilities;
- filesystem instructions without a previously activated matching effect;
- instructions after `HALT`;
- missing `HALT`;
- nonzero terminal stack depth;
- incompatible container or specification versions;
- excessive constant or instruction counts.

Compilation and execution both invoke the verifier. This creates a trust boundary between serialized bytecode and the VM implementation.
