# Evolution Planning alpha.23

ARIA can now turn a declarative repository-change request into a persistent,
content-addressed plan:

```powershell
.\aria.cmd evolve plan .\examples\evolution-plan.json
```

Planning is deliberately non-mutating. It reads the exact current bytes of
affected paths and the current Git commit, then produces:

```text
request
  → path and request validation
  → before/after content digests
  → proposal identity
  → original and candidate snapshots
  → semantic diff
  → executable rollback proof
  → awaiting-authorization record
```

The CLI requires a clean Git worktree before resolving those identities. This
prevents a proposal from naming one base commit while silently deriving
before-digests from unrelated local modifications.

## Request contract

An `aria.evolution-request/0.7` document declares:

- proposer identity;
- target semantic version;
- repository resource;
- referenced capability identities;
- requested writes or deletions;
- content-addressed evidence.

The planner fixes `repository.write` as the requested effect and requires the
`manifest`, `doctor.strict`, and `conformance` gates.

## Persistent records

Successful planning writes five canonical JSON documents beneath:

```text
.aria/evolution/<proposal-digest>/
  request.json
  proposal.json
  original-snapshot.json
  candidate-snapshot.json
  plan.json
```

The directory is local runtime state and is excluded from the repository
manifest. Repeating the same plan is idempotent. Existing records with
different bytes are treated as identity collisions and rejected.

## Authority boundary

The resulting state is always:

```text
awaiting-authorization
```

`evolve plan` does not:

- grant or resolve a capability;
- create human authorization;
- apply candidate content;
- reseal the repository manifest;
- execute gates;
- commit or push Git state.

A capability identity in a request is a reference, not authority. Proposal
content remains inert data until a later verification command resolves the
capability chain and an exact human authorization artifact.

## Rejection contract

Planning rejects:

- absolute, traversing, `.git`, and unsafe repository paths;
- duplicate target paths;
- unknown operations;
- writes without content;
- deletions with replacement content;
- deletions of missing files;
- malformed capability identities;
- absent or malformed evidence;
- no-op and unverifiable proposals;
- dirty worktrees whose bytes are not represented by the named base commit;
- rollback plans that do not reproduce the original snapshot.

## Next boundary

`evolve verify` should consume the persisted proposal plus separate capability,
issuer-policy, and human-authorization artifacts. It may advance a record to
`authorized`, but it must still perform no repository mutation.
