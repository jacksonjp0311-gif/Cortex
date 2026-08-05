# Phase v8.5 — Authenticated Will & Unified Distillation Membrane

## Purpose

v8.4.5 produced typed distillation candidates from verified trajectories.

**v8.5 combines** what was previously sketched as 8.5.0 + 8.5.1 into one release:

```text
authenticated principal will
  +
will-bound unified distillation membrane
```

Direction may rank what matters. Evidence still decides what is true.

## Law

```text
will  →  direction only
candidates  →  measured change linked to outcomes
membrane  →  admit iff will ∧ ΓΞWOS ∧ trajectory_candidate ∧ support
will ↛ invent facts
will ↛ host.mutate
will ↛ auto-execute
membrane.invented_count ≡ 0
```

## Authenticated will (`cortex will`)

### Principal

Local will principal with secret shown once at registration.

### WillRoot

```text
principal_id, will_id
scopes: will.direct | will.prioritize | will.admit
clauses:
  prioritize_type | deprioritize_type | admit_type | forbid_type
  admit_candidate | cap_retain | prefer_support_min
HMAC-SHA256 signature over payload_hash
time window, optional session/epoch bind
invents_facts=false, alters_evidence=false
execution_authorized=false, host_mutate_authorized=false
```

Forbidden scopes: `host.mutate`, `source.edit`, `execute`, `invent_fact`, …

### Verify

`verify_will` checks structure, time, bindings, principal registration, and
HMAC when the secret is supplied. Membrane admission **requires** verified HMAC.

## Unified membrane (`cortex membrane`)

```text
candidates + batches
  + authenticated will
  + Γ Ξ W O S
  → DistillationMembraneAdmission
```

### Outcomes per candidate

| result | meaning |
|--------|---------|
| **admitted** | will directs, gates open, support enough → `retain=true` |
| **deferred** | will directs but gates closed |
| **rejected** | forbid, undirected, unverified will, weak support, cap |

Outcome-linked types (`verified_fact`, `successful_procedure`,
`failed_hypothesis`, `counterevidence`, `useful_route`) require **medium+**
support. Structural types may admit at the will’s `min_support`.

### Authority

```text
durable_write_authorized = admitted_count > 0 ∧ gates.open ∧ will.verified
host_mutate_authorized = false
execution_authorized = false
adaptation_authorized = false
invented_count = 0
sources_only_from_candidates = true
```

## Symbiosis integration

`consolidate_session(..., will=, will_secret=)` runs the membrane before
ΓΞWOS consolidation. Retained items only exist if the membrane marked
`retain=true`. Without will, candidates remain non-retained (v8.4.5 behavior).

## CLI

```powershell
python -m cortex will register --repo R --principal op --name Operator --json
python -m cortex will issue --repo R --principal op --secret S `
  --admit-types successful_procedure,verified_fact --json
python -m cortex will verify --repo R --secret S --json
python -m cortex membrane admit --repo R --secret S `
  --constitutional --epoch-ok --witnessed --outcome-closed --stable --json
python -m cortex symbiosis consolidate --repo R --will-secret S --constitutional --json
```

## Claim boundary

```text
will ≠ truth
admission ≠ execution
direction ≠ invention
durable_write ≠ host mutation
```

## Sequence

```text
8.4.3  shared heartbeat
8.4.4  verified trajectory
8.4.5  typed distillation candidates
8.5    authenticated will + will-bound membrane
8.6    admitted memory ledger
```
