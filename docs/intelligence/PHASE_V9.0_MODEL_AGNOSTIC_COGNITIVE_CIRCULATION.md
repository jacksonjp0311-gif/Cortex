# Cortex v9.0 — Model-Agnostic Cognitive Circulation

## Purpose

v9.0 closes the first executable model loop in Cortex while keeping the model
replaceable and temporary. The durable path is:

```text
verified Cortex context
  → model invocation
  → public structured proposal
  → independent task evaluation
  → externally observed outcome
  → independent task witness
  → bound trajectory
```

The implementation is in `cortex/model_circulation.py`, with the typed task
contract in `cortex/evaluation.py` and a convenience entry point from
`cortex.symbiosis.run_model_circulation`.

## Model boundary

Core Cortex depends only on the `ModelAdapter` protocol. An adapter declares:

- provider family;
- model identifier and declared version;
- adapter identifier and implementation version; and
- `invoke(ModelInvocationRequest)` returning a mapping of public fields.

`FixtureAdapter` is the deterministic test adapter. Provider SDKs are not
dependencies of Cortex core. Replacing `fixture-a` with `fixture-b` changes the
invocation provenance and request hash, not the Cortex contract.

## Canonical request and response

Every request binds repository identity, session, turn, body epoch, invocation
ID, task-contract hash, projected-context hash, tool scopes, configuration,
model identity, and request time. The response records a response hash,
public output, structured proposal, declared uncertainty, public citations,
declarative tool intents, rationale supplied for public inspection, and token
or cost metadata when available.

Provider-native fields are not part of the canonical schema. Unknown fields,
including hidden reasoning or provider response objects, are discarded at the
adapter boundary. Cortex never requests or persists private chain-of-thought.

## Independent evaluation

`TaskEvaluationContract` is serializable and contains no executable callback.
It is selected before invocation and hashed into the request. The current
contract supports deterministic `text_contains`, `field_equals`, and
`field_contains` criteria. `evaluate_task_result()` reads only the declared
contract and the externally observed result field. It ignores `success`,
`verified`, `witnessed`, and score-shaped claims supplied by a model.

An observed failure is valid evidence of failure; it is not a successful
procedure. Missing required observation remains `unknown`.

## Witness and trajectory

The task witness commitment is stored before adapter invocation. After an
observed result, Cortex stores an immutable generic task witness result in the
existing `witness_results` ledger. Its identity, commitment root, chronology,
contract, outcome, session, and epoch are independently checked by
`verify_task_witness_result()`. The existing retrieval witness verifier and
suite remain unchanged.

The six model receipts are appended to the existing append-only symbiotic
ledger:

```text
model_invocation
model_proposal
model_evaluation
model_outcome
model_witness
model_trajectory
```

`verify_model_circulation()` reloads those rows, recomputes content hashes,
re-evaluates the observation, validates the witness, checks every cross-step
binding, and verifies the symbiotic chain.

## Authority boundary

Model invocation grants no authority. Every v9.0 receipt carries:

```text
host_mutate_authorized      = false
execution_authorized        = false
memory_admission_authorized = false
policy_mutation_authorized  = false
policy_effect                = false
update_authorized            = false
```

The circulation function does not call memory admission, execute tools, write
host source, alter routing, or change constitutional bits. `tool_call_intents`
are declarative proposals only.

## Example

```python
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation

contract = TaskEvaluationContract(
    contract_id="docs-check-v1",
    task_type="text_contains",
    target_field="text",
    expected_value="fixture observation",
)

receipt = run_model_circulation(
    store,
    "YourProject",
    session,
    adapter=FixtureAdapter(model_id="fixture-a"),
    task_contract=contract,
    observed_result={"text": "fixture observation"},
)
```

The returned object is advisory and includes canonical receipt bodies,
independent evaluation, witness persistence status, and explicit authority
flags. Use `verify_model_circulation()` before treating the loop as valid.

## Failure modes

- malformed adapter output raises `ModelAdapterError` and cannot produce a
  proposal or outcome;
- a response bound to a different request is rejected;
- context projection tampering fails request verification;
- provider-specific and hidden-reasoning fields are not persisted;
- caller-supplied success or witness booleans do not open any gate;
- missing observation is unknown and cannot become a successful result;
- a witness result for another outcome, session, epoch, or task contract fails
  binding verification;
- canonical ledger or witness persistence errors are reported rather than
  converted into authority.

## Claim boundary

v9.0 proves only that a replaceable adapter can circulate a bounded public
proposal through an independently declared task evaluator and canonical
evidence ledgers. It does not establish model competence, reasoning quality,
task utility beyond the declared contract, cognition, consciousness, agency,
or authority.

## Remaining evidence

The fixture adapter demonstrates contract closure. Real provider adapters still
require their own security, privacy, cost, and outcome validation. No provider
SDK is bundled, and no model may self-authorize memory, execution, or policy.

The next research step may evaluate model-coupled task cohorts, but competence
distribution is intentionally outside v9.0.
