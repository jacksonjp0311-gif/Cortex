# Epistemic instrumentation and evidence-governed state

Implementation started September 5; zero-call closure September 6, 2026.
Baseline: `f2c025062ab3cf20570052a10e8414ef153ce5d7`.
**Research prototype, bounded assurance. Product version remains 10.0.0a39.**
Alpha.40 is a proposed release theme, not a claim that every workstream below is
complete. No model call is required to test the new measurement boundaries.

## The narrow architecture

```text
public behavioral contract + code
               │
               ▼
      frozen private evaluator ◄── alternate valid repairs + broken controls
               │                              │
               ▼                              ▼
     isolated observations ─────────► bounded instrument audit
               │                              │
               ▼                              ▼
       immutable Store receipt ─────► recomputed epistemic view
                                              │
                                      claim-specific gate
                                              │
                                      PASS / UNKNOWN / FAIL

future cognition: evidence → bounded semantic projection → replaceable model
                 → typed intent → compiler → isolated observation → evidence
```

The model is not the evaluator. An evaluator observation is not a claim.
An interpretation is not authority. Existing Store ledgers, domain verifiers,
native runtime and edit-intent compiler remain the underlying mechanisms.
There is no new memory database, agent scheduler, UI, or authority system.

## A common interface, not a common truth engine

\[
\mathcal C:(E_t,S_t,A_t)\mapsto(S_{t+1},A_{t+1},E_{t+1}),\qquad
S_t=\Pi(E_{\leq t}).
\]

The equation describes constrained transitions; it does not grant one.
For model-originated transitions, authority cannot expand. Source/evidence
history stays intact; later interpretation is another object with another ID.

`governed_state_view()` exposes identity, native kind/state, provenance,
support/opposition, freshness, applicability, temporal coordinates, supersession
and closed authority effects. Unsupported domain mappings explicitly remain
`UNKNOWN` or null. Receipt integrity does **not** populate those missing gates.
This is a read-only inspection interface, not a superclass or admission path.

| Domain | Native meaning retained | Required specialist boundary |
|---|---|---|
| Memory | Admitted historical lesson | Memory lineage, scope and semantic projection |
| Hypothesis | Proposed explanation | Supporting/opposing observations, not confidence alone |
| Evaluator | Measurement instrument | Bounded positive/negative controls and challenges |
| Experiment | Frozen method and observations | Task/model/evaluator/trajectory reconstruction |
| Policy | Host permission contract | Principal, lifetime, scope and revocation |
| Competence | Operational abstraction | Distillation plus fresh applicable transfer evidence |
| Action | Proposed or observed transition | Capability, compiler, execution and outcome gates |

An experiment's reconstructed record is canonical **as a record**, not canonized
as universal truth. Observation, hypothesis, procedure, decision, preference,
superseded interpretation and competence keep their domain meanings. Existing
memory/competence objects are not migrated or silently renamed in this phase.

## Instrument geometry

For each evaluator and case, retain two independent support/opposition channels:

\[
V_E=(\mathrm{acceptedValid},\mathrm{rejectedValid}),\quad
N_E=(\mathrm{rejectedInvalid},\mathrm{acceptedInvalid}).
\]

Each component contains execution-evidence roots, not a model confidence score.
Counts describe the tested control set, not population error-rate estimates.

| Observation | Derived instrument state |
|---|---|
| At least two distinct valid patches accepted and a negative rejected per case, no contrary observation, bounded assurance | `READY` |
| A host-labeled valid implementation rejected | `OVERCONSTRAINED` |
| A host-labeled invalid implementation accepted | `UNDERCONSTRAINED` |
| Both failure modes | `CONFLICTED` |
| Incomplete coverage, malformed binding, unavailable assurance | `UNRESOLVED` |

Readiness is noncompensatory:

\[
\mathrm{Ready}(E)=\bigwedge_{p\in P}E(p)\land
\bigwedge_{n\in N}\neg E(n)\land\mathrm{Coverage}\land\mathrm{Assurance}.
\]

The prior control-audit 1.0 object stays unchanged. New instrument-assurance 1.0
is a separate projection/receipt. `audit_instrument()` executes controls through
the existing local evaluator; it does not accept caller-provided success rows.
`verify_instrument()` reloads the canonical audit and recomputes diagnostics.
The pure `instrument_state()` helper alone is **not** a trust boundary.

A later evaluator challenge closes current claim eligibility without making a
historically valid receipt disappear. Resolving a challenge requires a new
instrument identity; a caller's `resolved` flag cannot reopen the old one.

## Stop the verifier regress

\[
D_v=|\text{declared fixed path}|-1=3\leq D_{\max}=3.
\]

The finite path is public contract → evaluator → controls → local observation.
The depth measures these declared edges, not all transitive software dependencies
or CPU trust layers. The fixed anchors are **host-reviewed control labels** and
**host-observed execution**. The caller can narrow the depth budget, not increase
the implementation ceiling. Exceeding it returns `UNKNOWN`; there is no recursive
call to another verifier to manufacture certainty.

Unresolved assumptions remain public: labels may be wrong, coverage incomplete,
patch diversity is not semantic independence, and host execution is trusted.
Detached worktrees isolate repository changes, **not the operating system**.
Neither source hashes nor locally issued receipts constitute provider attestation.

## Claim lattice and scope

\[
\mathrm{ClaimStrength}\leq\min(\mathrm{SourceValidity},
\mathrm{InstrumentValidity},\mathrm{ExperimentalValidity},\mathrm{CausalValidity}).
\]

This is an ordered prerequisite bound, not a numerical measure of intelligence.
Use `FAIL < UNKNOWN < PASS` and the meet of the gates required by each claim.

