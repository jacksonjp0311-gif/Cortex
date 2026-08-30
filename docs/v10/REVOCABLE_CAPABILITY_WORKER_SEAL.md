# Revocable Capability Closure & External Worker Seal

Status: **sealed in Cortex 10.0.0-alpha.11**

Alpha.11 closes two gaps in the authenticated campaign runtime: a one-shot
action could previously remain spendable after its parent session ceased to be
current, and an in-process return could not prove that an independently
observed worker process had exited.

## Capability lifetime law

An action is not a durable expansion of authority. At the instant of spend,
Cortex requires:

```text
ValidAction =
    canonical action receipt
  ∧ exact action and request hash
  ∧ canonical parent control session
  ∧ current parent epoch
  ∧ unexpired spend window
  ∧ no parent revocation
  ∧ unspent action identity
```

The database enforces uniqueness for both `(control session, nonce)` and the
canonical action receipt consumed by a downstream operation. Application checks
remain diagnostic; the immutable ledger constraint is the concurrency boundary.

## Campaign lifecycle law

`campaign_state()` no longer selects the largest sequence number as truth. It
reconstructs the complete lifecycle and verifies:

- genesis at `prepared_request`;
- sequence values beginning at zero and increasing by one;
- exact previous-receipt links;
- legal prepare/start/cancel transitions;
- invariant campaign, policy, and Storm identities;
- exact action/request binding for every transition;
- action authorization before consumption and before expiry or revocation;
- current epoch compatibility.

An individually hash-valid row with illegal lifecycle semantics holds the
entire active campaign state closed.

## External worker seal

The host can launch the fixed `cortex.campaign_worker_process` entry point with
`shell=False`. The worker reconstructs its Storm input from canonical receipts
and receives the policy secret only through a private stdin pipe. Secrets and
raw output are not persisted.

The supervisor records two immutable observations:

```text
campaign_worker_process_launch
  -> campaign_worker_process_exit
       -> canonical campaign_worker_terminal
```

The exit receipt binds the claim, launch, command hash, PID, exit code,
duration, timeout/termination path, output hashes, and canonical terminal. It
can establish `os_process_exit_verified=true`. It deliberately keeps:

```text
campaign_success = false
integration_authorized = false
model_host_mutate_authorized = false
model_execution_authorized = false
```

An observed exit is not evidence that a patch was useful. Candidate utility
still requires the isolated verification and counterfactual trial path;
integration still requires its separate authenticated host action.

## Remaining boundary

This phase seals process observation and capability lifetime. It does not prove
that autonomous campaigns generally improve Cortex, that arbitrary untrusted
verification commands are safe on the host, or that semantic claims produced
by agents are true. Stronger unattended campaigns should execute evaluators in
an OS/container sandbox and remain subject to empirical counterfactual review.
