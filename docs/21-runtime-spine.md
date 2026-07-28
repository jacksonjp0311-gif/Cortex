# Runtime Spine alpha.9

Runtime Spine routes command-level execution facts through the canonical Event Spine and Etherflow.

Integrated domains:

- `compiler` — semantic gate, translation, and compressed artifact creation;
- `verifier` — semantic acceptance and bytecode artifact acceptance;
- `policy` — explicit authority evaluation before VM execution;
- `vm` — execution activation and deterministic halt;
- `connection` — intent, proposal, consent evaluation, and closure.

The integration is deliberately orchestration-level. Compiler and VM internals remain deterministic and independently testable; the CLI publishes verified milestones after each subsystem returns successfully.

A PASS event is never emitted before the underlying operation succeeds. FAIL remains reserved for the outer pipeline exception handler.