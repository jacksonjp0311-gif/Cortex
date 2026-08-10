# Cortex v9.4 — Empirical Transfer Seal & Package-Use Binding

## Purpose

v9.4 closes two evidence boundaries left open by the v9.0–v9.3 mechanism:

1. a synthetic model fixture can prove that the transfer machinery works, but
   cannot prove empirical model transfer; and
2. a valid model circulation proves only that a circulation occurred, not that
   it consumed a particular target-bound competence package.

The release law is:

```text
synthetic mechanism evidence != empirical transfer evidence
valid circulation != valid package use
exact package exposure != counterfactual causal effect
```

## Evidence classes

New invocation and transfer evidence carries one canonical class:

| Class | Meaning | Empirical promotion |
|---|---|---|
| `synthetic` | Deterministic fixture lineage | Never |
| `simulated` | Host-registered simulator/test boundary | Never |
| `live_empirical` | Host-registered external or local live-inference boundary | Eligible, subject to all other gates |
| `empirically_attested` | Reserved for a stronger provider-attested boundary | Not currently issued |
| `unknown` | No trusted adapter registration resolves | Never |
| `legacy_partial` | Historical receipt predating evidence classification | Never without revalidation |

Evidence class is resolved by Cortex. Provider-family strings, model IDs,
adapter result fields, caller configuration, and an adapter's own `empirical`
claim cannot upgrade it.

`FixtureAdapter` places a non-serializable marker in its class body. Cortex
checks the complete class MRO before consulting the registration ledger, so a
renamed or subclassed fixture remains synthetic.

## Adapter provenance

The immutable adapter registration binds:

- repository identity;
- exact adapter implementation digest;
- sanitized non-secret runtime profile;
- registered provider/model/adapter identity;
- one execution-boundary class;
- host-principal authentication at registration time;
- a sanitized endpoint/profile digest; and
- the explicit absence of provider attestation.

Registration is exact: a subclass, changed model identity, or changed
non-secret configuration does not inherit another adapter's classification.
Credentials, bearer tokens, private keys, authenticated URLs, and secret query
parameters are excluded from the registration material. Credential-shaped
model request configuration is rejected before invocation.

The registration proves that the host classified and invoked a specific
adapter boundary. It is not cryptographic proof from a provider. Cortex reports
`provider_attestation = not_available` and does not issue the stronger
`empirically_attested` class.

## Structural and empirical transfer

v9.2 trial verification now independently reloads every A–E circulation and
reconstructs:

- canonical model and adapter provenance;
- task and context bindings;
- receipt roots and witness results;
- arm metrics and utility;
- matched-control gains; and
- the resulting transfer classification.

The resulting states distinguish:

```text
structural_cross_model_pass
structural_cross_family_pass
empirical_cross_model_verified
empirical_cross_family_verified
unresolved
incompatible
```

A persisted fixture-only trial can reach a structural pass. It cannot reach an
empirical state. An advisory (`persist=False`) trial cannot reach an empirical
state. The exact trial `receipt_hash`, not only its trial ID, is bound into a
distribution package.

## Distribution policy

Target profiles declare one of two modes:

- `production` requires at least `live_empirical` evidence; and
- `sandbox` may explicitly accept synthetic structural evidence.

Production is the default. A production profile cannot lower its minimum below
live empirical evidence. There is no implicit fallback.

A sandbox package produced from fixture or simulator evidence is marked:

```text
sandbox_only = true
synthetic_evidence = true
non_promotable = true
empirical_feedback_eligible = false
```

Target/type/tool, environment, epoch, authority-scope, active-profile, and
freshness checks remain separate noncompensatory diagnostics. A newly
registered target profile makes a package bound to an older profile stale for
active use. Historical package evidence remains immutable and inspectable.

## Exact package-use path

A package cannot be attached to a model session after the response is known.
The core circulation path must receive a canonical package ID before invoking
the adapter:

```text
immutable package
  -> profile + competence resolution
  -> bounded package projection
  -> model request context
  -> adapter invocation
  -> immutable competence_package_use receipt
  -> outcome + witness + trajectory
```

