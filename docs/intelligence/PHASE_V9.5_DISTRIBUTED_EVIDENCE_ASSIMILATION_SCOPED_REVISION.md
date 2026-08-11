# Cortex v9.5.0 - Distributed Evidence Assimilation & Scoped Competence Revision

## Purpose

v9.5 closes the governed return path from an exact v9.4 package exposure to a
proposed competence revision. It does not turn feedback into authority and it
does not update competence automatically.

The implemented path is:

```text
verified package-use feedback
    -> frozen evidence cohort
    -> canonical-observation deduplication
    -> dependence and diversity analysis
    -> scoped revision candidate
    -> independent revision verification
    -> explicit promotion
    -> immutable successor competence
```

The governing distinction is:

```text
evidence quantity != evidence structure
revision candidate != revision
exposure-bound observation != causal proof
```

## Claim boundary

v9.5 establishes a mechanically governed revision path. It does not establish
universal competence, autonomous learning, general intelligence,
consciousness, or cumulative real-world intelligence gain. No real external
model trial was executed as part of this release.

Every new cohort, analysis, candidate, verification, promotion, and successor
keeps these authority planes closed:

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
automatic_broadcast          = false
automatic_global_revision    = false
```

## Evidence eligibility

One feedback mapping is not an observation merely because it says that it is
verified. Cortex reloads and verifies the complete v9.4 binding:

```text
feedback
    -> package-use receipt
    -> immutable target package and profile
    -> competence receipt
    -> model invocation and context projection
    -> canonical outcome
    -> independent witness result
    -> trajectory