```text
receipt reconstructs
        ↓
sampled instrument controls supported       ← implemented bounded claim
        ↓
discriminative task region                  ← not established
        ↓
matched semantic contrast
        ↓
supported effect → repeated effect → cross-task / cross-model replication
        ↓
competence eligibility                     ← never granted by this layer
```

`inspect_measurement_claim()` currently derives only bounded instrument-control
eligibility. It independently consults current challenges. Higher claims remain
`UNKNOWN` (or `FAIL` when a prerequisite fails); no caller-supplied pass/confidence
can open them. It does not replace the existing competence/distribution verifiers.
All four authority-effect flags remain false even for a ready instrument.

## Realistic-defect frontier: prepared, not calibrated

The new path extends existing repair corpus schemas to **2.0** for source-file
maps, retaining 1.0 reconstruction. Path validation rejects traversal, Windows
aliases, Git internals, duplicate/colliding paths and evaluator-file overwrites.
The structured runner now renders all public files and compiles only allowed
source edits. No provider-specific code was introduced.

New structured preregistration **1.3** binds canonical instrument assurance,
stratum, source fingerprints, evaluator controls, existing model/provenance,
response contract and four-call one-shot execution policy. Task-only treatment
is rechecked. Reused exact source cannot become a fresh sample by changing its
case ID or prose. This does not detect every semantic clone or renamed program.

The first host-private prototype uses a catalog with storage, cache, service,
package and presentation files. Cross-tenant reads interact with cached revision
identity over time. Two repair strategies are allowed: partitioned cache keys and
globally unique revisions. Controls probe partitioning, stale versions and
returned-value aliasing. This is an **authored multi-file development fixture**,
not a production incident or a measured difficulty level. L3 denotes intended
cross-module/temporal structure, not measured model difficulty.

Only one prototype is prepared. A four-case frontier and confirmation cohort
are **not ready**. The live runner must not launch this one-case corpus.
Its private tests/reference repairs remain outside Git/in the host vault.
Public unit fixtures are architectural tests, never held-out empirical targets.

## Sequential calibration and treatment geometry

The 1.2 rule carries into 1.3: four cases screen only. Zero or four successes
identify a panel floor/ceiling; one to three request fresh confirmation at fixed
difficulty. There is no automatic difficulty movement or paid retry. Existing
historical 1.0/1.1/1.2 receipts keep their original semantics.

Before confirmation, freeze fresh task identities, fixed stratum, exact source,
evaluator commitments, model/provenance/configuration, tools/budgets, stopping
rule and total call limit. Repeated invocations are not new tasks. A complete
prospective multi-batch confirmation executor is **deferred**, not claimed here.
No p-value or population inference follows from these small heterogeneous screens.

Only after that threshold should an independently frozen experiment compare:

| Arm | Context |
|---|---|
| A | Task only |
| B | Task + verified irrelevant sham lesson |
| C | Task + independently sourced relevant lesson |

\[
G_{context}=U_B-U_A,\quad G_{relevance}=U_C-U_B,\quad G_{total}=U_C-U_A.
\]

Match B/C context size, tools, budgets and runtime; preserve all outcomes. Source
experience and held-out targets must differ; shared causal mechanism is not
permission to leak answers. None of these effects was measured in this phase.

\[
\mathrm{Truth}(m)\ne\mathrm{Utility}(m,t),\qquad
\mathrm{Competence}(l,F)\Rightarrow\mathrm{Verified}(l)\land
\mathrm{Transferable}(l,F)\land\mathrm{MeasuredGain}(l,F)>0.
\]

This necessary-condition research formulation does not retroactively redefine
historical competence candidates. Future same-model matched contrasts and
cross-model lesson reuse remain hypotheses, not findings.

## Fifteen design laws

1. Stored ≠ projected ≠ usable ≠ authorized knowledge.
2. Provenance representation ≠ cognitive representation.
3. Evidence ≠ truth ≠ authority ≠ success.
4. Hash integrity ≠ semantic validity.
5. Evaluator output ≠ ground truth.
6. Benchmark success ≠ calibration.
7. Calibration ≠ treatment effect.
8. Treatment effect ≠ general competence.
9. Specification complexity ≠ reasoning difficulty.
10. More context ≠ more capability.
11. Governed context ≠ useful context.
12. Useful context must supply task-relevant semantics.
13. Measurement cannot outrank its instrument.
14. Stronger optimization requires stronger oracle defenses.
15. Historical identity is immutable; interpretation may evolve separately.

These are design constraints and claim boundaries, not new physical laws.

## Research answers and limits

| Question | Current answer |
|---|---|
| Q1 Shared formalism? | Shared inspection/provenance interface works; domain admission remains separate. |
| Q2 Positive/negative validity? | Two support/opposition channels implemented per case. |
| Q3 Minimum assurance? | Fixed finite path plus declared host anchors; minimality not proven. |
| Q4 Separate over/underconstraint? | Separate observed counts and roots; population rates unknown. |
| Q5 Instrument uncertainty? | Explicit unresolved scope, coverage and anchor assumptions. |
| Q6 Latent complexity estimate? | Structural strata descriptive only; difficulty still requires observations. |
| Q7 Non-ceiling tasks? | Unknown. Multi-file temporal prototype is a candidate, not an answer. |
| Q8 Relevant lesson gain? | Unmeasured; requires A/B/C controlled experiment. |
| Q9 Model replacement gain? | Unmeasured; identity remains provider-neutral provenance. |
| Q10 Accumulating capability? | Unestablished. Stored verified experience alone is insufficient. |

## Closure record

Exact tests and zero-call audit result are appended after execution. No historical
benchmark artifact is modified, no positive result is manufactured, and no alpha.40
release is sealed solely because these interfaces exist.
