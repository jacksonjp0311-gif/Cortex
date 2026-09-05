# Mathematical contract audit — 2026-09-04

Reviewed baseline: `6e8f642486fbc584b10b3dbc1ce26ba29727b237` (10.0.0a39).
This audit keeps the product version and historical experiment receipts intact.
It uses source inspection, executable counterexamples, and reconstruction of
existing local receipts. No new model inference was requested.

## Assessment

Cortex has implemented substantial evidence and authority machinery. Its
mathematics is strongest where a claim has an explicit executable invariant.
The main weakness is uneven enforcement: some newer experiment verifiers check
hash integrity while omitting relationships that their documentation promises.
Some bounded-context mathematics is currently an experimental module, rather
than the path that prepares native chat context.

The evolution justified by this audit is to make those contracts executable,
clarify which mathematical objects they govern, and stabilize experimental
design before buying additional model calls.

## Four mathematical objects that must remain distinct

| Object | Mathematical meaning | Implementation and scope |
|---|---|---|
| Constitutional eligibility | A conjunction over eligible evidence, authority, epoch and witness bits | `constitutional_geometry.py`, `constitutional_requirements.py`; live gates use provenance-qualified `gate_bits` |
| Epistemic support | Two independent bits: support and opposition | `epistemic_kernel.py`; the four states summarize recorded evidence, not independently established truth |
| Context sufficiency | Preserve requested support bits under a declared representation budget | Kernel compiler; does not establish equivalence of model decisions |
| Experimental effect | A contrast between matched outcomes under frozen conditions | `autonomy_differential.py`, `causal_trial.py`; a task-only success rate supplies no treatment contrast |

For eligible operation gates, an ordered set `FAIL < UNKNOWN < PASS` permits
the conservative meet:

\[
\Theta = \bigwedge_i g_i = \min_i g_i,
\qquad \text{eligible}\iff\Theta=\mathrm{PASS}.
\]

This is a statement about verified prerequisites. It is not a weighted quality
score. Epistemic support has a different structure:

\[
b(p)=(s^+(p),s^-(p))\in\{0,1\}^2.
\]

`BOTH=(1,1)` carries more evidence than `NEITHER=(0,0)`, but does not grant more
permission. Neither these bits nor spectral coupling metrics increase a model's
host-granted authority. The old four-axis cube and newer evidence gates can
coexist when their input propositions and accepted proof sources are explicit.

Within a fixed host grant, capability attenuation is a set relation:
`A_child ⊆ A_parent ∩ A_host`. It must not be confused with an unconditional
claim that all future authority can only decrease: the host can issue a new
grant. Likewise, `State = Fold(verified history)` requires the fold to validate
semantic relationships as well as event hashes.

For matched binary experiments, the relevant effect is
`(benefit_pairs - harm_pairs) / paired_cases`. A success rate from a single arm
cannot estimate that quantity. The current causal-trial module already has an
exact discordant-pair test and a power-planning surface; those should supply
new experiments instead of introducing another independent scoring convention.

## Reproduced failures and implemented corrections

### 1. Budget truncation could conceal a conflict

The old compiler appended supporting evidence before checking whether the
opposing evidence also fitted. Its `claims` field separately included all
requested claim records and all their root lists, outside its reported cost.
It also selected the first evidence row, so the representation depended on
input order.

The corrected compiler emits each claim and its required polarities together.
If a `BOTH` claim does not fit, neither side becomes guidance. It counts the
serialized `claims` and `evidence` payload, including punctuation and claim
summaries. Audit metadata is explicitly outside that named budget. Even the
empty JSON payload has a cost; a smaller budget returns `UNKNOWN`.

For each emitted claim:

\[
b_{\mathrm{projection}}(p)=b_{\mathrm{active\ history}}(p),
\qquad L(\mathrm{claims},\mathrm{evidence})\le B.
\]

One representative per present polarity is minimal in **representative count**.
The compiler does not solve a global utility-maximizing knapsack problem or
prove that a model will choose the same action. Caller claim priority remains
the selection order. Stable evidence-hash ordering resolves equivalent choices.
Reused claim IDs with different active claim text are withheld as unresolved;
this conservative guard does not solve semantic equivalence.

### 2. Time zero and retraction intervals were mishandled

`value or time.time()` replaced an explicit zero with wall-clock time. Retraction
selection ignored the retraction's valid-time interval and its claim identity.

Zero now remains a real coordinate. A retraction affects its exact event under
the same claim only during the retraction's declared valid interval. Knowledge
time still controls whether that retraction was known. Existing inclusive
interval endpoints are preserved. Stored events are not rewritten.

### 3. Invalid numbers could produce a continuation recommendation

The intended recurrence is:

\[
D_{t+1}=\max\{0,\rho D_t+\alpha U_t+\beta C_t+
\gamma\Delta_t+\eta S_t-\delta V_t\}.
\]

The old implementation accepted negative coefficients, nonfinite values and
reversed thresholds. NaN could be masked by the clamp and appear as zero debt.

The implementation now requires finite, nonnegative observations and weights,
`0 < rho <= 1`, and `0 <= reanchor < quarantine`. Booleans and overflow cannot
produce a regime recommendation. Invalid inputs return `UNKNOWN`.

