# Verified Improvement Circulation

Cortex 10.0.0-alpha.4 separates three propositions that must not collapse:

```text
proposal validity != verification success != operator promotion
```

## Circulation

```text
model proposal
  -> immutable trajectory
  -> exact operator review
  -> host-owned verification contract
  -> detached Git worktree
  -> fixed verification steps
  -> immutable verification receipt
  -> second operator promotion decision
  -> HEAD and preimage revalidation
  -> bounded active-tree application
  -> immutable application receipt
```

The active checkout is unchanged during verification. The host creates the
command contract from the proposal's target scope. Neither the model nor the
HTTP caller supplies command vectors, thresholds, or pass states. Runtime
source changes receive `compileall` and the repository test suite in addition
to target-scoped Git whitespace checks. Documentation-only changes receive the
scope-appropriate Git check.

Model proposals cannot edit the evaluator surfaces used at this boundary:
tests, CI workflows, CI scripts, and test-runner configuration are protected.
Changing an evaluator requires a separate human-authored transaction. The
detached worktree isolates repository state; it is not an operating-system
security sandbox, so approving verification also explicitly approves executing
the reviewed candidate under the declared host checks.

Verification receipts preserve the source HEAD, proposal hash, contract hash,
step results, durations, bounded public output, and candidate postimage hashes.
A failed step produces `held`; continuous scores cannot compensate for it.

Promotion is a distinct authority edge. It requires a canonically valid
`verified` receipt for the same proposal and native session, an unchanged Git
HEAD, fresh target preimages, and a second explicit operator decision. The
receipt does not become reusable mutation authority.

## Claim boundary

Alpha.4 establishes independently tested source-change circulation. It does
not establish autonomous self-improvement or a positive capability delta. A
future improvement trial must freeze a baseline, metric, minimally important
effect, and comparison method before execution.

All evidence surfaces preserve:

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
```
