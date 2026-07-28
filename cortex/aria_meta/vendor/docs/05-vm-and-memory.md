# Virtual Machine and Memory

## VM posture

The bootstrap VM is intentionally an interpreter. It verifies container integrity before executing a fixed opcode table. ARIA source is never passed to PowerShell evaluation.

## Memory classes

ARIA distinguishes:

1. **Operand memory:** transient stack values.
2. **Local memory:** transient flow bindings.
3. **Declared memory:** durable program state.
4. **Provenance memory:** future append-only state transition history.

Declared memory is merged from compiled defaults and `.aria/state/<program>.memory.json`. The state file is repository-local, inspectable JSON, excluded from source control by default, and written atomically.

## Why memory is outside bytecode

Keeping mutable state outside `.ariac` preserves reproducible builds, permits memory erasure without recompilation, and prevents a compiled artifact from silently carrying a user's historical state.

## Future evolution

The next memory model adds typed schemas, fact identity, confidence/evidence metadata, expiration, dispute state, event-sourced history, migration functions, and capability-separated read/write authority.
