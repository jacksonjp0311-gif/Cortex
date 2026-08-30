# Canonical Autonomous Campaign Seal

Version: `10.0.0-alpha.9`

## Purpose

Alpha.9 closes the difference between a valid-looking campaign mapping and a
campaign reconstructed from Cortex's immutable evidence ledger.

The release law is:

```text
reference
  -> canonical reload
  -> identity and chain verification
  -> cross-object binding verification
  -> noncompensatory policy gate
  -> isolated canary
  -> bounded active-tree application
```

Never:

```text
caller mapping + valid=true -> promotion
```

## Canonical campaign path

`resolve_canonical_storm_result()` accepts only a Storm summary receipt hash.
It invokes the canonical Storm verifier, reloads the summary, and reloads every
linked observation. Candidate extraction then reloads each native-agent
trajectory and accepts only exact `workspace.propose_patch` tool results.

The campaign persists isolated verification, matched counterfactual trials,
and the deterministic tournament. Promotion reloads the tournament and selected
trial by receipt hash and verifies their policy, proposal, and result bindings.

## Policy lifecycle

An autonomy policy is signed by a registered host principal and includes its
body epoch in signed material. A stale, unverified, expired, not-yet-current,
secret-mismatched, or immutably revoked policy cannot authorize promotion.

Automatic promotion requires at least one host-declared canary command vector.
No shell string is introduced at the execution edge.

## Transaction boundary

The signed canary runs after applying the candidate in a detached temporary Git
worktree. Canary failure discards that candidate worktree and never changes the
operator's active files. Only a successful isolated canary permits the existing
bounded active-tree application, whose own diff and compilation checks retain
automatic reverse-patch recovery.

This is a pre-apply isolation boundary, not a database/source distributed
transaction. A future authenticated control phase should add prepared,
integrated, and recovered states around commit-level integration.

## Service boundary

`/v1/autonomy` reports immutable policy, revocation, tournament, and promotion
counts. It does not expose policy issuance, campaign execution, or promotion.
The current loopback service has no independent operator-authentication and
anti-CSRF boundary, so adding a mutation endpoint would weaken host sovereignty.

## Claim boundary

Alpha.9 verifies canonical campaign resolution, epoch-bound revocable policy,
and isolated pre-apply canaries. It does not establish beneficial recursive
self-improvement, autonomous goals, consciousness, or safe unattended operation.
No model acquires host mutation, execution, memory admission, competence
promotion, or policy authority.