The package projection contains only provider-neutral public competence
semantics, counterevidence, exclusions, target compatibility information, and
canonical identity roots. It carries no execution authority.

The optional `competence_package_use` receipt lives in the existing append-only
symbiotic circulation ledger. It binds:

- package ID/hash;
- competence ID/receipt hash;
- profile ID/hash and target ID;
- target environment and epoch;
- exact package-projection hash;
- session, turn, invocation, request, and context hashes;
- task contract and tool scopes;
- adapter provenance and evidence class;
- same-turn outcome and witness content hashes;
- witness-result hash; and
- sandbox/non-promotable policy flags.

The trajectory binds the package-use content hash. Ordinary and historical
v9.0 circulations remain valid without this optional receipt, but they cannot
verify competence-package feedback.

## Feedback verification

Verified feedback resolves this complete path:

```text
feedback
  -> exact package-use ledger receipt
  -> immutable package
  -> target profile
  -> canonical competence
  -> same-turn model invocation
  -> canonical outcome
  -> independent witness result
  -> trajectory
```

A session ID is retained only as a non-authorizing legacy reference. A valid
unrelated session cannot substitute for the package-use receipt.

Feedback states are:

- `unverified` — no package-use root;
- `synthetic_verified` — exact synthetic/simulated package exposure is bound;
- `empirically_verified` — exact live empirical exposure is bound under an
  empirical-eligible production package;
- `binding_failed` — an identity/content/path mismatch exists; and
- `unknown` — a required currentness or evidence surface cannot be resolved.

`local_exception`, `target_class_exception`, and `global_contradiction` remain
claims about scope. v9.4 does not promote any of them into a global fact.
Synthetic feedback is retained, but it is not eligible for empirical
aggregation. No feedback directly rewrites competence.

## Freshness

New target profiles carry explicit limits for competence age, transfer-evidence
age, profile age, package age, and future feedback age. Missing modern policy
surfaces resolve as unknown rather than inheriting an unstated expiration law.

## Legacy behavior

Immutable v9.0–v9.3 receipts are not rewritten.

- Historical model circulations preserve their original request hash and are
  structurally inspectable with `legacy_partial` empirical status.
- Historical transfer trials without evidence class are never production
  empirical proof.
- Historical target profiles/packages without a modern evidence policy resolve
  unknown for new production distribution.
- Historical feedback without a package-use root remains unverified even if its
  stored payload once described itself as passed.

## Authority boundary

Every invocation, transfer trial, package, use receipt, and feedback receipt
preserves:

```text
host_mutate_authorized = false
execution_authorized = false
memory_admission_authorized = false
policy_effect = false
```

Model output cannot witness itself, mark itself successful, admit itself to
memory, distribute competence, or upgrade its evidence class. Hidden reasoning
and provider-native response bodies are not persisted.

## Verification

Focused adversarial coverage includes:

- renamed fixture subclasses remaining synthetic;
- unregistered adapters remaining unknown;
- exact implementation/config registration binding;
- secret sanitization and principal-secret rotation;
- fixture A–E gains remaining structural;
- forged empirical trial status failing independent reconstruction;
- production rejection and explicit sandbox acceptance;
- exact same-turn package-use verification;
- unrelated circulation rejection;
- cross-target use-receipt replay rejection;
- changed target profile/currentness blocking;
- synthetic global-contradiction feedback remaining non-aggregating; and
- all authority flags remaining false.

## Empirical status of this release

No external model credentials or live inference service were available or used
for the release suite. No secrets were committed. The release result is:

```text
EMPIRICAL_TRIAL_NOT_EXECUTED
```

The architecture can now preserve live empirical evidence when a host registers
and invokes a real adapter. The repository test suite proves the boundary and
failure behavior; it does not claim real-world cross-model improvement.

## Claim boundary

v9.4 establishes typed evidence provenance and exact package-exposure binding.
It does not establish universal competence, counterfactual causal benefit,
provider attestation, cognition, consciousness, autonomous agency, or authority.

## Next phase

The next bounded phase is v9.5 — Distributed Evidence Assimilation & Scoped
Competence Revision. It must aggregate independently bound feedback without
allowing popularity, volume, or one target to manufacture global truth. v9.5 is
not implemented here.
