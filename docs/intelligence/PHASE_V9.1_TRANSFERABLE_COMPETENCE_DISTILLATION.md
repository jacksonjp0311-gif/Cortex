# Cortex v9.1 — Transferable Competence Distillation

## Purpose

v9.1 introduces a canonical competence-candidate surface alongside (not in
place of) admitted memory. Memory preserves a historical lesson. Competence is
an operational abstraction that may later be tested in another context.

The implemented path is:

```text
verified model trajectory
  → competence abstraction
  → preserved applicability/failure/counterevidence
  → append-only competence candidate
  → independent re-verification
```

No candidate is created from fluent text alone. The derivation reloads the
canonical v9.0 invocation, proposal, evaluation, outcome, witness, and
trajectory receipts and requires `verify_model_circulation()` to pass.

## Canonical representation

`cortex.competence` stores the smallest useful portable unit in the
`competence_candidates` ledger. Its body includes:

- capability and intended outcome;
- prerequisites, applicability conditions, environmental assumptions, and
  required tools;
- failure conditions, counterevidence, and uncertainty;
- canonical trajectory, outcome, and witness hashes;
- lifecycle and portability state;
- model-origin provenance, kept separate from semantic identity.

The semantic identity hash is computed from structured capability/outcome and
operational conditions. Public descriptions, rationales, and model identity are
not identity material. Thus a wording change or a replacement origin model does
not create a different semantic competence when the declared structure is the
same. Supporting evidence is still retained separately and is never silently
replaced by the abstraction.

## Lifecycle and portability

Candidates use explicit states: `candidate`, `origin_verified`,
`transfer_pending`, `transfer_verified`, `contested`, `superseded`, and
`revoked`. v9.1 can produce an origin-verified, model-independent candidate,
but it does not fabricate a second-context transfer proof. `transfer_verified`
therefore remains closed until a later phase supplies independent transfer
evidence. A `model_specific_preference` is retained as a blocked, non-universal
candidate rather than promoted as general competence.

Verified failures are valid negative evidence. A failed outcome cannot be
represented as `successful_procedure`; it may be represented as a
`failed_hypothesis` or `counterevidence` candidate, with the failure preserved.
An empty counterevidence set prevents a candidate from being marked a portable
candidate.

## Verification and read purity

`verify_competence_candidate()` recomputes the candidate receipt hash and
semantic identity, verifies the lineage hash, reloads the originating model
trajectory, and checks every authority flag. It does not load or invoke the
originating model. `competence_is_applicable()` is read-only: stale or
incompatible conditions are reported as inapplicable and never append an
`epoch_stale` or other state transition merely because the candidate was read.

The competence ledger is append-only with immutable rows and duplicate
semantic-identity handling. A candidate cannot authorize distribution,
execution, host mutation, policy mutation, learning, or memory admission:

```text
distribution_authorized = false
execution_authorized    = false
host_mutate_authorized  = false
memory_admission_authorized = false
```

## Claim boundary

v9.1 demonstrates canonical distillation from verified model experience. It does
not establish universal transfer, task competence, cognition, consciousness,
agency, or authority. “Model-independent” means the canonical verifier no
longer needs the originating model; it does not mean the abstraction has passed
a new-world transfer test. That evidence belongs to v9.2.

## APIs

```python
from cortex.competence import (
    derive_competence_candidate,
    verify_competence_candidate,
    competence_is_applicable,
)

candidate = derive_competence_candidate(
    store, repo,
    session_id=session_id,
    turn_id=1,
    capability={"id": "cap.example", "description": "public wording"},
    intended_outcome={"id": "out.example"},
    counterevidence=[{"kind": "known_limit", "text": "fixture boundary"}],
)
report = verify_competence_candidate(store, repo, candidate["competence_id"])
projection = competence_is_applicable(candidate, {"body_epoch_id": epoch_id})
```

The caller supplies an abstraction to evaluate; it does not supply the truth
of the trajectory. Missing or invalid canonical origin evidence raises a
closed admission error, and a caller-provided success/authority field cannot
open the boundary.

## Tests

`tests/test_v91_competence.py` covers unsupported advice, model replacement,
prose changes, negative outcomes, counterevidence conservation, stale/read-only
applicability, model-specific preferences, immutable persistence, and authority
flags. The existing v9.0 circulation tests remain the independent origin proof.

## Remaining evidence / next phase

v9.1 deliberately stops before universal transfer. v9.2 must execute an
independent second-context or second-model transfer evaluation and bind its
outcome and witness to the same semantic competence. Until then,
`transfer_pending`/`portable_candidate` is an evidence status, not a claim that
the competence works everywhere.
