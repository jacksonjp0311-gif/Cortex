# Authenticated Campaign Control

Status: **sealed in Cortex 10.0.0-alpha.10**

Alpha.9 intentionally kept the loopback web service observational. Alpha.10
begins closing the next boundary: a human operator may authorize a narrowly
described campaign action, while models, UI payloads, and stale browser state
remain unable to manufacture host authority.

## Control law

```text
registered host principal
  -> current verified body epoch
  -> short-lived loopback control session
  -> bearer proof + CSRF proof + exact origin
  -> allowed action + unique nonce + request hash
  -> immutable one-shot authorization
```

Caller intent is not authority. A control action is accepted only after Cortex
reloads and verifies the canonical session receipt, matches both secret hashes,
checks the exact loopback origin, confirms the action was delegated, verifies
freshness and the current body epoch, rejects revocation, and consumes a unique
nonce.

## Secret boundary

The raw bearer token and CSRF token are returned once to the host operator.
Only SHA-256 digests are persisted. Raw tokens must never enter Cortex memory,
evidence, trajectories, UI telemetry, or ordinary configuration.

The control session also binds the registered principal. Issuance requires an
explicit match against the registered principal secret. Renaming a caller or
supplying a different secret cannot open control.

## Authority split

An accepted action receipt may state `host_control_authorized=true` for its one
exact request. It simultaneously preserves:

```text
model_host_mutate_authorized = false
model_execution_authorized = false
memory_admission_authorized = false
competence_promotion_authorized = false
policy_effect = false
```

The model cannot read, hold, or spend the control session. The native operator
drawer now exposes only this authenticated path. Raw bearer and CSRF values
remain in browser memory and every mutation consumes a fresh one-shot action
receipt; there is no direct UI-to-worker or UI-to-Git shortcut.

## Durable lifecycle foundation

Campaign preparation now binds an exact canonical policy receipt row and Storm
summary receipt row to an immutable `prepared_request` state. These are
identity bindings only; the worker must still independently verify the policy
signature and complete Storm semantics before executing. Starting and
cancellation each require a new one-shot action bound to the exact prior state
receipt. The implemented host-intent chain is:

```text
prepared_request -> start_requested -> cancel_requested
```

Neither request state claims that execution began. Each row carries a monotonic
state sequence and previous-state hash. The
`cancel_requested` state explicitly requires cooperative stop; it does not
falsely claim the worker has already stopped.

## Worker observation boundary

The runtime now has separate immutable receipts for worker claims, heartbeats,
and cooperative cancellation acknowledgement.

A worker claim is admitted only after the worker independently reloads and
verifies:

- the exact canonical `start_requested` state;
- the signed autonomy policy with the registered principal secret;
- the complete canonical Storm plan/observation/summary relationship;
- the current repository source HEAD.

The claim is exactly once per campaign. A second worker cannot take over by
presenting the campaign ID. The receipt records a bounded lease but explicitly
keeps execution success and integration authority false.

Heartbeats form their own monotonic previous-hash chain. Each one records a
bounded stage and lease. Read-only observation derives `worker_claimed`,
`running`, `stale`, `cancelling`, or `cancellation_acknowledged` without writing
new state. A missing process or expired lease therefore becomes `stale`, never
`completed`.

Cancellation acknowledgement requires both the canonical cancel request and a
worker heartbeat that records cancellation observation. It still reports
`independent_process_exit_verified=false`: cooperative acknowledgement is not
yet an external proof that the process has exited.

## Real campaign checkpoints

The existing autonomous improvement loop now accepts a host-owned checkpoint
callback. It invokes that boundary before or between:

```text
policy verification
Storm resolution
candidate evaluation
isolated patch verification
counterfactual trial
tournament evaluation
active integration preparation
```

`CampaignRuntimeGuard` implements the canonical callback. At each boundary it
checks that the Git source HEAD still equals the worker claim, observes the
latest control state, and appends the next heartbeat. When cancellation is
pending, it records `cancellation_observed=true` and raises a bounded stop
signal before the next stage begins.

