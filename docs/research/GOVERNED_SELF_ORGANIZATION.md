# Governed self-organization: observation-path audit

**Current overlay (September 7, 2026):** platform health at `b0106c7` is
PASS_WITHIN_DECLARED_MATRIX. A shadow organization kernel, mechanical recursive
closure, and bounded self-stabilization panel now exist with
`authority_effect=false` and `production_effect=false`. They do **not** unHOLD
live GSO, retention utility, or organizational heredity. See
[epistemic substrate](EPISTEMIC_SUBSTRATE_2026-09-07.md) and
[claim registry](../CORTEX_CLAIM_REGISTRY.json). The historical audit below is
unchanged.

September 6, 2026. Reconstructed local and fetched public HEAD:
`a3726be910892b79bcd74d0bb48e91d12784d5bb`, Cortex `10.0.0a39`.
The worktree was clean. This pass uses **zero model calls**. Audit artifacts bind
the baseline commit plus implementation file hashes for the added audit code.

**Disposition: HOLD at observation-path assurance.** Organization proposals,
retention cycles and fresh inference are not commissioned by this pass. These
are prerequisites, not optional precautions to skip after an exciting result.
No version promotion, new database, agent, provider, UI or autonomous authority.

## What exists and what does not

| Surface inspected | Implemented mechanism | Evidence/limitation |
|---|---|---|
| `Store.append_symbiotic_receipt`, `verify_symbiotic_receipt` | Immutable identity, session linkage, canonical reconstruction | Integrity of recorded content; not independent truth of content |
| `epistemic_instrumentation.governed_state_view` | Shared read-only epistemic interface | Specialized mapping initially covers instruments; other domain support/freshness remains UNKNOWN |
| `instrument_state`, `audit_instrument`, `verify_instrument` | Dual-support finite controls and explicit anchors | Existing controls used authored patches, not all model-intent delivery shapes |
| `structured_repair_screen` | Frozen model/tasks/evaluator, native trajectory, one-shot execution, result reconstruction | Compiler hash is recorded but not recomputed by screen reconstruction |
| `repair_calibration_cohort` | Prospective 4+4, fixed stage assignment and chronology | Exact source freshness, not semantic independence; missing candidate observations hold region selection |
| `contract_aligned_repair`, `executable_repair_forge` | Public contract/private tests, valid/broken controls, baseline/candidate evaluation | Finite host-authored judgments; not semantic completeness or OS isolation |
| `edit_intent`, `coding_workspace` | Exact replacements, deterministic diff, byte stdin, isolated worktree | New counterexamples below prevent whole-path assurance |
| `semantic_projection`, `admitted_memory` | Canonical memory admission and applicability/epoch/contradiction gates | Semantic binding is weaker than arbitrary relational entailment; native task-only arms explicitly omit lessons |
| `competence`, `competence_revision` | Candidate identity, lineage, applicability and specialized revision/promotion | A stored candidate is not measured general competence |
| `NativeAgentRuntime`, `CortexRuntimeBridge` | Context/model/tool loop and canonical trajectory | Live external inference exists historically; no new invocation here |
| `ProviderFabric`, `CapabilityGrant` | Runtime model selection, host-secret transport, scoped nondelegable tools | Provider identity is provenance, not authority or attestation |
| `autonomous_improvement.run_improvement_tournament` | Candidate selection and host-policy machinery | Reuse rather than duplicate; not an assured recursive retention experiment |
| `epistemic_kernel` | Event-derived support/opposition, bounded projection, continuation debt | Existing geometry, not proof of cumulative organizational utility |
| GSO organization prior / cycle | Proposed research interface | Not implemented or empirically established in this pass |

Historical v9/v10 experiments remain separate from current-head behavior.
Synthetic/local fixtures establish only their tested mechanism. Live task-only
repair screens do not supply a Cortex-versus-control treatment contrast.

## Actual transduction graph

