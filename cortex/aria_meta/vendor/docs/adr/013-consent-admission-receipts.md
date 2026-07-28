# ADR 013: Consent and admission receipts

Status: Accepted for Consent and Admission Receipts alpha.12.

## Decision

ARIA introduces two content-addressed artifacts:

- `aria.semantic-consent/1` records an independent human decision over the exact
  alpha.11 proposal, intent, semantic scope, rollback scope, and authority
  acknowledgement.
- `aria.admission-receipt/1` deterministically reconstructs eight admission
  obligations from the proposal, consent, trusted approvers, and current Git
  baseline.

Consent may record approval or rejection. Only exact, trusted, independent
approval can produce `verdict = admitted`. Admission enables the next
`evolution-planning` boundary but grants no repository capability and performs
no mutation.

## Separation

Semantic consent is not the older file-transaction authorization. Admission is
the bridge into that established layer. The existing capability verifier must
still authorize exact filesystem effects before apply.

## Consequences

- Self-approval, untrusted approval, proposal drift, scope drift, stale
  baselines, missing acknowledgements, and tampering are rejected.
- Withheld consent remains valid evidence and deterministically closes as
  rejected.
- Identical inputs reconstruct the same admission receipt.
- Admission means eligible for governed planning, not executable, correct,
  remotely attested, or authorized to mutate files.