The callback's arbitrary payload is intentionally discarded. A model or
campaign stage cannot inject its own evidence through checkpoint details.

## Candidate-commit integration

The integration path now creates the winning proposal as a detached candidate
commit in an isolated Git worktree. Cortex pins that commit under a dedicated
`refs/cortex/candidates/` reference and persists its base, tree, targets,
preimages, postimages, policy, trial, tournament, terminal, and recovery anchor.
The active worktree remains untouched during preparation.

Applying the integration requires a second one-shot `campaign.integrate`
authorization. Cortex refuses a changed HEAD, dirty worktree, or substituted
candidate ref, then uses a fast-forward merge to preserve the exact candidate
identity. Postimage hashes and `git diff --check` are recomputed before the
result may say `verified_complete`. This verifies source integration, not
campaign utility or model competence.

Rollback is a third independent host action. Cortex reloads the canonical
integration and preparation, requires the active HEAD to equal the integrated
candidate and the worktree to be clean, then creates a normal Git revert
commit. It checks every recorded preimage and compares the complete restored
tree to the recovery anchor. A mismatch is recorded as
`manual_recovery_required`; it is never relabeled as success.

## Native operator interconnect

The loopback service now provides a narrow campaign plane:

```text
POST /v1/control/sessions
GET  /v1/campaigns
POST /v1/campaigns/{id}/prepare
POST /v1/campaigns/{id}/start
POST /v1/campaigns/{id}/cancel
POST /v1/campaigns/{id}/integrate
POST /v1/campaigns/{id}/rollback
```

Mutation calls require `Authorization: Bearer`,
`X-Cortex-Control-Session`, `X-Cortex-CSRF`, `X-Cortex-Action-Nonce`, and the
exact loopback `Origin`. The server reconstructs action material from canonical
receipts before authorizing it. Caller-provided candidate identities cannot
replace the prepared candidate.

## Replay and revocation

Each action consumes a caller-provided nonce exactly once within the control
session. Reusing the nonce is rejected. Revocation itself requires a canonical
one-shot `control.revoke` authorization and is recorded immutably; replaying
the same revocation returns the existing receipt instead of creating a second
canonical row.

## Current verification

Fast iteration uses the focused harness rather than the full repository suite:

```powershell
python scripts/ci/alpha10_runtime_smoke.py
```

The focused adversarial suite covers:

- wrong registered-principal secret;
- non-loopback origin;
- wrong bearer proof;
- wrong CSRF proof;
- exact-origin mismatch;
- undelegated action;
- nonce replay;
- expiry;
- body-epoch drift;
- immutable-receipt tampering;
- authenticated revocation and post-revocation denial;
- persistent closure of all model authority flags.
- exact request binding and lifecycle-action consumption;
- durable prepared/start/cancel request-state linkage.
- independent policy and Storm reverification at worker claim;
- exactly-once worker ownership;
- monotonic heartbeat linkage and read-only stale detection;
- cancellation-observation ordering and cooperative acknowledgement.
- real campaign-stage checkpoint wiring;
- source-HEAD drift blocking between stages;
- cancellation interruption between expensive operations.
- off-tree candidate identity and active-tree purity;
- fast-forward integration under a clean unchanged base;
- history-preserving rollback with full-tree verification;
- loopback API rejection without Origin, bearer, CSRF, and fresh nonce;
- native operator ledger visibility without model authority.

## Claim boundary and remaining work

Alpha.10 verifies an in-process campaign boundary, not an independently
supervised operating-system process. Terminal receipts therefore preserve
`os_process_exit_verified=false`. The release also does not establish that a
campaign improved Cortex, that a model is autonomous, or that rollback can
repair arbitrary conflicts after unrelated commits. A future process supervisor
may add externally observed process lifecycle evidence without weakening these
locks.