```text
ProviderFabric.adapter → NativeAgentRuntime.run
        ↓ CortexRuntimeBridge.seal / native_agent_trajectory.final_answer
structured_repair_screen.execute_structured_repair_screen
        ↓ edit_intent._parse
compile_edit_intent → compilation_hash + proposal_hash + intended postimage_hashes
        ↓ proposal.patch
executable_repair_forge.evaluate_executable_patch
        ↓ coding_workspace.create_patch_proposal / source HEAD
verify_patch_in_isolated_worktree
        ↓ _git(input=patch.encode("utf-8"))
Git --check → Git apply → detached candidate
        ↓ run_host_verification_step / frozen external_test.py
candidate status + steps + postimage hashes (currently AFTER evaluator)
        ↓ evaluation_hash
Store.append_symbiotic_receipt(structured_repair_case)
        ↓ structured_repair_result
verify_structured_repair_screen → inspect_repair_cohort
        ↓ NEW inspect_repair_observation_path
bounded interpretation, NOT retention or authority
```

| Edge / representations | Identity already present | Distortion / missing assurance | Existing evidence |
|---|---|---|---|
| Request → public response → final answer | Request, response, trajectory and public-output hashes | External serving internals unobserved; no hidden reasoning retained | Historical live calls |
| JSON → typed intent | Intent hash, schema checks | Non-string fields coerced; invalid top-level shapes need stricter handling | New numeric counterexample |
| Intent → diff | Reconstructable compiler object, preimages, intended postimages | No-terminal-newline diff malformed; screen retains hashes rather than reconstructing this edge | New shape panel |
| Diff → stdin | Exact UTF-8 bytes after prior fix | Correct bytes do not prove downstream application fidelity | Existing Windows regression + new shapes |
| stdin → applied tree | Source HEAD, preimages, proposal hash, strict Git checks | No independently recorded applied-before-evaluator postimage in this path | Detached-worktree tests |
| Tree → executable test | Frozen command/contract, evaluator commitment | Candidate and evaluator share OS trust; detached worktree is not an OS sandbox | New evaluator-mutation counterexample |
| Execution → observation | Return code, duration, bounded text | Output uses text decoding with replacement, strip and 4,000-character truncation; no raw-output digest | Source inspection; binary fidelity untested |
| Observation → receipt | Canonical serialization and immutable linkage | Hash-valid incorrect observation remains possible | Historical reconstruction |
| Receipt → claim | Domain verifier, instrument challenge and cohort gates | Complete path assurance not available; no reasoning attribution from non-pass | New read-only path view |

Every evidence/interpretation object keeps authority effects false. The host
explicitly authorizes disposable audit execution; those observations do not grant
permission for production mutation, memory admission, retention or another call.

## Zero-call adversarial panel

[Machine-readable control audit](../../benchmarks/results/gso_transduction_audit_2026-09-06.json)
records **13/16 expectations met; HELD**, not a successful whole-path seal.
The [committed-source repeat](../../benchmarks/results/gso_transduction_committed_check_2026-09-06.json)
reproduced the same 13/16 at `41c6b31`. This repeats the same local controls, not
fresh independent samples. The earlier audit and its implementation hashes remain
unchanged. [Typed emergence log](GSO_EMERGENCE_LOG.json) separates observations,
interpretations and hypotheses.
Controls use exact expected source bytes and disposable Git repositories with
`core.autocrlf=false` to isolate authored bytes. The prior Windows transport test
also remains in the focused suite. This is not a cross-OS rerun.

Eight delivery controls passed: first-line import, interior replacement, final
line with newline, multi-hunk, multi-file/nested path, UTF-8, added blank lines,
and sequential replacements in one target. Repeated targets are supported only
when each successive preimage resolves exactly once.

Five negative controls remained rejected: real trailing whitespace, stale
preimage, unauthorized evaluator target, malformed patch, and deliberately
distorted candidate. The last reaches the evaluator and fails the known check;
this is a local fault injection, not independent general failure attribution.

Three unmet expectations:

1. **No terminal newline:** compilation succeeds, but its emitted diff cannot be
   parsed by Git. Either support the missing-newline marker correctly or reject
   this input explicitly at the compiler boundary. Do not silently alter bytes.
2. **Numeric edit fields:** `old=1, new=2` is coerced to strings and accepted.
   This violates strict typed-intent expectations even if the resulting code is
   valid. New parser semantics need a versioned compatibility boundary.
