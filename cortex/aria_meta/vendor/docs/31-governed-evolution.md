# Governed Evolution alpha.20

ARIA can now represent a language change as a verified proposal rather than an ambient edit.

```text
AI proposes
  → content-addressed envelope
  → capability authority
  → explicit human authorization
  → base-state verification
  → candidate repository state
  → semantic change summary
  → rollback proof
  → required gates
  → governed decision event
```

## Proposal envelope

An `aria.evolution-proposal/0.6` envelope contains:

- proposer identity;
- exact base commit;
- target semantic version;
- repository resource;
- requested effects;
- referenced capability identities;
- content-addressed changes;
- evidence;
- required gates;
- complete rollback plan;
- reserved signature form;
- proposal identity.

A proposal is not authority. It is a deterministic request for authority.

## Change identity

Each change declares:

```text
path
operation
before digest
after digest
after content
```

The verifier rejects:

- path traversal;
- absolute or drive-qualified paths;
- `.git` mutation;
- duplicate paths;
- unknown operations;
- after-content digest mismatch;
- no-op changes;
- current-state digest mismatch.

## Human authorization

Human approval is a separate content-addressed artifact.

```text
proposal identity
authorizer identity
approved or rejected
decision time
nonce
authorization identity
```

Embedding `"approved": true` inside a proposal is not sufficient. The approval artifact must reference the exact proposal identity and come from a trusted authorizer.

## Authority

The proposal's capability identity must resolve to a valid Alpha.19 capability chain.

Authority verification binds:

```text
token subject   = proposal proposer
token resource  = proposal resource
token effects   ⊇ proposal requested effects
```

Issuer policy, delegation, time, revocation, and nonce rules remain load-bearing.

## Candidate repository

Alpha.20 applies changes to a deterministic repository snapshot, not directly to an unverified workspace.

The candidate is content-addressed. Its semantic summary reports added, removed, and modified paths by digest.

## Rollback proof

Every changed path requires an inverse operation.

ARIA applies the rollback plan to the candidate and requires the restored snapshot identity to equal the original snapshot identity.

```text
candidate
  → rollback plan
  → restored snapshot
  → original identity reproduced
```

A written rollback paragraph is not proof. Reproduced identity is proof.

## Required gates

Every proposal must require:

```text
manifest
doctor.strict
conformance
```

The evolution program still runs these gates after writing the actual repository changes and before commit.

## Governed decision event

An approved plan emits a content-addressed event containing:

- proposal identity;
- authorization identity;
- authority-decision identity;
- base commit;
- original and candidate snapshot identities;
- semantic diff;
- rollback verification;
- required gates.

The event type is:

```text
aria.evolution.plan.approved
```

## Current boundary

Alpha.20 proves and records a governed plan. The outer evolution program remains responsible for applying the accepted repository files, running real gates, committing, pushing, and verifying remote identity.

This separation prevents arbitrary proposal content from becoming an implicit command runner.

## Evolution invariant

```text
AI may propose.
A capability chain may authorize the proposer.
A human must approve the exact proposal identity.
The candidate must be reversible.
The gates must pass.
Only then may Git record the transition.
```