# Cortex v9.6 — Empirical Commissioning Seal

**Status:** implemented with one verified live circulation and one held live
transfer trial

## Purpose

v9.6 crosses the first real model boundary in the live Cortex body while
preserving the distinction between a correctly measured circulation and a
useful transferable competence.

The release law is:

```text
live invocation != task success
task success != competence benefit
equal controls != transfer gain
model output != evidence legitimacy
```

## Prior wound

The v9.0-v9.5 architecture could preserve live empirical evidence, but the
release suite had used fixtures and simulated adapters only. No provider-neutral
live circulation had been commissioned in the canonical Cortex body.

The live audit also found that older SQLite bodies retained v9.4's original
uniqueness constraint:

```text
UNIQUE(repository_id, implementation_digest, boundary_kind)
```

That allowed one model per adapter implementation and boundary, contradicting
the modern exact binding law and blocking replaceable cross-model trials.

## Optional live adapter

`cortex.adapters.ollama_local.OllamaLocalAdapter` is an optional integration
boundary. Provider-specific transport remains outside `model_circulation.py`.

The adapter:

- accepts only a valid `ModelInvocationRequest`;
- accepts only loopback HTTP `/api/generate` endpoints;
- rejects endpoint credentials, query material, nonlocal hosts, and malformed
  model identities;
- requires a canonical `task_instruction` or frozen transfer task;
- constrains the response with a public JSON schema;
- sets Ollama thinking off and never requests hidden reasoning;
- returns only provider-neutral public output, proposal, uncertainty,
  citations, token counts, cost, and completion time;
- rejects a response declaring a different model; and
- carries no credentials in its instance state or canonical registration.

Host adapter registration still means only that a local principal classified
one exact implementation/runtime/model boundary. Provider attestation remains:

```text
provider_attestation = not_available
provider_attestation_claimed = false
```

## Independent commissioning verification

The commissioning seal does not trust the function return object. It reloads
the append-only circulation ledger and independently calls the canonical v9.0
verifier. A seal passes only when it resolves:

```text
host-registered live adapter
  -> canonical model invocation
  -> public proposal
  -> frozen independent evaluation
  -> verified success or verified failure outcome
  -> immutable witness result
  -> bound trajectory
```

All six receipt and content hashes must exist. The witness result must resolve,
the evidence class must reconstruct as `live_empirical`, and all authority
flags must remain false.

A verified failure is still an empirical observation. Task success is reported
separately from measurement integrity.

## Adapter-registration migration

The v9.6 migration detects only the legacy implementation-wide uniqueness law.
Inside one SQLite transaction it:

1. reads every registration column in deterministic order;
2. creates a new exact-binding table;
3. copies every immutable value byte-for-byte;
4. compares the complete before/after row tuples;
5. aborts on any mismatch;
6. drops the legacy table only after equality; and
7. restores immutable update/delete triggers and indexes.

The new identity law is:

```text
UNIQUE(repository_id, binding_digest)
```

where the binding digest covers implementation, sanitized runtime profile, and
host model identity. One adapter implementation can now serve multiple exact
replaceable models without one registration authorizing another.

## Live commissioning result

The local host exposed Ollama 0.32.9 with `phi4-mini:latest`. A one-time local
principal registered the exact adapter/model/runtime profile; its plaintext
secret was discarded after registration and was never printed or persisted.

The frozen task required the exact public token:

```text
CORTEX_EMPIRICAL_960
```

The model returned the token and Cortex independently evaluated it. The
canonical live seal is:

```text
status                    EMPIRICAL_CIRCULATION_VERIFIED
session                   sym_2bf5cf0c0122acce250d
evidence class            live_empirical
outcome                   verified_success
task evaluation           pass
witness result            dd4ace15a689c90d646293d839d1cb30d9cac9d17405d2d203e1ed9d5e8c0edc
commissioning receipt     2898d2e86edd10de9958b900792edffde7f4f5a89689793fd305c2ac8e5e010c
provider attestation      not_available
```

The console initially failed while printing the Unicode glyph under Windows
legacy encoding. The canonical ledger had already committed correctly, and the
independent verifier reconstructed the seal from that ledger. The script now
configures UTF-8-safe output and reuses an existing immutable registration on
retry.

## Strict transfer result

Only the externally demonstrated behavior was distilled:

```text
When a bounded task explicitly supplies an exact public token, reproduce that
token verbatim in public_output.text without tools.
```

The candidate preserves counterevidence that one case does not establish
benefit. Five stateless `mistral:latest` arms then ran against a frozen contract:

| Arm | Context | Evaluation | Evidence |
|---|---|---|---|
| A | ordinary task/repository context | pass | live empirical |
| B | bounded raw public origin history | pass | live empirical |
| C | unfiltered admitted memory | pass | live empirical |
| D | distilled competence | pass | live empirical |
| E | competence plus prior verified feedback | pass | live empirical |

The declared policy weighted task success only and required a minimum gain of
`0.05`. Observed gains were:

```text
G_continuity   = 0.0
G_distillation = 0.0
G_governance   = 0.0
G_credit       = 0.0
```

Therefore:

```text
trial valid          true
portability status   unresolved
classification       declared_gain_threshold_not_met
distribution         blocked
```

This is the correct result. All models succeeding proves that the task was easy
for the controls; it does not prove the competence caused improvement.

## Read/write and authority boundary

Canonical writes in this phase are limited to explicit host registration,
model circulation receipts, witness results, one competence candidate, and one
transfer trial. Verification remains observational.

Every output preserves:

```text
host_mutate_authorized = false
execution_authorized = false
memory_admission_authorized = false
policy_effect = false
update_authorized = false
distribution_authorized = false
```

No package was created because transfer remained unresolved. No v9.5
assimilation or competence revision was attempted.

## Tests

Focused v9.6 tests cover:

- loopback-only endpoint enforcement;
- credential-bearing endpoint rejection;
- canonical request verification;
- structured public response parsing;
- provider-native and hidden-reasoning field exclusion;
- response-model mismatch rejection;
- fixture and simulated evidence remaining nonempirical;
- ledger reconstruction ignoring caller-modified result mappings; and
- multiple exact models sharing one adapter implementation after safe legacy
  migration.

## Claim boundary

v9.6 establishes one real local model circulation and a truthful controlled
transfer result. It does not establish provider attestation, universal model
quality, competence benefit, cross-family transfer, distributed learning,
cognition, consciousness, autonomous agency, execution authority, or host
mutation authority.

## Next evidence gate

The next experiment needs a task on which fresh controls measurably fail or
cost more while the frozen competence arm improves under a preregistered policy.
Only a positive, independently verified gain may open production distribution
and exact package-use feedback. More structural code is not a substitute for
that experiment.