3. **Evaluator mutation:** a test rewrites the candidate from the intended value
   to another value, exits successfully, and isolated verification returns
   `verified`. The recorded postimage differs from the compiler's expected one.
   Before/after execution identity needs explicit nonmutation verification.

These are preserved counterexamples, **not fixes claimed completed**. They hold
GSO-2/3 and consequently GSO adaptation/retention and fresh inference. Fixing them
requires targeted versioned changes, not relaxed whitespace or evaluator rules.

## Failure attribution and historical preservation

The new `inspect_repair_observation_path` reloads a canonical structured result
and requires existing reconstruction before emitting case diagnostics. It is
read-only; it neither reruns candidates nor alters their success values.

| Evidence available | Diagnostic |
|---|---|
| Compiler error recorded | `INTENT_COMPILE_FAILURE` (parser subtype not independently known) |
| Candidate error before evaluator steps | `PRE_EVALUATION_FAILURE` |
| Executed, recorded pass | `OBSERVED_CANDIDATE_PASS` |
| Executed, recorded non-pass | `OBSERVED_NONPASS_CAUSE_UNRESOLVED` |
| Missing observations | `UNRESOLVED` |

A generic application error cannot independently distinguish transport, Git,
environment or candidate defects. The prior targeted replay localized the Windows
fault; the historical error string alone cannot do so. All reasoning-failure and
capability-inference claims remain unavailable from this view. Executed legacy
paths remain `UNRESOLVED`; missing execution makes the path `INCOMPLETE`.

[Both historical stages reconstruct](../../benchmarks/results/gso_historical_path_inspection_2026-09-06.json).
The original 3/4 + 2/4 = **5/8** stays untouched. The exhausted cohort receives no
calls. Its zero-call corrected-transport replay remains a separate interpretation
as documented in [the fixed L3 report](FIXED_L3_COHORT_2026-09-06.md). No 8/8 live
result, population estimate, calibrated frontier or transfer effect follows.

## Governed-state geometry and bounded assurance

For the claim-specific prerequisites, `FAIL < UNKNOWN < PASS`:

\[
\Theta_{claim}=\bigwedge_{g\in\{source,instrument,compiler,transport,
application,execution,observation,experiment,causality,replication\}}g.
\]

The meet is noncompensatory, not a numerical confidence average. In particular:

\[
\text{ReceiptIntegrity}\not\Rightarrow\text{PathFidelity},\qquad
\text{DeliveryFailure}\not\Rightarrow\text{ReasoningFailure}.
\]

Anchors are explicit: host-authored expected labels/bytes, current local Python
and Git, the local OS, canonical Store reconstruction. This audit does not verify
every software dependency, prove semantic completeness, or attest hardware.
Existing depth-limited instrument assurance must be extended with a separately
declared path scope; adding names to a depth count does not prove those edges.

For model-originated changes, `A_next ⊆ A_current` unless the host supplies a new
grant. An adaptation can request authority but cannot grant it. The architecture
needs no universal self object: evidence, domain views, compiler and constrained
transitions already provide the appropriate narrow interfaces.

## Staged organization design — HELD, not implemented

Reuse the Store and domain verifiers for a future organization-state view. It
should aggregate only verified/challenged roots, active instrument identities,
transport revisions, applicable lessons and unresolved debt. Missing freshness,
semantic independence, replication or authority stays UNKNOWN.

```text
PROPOSED → OBSERVED → VERIFIED → REPLICATED → RETENTION_ELIGIBLE
                                                   ↓ host approval
                                                RETAINED
                                                   ↓ explicit provenance
                                              ProposalPrior
                                                   ↓ shadow ranking only
                                            future candidate set
```

Typed proposals must bind prior state, proposer provenance, bounded delta,
measurable hypothesis, evidence, applicability, frozen experiment/instrument/path,
rollback identity and fixed budget. Initial classes should be retrieval/context
ranking only. Reject credential, authority, security, capability, scoring-rule,
network and budget changes. Candidate success cannot approve the candidate.

