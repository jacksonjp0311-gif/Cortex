# Event Spine v3

Event Spine is ARIA's canonical internal event bus. Compiler, verifier, VM, policy, connection, and provider subsystems can now describe runtime facts with one typed object rather than writing provider-specific terminal text.

Every current `aria.event` contains:

- a workspace-wide sequence that resumes across CLI processes;
- a cryptographic operation identity and operation-local sequence;
- the previous ledger event digest;
- domain and phase identities;
- execution state;
- Etherflow's energy, information, and coherence lanes;
- source identity and UTC occurrence time;
- typed data;
- a canonical SHA-256 digest.

The spine supports in-memory subscribers, append-only NDJSON persistence under
`.aria/events`, replay verification, direct semantic-projection rendering, and
an exclusive append boundary. Event versions 1 and 2 remain individually
verifiable; all new events use version 3.

The v3 ledger is a chain rather than a bag of records:

```text
event[n-1].digest == event[n].previousDigest
event[n].sequence == physical ledger position
```

Deletion, reordering, duplication, tampering, stale append attempts, and
cross-session sequence resets are rejected.

Full initialization and replay validate every record and establish the exact
ledger-byte identity. Later appends take an exclusive lock and require those
bytes plus the verified tail identity to remain unchanged. This lets iterable
language operations record bounded per-iteration events without reparsing the
complete history for each append.

Verified iterable operations persist constructed events in bounded 32-record
chunks. Each chunk takes one exclusive append lock, checks the exact prior
ledger-byte identity and verified tail, verifies sequence and previous-digest
continuity for every record, writes once, and updates the cached byte identity.
Publicly supplied events still cross the complete event verifier. Events
constructed and sealed inside Event Spine avoid a redundant second digest
verification before publication.

The content-addressed semantic-cue registry is fully verified once per module
process and then reused as that exact in-memory identity. Passing an explicit
registry to projection APIs continues to trigger full validation.

Verified Map, Filter, and Reduce terminal events now derive one
`aria.card-execution-evidence/1` receipt. The receipt binds the exact card,
program artifact, effect graph, policy, admission-test contract, aggregate
counts, and terminal event identity. A privacy-filtered SignalSubset records
the exact selected and excluded event fields. Event Spine then seals a bounded
`evidence.card.execution` linkage event.

## Authority boundary

Events describe what happened. They do not grant authority. Policy and bytecode verification remain independent execution gates.

## CLI

`aria events` reads the verified local event ledger and renders recent events through the active Etherflow profile.

`aria transmit` publishes provider normalization, artifact sealing, and provenance verification into the same spine used by future compiler and VM integrations.

The aggregate test orchestrator reinitializes and fully verifies the workspace
ledger after all suite-level module reloads and before publishing its closure
event. A stale cached byte identity is never silently accepted.