```

For observation `e_i`, the empirical gate is noncompensatory:

```text
Theta_i = min(
    empirical_class,
    provenance,
    package_use_binding,
    historical_package_currentness,
    outcome_binding,
    witness_binding,
    target_identity,
    competence_identity,
    freshness
)
```

Only `Theta_i = pass` enters the empirical plane. A failed or unknown plane is
not repaired by utility, repetition, confidence, or a caller scope label.

## Frozen cohorts

`freeze_evidence_cohort()` binds evidence membership, evidence cutoff,
selection policy, analysis policy, source competence receipt, canonical
observations, evidence roots, and creation time into one immutable hash.

The cohort is appended only when `persist=True`. Later feedback, a later
threshold, or a later policy produces a new cohort or analysis; it cannot alter
the old object. UPDATE and DELETE are rejected by SQLite triggers.

Negative, invalid, unknown, duplicate, and synthetic observations remain
inspectable in the cohort. Exclusion from empirical inference is not erasure.

Production selection has one canonical mode: every feedback observation for
the competence that exists when Cortex freezes the cohort. A caller-selected
list and an explicitly historical cutoff remain useful structural/as-of
objects, but are typed `unknown` and cannot authorize revision. This prevents
post-hoc removal of inconvenient outcomes or hindsight selection of a
favorable time window.

The dependence axes, evidence-retention rule, canonical observation root, and
non-causal interpretation are constitutional v9.5 boundaries. Host-verified
adapter principal identity is one of those axes: registrations, models, and
providers controlled by the same principal do not become independent merely
because their labels differ. A host may freeze explicit global thresholds,
but a caller cannot delete a dependence axis or redefine a shared upstream
root as independent.

## Deduplication

Equivalent feedback representations resolve to one observation identity built
from the exact package-use, outcome, witness-result, and trajectory roots. The
same canonical exposure cannot become independent evidence by changing caller
text or submitting it repeatedly.

The report preserves requested feedback count, unique feedback count, raw
canonical observation count, and duplicate count. Replaying one feedback ID a
thousand times still resolves to one root. Genuinely distinct package uses
remain distinct even when their outcomes are equal.

## Dependence and effective evidence

v9.5 does not define evidence strength as raw count. The frozen policy declares
the axes used to inspect shared lineage, adapter registration, consuming model,
provider, target class, environment, task contract, witness suite, and transfer
root.

The output classifies pair relationships as:

- strongly dependent;
- partially dependent;
- independent under the declared policy;
- unresolved.

Strongly dependent, partially dependent, and unresolved pairs are collapsed
into conservative policy-separated components. `effective_evidence_count`
means the number of complete components after that collapse. It is an audit
count—not independent support, a probability, or a scientific significance
claim. Missing required axes produce unresolved dependence and never
manufacture independence.

Temporal repetition is reported separately from cross-target, cross-model, and
cross-environment diversity. A hundred targets sharing the same declared
causal surfaces remain visibly correlated.

## Diversity

The analysis reports distinct targets, target classes, profiles,
environments, model identities and families, provider families, task
contracts, packages, and temporal span. Diversity describes evidence
structure; it does not prove a proposition by itself.

Global contradiction has no hidden default threshold. It remains unknown
until the frozen host policy explicitly declares minimum complete clusters and
minimum diversity, and every required independence surface resolves.

## Scope classification

Scope is derived from canonical outcomes, not from the feedback `kind` chosen
by a caller.

| Derived scope | Conservative interpretation |
|---|---|
| `local_exception` | Contradiction is confined to one target and yields an enforceable target exclusion after verification and promotion. |
| `target_class_exception` | Failure is confined to one target class with support elsewhere. |
| `environment_specific_exception` | Failure is confined to one environment with support elsewhere. |
| `model_capability_exception` | Failure is confined to one model-capability regime. |
| `competence_specialization_candidate` | Support and contradiction occupy distinct regimes. |
| `global_contradiction_candidate` | An explicit frozen diversity/independence policy is satisfied. |
| `supporting_evidence` | Verified support is retained without silently broadening scope. |
| `unresolved` | Required structure is incomplete or non-identifying. |

The ordering is applicability-first: a scoped exclusion or specialization is
preferred to declaring the entire competence false when the evidence supports
that narrower interpretation.

Scoped support and contradiction may share upstream lineage and still justify
a narrow exclusion only when a complete canonical discriminator separates the
regimes. Overlapping or missing discriminator values remain unresolved. Shared
upstream evidence never counts as independent replication for a global claim.

## Causal discipline

Ordinary distributed feedback is typed
`observational_exposure_bound`. Exact package exposure is known; a
counterfactual causal effect is not. The analysis therefore records:

```text
causal_effect_established = false
```

A stronger causal class requires a separately declared controlled or
randomized design. High utility cannot upgrade observational evidence.

## Synthetic and legacy evidence

Fixture and simulated evidence remains visible for architecture testing and
failure injection. It contributes zero empirical support, zero empirical
diversity, and cannot promote a production revision.

Legacy or incomplete v9.4 feedback remains inspectable but resolves as unknown
or ineligible when the exact package-use/outcome/witness path cannot be
reconstructed. Pre-v9.5 adapter receipts without host model classification are
reported as `legacy_partial`; they keep their historical identity but cannot
manufacture model-family or principal diversity. Immutable historical rows are
not rewritten.

## Revision candidates

`CompetenceRevisionCandidate` is immutable and non-authorizing. Its proposed
revision type, applicability change, failure-condition additions,
counterevidence additions, uncertainty additions, scope, dependence analysis,
and evidence roots are derived from the verified frozen analysis.

Caller prose may explain a proposal. It cannot add semantic changes. A
candidate cannot mark itself verified, create its own successor, remove
counterevidence, claim observational causation, broaden applicability from the
absence of failures, or open an authority flag.

## Independent revision verification

`verify_revision_candidate()` is read-only unless `persist=True`. It reloads
the cohort and analysis and independently recomputes:

- evidence membership and canonical validity;
- deduplication roots;
- dependence clusters and unresolved axes;
- diversity;
- scope classification;
- every proposed semantic change;
- counterevidence conservation;
- all evidence-root bindings.

The candidate's cached booleans are not verification inputs. A separately
hashed verification receipt is required at promotion time, and promotion
re-runs the verifier.

Historical validity and current applicability are separate propositions. A
cohort reconstructs package, profile, event, promotion, use, and feedback state
at its immutable cutoff. A distinct promotion-time gate then requires those
same observations to remain current and unexpired. A later target profile or
expiry can block promotion without rewriting the historical cohort; a later
successful promotion likewise cannot invalidate the evidence that justified
it.

## Successor competence lineage

Promotion is an explicit call with a canonical passing verification receipt
and a public promotion reason. Semantic narrowing or specialization creates a
new immutable competence identity. The parent is never updated.

```text
K(n)
  -> frozen cohort
  -> analysis
  -> revision candidate
  -> independent verification
  -> promotion receipt
  -> K(n+1)
