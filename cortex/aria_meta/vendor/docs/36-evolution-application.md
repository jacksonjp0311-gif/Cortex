# Evolution Application alpha.25

ARIA now completes an authorized repository evolution as one bounded transaction:

```powershell
.\aria.cmd evolve apply <proposal-id> -Message "Describe the authorized evolution"
```

Add `-Push` only when the resulting commit should be transported to `origin/main`.

## Glyph execution sequence

```text
🜁 reconstruct authorized snapshot
🜃 verify clean tree and exact base commit
🜄 preserve rollback boundary
🜂 apply candidate bytes
🜍 seal manifest, run doctor strict, run conformance
◆ commit exactly the approved paths plus MANIFEST.sha256
∿ optionally push and verify remote identity
```

## Safety invariants

Application rejects a proposal when:

- the verification record is absent or not `authorized`;
- plan, verification, and candidate identities differ;
- rollback proof is not verified;
- the current Git commit differs from the authorized base commit;
- the worktree is dirty;
- candidate content does not match its authorized digest;
- manifest, doctor, or conformance gates fail;
- changed paths differ from the authorized path set.

Before a commit exists, any failure resets tracked files to the exact base commit and removes newly added proposal paths. A push failure does not destroy the verified local commit.

## Receipt

Successful application writes ignored runtime state to:

```text
.aria/evolution/<proposal-digest>/application.json
```

The receipt binds the proposal, verification, candidate snapshot, base commit,
resulting commit, gate results, path set, and optional remote transport state.