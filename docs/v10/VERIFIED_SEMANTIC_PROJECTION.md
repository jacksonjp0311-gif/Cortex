# Cortex v10.0.0-alpha.14 — Verified Semantic Projection & Causal Transfer

Alpha.14 closes a concrete cognitive bottleneck discovered by the alpha.13
null result. Cortex already selected canonical memory summaries, but the native
model projection received only their SHA-256 digests. Those digests proved
identity while conveying none of the lesson.

## Dual representation

```text
canonical admitted memory
          │
          ├── proof form: receipt, lineage, outcome/witness roots
          │
          └── cognitive form: bounded public lesson + conditions + uncertainty
                                  │
                                  ▼
                         transient reasoning model
```

The proof form remains canonical. The cognitive form is reconstructed from the
canonical row; callers and models cannot supply or rewrite it. Hidden reasoning
is never requested or persisted.

```text
Knowledge stored != knowledge projected != knowledge usable
Provenance representation != cognitive representation
Knowledge = bounded semantic payload + provenance proof
```

Each active lesson carries its canonical memory receipt, evidence roots,
semantic-content hash, lesson hash, support level, and explicit unresolved
completeness fields. Its scope is `trajectory_bound`; Cortex does not promote a
single witnessed observation into a universal rule.

## Noncompensatory projection gate

For memory `m` and task `t`:

```text
Theta_P(m,t) = min(V, S, A, F, C)

V = canonical memory and lineage verification
S = exact semantic binding to canonical candidate material
A = task applicability
F = epoch and lifecycle freshness
C = contradiction clearance

Project(m,t) iff Theta_P(m,t) = PASS
```

The order remains `FAIL < UNKNOWN < PASS`. Ranking, overlap, support scores, or
caller assertions cannot compensate for a failed hard plane. Missing identity
stays `UNKNOWN`; stale, contested, mismatched, or tampered content stays out of
active guidance.

Current semantic support proves exact binding to the admitted trajectory-bound
candidate. It does **not** prove prerequisite completeness, applicability
completeness, counterevidence completeness, or universal entailment. Those
unknowns are carried into the model-visible lesson instead of being hidden.

## Historical authority versus current restriction

An admitted memory retains its historical authenticated admission even though
the HMAC secret is intentionally absent from durable storage. Alpha.14 no longer
requires that unavailable secret merely to read an immutable memory. Current
projection restrictions are accepted only from Cortex's canonical latest will
tip after all non-secret identity, body, time, repository, and receipt checks
pass. This read path cannot mint action authority.

## Causal transfer experiment

The next empirical panel uses three frozen, model-matched arms:

```text
A  task only
B  task + equally bounded verified but irrelevant sham lesson
C  task + independently verified applicable lesson

G_total     = U_C - U_A
G_context   = U_B - U_A
G_relevance = U_C - U_B
```

`G_relevance` separates useful semantics from prompt length, formatting,
Cortex identity, or generic governed metadata. Source and target tasks must
differ while sharing a latent mechanism; the lesson may describe a general
verified procedure but may not contain the held-out answer.

This release implements and adversarially verifies the semantic bridge. It does
not fabricate a sham corpus or claim positive causal transfer. A live A/B/C run
remains `NOT EXECUTED` until Cortex has a preregistered, non-ceiling held-out
panel and canonical relevant/sham lesson pairs.

## Authority and claim boundary

Every lesson and projection keeps these closed:

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
```

Alpha.14 establishes that verified semantic memory can reach transient
cognition without losing its proof roots. It does not establish that Cortex
improves model capability, that stored lessons are complete, or that semantic
transfer produces positive gain.
