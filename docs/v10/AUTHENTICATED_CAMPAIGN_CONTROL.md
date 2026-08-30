# Authenticated Campaign Control

Status: **alpha.10 foundation in development**

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

The model cannot read, hold, or spend the control session. The UI does not yet
expose a mutation endpoint. That exposure remains closed until durable campaign
lifecycle execution, cooperative cancellation acknowledgement, and integration
recovery are implemented and verified.

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

## Remaining alpha.10 work

Before alpha.10 can be sealed, Cortex still needs to wire these receipts into
the campaign loop at every expensive boundary, add an external process-exit
observation, implement commit-level integration/recovery receipts, and expose a
UI/API surface that can invoke only these authenticated operations. Until those
gates close, alpha.9 remains the product version.