```

The successor records the parent receipt, cohort and analysis hashes, revision
candidate, verification receipt, and relationship (`narrows`, `specializes`,
or `supersedes`). Parent counterevidence is a required subset of successor
counterevidence. The successor returns to transfer-pending state and requires
fresh transfer verification before distribution.

Successor insertion and promotion append occur in one SQLite transaction. A
partial commit cannot appear as a completed promotion.

Schema `cortex-competence/1.1` is reserved for that atomic promotion path. The
general competence append API rejects caller-built successors, and deep
candidate verification resolves every successor back through the immutable
promotion, revision verification, analysis, cohort, and parent. Typed target,
class, environment, and model-family constraints are enforced rather than
stored as descriptive metadata.

## Distribution interaction

Existing packages remain byte-for-byte bound to the parent competence.
Verified semantic promotion makes those packages resolve as superseded; it
does not rewrite or broadcast them. A successor requires a new transfer trial,
target compatibility check, and projection.

Historical package-use evidence remains inspectable after promotion. Package
currentness and historical exposure are separate propositions.

A successor cannot regain transfer status without a frozen applicability
context proving that the transfer trial ran in an allowed target, class,
environment, and model-capability regime. Missing required context is unknown
and blocks transfer; provider-neutral context is part of the trial identity.

## Read/write separation

Read-only operations:

- resolve an observation;
- verify a cohort or analysis;
- analyze with `persist=False`;
- verify a revision candidate with `persist=False`;
- verify promotion and successor currentness.

Explicit canonical writes:

- freeze a cohort with `persist=True`;
- persist an analysis;
- persist a revision candidate;
- persist an independent verification receipt;
- explicitly promote a verified revision.

No observational operation updates feedback, competence, packages, policy, or
authority.

## Tests

The focused v9.5 suite exercises immutable cohorts, duplicate package-use
roots, synthetic exclusion, post-cutoff and retroactive selection, correlated
repetition, caller scope labels and dependence policy, unresolved dependence,
as-of replay, promotion-time expiry, read purity, self-verification,
evidence-derived semantic changes, counterevidence conservation, explicit
promotion, parent immutability, successor lineage, typed applicability,
transfer-context binding, and fail-closed package currentness.

The v9.0-v9.4 suites remain regression gates for model circulation,
competence, transfer, distribution, empirical evidence classification, and
package-use binding.

## Remaining evidence

- No external-provider empirical trial was executed during this release.
- Host-registered live adapter provenance is local boundary evidence, not
  cryptographic provider attestation.
- Model-family evidence is available only when the host binds that optional
  capability class into adapter registration; absent legacy fields remain
  unknown and cannot manufacture cross-family diversity.
- Dependence is conservative and policy-declared; unresolved upstream causal
  structure remains unresolved.
- v9.5 does not estimate probabilities or causal effect sizes.
- A future phase may study governed composition across independently verified
  competence lineages, but that phase is not implemented or canonized here.

The release law is:

```text
verify -> freeze -> deduplicate -> analyze dependence -> derive scope
       -> propose -> independently verify -> explicitly promote
```

Never:

```text
feedback volume -> confidence -> automatic rewrite
```
