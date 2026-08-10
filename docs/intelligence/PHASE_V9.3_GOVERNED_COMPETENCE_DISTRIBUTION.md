# Cortex v9.3 — Governed Competence Distribution Fabric

## Purpose

v9.3 projects a competence that already survived v9.1 distillation and v9.2
cross-model transfer into heterogeneous internal systems. The package is
target-bound, portable, revocable, and advisory. Cortex remains the durable
competence substrate; a consumer never becomes an authority over the canonical
ledger.

The governing law is:

```text
learn globally
apply locally
```

This phase does not add a model provider, autonomous execution, policy
mutation, or automatic competence promotion.

## Architecture

```text
                         CORTEX
              canonical competence + evidence
                              │
                     governed projection
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          System A        System B        System C
          profile A       profile B       profile C
          package A       package B       package C
```

The canonical path is:

```text
candidate → transfer trial → target profile → distribution gates
         → immutable package → local use receipt/feedback
         → independent evidence → future revision event
```

## Target profiles

`register_target_profile()` records an immutable compatibility profile. It
contains the target identity, environment, role and task family, model
capability, available tools, authority scope, epoch, privacy boundaries,
required/prohibited competence types, and freshness policy. A new profile
version is a new immutable row; old profiles remain inspectable.

The profile is evidence about compatibility, not a declaration that the target
is authorized to execute a package.

## Distribution gates

`project_competence()` resolves and verifies:

| Gate | Required evidence |
| --- | --- |
| Provenance | Canonical candidate receipt and full v9.1 lineage verify. |
| Transfer | A valid v9.2 trial for the same competence is classified `cross_model_verified` or `cross_family_verified`. |
| Active competence | The candidate is not contested, revoked, superseded, or otherwise terminal. |
| Target compatibility | Candidate type, role, task family, and required tools fit the profile. |
| Environment | Declared environmental assumptions are present and equal. |
| Authority scope | The target publishes an explicit scope; the package grants none. |
| Freshness | Candidate age is within the profile TTL. |
| Event state | No challenge, quarantine, revocation, supersession, or rollback blocks the projection. |

The gate algebra is noncompensatory:

```text
FAIL < UNKNOWN < PASS

active guidance ⇔ every required gate is PASS
```

Missing compatibility is `UNKNOWN`, not an implicit match. A blocked projection
returns a diagnostic report and writes no package.

## Package contract

Each immutable package contains:

- target/profile identity and profile hash;
- competence identity and receipt hash;
- transfer-trial provenance roots;
- applicability and compatibility proofs;
- exclusions, failure conditions, and counterevidence;
- freshness and event-derived revocation state;
- previous package identity for rollback;
- package identity/hash and distribution receipt metadata.

Packages carry `distribution_authorized=false`,
`host_mutate_authorized=false`, `execution_authorized=false`, and
`advisory_only=true`. A package is a portable projection, never blanket
authority.

## Revocation, quarantine, supersession, and rollback

Package rows are immutable. Lifecycle changes are append-only events:

- `challenge` and `quarantine` stop active guidance while evidence is reviewed;
- `revoke` blocks future use and remains visible to already distributed targets;
- `supersede` points to a replacement package without erasing history;
- `rollback` marks the newer package inactive and restores its previous valid
  package as the current projection.

`verify_distribution_package()` derives current state from the package plus
its event ledger. No event rewrites candidate provenance or changes the
canonical competence state.

## Feedback

`submit_distribution_feedback()` appends target context, result, outcome,
counterevidence, and applicability failures. Feedback is scoped to one target
and package. If a v9.0 circulation session is supplied, Cortex independently
verifies that canonical circulation and records the witness result hash;
otherwise feedback remains explicitly unverified.

Feedback cannot self-promote, rewrite a package, mutate a competence, or
invalidate every other target. A local exception, target-class exception, and
global contradiction remain distinct evidence categories for a later governed
revision.

## Portability and provider independence

The package contains no provider-native response object and no hidden reasoning.
It remains interpretable when the originating model, consuming model, or
provider is replaced, provided the target profile still satisfies the declared
requirements. Model identity remains provenance, not semantic authority.

## Verification surface

The Store exposes:

```python
store.register_target_profile(repo, profile)
store.project_competence(repo, competence_id=..., profile_id=...)
store.verify_distribution_package(repo, package_id)
store.append_distribution_event(repo, package_id=..., event_type="revoke", reason=...)
store.submit_distribution_feedback(repo, package_id=..., kind="use", ...)
```

The underlying ledgers are SQLite-backed, transactionally appended, and
protected against update/delete. Distribution reads are observational unless a
caller explicitly invokes a package/event/feedback write operation.

## Tests and claim boundary

The v9.3 tests cover heterogeneous target packages, incompatibility blocking,
revocation, rollback, stale detection, feedback isolation, origin-model
detachment, and authority flags. The phase demonstrates a governed distribution
mechanism; it does not demonstrate universal competence, task improvement,
consciousness, autonomous agency, or safe execution.

```text
host_mutate_authorized = false
execution_authorized   = false
automatic_broadcast    = false
```

## Remaining evidence

Before a competence is distributed broadly, Cortex still needs repeated,
independently evaluated target feedback across the declared target class and a
policy decision for what constitutes a global contradiction. v9.3 records that
evidence but does not silently promote it.

## Next phase

The next bounded evolution can study governed feedback aggregation and
target-class revision. Any future promotion must preserve the same law:

```text
evidence → verification → scoped revision → explicit distribution
```
