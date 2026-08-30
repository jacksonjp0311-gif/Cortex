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

## Replay and revocation

Each action consumes a caller-provided nonce exactly once within the control
session. Reusing the nonce is rejected. Revocation itself requires a canonical
one-shot `control.revoke` authorization and is recorded immutably; replaying
the same revocation returns the existing receipt instead of creating a second
canonical row.

## Current verification

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

## Remaining alpha.10 work

Before alpha.10 can be sealed, Cortex still needs to wire the durable lifecycle
into campaign workers, record cooperative stop acknowledgement, add commit-level
integration/recovery receipts, and expose a UI/API surface that can invoke only
these authenticated operations. Until those gates close, alpha.9 remains the
product version.
