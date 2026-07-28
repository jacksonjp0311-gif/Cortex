# Algorithm: Gated Compilation

Input: normalized source `S`, repository policy `P`, compiler version `V`.

1. Reject if source exceeds the bootstrap limit.
2. Lex non-empty lines while removing comments outside strings.
3. Parse blocks into semantic IR.
4. Validate language and program versions.
5. Build name maps and reject duplicates or unresolved references.
6. Validate expression dataflow within each flow.
7. Validate each declared capability against `P`.
8. Require matching activated capabilities before host instructions.
9. Compile the entry flow to stack bytecode.
10. Serialize the ordered bytecode model to canonical compact JSON.
11. Hash the uncompressed payload with SHA-256.
12. Compress and envelope it as `.ariac`.
13. Repeat steps 10–12 and compare the complete bytes.
14. Decompress and verify the embedded digest and source hash.
15. Permit artifact writing and execution only after all checks pass.

Complexity is linear in source lines plus graph edges for the bootstrap feature set, assuming hash-table name resolution.
