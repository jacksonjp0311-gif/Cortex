# Algorithm: Container Integrity

The `.ariac` reader:

1. reads fixed header fields;
2. rejects an invalid magic, version, compression identifier, or truncated payload;
3. decompresses exactly the declared payload;
4. rejects an uncompressed length mismatch;
5. computes SHA-256 over the uncompressed bytes;
6. compares it with the embedded digest;
7. parses bytecode JSON only after integrity succeeds.

This catches corruption and accidental substitution. It is not a digital signature and does not prove who produced the artifact. Signed provenance is future work.
