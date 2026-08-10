# Cortex v8.9.3 — Canonical Evidence & Witness Closure

## Purpose

v8.9.3 closes the evidence side of Cortex's v8.9.2 provenance boundary. A
reference to a receipt is only an address. A row existing in SQLite is only an
object. A gate may pass only after Cortex resolves the canonical object,
recomputes its identity, checks its content and bindings, and verifies the
semantic property required by that gate.

The release is metrology and admission integrity. It does not add a model,
autonomous invocation, host mutation, execution authority, learning, or a
claim about consciousness or subjective sensing.

## Prior wound

Before this phase, several paths could turn a hash-shaped reference plus a
caller Boolean into evidence. A witness commitment proved that an evaluation
had been sealed before reveal, not that it passed. Outcome mappings could carry
their own `verified=True` bit. Cohort compatibility was partly asserted, and
principal-secret verification was implicit in issuance history.

Those paths are now references only. The canonical object is the source of the
fact.

## Canonical locks

The following distinctions remain hard boundaries:

- memory ≠ evidence;
- observation ≠ truth;
- coherence ≠ authority;
- utility ≠ truth;
- continuity ≠ legitimacy;
- receipt existence ≠ receipt validity;
- historical authorization ≠ current authority;
- unknown ≠ pass.

Every gate proof and admitted-memory receipt also preserves
`host_mutate_authorized = false` and `execution_authorized = false`.

## Provenance chain

The model-facing path is resolved, not narrated:

```text
memory
  → membrane receipt
  → canonical candidate batch
  → candidate body
  → transition
  → prior/next frames
  → outcome and witness result (when required)
  → authenticated will
```

`verify_candidate_provenance()` reports typed planes for candidate, batch,
trajectory, cohort/schema, outcome, and witness. It distinguishes `pass`,
`fail`, `unknown`, and `legacy_partial`. Candidate types carry an explicit
requirement matrix: outcome-linked lessons require outcome-bound witness
evidence; structural warnings can declare outcome not applicable and witness
optional. Not applicable is documented, not silently treated as proof.

Provenance accounting reports pass, fail, unknown, legacy-partial,
noncanonical, and invented-or-unresolved counts. A naked or unresolved
candidate cannot be durably admitted.

## Gate derivation

`derive_gate_state()` returns a typed `GateProofReceipt`-shaped diagnostic with
the following planes:

- **Γ constitutional:** canonical activation-conformance receipt, chain,
  status, invariants, epoch/cohort/schema bindings, and policy boundary;
- **Ξ epoch/cohort:** current epoch plus a canonical conformance receipt in the
  requested measurement cohort;
- **W witness:** immutable `witness_results` row, commitment chronology,
  result hash, evaluator/controller, bindings, and the required success
  criterion;
- **O outcome:** canonical `task_outcomes` row, closed status, accepted
  verification type, activation/transition bindings, and repository identity;
- **S stability:** current self-sensing, binding, and resonant-frame telemetry
  with verified hashes and an explicitly stable operational classification;
- **A authority:** current will receipt, canonical receipt hash, signature,
  time window, principal identity, and explicit principal-secret match.

The gate algebra is tri-state. With `F < U < P`, the durable boundary is:

```text
Θ_t = min { Γ_t, Ξ_t, W_t, O_t, S_t, A_t }
Durable(M) only when Θ_t = P
```

Scores, utility, coherence, or a caller-supplied `True` cannot compensate for a
failed or unknown plane.

## Witness commitment versus witness result

`witness_commitments` is a pre-reveal commitment ledger. It establishes
chronology and binds the case manifest, evaluator, controller, repository
snapshot, and Cortex version.

`witness_results` is a separate immutable ledger. `run_witness()` recomputes
the revealed result, persists it exactly once, and returns its canonical hash.
`verify_witness_result()` then checks commitment existence, chronology, reveal
identity, result hash, case coverage, evaluator/controller binding, and any
declared outcome, activation, epoch, session, or transition binding. A
commitment without a result is never a passing W gate.

