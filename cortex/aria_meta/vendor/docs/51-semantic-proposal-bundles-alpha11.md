# Semantic Proposal Bundles alpha.11

Alpha.11 adds the missing semantic contract before ARIA's governed repository
transaction.

```text
verified intent
  → semantic proposal (unapproved, non-executable)
  → human review
  → alpha.12 consent and admission
  → existing deterministic evolution transaction
```

`aria.semantic-proposal/1` gives a human and an AI one content-addressed object
for discussing what a language evolution means. It contains:

- the exact intent and baseline identities;
- producer identity and semantic subject;
- explicit grammar, lowering, type, effect, opcode, policy, and authority deltas;
- an exact repository-relative changed-path allowlist;
- proof obligations and generated tests;
- compatibility, migration, and exact reversal statements;
- optional references to alpha.10 card-execution receipts.

## Safety boundary

A proposal cannot approve itself, execute, grant a capability, or mutate the
repository. Declared authority expansion remains inert and requires explicit
admission. Validity means that the proposal is complete, internally coherent,
content-addressed, and reviewable—not that its claims are universally true.

The verifier rejects unsafe or duplicate paths, no-op changes, rollback
asymmetry, missing language dimensions, empty obligations, malformed evidence
references, implicit authority, embedded approval, and digest tampering.

## Operator use

```powershell
.\aria.ps1 semantic propose .\proposal-request.json
.\aria.ps1 semantic verify .\proposal.json
```

The first command constructs canonical JSON without mutation. The second
recomputes its identity and reports the exact approval boundary.

## Next boundary

Consent and Admission Receipts alpha.12 will bind an independent human decision
to the exact proposal digest before the existing apply machinery may act.
