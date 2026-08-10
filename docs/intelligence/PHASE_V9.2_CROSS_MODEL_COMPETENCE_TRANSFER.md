# Cortex v9.2 — Cross-Model Competence Transfer

## Purpose

v9.2 makes model independence experimentally measurable. A competence candidate
`K` is loaded from the immutable v9.1 ledger, the originating model is detached,
and fresh adapter instances are evaluated under a frozen task contract.

The experiment is:

```text
A1 verified trajectory → K
A1 detached
fresh A2 instances → matched arms A, B, C, D, E
                         ↓
              independent evaluation + witness
                         ↓
                immutable transfer receipt
```

The trial measures transfer; it does not turn a positive score into automatic
distribution or authority.

## Matched arms

`run_cross_model_transfer_trial()` requires a factory that creates one fresh
adapter instance per arm:

| Arm | Context |
| --- | --- |
| A | ordinary repository/task context only |
| B | public raw originating interaction/history |
| C | unfiltered admitted-memory context |
| D | distilled competence `K` (without model-origin provenance) |
| E | `K` plus prior canonically verified transfer-trial feedback |

No model is called to create `K` during the transfer run. Arm A/B/C contexts do
not contain the competence projection. Arm D/E preserve failure conditions and
counterevidence in the projected candidate.

## Frozen trial contract

Before any arm invokes a model, the receipt freezes:

- the public `TaskEvaluationContract` and its hash;
- task text, tools, token/latency budgets, and model configuration;
- repository identity and manifest snapshot;
- the origin epoch used to produce `K`, the live epoch observed at setup, and
  optional measurement cohort;
- competence receipt and semantic identity;
- all required arms and the declared transfer policy;
- fresh adapter identities.

The origin epoch is the trial epoch. If canonical receipts advance the live
epoch while the trial is prepared, that drift is recorded rather than silently
relabeling the candidate. Applicability conditions are checked before the trial;
stale or incompatible `K` raises a closed `TransferTrialError` and does not
write a state transition.

## Metrics and gains

Each arm records externally observable task success and, where applicable:

- repeated-error rate;
- unsupported claims and prohibited-action attempts;
- stale-competence use and applicability violations;
- abstention quality and correction rate;
- token/context cost and latency;
- counterevidence retention.

The declared policy supplies utility weights. The receipt reports:

```text
G_continuity  = U_D - U_A
G_distillation = U_D - U_B
G_governance  = U_D - U_C
G_credit      = U_E - U_D
```

Utilities are diagnostic experiment quantities, not truth or authority. A
failed arm is retained; missing arms prevent a verified portability result.

## Portability states

The classification is explicit and policy-bound:

`model_specific`, `capability_class_specific`, `cross_model_verified`,
`cross_family_verified`, `unresolved`, and `incompatible`.

The default policy is stored inside the trial receipt and can be replaced by a
declared configuration. It is not part of competence ontology and is not
silently hard-coded into the candidate. A weak fresh model or missing
prerequisite yields `incompatible`; it does not disprove the competence. A
positive arm difference that fails the declared gain, cost, repetition, or
portability target remains `unresolved`.

## Canonical evidence and isolation

Every persisted arm uses the v9.0 model-circulation path, including canonical
invocation, independent task evaluation, outcome, commit-before-reveal witness,
and trajectory receipts. The transfer receipt binds each arm to those witness
results and to the frozen task hash.

Arm E feedback may identify only an existing immutable transfer receipt whose
hash and arm surfaces verify. Caller-supplied success or feedback values cannot
open a trial gate.

`verify_transfer_trial()` recomputes the trial receipt hash and checks that every
required arm exists and that authority flags remain false. The transfer ledger
is append-only. Replaying a trial identity is deterministic; changing the
frozen contract, model identity, policy, or nonce creates a new trial identity.

## Authority boundary

Trials are advisory evidence only:

```text
distribution_authorized = false
execution_authorized    = false
host_mutate_authorized  = false
memory_admission_authorized = false
promotion_eligible      = false
```

No competence state is updated from a trial. No adapter can witness or promote
its own output, and no hidden chain-of-thought is requested or persisted.

## API

```python
from cortex.competence_transfer import (
    run_cross_model_transfer_trial,
    verify_transfer_trial,
)

trial = run_cross_model_transfer_trial(
    store,
    repo,
    competence_id=competence_id,
    task_contract=frozen_contract,
    adapter_factory=lambda arm: make_fresh_adapter(arm),
    task="apply the declared procedure",
    policy={"min_success_gain": 0.1, "min_repetitions": 2},
)
report = verify_transfer_trial(store, repo, trial["trial_id"])
```

The adapter factory is invoked once per arm. Reusing one object across arms or
using the originating model identity is incompatible with a fresh-model trial.

## Claim boundary and next phase

v9.2 can establish only that a declared competence performed better, worse, or
incompatibly under a particular frozen trial policy. It does not establish
universal transfer, model competence in general, cognition, consciousness, or
authority. No positive receipt distributes `K` automatically.

Additional models, capability classes, repetitions, and independent outcome
cohorts are required before a stronger portability claim. Policy-governed
distribution remains a later phase.