## Outcome verification

An outcome ID identifies a row; it does not verify the row. Cortex resolves the
canonical `task_outcomes` row and derives closure and verification from its
stored status, verification type, payload, repository, activation, session,
reward, and transition binding. A verified failure can pass the O evidence gate
while remaining a failure; it cannot be relabeled as a successful procedure.

## Cohort verification

Cohort compatibility is an equality check over the canonical
`measurement_cohort_id`, `coordinate_schema_digest`, and body epoch surfaces.
Missing values are unknown; unequal values fail. No receipt from another
cohort or schema is combined merely because a mode label appears in a list.

## Principal authentication

Will verification now explicitly computes:

```text
sha256(secret_supplied) == registered_principal.secret_hash
```

`principal_secret_match`, signature validity, canonical receipt validity, time
window, scope, and body bindings must all pass for current authority. Historical
fields in an admitted memory describe what was authorized at admission; they
do not grant present memory-write, execution, or host-mutation capability.

## Read/write separation

Observational operations—will status, provenance verification, eligibility,
projection with `persist=False`, and interconnect inspection—do not append
memory-state transitions. A projection receipt is written only when the caller
explicitly requests `persist=True`. Canonical admission, witness-result
persistence, outcome recording, and explicit state transitions remain separate
write paths; none is an authority-bearing host mutation.

## Deep memory verification

Deep verification recomputes immutable receipt identity and resolves the
membrane, candidate batch, transition, frames, current epoch, cohort/schema,
will, outcome, and witness surfaces required by the candidate type. Shallow or
legacy lineage is inspectable for history but remains closed to model-facing
guidance until revalidated.

The release law is:

```text
Durable(M)=1
    ⇒
VerifyLineage(M)=1
∧ VerifyWill(W)=1
∧ Γ=1
∧ Ξ=1
∧ W=1
∧ O=1
∧ S=1
```

Here `W_receipt` means the authenticated principal will receipt, while
`W_gate` means the independent witness gate. The symbols are intentionally
separated in implementation diagnostics so a will cannot masquerade as a
witness result.

## Failure modes

- Fake 64-character constitutional or stability references remain unknown.
- A commitment without an immutable result remains unknown.
- A tampered result, stale reveal chronology, wrong outcome, or wrong
  repository/epoch/session binding fails verification.
- Missing or mismatched cohort/schema data remains unknown or fails.
- Caller `True` values can close a gate when explicitly constrained, but cannot
  open a gate.
- Canonical append failure is reported as failure; mutable latest settings do
  not make it appear committed.
- All paths preserve `host_mutate_authorized=false` and
  `execution_authorized=false`.

## Tests

Focused adversarial coverage lives in:

- `tests/test_v893_gate_proofs.py`;
- `tests/test_v892_provenance.py`;
- `tests/test_independent_witness.py`;
- witness, will/membrane, admitted-memory, and interconnect suites.

The v8.9.3 checks include fake gate receipts, commitment/result separation,
tampered and chronologically invalid results, outcome body mismatch, cohort
unknown propagation, principal-secret mismatch, naked candidate accounting,
and caller-Boolean non-promotion.

## Claim boundary

v8.9.3 establishes canonical evidence resolution and witness closure. It does
not establish improved task performance, reasoning quality, cognition,
consciousness, agency, authority, or autonomous model competence. No telemetry
or gate proof changes retrieval ranking, routing, cadence, training,
plasticity, promotion, host source, or execution policy.

## Remaining evidence

Legacy receipts that lack modern identity or evidence fields remain
`legacy_partial` until revalidated. Outcome-bound candidate types still need
independently verified outcomes and witness results for each production
trajectory. A verified failure is useful counterevidence, not a success claim.

## Next phase

Only after this evidence substrate is mechanically closed should Cortex consider
v9.0 — **Model-Coupled Cognitive Circulation**. That future phase may connect a
replaceable model to verified context and independently evaluated outcomes; it
is intentionally not implemented here.

