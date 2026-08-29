# Governed Coding Workspace

Cortex 10.0.0-alpha.3 closed the first operator-mediated source-change loop.
Alpha.4 separates isolated verification from active-checkout promotion; see
`VERIFIED_IMPROVEMENT_CIRCULATION.md`.
The reasoning model may inspect the attached repository and submit an exact git
unified diff through `workspace.propose_patch`. That tool is observational: it
records the summary, patch, target paths, file preimage hashes, and proposal
hash in the immutable native-agent trajectory. It cannot apply the patch.

```text
model proposal
    → sealed trajectory
    → canonical proposal resolution
    → exact diff review
    → explicit local operator approval
    → preimage freshness check
    → git apply --check
    → bounded application
    → fixed verification
    → immutable application receipt
```

The approval request contains only the proposal hash and a session-bound review
challenge. Cortex reloads the patch body from canonical trajectory evidence;
the caller cannot substitute another diff at the authority edge. A stale target
preimage blocks application.

Initial verification is intentionally narrow and deterministic:

- target-scoped `git diff --check`;
- `python -m py_compile` for changed Python files;
- automatic reverse-application when a fixed verification step fails.

Binary patches, deletion, rename, `.git`, `.cortex`, generated star-history
targets, path escape, duplicate target declarations, stale preimages, malformed
diffs, and mismatched approval challenges fail closed.

An application receipt records exactly what changed and which checks passed.
It keeps model authority closed:

```text
model_host_mutate_authorized = false
model_execution_authorized   = false
memory_admission_authorized  = false
policy_effect                = false
```

The operator authorizes one exact transaction. That approval is not durable
authority and cannot be reused for a different proposal. Alpha.3 therefore
supports supervised improvement of Cortex from within Cortex without claiming
autonomous self-modification, successful task completion, or competence.
