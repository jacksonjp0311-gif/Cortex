# Governed Autonomous Improvement

Version: `10.0.0-alpha.8`

## Purpose

Alpha.8 closes one real but bounded autonomous source-improvement loop:

```text
host objective
  -> governed Storm candidates
  -> canonical patch tool receipts
  -> isolated host verification
  -> frozen baseline/candidate trial
  -> deterministic candidate tournament
  -> authenticated autonomy policy
  -> bounded promotion
  -> signed canary
  -> retain or exact rollback
  -> historical improvement episode
```

Autonomy means Cortex may complete those steps without another click only when
the operator previously issued an exact policy that permits them. Cortex has no
authority outside that envelope and cannot widen the envelope itself.

## The noncompensatory law

For candidate `c`, promotion requires:

```text
Theta(c) = min(P, V, DeltaU, N, S, R, A) = PASS
```

- `P` - canonical Storm and patch provenance;
- `V` - isolated host verification;
- `DeltaU` - an allowed measured trial classification;
- `N` - no blocking regression;
- `S` - exact policy scope and freshness;
- `R` - executable canary and rollback path;
- `A` - authenticated operator policy.

Candidate quality, fluency, agreement count, provider identity, or tournament
rank cannot compensate for a failed gate.

## Storm synthesis

Agents may express affirming, denying, or uncertain claims. Cortex groups them
by exact claim key and evidence root. This detects shared lineage and explicit
conflict but never labels agreement as truth:

```text
five agreeing agents + one shared root = one evidential lineage
agreement_state != semantic_truth
```

## Autonomous campaign

`run_autonomous_improvement_campaign()` accepts only a verified Storm result.
It reloads each child trajectory and extracts patch candidates from canonical
`workspace.propose_patch` tool receipts, not from prose. Every candidate then
receives the same architecture-native verification and counterfactual path.

The tournament is deterministic and non-authorizing. Eligibility is a hard
gate; among eligible candidates, Cortex prefers higher measured effect, fewer
files, fewer changed lines, lower measured candidate duration, then canonical
proposal identity.

## Authority envelope

`AutonomyPolicyEnvelope` is issued by a principal already registered in the
canonical will-principal ledger. Cortex verifies both the principal secret hash
and the HMAC over the exact policy body. The persisted policy freezes:

- path allowlist and permanent denylist;
- maximum files and changed lines;
- accepted trial classifications;
- exact canary command vectors;
- issue/expiry time;
- automatic-promotion permission;
- recursive-generation permission.

Permanent protected surfaces include constitutional authority, will,
capability, promotion, CI, Cortex control metadata, the autonomy implementation,
and its adversarial test. A policy cannot remove those protections.

## Promotion and rollback

Promotion re-verifies the policy, tournament identity, exact winner, trial,
scope, and Git HEAD. It then applies the exact canonical patch using the
existing bounded workspace implementation. Signed canary steps run after the
application. Any canary failure reverses the exact patch before the promotion
receipt is sealed.

The receipt distinguishes:

```text
promoted_canary_pass
rolled_back_canary_failed
```

No model receives host mutation or execution authority. The host policy is the
authority edge; the model remains only the candidate source.

## Recursive generation

A candidate generation may not verify itself. Recursive eligibility requires:

```text
candidate_generation != parent_generation
verifier_generation = parent_generation
recursive_generation delegated by policy
candidate is the tournament winner
protected surfaces untouched
```

This is eligibility for the normal promotion path, not self-authorization.

## Improvement memory

An `improvement_episode` records the canonical promotion, observed outcome,
lessons, and counterevidence. It is historical evidence only:

```text
historical_evidence_only = true
active_guidance = false
memory_admission_authorized = false
```

Existing governed distillation and admission machinery must independently
decide whether any lesson later becomes memory or competence.

## Remaining boundary

Alpha.8 proves the mechanics using deterministic adapters and real temporary
Git repositories. It does not establish that Cortex generally improves itself,
that model-generated changes are safe, or that one measured repair generalizes.
Production autonomy requires an operator-issued policy appropriate to the
specific repository and risk class. Unbounded self-authorization remains
forbidden.
