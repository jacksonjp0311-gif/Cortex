# Algorithm: Reproducible Build

The executable model contains only deterministic inputs: normalized source-derived IR, compiler/spec/container versions, constant pool, graph metadata, declarations, and instructions.

It excludes current time, machine path, user identity, mutable memory, random identifiers, and environment ordering.

The gate serializes the same model twice in the active bootstrap runtime, compresses it twice, and compares complete artifact hashes. Cross-runtime byte identity remains a conformance target until CI compares multiple hosts. Timestamped paths and provenance are written after this proof and do not alter the executable bytes.
