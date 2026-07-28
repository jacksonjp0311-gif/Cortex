# ADR 012: Semantic proposal bundles

Status: Accepted for Semantic Proposal Bundles alpha.11.

## Decision

ARIA introduces `aria.semantic-proposal/1` as the non-mutating semantic contract
between verified intent and the existing governed file transaction.

The bundle binds the exact intent, proposer, baseline, semantic subject, all
language-dimension deltas, changed-path allowlist, proof obligations, test plan,
compatibility classification, reversal map, and optional alpha.10 execution
evidence references. Its digest is derived from canonical content.

A proposal has `authority.class = proposal`, grants no capabilities, is always
`unapproved`, and is never executable. Authority expansion may be described only
when `requiresExplicitAdmission` is true. The producer cannot embed approval.

## Boundary

This milestone does not admit or apply proposals. Human consent and deterministic
admission are alpha.12. Existing `aria evolve plan`, verify, and apply machinery
continues to govern repository mutation.

## Consequences

- Humans and AI can review the same bounded meaning before byte changes.
- Hidden paths, incomplete semantic dimensions, missing rollback, implicit
  authority, self-approval, evidence drift, and digest tampering are rejected.
- A valid proposal proves internal coherence, not correctness or permission.
