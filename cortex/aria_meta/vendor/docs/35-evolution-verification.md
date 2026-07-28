# Evolution Verification alpha.24

ARIA can now authorize a persisted evolution plan without applying it:

```powershell
.\aria.cmd evolve verify <proposal-id> `
  -Capability .\capability-bundle.json `
  -Authorization .\authorization.json `
  -IssuerPolicy .\verification-policy.json
```

## Verification path

```text
persisted plan
  → canonical record reload
  → proposal and snapshot identity verification
  → request regeneration
  → current commit and workspace-byte comparison
  → capability-chain resolution
  → trusted-authorizer decision
  → candidate reconstruction
  → rollback proof
  → authorized verification record
```

The CLI requires a clean worktree. The current commit must equal the proposal's
base commit, and regenerating the request against current files must reproduce
the proposal, original snapshot, candidate snapshot, and plan-record identities.

## Capability input

`-Capability` accepts either:

- a root `aria.capability/0.5` token; or
- an `aria.capability-bundle/0.8` object containing `token` and `knownTokens`
  for delegated chains.

The token must be referenced by the proposal and grant `repository.write` to
the proposal's exact proposer and repository resource.

## Verification policy

`aria.evolution-verification-policy/0.8` keeps two trust decisions explicit:

- issuer trust for capability chains;
- human authorizer trust for the exact proposal decision.

The authorization timestamp is the deterministic capability decision time.
No ambient clock value participates in verification identity.

## Append-only records

Successful verification adds four files to the existing proposal directory:

```text
authorization.json
authority-decision.json
governed-event.json
verification.json
```

`verification.json` is content-addressed and has state `authorized`. Existing
planning records remain unchanged.

## Non-mutation invariant

`evolve verify` does not:

- write candidate files;
- reseal `MANIFEST.sha256`;
- execute repository gates;
- create commits;
- contact or push a Git remote.

Authorization proves that a specific candidate may proceed to the future apply
boundary. It is not itself repository mutation.

## Next boundary

`evolve apply` must consume an authorized verification record, recheck all
identities immediately before mutation, apply only declared paths
transactionally, run the three required gates, and restore the original
snapshot automatically if any gate fails.