With fixed valid policy, increasing uncertainty cannot decrease debt and
increasing successful verification cannot increase debt. Those are algebraic
properties. The weights' predictive value, debt calibration, stability of a
closed feedback loop, and any Lyapunov claim remain unestablished. The current
function is an advisory recurrence, not a controller with hysteresis.

### 4. Hash validity did not establish experiment identity

A focused test appended twelve independently hash-valid substitutions to an
isolated Store. Before correction, all twelve verified: altered call count,
calibration flag, next action, model identity, result kind/evidence class, case
hash, case preregistration, case kind/evidence class, case authority, and
evaluator commitment.

The verifier now checks those relationships and reconstructs the exact task
given to the native trajectory. It checks the provider identity on both the
trajectory and request, one request/response per case, zero tools, distinct
case receipts, frozen case order, evaluator commitments, and outcome
classification against the stored process observations.

\[
\mathrm{ValidExperiment}=
\mathrm{HashIntegrity}\land\mathrm{CaseBinding}\land
\mathrm{TaskBinding}\land\mathrm{ModelBinding}\land
\mathrm{EvaluatorBinding}\land\mathrm{OutcomeConsistency}.
\]

Execution also rechecks the private evaluator's hash and salted commitments
before creating the runtime and rejects grants with tools. The runtime is
limited to one iteration per case, closing an implicit multi-call path.

This verification observes host-recorded evidence. It does not rerun arbitrary
candidate code, prove host honesty, provide provider attestation, or certify
all possible semantic relationships. Hashes do not independently prove that
an OS process executed the described code.

## The screening policy explains some repeated difficulty changes

The alpha.34–39 repair rule admits a rate in `[0.30,0.70]` only when `k=2` at
`n=4`. Rates are discrete:

\[
\hat p\in\{0,1/4,1/2,3/4,1\}.
\]

As an analytical illustration, suppose four independent cases each have
success probability `p=0.5`. This is an assumed model for explaining the rule,
not an estimate of Cortex's heterogeneous task population:

| Successes | Probability under the illustration | Historical repair disposition |
|---|---:|---|
| 0 or 1 | 5/16 = 31.25% | Move easier |
| 2 | 6/16 = 37.50% | Inside window |
| 3 or 4 | 5/16 = 31.25% | Move harder |

Thus an ideally centered process would be directed away from its current level
62.5% of the time by this four-case rule. The reported `3/4` is a correct
historical policy classification; it does not demonstrate that the population
success probability exceeds 0.70. Nor can one reservation failure establish
a general concurrency weakness. That is a hypothesis requiring more cases.

The existing `information_calibration.assess_sequential_level` already offers
a better development decision: a mixed four-case panel is `screening_candidate`
and requests confirmation before classifying its difficulty. That route is not
used by `_screen` in the newer repair runner. This audit documents the
inconsistency without changing a policy after viewing its outcomes.

## Remaining gaps, prioritized

1. **Freeze one prospective sequential experiment policy.** Reuse the existing
   confirmation rule, record model configuration and task-family strata, bound
   total calls and stopping, and accumulate fresh cases at a fixed level.
   Preserve alpha.39's original score and policy. Confirmation is still
   development calibration, not a confirmatory treatment-effect trial.
2. **Test useful semantic exposure.** `native_agent` receives lessons through
   `symbiosis` and `semantic_projection`; it does not call the epistemic
   context compiler. The compiler's corrected invariants do not imply a chat
   improvement until that integration is independently evaluated.
3. **Strengthen semantic support.** `semantic_projection` verifies canonical
   field binding; `distillation_witness` primarily matches atomic public values.
   These checks do not establish arbitrary relational entailment or prerequisite
   completeness. Keep that distinction visible in UI and promotion policy.
4. **Audit host execution as a separate trust boundary.** Detached worktrees
   protect repository state; they do not by themselves sandbox candidate code
   from the host. Test adapters registered as external boundaries exercise
   mechanisms but are not empirical model experiments.
5. **Consolidate measurement implementations.** The older differentiation
   helper still returns zero spread at `n=1`; newer paired inference correctly
   reports insufficient variance information. Historical formulas need explicit
   versioned interpretation, not silent rewriting. Bootstrap output also
   expands beyond its small cognitive packet with duplicated diagnostic data;
   the operator interface should expose that detail on demand.

## Verification record

Initial counterexamples: 15 failing mathematical cases and one test exposing
12 accepted hash-valid substitutions. Corrections were then checked with the
focused mathematics, epistemic seed, structured repair, aligned repair and
information-calibration suites: **43 tests passed**. Ruff, targeted compileall,
and `git diff --check` passed. The twelve substitutions are now rejected and a
changed private evaluator is rejected before constructing any model runtime.
The full repository suite and paid inference were not run.

The preserved alpha.34, alpha.35, alpha.37 and alpha.39 receipt chains pass the
stronger verifier. Their scores remain `4/4`, `3/4`, `4/4`, `3/4` respectively.
This audit makes no new empirical capability or self-improvement claim.