Selection must reuse tournament-style evidence while retaining the entire
candidate set, including rejected and held alternatives. Retention requires fresh
replication, counterevidence, scope, expiry, supersession and an existing rollback
identity. The initial shadow projection has **all five authority flags false**,
including `adaptation_authorized`. No production registry may read shadow priors.

A cycle must freeze policy, candidate family, experiment, instrument/path,
model/proposer identity, prior influence, budget and stop rule before outcomes.
Only an explicit provenance-backed prior may affect future ordering. It may not
change the evaluator, scoring, privileges or resources. Historical hash validity
and exact-source deduplication do not prove task independence; detected semantic
near-clones and unresolved dependence HOLD retention.

Homeostasis is initially a conservative rule table, not an invented scalar:
challenged instrument, distorted path, unresolved contamination, stale applicability
or budget exhaustion → HOLD; known unsafe retained influence → quarantine that
influence. Instability must never widen authority or weaken tests. Contradiction
causes review/supersession, not silent reinforcement. Roles must disclose shared
model/human origins; one proposer/labeler/selector is not independent replication.

## Order parameters and next empirical boundary

These are **definitions for future measurements**, not current scores:

| Parameter | Declared measurement | Current status |
|---|---|---|
| Recursive closure R_c | Retained structures influencing later proposals / eligible retained structures | UNKNOWN; no cycle |
| Retention utility U_r | Fresh matched utility with retention minus without | NOT EXECUTED |
| Selection precision P_s | Retained adaptations surviving fresh replication / evaluated retained adaptations | UNKNOWN |
| Transduction fidelity T_f | Faithfully delivered valid controls / exercised valid controls | 8/9 declared delivery shapes only; not whole-path reliability |
| Attribution completeness F_a | Causally localized non-successes / non-success observations | Not estimated from generic errors |
| Self-model fidelity M_f | Preregistered prediction-versus-outcome agreement | NOT EXECUTED |
| Persistence | Retained utility across restart, model replacement and repository evolution | NOT EXECUTED |

Undefined denominators are UNKNOWN, not zero. The 13/16 audit expectation count
mixes positive and negative controls and is **not** T_f or a population estimate.

Next zero-call prerequisite: strict versioned parser/EOF behavior, reconstructable
compiler→patch binding, before-evaluation expected postimage comparison, and
after-evaluation nonmutation checks. Include evaluator/infrastructure faults and
bounded raw-observation hashing; maintain intentional text previews separately.

Only after these pass should an entirely fresh prospective frontier be authored
with semantic-clone review, multiple allowed edit shapes through the complete
path, frozen costs and model configuration. Do not reuse the exhausted eight.
Then test low-authority shadow retrieval alternatives under matched resources,
followed by a separate fresh cycle with/without retained priors. Preserve the
parallel A/B/C semantic design: task-only, irrelevant sham, relevant independent
lesson; relevance gain is `U_C-U_B`, not a task-only pass rate.

Measured cumulative organization requires assured path and instruments, explicit
recursive closure, changed later behavior, positive fresh matched utility,
replication, and unchanged governance. None is inferred from architecture alone.
Consciousness, sentience, AGI and general self-improvement are not eligible claims.

## Emergence log

- **OBSERVATION:** 13/16 local expectations met; three concrete counterexamples
  remain. Historical stage receipts still reconstruct without new inference.
- **INTERPRETATION:** measurement trust must cover representation and execution
  boundaries. Valid receipts and passing exit codes are insufficient on their own.
- **HYPOTHESIS:** explicit retained operational lessons could improve later
  proposal selection. No recursive-retention utility has been measured here.

The strongest emerging engineering requirement is **artifact conservation across
measurement**, not increased autonomy. This pass intentionally stops at that gate.

## Verification receipt

Focused tests: **37 passed in 17.24s** across transduction diagnostics, patch
transport, epistemic instrumentation and the prospective cohort. These tests
verify the audit's HELD disposition and reproduce the three gaps; they do not
mean 16/16 assurance controls passed. Ruff, targeted compileall and diff checks
passed. Full repository suite, cross-platform CI and paid inference were not run.
Historical L3 files were not changed. Product version remains alpha.39.
Three manifest tests also passed in 0.09s: **40 distinct focused tests total**.
