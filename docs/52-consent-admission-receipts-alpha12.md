# Consent and Admission Receipts alpha.12

Alpha.12 connects alpha.11 semantic proposals to ARIA's established governed
evolution transaction without collapsing meaning, consent, and capability.

```text
verified intent
  → semantic proposal
  → independent human consent
  → deterministic admission receipt
  → governed evolution planning
  → capability authorization
  → deterministic apply
```

## Semantic consent

`aria.semantic-consent/1` binds:

- the exact proposal, intent, semantic path scope, and rollback scope;
- distinct producer and human approver identities;
- approved or rejected decision, canonical decision time, and nonce;
- acknowledgements that a proposal is not authority and that scope and rollback
  were reviewed;
- an explicit acknowledgement when the proposal describes authority expansion.

Alpha.12 retains the reserved unsigned local signature form. Cryptographic
operator signatures remain a future hardening boundary.

## Admission

`aria.admission-receipt/1` reconstructs:

- proposal identity;
- consent identity and decision;
- producer/approver separation;
- current baseline identity;
- exact semantic scope;
- complete rollback;
- explicit authority handling.

An admitted receipt is deterministic, non-mutating, and capability-free. Its
only legitimate next boundary is `evolution-planning`.

## Non-meaning

An admission receipt does not mean the proposal is universally correct, that
tests passed, that remote CI passed, or that repository mutation is authorized.
Those claims require later transaction and closure evidence.

## Next boundary

Deterministic Semantic Replay was renumbered alpha.14 after Agent Semantic
Handshake alpha.13 and now reproduces the same admitted semantic state—or
identifies the first exact drift boundary—before handoff, provider, or mesh
coordination.
