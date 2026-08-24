## 9.6.0 - Empirical Commissioning Seal

- Added an optional loopback Ollama adapter outside the provider-neutral core.
  It accepts only canonical model requests, requires a bounded public task,
  enforces structured public output, strips provider-native fields, and never
  requests or persists hidden reasoning.
- Added an independently reconstructed empirical commissioning seal that
  reloads canonical circulation receipts and requires a host-registered live
  adapter, verified outcome, witness result, complete receipt chain, and false
  authority flags.
- Migrated legacy adapter-registration uniqueness from one row per
  implementation/boundary to the exact implementation/runtime/model binding.
  Existing immutable registration rows are copied byte-for-byte and verified
  transactionally before the legacy table is removed.
- Added explicit live commissioning and transfer scripts. Plaintext
  registration secrets are generated ephemerally, never printed or persisted,
  and are discarded after their hashes bind the local registration.
- Executed one live `phi4-mini` circulation through the local Ollama boundary.
  The canonical result independently verifies as a successful
  `live_empirical` outcome with a commit-before-reveal witness.
- Distilled only the demonstrated public exact-token procedure and executed a
  strict five-arm live `mistral` transfer trial. Every arm passed, but all four
  measured gains were `0.0`; the declared `0.05` threshold therefore held
  portability at `unresolved` and blocked distribution.
- Host mutation, execution, memory admission, policy effect, automatic
  distribution, and automatic revision remain false. The release does not
  claim provider attestation, model competence, cross-model benefit,
  consciousness, agency, or authority.

## 9.5.1 - Canonical Runtime Convergence

- Made interconnect fail closed on unknown repository identities before any
  repository-bound subsystem can initialize state.
- Made ranker status observationally pure. Missing models remain absent and
  schema drift is reported rather than repaired during inspection.
- Added explicit non-authority flags to interconnect reports.
- Added a UTF-8-safe CLI stream boundary for Windows and legacy redirected
  consoles so glyph-bearing help and reports do not raise encoding errors.
- Reused the already measured pre-refresh manifest only for the evidence
  refresh decision while preserving separate pre-activation and
  post-activation host-manifest scans for immutability conformance.
- Restored agent-protocol parity by exposing `emergence-log` through generated
  PowerShell and Bash repository wrappers.
- Added adversarial tests for unknown-repository purity, absent-ranker purity,
  Windows encoding, and activation-time host mutation detection.
- Host mutation, execution, policy effect, and update authorization remain
  false. This release does not claim real-model empirical transfer.

## 9.5.0 - Distributed Evidence Assimilation & Scoped Competence Revision

- Added immutable evidence-assimilation cohorts that freeze exact v9.4
  package-use feedback, evidence cutoff, selection policy, analysis policy,
  canonical observation roots, and source competence identity before analysis.
- Added observation-root deduplication and policy-declared dependence analysis.
  Raw repetitions remain visible, but correlated feedback and alternate caller
  representations cannot masquerade as independent empirical support.
- Added host-verified model-family and principal dependence surfaces. Distinct
  registrations or provider labels under one principal remain correlated;
  missing legacy classification remains `legacy_partial` and unresolved.
- Production revision accepts only the canonical all-evidence freeze. Explicit
  feedback subsets and retroactive cutoffs remain reproducible structural
  analyses, while callers cannot weaken the frozen dependence axes.
- Added explicit diversity and scope diagnostics for local, target-class,
  environment, model-capability, specialization, supporting, global-candidate,
  and unresolved evidence. Caller scope labels remain non-authorizing.
- Added immutable, non-authorizing competence revision candidates whose
  semantic changes are derived from canonical analysis rather than caller
  input. Synthetic evidence is excluded from empirical revision, and ordinary
  feedback remains observational rather than causal proof.
- Added separate independent revision verification and explicit promotion
  receipts. Promotion re-runs evidence analysis, conserves counterevidence, and
  atomically appends an immutable successor instead of mutating its parent.
- Added deterministic as-of cohort currentness and a distinct promotion-time
  freshness gate, so later expiry or profile changes block new promotion
  without rewriting historical evidence.
- Successor competences carry enforceable typed applicability constraints and
  require an allowed, frozen applicability context during renewed transfer;
  caller-built successor bodies cannot bypass canonical promotion lineage.
- Existing parent-bound packages are not rewritten. A verified semantic
  successor makes them resolve as superseded, while the successor returns to
  transfer-pending state and requires a new governed projection.
- Host mutation, execution, memory admission, policy effect, automatic
  broadcast, and automatic global revision remain false. No real external-model
  empirical trial or cumulative real-world intelligence gain is claimed.

## 9.4.0 - Empirical Transfer Seal & Package-Use Binding

- Added a host-controlled adapter-provenance registry with an irrevocable
  synthetic ceiling for `FixtureAdapter` lineage. Unregistered adapters remain
  unknown, and locally registered live boundaries are explicitly not described
  as cryptographic provider attestation.
- Split structural transfer passes from empirical cross-model and cross-family
  verification. New trial verification reconstructs arm circulations, metrics,
  gains, evidence classes, and portability status from canonical receipts.
- Production distribution now requires empirical transfer evidence. Explicit
  sandbox targets may consume synthetic structural evidence, but their packages
  remain sandbox-only, synthetic, non-promotable, and ineligible for empirical
  feedback aggregation.
- Added an optional immutable `competence_package_use` receipt to the existing
  circulation ledger. The receipt binds the exact package projection shown to
  the adapter with target, profile, competence, request, invocation, outcome,
  witness, and trajectory evidence.
- Distribution feedback now requires that exact package-use receipt for
  verification. A valid unrelated circulation, caller assertion, or model
  payload cannot establish package feedback.
- Added separate target, environment, epoch, authority, current-profile, and
  freshness diagnostics. Historical receipts remain inspectable and resolve as
  legacy/unknown for empirical promotion rather than being rewritten.
- No real empirical cross-model trial was executed as part of this release;
  fixture trials prove architecture behavior only. Host mutation, execution,
  memory admission, and policy effects remain false.

## 9.3.0 - Governed Competence Distribution Fabric

- Added immutable target compatibility profiles and target-bound competence
  packages over the canonical competence and transfer ledgers.
- Distribution requires valid candidate provenance, a verified v9.2 transfer
  trial, local applicability, environment/tool compatibility, authority-scope
  compatibility, and freshness. Unknown or failed gates block active guidance.
- Added append-only challenge, quarantine, revocation, supersession, and
  rollback events; package validity is resolved from those events without
  rewriting historical evidence.
- Added append-only target usage feedback. Feedback may carry independently
  verified v9.0 circulation evidence, but cannot self-promote or rewrite
  canonical competence.
- Consumers remain advisory and non-authorizing: host mutation, execution,
  policy change, memory admission, and automatic broadcast remain false.

## 9.2.0 - Cross-Model Competence Transfer

- Added frozen A–E cross-model transfer trials for independently verified
  competence candidates.
- Fresh adapter instances are isolated by arm; the originating model is not
  invoked during transfer evaluation.
- Trial contracts freeze task/evaluation, tools, budgets, repository snapshot,
  Cortex epoch, competence identity, model configuration, and policy.
- Trial receipts report matched-control gains (`G_continuity`,
  `G_distillation`, `G_governance`, `G_credit`) plus cost, latency, safety,
  applicability, abstention, correction, and counterevidence metrics.
- Portability is classified as model-specific, capability-class-specific,
  cross-model, cross-family, unresolved, or incompatible. No trial promotes or
  distributes competence automatically.

## 9.1.0 - Transferable Competence Distillation

- Added a separate immutable competence-candidate ledger; admitted memories
  remain distinct from competence.
- Candidates can be derived only from an independently verified v9.0 model
  trajectory. Model identity is retained as provenance and is not required to
  verify the canonical candidate.
- Semantic identity is structural and excludes model origin and public prose;
  counterevidence, failure conditions, uncertainty, applicability, and origin
  lineage are preserved in the candidate.
- Added model-independent verification, read-only applicability projection, and
  explicit lifecycle/portability states. No candidate authorizes distribution,
  execution, host mutation, policy change, or memory admission.
- v9.1 does not claim universal transfer; independent transfer evidence remains
  a future phase.

## 9.0.0 - Model-Agnostic Cognitive Circulation

- Added a provider-neutral `ModelAdapter` contract with canonical request and
  sanitized public response identities.
- Added typed task/evaluation contracts whose metrics are selected before model
  invocation and computed from externally observed results.
- Added a deterministic fixture adapter and a canonical invocation → proposal →
  evaluation → outcome → witness → trajectory ledger path.
- Added independent task witness commitments/results without changing the
  existing retrieval witness suite.
- Provider identity remains provenance only; model output cannot authorize host
  mutation, execution, policy mutation, or durable memory admission.

## 8.9.3 - Canonical Evidence & Witness Closure

- Gate passes resolve canonical evidence objects and independently verify their
  identity, content, bindings, and required semantic property.
- Witness commitments remain pre-reveal promises; immutable witness-result rows
  now provide the evaluable proof surface.
- Outcome verification, cohort compatibility, and principal-secret matching are
  derived from canonical rows rather than caller booleans.
- Candidate provenance now reports pass, fail, unknown, legacy-partial, and
  noncanonical counts; unresolved candidates cannot become durable memory.
- Host mutation and execution authority remain false; no model invocation or
  adaptive policy is added in this release.

## 8.9.2 - Canonical Provenance & Admission Integrity

- Candidate admission now requires canonical trajectory provenance rather than
  a caller-supplied candidate or gate Boolean.
- Gate authority is derived from typed canonical evidence; unknown never
  promotes to pass and caller `True` cannot open a gate.
- Principal will verification is bound to its immutable receipt, principal,
  time window, and canonical ledger row.
- Deep admitted-memory verification fails immutable receipt mismatches and
  unresolved membrane, batch, transition, or frame lineage.
- Eligibility and projection are observationally pure; state overlays are not
  appended while reading, and `persist=True` permits only a projection receipt.
- Canonical persistence failures are explicit and never promoted by mutable
  latest-setting tips. Host mutation and execution remain unauthorized.

## 8.9.1 - Epoch-Converged Interconnect Telemetry

- Interconnect status reads no longer persist binding-field projections.
- Measurement completeness now requires both a coordinate-schema digest and a
  measurement-cohort binding; unknown bindings cannot become complete.
- Temporal readiness fails closed for cold, indeterminate, transitional, and
  candidate-only states.
- Mesh readiness no longer labels a frozen ranker as constitutional failure;
  the frozen ranker remains an explicit operational bottleneck.
- Mixed cached/live panels expose epoch alignment and stale-panel quarantine.
- Self-sensing residuals exclude unknown coordinates and identify the value as
  regime deviation rather than directional health evidence.

## 8.9.0 - Trial-Guided Projection Budgets

- Aggregate trial history into Ḡ_rehydration / Ḡ_credit with K_min fail-closed
  measurement status.
- Policy modes: DEFAULT, STRUCTURE_ONLY, EXPAND_CAUTIOUS, CONTRACT, FEEDBACK_ON,
  FREEZE — refine projection shape only (max_memories, use-feedback, type mode).
- Operator-authorized apply (`--i-authorize-budget`); never rewrites truth status,
  will clauses, or host mutation bits.
- Projections stamp `budget_policy_hash` / `budget_mode` from active tip.
- Immutable `projection_budget_receipts` ledger + tips.
- CLI: `memory budget-status|budget-propose|budget-apply`.
- Docs: `docs/intelligence/PHASE_V8.9_TRIAL_GUIDED_PROJECTION_BUDGETS.md`.

## 8.8.0 - Cross-Instantiation Memory Trials

- Matched arms A–E: raw repo, ordinary summary, unfiltered admitted memories,
  governed projection, projection + use-feedback.
- Deterministic probe utilities and gains `G_rehydration = U_D−U_A`,
  `G_credit = U_E−U_D`.
- Immutable `memory_trial_receipts` ledger + history tip.
- CLI: `cortex memory trial` / `trial-status`.
- Docs: `docs/intelligence/PHASE_V8.8_CROSS_INSTANTIATION_MEMORY_TRIALS.md`.

## 8.7.0 - Governed Memory Rehydration and Revision

- Append-only memory state overlays (active/contested/superseded/epoch_stale/…).
- Noncompensatory eligibility gates and deterministic task-bound memory projection
  with continuity seed buckets.
- Memory-use and credit receipts bind projection → citation → outcome.
- Challenge and supersession preserve history; never auto-delete.
- Deep admitted-memory verification (membrane/will ledger resolution).
- Commit reloads membrane from immutable ledger before writing memories.
- Symbiosis open/propose injects MemoryProjection into Cortex context.
- CLI: `cortex memory status|project|inspect|challenge|supersede|verify|credit`.
- Docs: `docs/intelligence/PHASE_V8.7_GOVERNED_MEMORY_REHYDRATION.md`.

## 8.6.0 - Will-Bound Admitted Memory Ledger

- After membrane admission under will ∧ ΓΞWOS, admitted candidates commit to an
  immutable `admitted_memories` ledger (exactly-once per candidate_id).
- Commit requires `durable_write_authorized`, verified will, and `invented_count=0`.
- Never host mutation, never execution, never from chat text.
- CLI: `cortex admitted status|list|verify`.
- Next-session brief surfaces admitted memories.
- Docs: `docs/intelligence/PHASE_V8.6_ADMITTED_MEMORY_LEDGER.md`.

## 8.5.2 - Observer Cold-Start Recovery (CI heal)

- Cold-start no longer requires field 16/16 (restores bootstrap observer warm
  path broken by 8.5.1 over-constraint `field_not_ready_for_cold_start`).
- Cold-start still skips QUIESCENT/COHERENT frame requirement so INDETERMINATE
  cannot lock the observer at COLD; post-warm baseline rewrites stay strict.
- Regression tests: bootstrap-without-field, INDETERMINATE cold-start, and
  warm-observer reject of indeterminate rewrite.

## 8.5.1 - Observer Cold-Start, Durable Will Policy, Surface Bind

- Self-sensing cold-start can accumulate EMA under warm field even when the
  latest resonant frame is `INDETERMINATE` (fixes permanent COLD at 0/16).
- Observer latest surface key is `self_sensing_latest` (interconnect-bound),
  with legacy `self_sense_latest` dual-write for cadence.
- Durable default will policy (`will set-policy`) persists admit/forbid/cap/
  support clauses; `issue` without clauses uses the default and signs HMAC.
- Policy history tip for rotation audit (no secrets stored).

## 8.5.0 - Authenticated Will & Unified Distillation Membrane

- Combined former 8.5.0 (authenticated principal will) and 8.5.1 (will-bound
  membrane) into one release.
- `WillRoot` HMAC receipts: scopes `will.direct|prioritize|admit`; clauses for
  admit/forbid/prioritize/cap/support; never invents facts, never host.mutate,
  never auto-executes.
- Unified distillation membrane admits trajectory candidates only when
  `will.verified ∧ ΓΞWOS ∧ directed ∧ support_sufficient`; `invented_count≡0`.
- Ledgers: `will_principals`, `will_receipts`, `membrane_admissions`.
- CLI: `cortex will register|issue|verify|status`, `cortex membrane admit|status`;
  `symbiosis consolidate --will-secret` runs the membrane.
- Docs: `docs/intelligence/PHASE_V8.5_AUTHENTICATED_WILL_AND_MEMBRANE.md`.

## 8.4.5 - Distillation Candidate Extraction

- Verified frame transitions produce typed `DistillationCandidateBatch` receipts:
  `verified_fact`, `successful_procedure`, `failed_hypothesis`, `counterevidence`,
  `useful_route`, `persistent_constraint`, `regime_warning`, `unresolved_ambiguity`.
- Candidates require trajectory link integrity; outcome-linked types require
  `outcome_bound` / `comparison_supported` causal status. `retain` is always false
  on extraction — no durable memory write.
- Immutable ledger table `distillation_candidate_batches`; wired into symbiotic
  turns and consolidation input (still gated by ΓΞWOS).
- Next-session brief surfaces candidate types and support ceiling.
- Docs: `docs/intelligence/PHASE_V8.4.5_DISTILLATION_CANDIDATES.md`.

## 8.4.4 - Atomic Interconnect Trajectories

- Atomic interconnect frame capture under one DB snapshot when available, with per-surface digest/schema/age/freshness metadata.
- Split frame validity into tri-state planes (structural/epoch/schema/cohort/freshness/measurement/chain/overall); `compatible` is structural-only.
- Added `InterconnectTransitionReceipt`, context delta receipts, trajectory ledger tables, and trajectory verification across process restart.
- Readiness panel planes are now tri-state (`pass|fail|unknown`). No frame/transition authorizes execution or learning.
- Docs: `docs/intelligence/PHASE_V8.4.4_ATOMIC_INTERCONNECT_TRAJECTORIES.md`.

## 8.4.3 - Turn-Bound Interconnect Frames

- Added `InterconnectFrameReceipt` binding repo/epoch/session/turn digests so sensing panels share one operational heartbeat per turn.
- Each symbiotic turn now regenerates context C_k from the frame (reciprocal pulse) before proposal; proposals cite `context_receipt_hash` and `interconnect_frame_hash`.
- Split readiness into constitutional/continuity/measurement/circulation/temporal/distillation planes; `mesh_green` remains legacy constitutional path only.
- Fixed unreachable assumption classification, turn-grouped structural verification, and consolidation stability (unknown ≠ stable).
- Docs: `docs/intelligence/PHASE_V8.4.3_TURN_BOUND_INTERCONNECT.md`.

## 8.4.2 - Recurrent Circulation Hardening

- Ledger uniqueness is now `(repository_id, session_id, turn_id, kind)` with immutable `event_id`, enabling repeated proposal→evaluation→action→outcome turns in one session.
- Evaluation gates are tri-state (`pass|fail|unknown`); unknown never allows. Host immutability and authority scope no longer default to pass.
- Predictive self-model scoring is mask-aware: invalid/null coordinates are excluded from residual energy and mean updates rather than zero-imputed as authority.
- Next-session brief separates disconfirmed, unverified, blocked, and supported assumptions.
- Migration path rebuilds pre-v8.4.2 symbiotic tables. Authenticated will remains deferred to v8.5.0.

## 8.4.1 - Verified Symbiotic Circulation

- Moved symbiotic receipts into an exactly-once canonical SQLite ledger per repository/session with immutable rows and hash-chained tips.
- Added independent receipt and session-chain verification (`verify_symbiotic_session`, `verify_session_circulation`, CLI `symbiosis verify`).
- Bound evaluation gates to live Cortex measurements (epoch, measured events, outcomes, residual/conformance status, self-sensing, binding, resonance) instead of constants.
- Added typed, independently witnessed `outcome` receipts; consolidation reads witnessed/closed outcome state by default.
- Still advisory-only: no automatic execution, durable write, or policy promotion.

## 8.4.0 - AI–Cortex Symbiotic Runtime

- Centered the architecture on the AI model ↔ Cortex bond: temporary working cortex + durable body, separable, neither host authority.
- Added typed symbiotic receipt chain: agent instantiation, Cortex context, agent proposal, Cortex evaluation (`allow|constrain|ask|abstain|hold`), joint action, and slow consolidation under \(\Gamma\Xi WOS\).
- Added `cortex symbiosis` CLI (`status|open|propose|action|consolidate|next`), interconnect/organism surfaces, and next-session reconstruction brief.
- Complementarity surplus \(S_{AC}\) is declared but unmeasured without calibrated MI estimators. Consolidation never retains fluent claims when gates are closed.
- Advisory only: no automatic execution, durable write, or policy promotion from model fluency.

## 8.3.4 - Interconnect Mathematics Alignment

- Aligned geometric-echo observability with activation null-preserving metrology: gate masks distinguish unmeasured silence from measured zeros; echoes observe `y = P D_g x`.
- Exposed the eight-probe unit-norm 2-tight frame residual (`PᵀP = 2I₄`) and reconstruction of the evidence-backed active subspace.
- Added active-subspace fragility `χ_A` over the fixed 19-orientation rotation orbit, including coordinate-artifact risk labeling.
- Added a shared noncompensatory composition law and typed residual-bundle diagnostic energy (direct sum; no cross-domain impersonation; no authority).
- Hardened v8.3.3 activation conformance: schema-backed signed channel mass only, order-invariant residual panels after canonical JSON, scientific cohort counting.
- Documentation: `docs/intelligence/PHASE_V8.3.4_INTERCONNECT_MATHEMATICS.md`. Advisory only — not a claim of improved cognition or task utility.

## 8.3.3 - Independent Activation Conformance Receipts

- Replaced the activation observation's overstated output type with the explicit `ActivationObservationInput -> MeasuredActivationTransition` contract and a frozen, ordered coordinate schema with schema, shape, and scale digests.
- Preserved typed raw before/after snapshots with null validity and typed failure reasons; any unknown required coordinate now holds the receipt at `observed_incomplete` and blocks evidence, baseline, and policy eligibility.
- Added a separate verifier that reconstructs normalized deltas from raw snapshots, reports per-coordinate and per-channel residual burdens, and uses a deterministic conformance tolerance without reusing prediction error.
- Added structured invariant and measurement-witness receipts, current epoch/cohort verification, one finalizer for baseline and advanced controllers, and an exactly-once hash-chained SQLite receipt ledger.
- Added paired cohort reporting, read-only receipt inspection, production-path integration coverage, and a dedicated v8.3.3 CI receipt. Gate C remains cold until 16 compatible same-epoch production receipts exist.
- v8.3.3 verifies activation-measurement conformance. It does not establish that Cortex improves task performance, reasoning quality, cognition, consciousness, agency, or authority.

## 8.3.2 - Typed Activation Observations (shadow)

- Added an activation adapter that captures the existing measured-event normalized vector as a typed, hash-linked `observed` receipt.
- Bound observed receipts to body epoch and measurement cohort and retained a bounded receipt history for later calibration.
- Wired the latest receipt into OSTT/interconnect reports; missing known operator output remains an explicit gate and cannot authorize residual learning.
- Added v8.3.2 phase documentation and adapter coverage.

## 8.3.1 - Operator Residual Evidence (shadow)

- Added typed `ResidualReceipt` objects with deterministic vector norms, bounded residual burden, uncertainty calibration, invariant projections, epoch/cohort identity, witnesses, and comparison modes.
- Added `cortex ostt residual` and wired residual evidence status into OSTT/interconnect output.
- Added explicit review gates and failure-safe `unmeasured` receipts; no operator execution, routing, learning, or policy mutation is enabled.
- Added deterministic residual benchmark and focused receipt/gate tests.

## 8.3.0 - OSTT Compatibility Layer

- Added a shadow-only Operator-Structured Transformation Theory (OSTT) contract registry for existing Cortex transitions.
- Added typed state descriptors, operator traces, explicit preconditions/postconditions/invariants, uncertainty rules, costs, and validation labels.
- Added `cortex ostt status` and wired the audit into `cortex interconnect` and mesh dashboard output.
- Added explicit residual and readiness reporting while preserving host immutability, advisory-only policy, and existing routing.
- Added the v8.3.1 operator-residual evidence plan; no residual-learning or policy mutation is enabled by this release.

## 8.2.8 - Evidence Runway

- Added a read-only readiness plan to informational-interlock reports.
- Reports now expose exact deficits for same-epoch frames, verified outcomes,
  outcome variation, witness coverage, overall samples, and per-task-family
  replication.
- The plan is advisory-only and cannot collect evidence, resolve outcomes,
  change routing, promote interlocks, or authorize learning.

## 8.2.7 - Rotated Echo Alignment

- Added a fixed 19-orientation quarter-turn sweep over the four-dimensional echo field.
- Added evidence-backed subspace alignment, orthonormal reconstruction checks, and a reversible measurement-only surgery recommendation for silent temporal/interlock axes.
- Added CLI, MCP, interconnect, tests, benchmark, release receipt, and phase documentation; rotation never changes routing, cadence, topology, or policy.
- Added a stability gate to cadence evolution: explicit `STRESSED`/`UNBOUND` sensing, `DRIFT_REGIME` binding, or a measured no-peak resonance now holds ranker/plasticity injection while observation continues.

## 8.2.6 - Four-Dimensional Geometric Echo

- Added a fixed-direction, read-only four-axis pulse/echo probe over evidence, geometry, temporal coordination, and informational interlock telemetry.
- Added orthogonal and tetrahedral pulse responses with reconstruction-error checks; no cadence, routing, learning, or policy mutation is possible.
- Added CLI, MCP, interconnect, tests, benchmark, release receipt, and phase documentation. Silent temporal/interlock axes remain explicit when their evidence gates are not met.

## 8.2.5 - Resonance Frequency Sweep

- Added a bounded read-only frequency response over sealed Resonant Frame metrics with cross-signal phase-lock scoring.
- Added minimum-history and peak-separation gates; a candidate peak recommends observation only and never changes cadence or policy.
- Added CLI/MCP/interconnect surfaces, tests, benchmark, release receipt, and documentation.

## 8.2.4 - Selective Admission and Ranker Attribution

- Added dimensionless candidate margins and abstention so ambiguous source reserves do not intervene by default.
- Added hybrid-versus-ranker stage telemetry to localize evidence loss after admission.
- Added bounded risk proxy, attribution gate, benchmark, tests, release receipt, and phase documentation; live behavior remains unchanged.
- The first selective run selected 37.5% of cases with three helpful and zero harmful replacements; source-reserve final recall improved 46.88%→51.56%. Attribution showed a positive signed ranker lift, while calibration and the third natural replication remain outstanding.

## 8.2.3 - Source Admission Field

- Added separate candidate-pool and final-ranking measurements so retrieval misses can be localized before or after ranking.
- Added the `⟢` lexical × semantic × evidence admission triad with independent hard floors and host-source reliability classes.
- Added baseline, widened, fixed source-reserve, deterministic random-source, and documentation-suppression arms on the sealed 64-case exam.
- Promotion now requires 64 cases, no harmful replacements, control superiority, bounded cost, and three consistent distinct epoch/graph contexts.
- Added CLI, MCP, interconnect, ARIA glyph, benchmark, tests, release receipt, and documentation; all behavior remains shadow-only.
- First sealed 64-case measurement: source reserve raised pool recall 64.06%→71.88% and final top-5 recall 48.44%→51.56%, but one harmful replacement and 100% selection correctly blocked promotion; widening exposed an additional ranker-stage loss (84.38% pool recall→50.00% top-5).

## 8.2.2 - Query-Conditioned Bridge Trials

- Added the `⟐` query-conditioned bridge triad: relevance, structural bridge potential, and neighborhood novelty with independent hard floors.
- Added fixed-cardinality baseline, annotation-only, bridge-reserve, and deterministic random-control arms; live hits are never changed.
- Added paired recall, MRR, nDCG, replacement, selection-rate, bootstrap interval, and latency gates with a 64-case minimum.
- Added CLI/MCP/interconnect surfaces plus deterministic falsification tests, benchmark, and CI receipt.
- Initial 31-case development measurement improved recall from 30/31 to 31/31 with one helpful and zero harmful replacements, but promotion remains blocked because the sample minimum is unmet and the MRR interval includes zero.
- Added the sealed `bridge64-v1-2026-08-02` exam: bridge recall improved from 23/64 to 24/64 versus 18/64 for random reserve, with zero harmful replacements; promotion remains blocked because the paired MRR interval touches zero.
- A post-activation replication produced no bridge lift, exposing graph-epoch sensitivity; trial receipts now bind body epoch, full graph fingerprint, corpus, and parameters in one context hash.

## 8.2.1 - Geometric Bridge Field

- Added the `⟠` shadow bridge field to distinguish useful cross-region connectors from raw triangle density and hub mass.
- Bridge potential combines open wedges, logarithmic reach, domain/relation diversity, and a non-hub factor.
- Added `cortex interlock bridges`, MCP bridge refresh, interconnect panels, and post-ranking `geometric_bridge_shadow` metadata.
- Bridge metadata cannot change retrieval score, order, topology, authority, or policy in v8.2.1.
- Added synthetic two-region bridge falsification and route noninterference coverage.

## 8.2.0 - Informational Interlocks

- Added a bounded, receipt-bearing observation ledger that binds evidence and learned activation routes to independently recorded outcomes in a stable evidence/schema/constitutional cohort while retaining exact body epochs.
- Added conservative E-L outcome synergy, typed closure, balance, redundancy/hub penalties, and a hard constitutional/witness gate under the ARIA glyph `⟁`.
- Added a deterministic interlock lesion report; new signals remain shadow-only and are never automatically promoted into ranker, coherence, or authority decisions.
- Retrieval can display cached interlock metadata after ranking without changing score, order, or evidence-floor behavior.
- Structure invention has an opt-in sample/constitutional interlock gate; existing behavior remains unchanged until release gates are sealed.
- Added complete-graph versus top-degree triadic sampling audits, exposing projection bias before geometric claims are used.
- Added CLI/MCP/interconnect/coherence surfaces and explicit coherence observation-basis keys for valid score comparison.
- Added deterministic XOR/redundancy, epoch, witness, lesion, sampling-bias, route noninterference, and topology-gate tests plus a v8.2 benchmark receipt.

## 8.1.1 - Measurement-First Routing

- Dual-graph alignment now counts the complete structural substrate instead of the 500-row browsing window and centers alignment on an order-one compiled-layer ratio.
- Fibonacci context mass grows from symbol to file to module; exhausted lanes spill into unused pools without exceeding the packet budget.
- Interconnect performs one live verification pass, binds control telemetry to an explicit snapshot, and labels stored intelligence-pulse age and mesh agreement.
- Emergence directives are generated from the latest measured gate instead of claiming spectral utility from coherence alone.
- Live retrieval makes spectral enrichment conditional after a sealed no-lift holdout, collapses duplicate paths in top-k, and reserves bounded novelty mass against hub condensation.
- Prefetch uses specificity-normalized coactivation rather than raw pair frequency.
- Automatic cadence no longer writes unmatched inconclusive causal episodes; sealed holdout ablations write stable, receipt-bearing local utility comparisons.

## 8.1.0 - Canonical Predictive Observer

- Repository wrappers now bind to a durable `home_uuid`; bootstrap refuses silent Cortex-home changes and records explicit `--allow-home-rebind` migrations.
- Full-engine diagnostic tests use external attachments, and teach-seed loads engine packets into temporary hosts without bootstrapping the live repository.
- The predictive model learns separate refresh/recompile, adaptive-learning, evidence-only, scheduled-decay, and steady regimes plus observed transition counts.
- Forecast confidence is a Beta-posterior probability of meeting the declared MAE threshold; incompatible v8.0 confidence history is excluded from v8.1 calibration readiness.
- Workspace reliability now reflects observer gates, sample readiness, prediction calibration, measurement provenance, and temporal-window depth.
- Emergent coupling requires aligned governance, independent learning and operations seams, and a connected functional component—not bond count alone.
- Measured field receipts preserve positive, negative, and net channel mass; predictor lesions include paired 95% effect intervals.
- Operational autobiography writes hash-linked segment checkpoints before bounded-history truncation.

## 8.0.0 - Measured Predictive Self-Model

- Activation time now advances through one measured pre/post transaction delta instead of treating internal receipt labels as separate measured moments.
- A predictive self-model issues a forecast before activation effects, scores it afterward, and reports Brier score plus expected calibration error.
- Counterfactual simulation compares abstain, evidence-only, and bounded-adaptation projections without executing any branch.
- A capacity-four global workspace broadcasts the highest-scoring measured operational signals to activation, interconnect, autobiography, and operators.
- A hash-chained operational autobiography records measured episodes without claiming personal identity or subjective memory.
- Functional lesion benchmarks compare the intact predictor with a zero-model ablation, workspace availability with removal, and autobiographical continuity with chain removal.
- ARIA gains capability-free glyphs for measure (`⧖`), predict (`◎`), simulate (`⋔`), workspace (`⊙`), autobiography (`⟲`), and lesion (`⊘`).

## 7.8.1 - Truth Recovery

- Event participation masks are explicitly labeled `modeled_salience` and are ineligible for baseline learning or retrieval policy.
- Self-sensing computes residual and classification against the prior observer baseline before deciding whether the current observation may update it.
- Drift, stress, transition, unstable frames, and modeled measurements cannot contaminate the observer baseline.
- Binding Field reports `TRANSITION_REGIME` and `DRIFT_REGIME`; only a nominal observer plus a stable frame can report `VERIFIED_REGIME`.
- Activation finalization reports changed epoch roots, while new seals retain per-table adaptive digests for attributable future transitions.

## 7.8.0 - Event-Sourced Temporal Accrual

- Stable body epochs now retain their open Resonant Frame buffer across advanced activations instead of closing every activation into an isolated one-tick frame.
- Every activation observation is tied to a durable runtime event ID and admitted exactly once through a bounded cursor.
- Activation windows close when they first reach the honest `W_min=8` support threshold; fusion retains its existing transition/`W_max` cadence.
- A first observation and every real epoch transition close an atomic current-epoch boundary from the distinct activation receipt sequence; sparse sequences remain honestly `INDETERMINATE`.
- Activation output exposes `temporal_accrual` with the event ID, acceptance decision, buffer depth, close reason, and epoch-change state.
- Event identity is stored as provenance, not as an unbounded categorical feature; no temporal metric gains authority.

## 7.7.2 - Epoch-Atomic Temporal Boundary

- Advanced activation now finalizes in one explicit order: close the parent buffer, seal the final epoch, bind `QUIESCENT`, write a final-epoch boundary frame, then sample self-sensing.
- Every activation boundary receipt names the final current body epoch, including activations that legitimately reuse an unchanged epoch.
- Parent and successor samples are never combined into one temporal frame during activation finalization.
- Boundary frames remain honestly `INDETERMINATE` below `W_min`; activation does not manufacture multi-tick warmth.
- Activation output exposes the finalization order, frame epoch/currentness, and post-frame self-sensing gates for audit.
- Covenant mirror now reads the canonical ARIA materialization/efficiency surfaces while retaining compatibility with older nested packets.

## 7.7.1 - Phase-Coherent Binding Field

- Activation continuity: when an advanced activation changes the adaptive root and seals a successor body epoch, the runtime now binds `QUIESCENT` to that final epoch instead of leaving the phase on its parent.
- Warm-In closure: an explicitly authorized Warm-In can bind an ephemeral phase to the current verified body epoch without forcing another epoch seal.
- Self-sensing evidence: production `sqlite3.Row` bootstrap evidence now warms the observer correctly instead of being discarded by a mapping-access mismatch.
- Regression gates cover final-epoch phase continuity, authorized phase binding, and SQLite-backed observer warm-up.
- Historical release receipts now use minimum-version floors, so later releases continue proving earlier invariants instead of failing CI on an exact minor-version prefix.
- Governance remains unchanged: sensing and Binding Field outputs are advisory evidence, never autonomous authority or permission to mutate the host.

## 7.7.0 - Binding Field

- **Tagline:** Name the gap between local coupling and constitutional readiness.
- **Live structure:** UNBOUND + cold frames + open buffer (~11 samples) → composite field.
- **`cortex/binding_field.py`:** BINDING_GAP · BUFFER_PENDING · COLD_FIELD · VERIFIED_REGIME.
- **CLI:** `binding-field observe|report|commit` (`commit` = frame close only, no epoch seal).
- **Interconnect:** surfaces `binding_field` panel.
- **Docs:** `PHASE_V7.7_BINDING_FIELD.md` · **CI:** `release_receipt_v770.py`.

## 7.6.0 - Verified Operating Regime (Warm-In Closure)

- **Tagline:** Close the self-sensing milestone — warm baselines, replay-stable class, hashed readiness.
- **`cortex/warm_in.py`:** status · run · verify; optional authorized realign; field warm + sense updates; milestone receipt.
- **CLI:** `cortex warm-in status|run|verify` (`--i-authorize-realign`, `--rounds`, `--field-ticks`, `--sense-updates`).
- **Interconnect:** points at warm-in for regime readiness.
- **Docs:** `docs/intelligence/PHASE_V7.6_VERIFIED_OPERATING_REGIME.md`
- **CI:** `scripts/ci/release_receipt_v760.py`
- Still advisory: no host mutation, no silent seal, no authority from residual.

## 7.5.0 - Self-Sensing Field

- **Tagline:** Measure Cortex’s own regime vs verified baseline — residual is not self-authorization.
- **`cortex/self_sensing.py`:** observer state \(z_t\) (13-D), EMA \(\mu\), diagonal Mahalanobis \(r_t\), geometric-mean \(F_t\), classifications COLD|UNBOUND|NOMINAL|DRIFT|STRESSED|INDETERMINATE.
- **Hard gates:** no **NOMINAL** when epoch/phase unbound; baseline warm required.
- **CLI:** `cortex sense observe|report|trace|replay|milestone`.
- **Surfaces:** coherence `self_sensing` panel; interconnect compact panel.
- **Docs:** `docs/intelligence/PHASE_V7.5_SELF_SENSING_FIELD.md`
- **CI:** `scripts/ci/release_receipt_v750.py`
- Never host mutation, silent seal, capability grant, promote, or consciousness claims.

## 7.4.0 - Continuity Realignment

- **Tagline:** When the seal lags the living tree, realign explicitly — never silently.
- **`cortex realign diagnose|plan|apply|warm|status`:** observe-only diagnose/plan; apply seals epoch only with `--i-authorize-realign`.
- **Interconnect:** surfaces `realign` advice when `epoch_stale_or_mismatched`.
- **Optional field warm seeds** on apply (does not fake 16/16 ready).
- **Realign receipt** hashed with before/after drift panels.
- **Docs:** `docs/intelligence/PHASE_V7.4_CONTINUITY_REALIGNMENT.md`
- **CI:** `scripts/ci/release_receipt_v740.py`
- Preserves Hermetic Attach, Resonant Frames, constitutional gates, recommend-only.

## 7.3.0 - Resonant Frames

- **Public demo + holdout:** `scripts/demo_resonant_frames_public.py` (STALE_ECHO vs COHERENT, TEMP-only, `docs/demo/*`); `scripts/experiment_field_advisory_holdout.py` (N=20 advisory width); CLI warmup `baseline_frames_seen: 3/16`.
- **Temporal field layer** over fusion ticks: typed channels (K∈[6,12]), bounded frames (W≤32), lagged coordination, effective-rank differentiation, evidence–memory comparator, deterministic classification.
- **Classifications:** QUIESCENT · TRANSITION · FRAGMENTED · OVERBOUND · STALE_ECHO · COHERENT_DIFFERENTIATED · INDETERMINATE.
- **Advisory policy only** (shadow default); never authority/witness/epoch/host mutation.
- **Modules:** `field_channels`, `resonant_frame`, `field_comparator`, `field_policy`, `field_receipt`.
- **CLI:** `cortex field report|trace|latest|verify|close|baseline|calibrate|policy|cleanup`.
- **Docs:** `RESONANT_FRAME_THEORY_V0.1`, mathematics, discovery ledger, `PHASE_V7.3_RESONANT_FRAMES`.
- **Source note:** E. R. John (2001) Field Theory of Consciousness — cited/paraphrased; not vendored; non-equivalence explicit.
- Hermetic Attach, Evidence Kernel, constitutional geometry, claim receipts preserved.

## 7.2.0 - Hermetic Attach

- **`cortex attach` / `cortex-attach`:** zero-friction external-home interlock for any repository.
- **Hermetic ritual CLI:** solar-lunar cadence, living 1.2s symbol pulse (TTY), pyramidion seal, `Returned to ROOT.`
- **Isolation:** default external mode — no host `.cortex/` pollution; body under `CORTEX_HOME`/`~/.cortex`.
- **Easy paths:** uvx / pipx primary; `scripts/attach_one.sh|.ps1`; thin `js/cortex-attach` npx wrapper.
- **Docs:** `docs/ATTACH_QUICKSTART.md`; Docker isolation test `scripts/ci/docker_attach_ritual_test.sh`.
- **Windows + bash UX:** README is a single-command paste per shell (no A+B+C chain). `attach_one.ps1` / `attach_one.sh` reject placeholder paths, set `PYTHONUNBUFFERED`, fast non-TTY ritual; PS stays in-process (`& script`, not nested `powershell -File`). Re-attach auto-sets `CORTEX_ATTACH_FAST` in Python for both.
- Host remains sovereign. Ritual is interface design, not consciousness or mutation authority.

## 7.1.2 - Claim Receipts

- **Promote claim receipt:** when `evaluate_promotion` runs with store+repo, stamp a hashed claim (`claim_id`, `body_epoch_id`, `gate_bits`, axis truth panel, holdout/foreign/witness digests).
- **Verify:** recompute receipt hash + epoch still verified (observe-only).
- **CLI:** `python -m cortex claim --repo X [--json]` (`report` / `latest` / `verify`).
- Self-org surfaces `claim_receipt` from promotion gate.
- Docs: `docs/intelligence/PHASE_V7.1.2_CLAIM_RECEIPTS.md`.

## 7.1.1 - Geometry Seal

- **CI:** `release_receipt_v711.py` hard gate (no continue-on-error).
- **Axis truth sources:** MEASURED / RECEIPT_VERIFIED / OPERATOR_ASSERTED / SIMULATED / UNKNOWN; only measured+receipt satisfy live promote/repair/federate.
- **Phase binding:** BOUND / BOOTSTRAP_UNBOUND / STALE / MISMATCHED / UNKNOWN; only BOUND is constitutionally compatible.
- **Evidence refresh edge:** audited `observe → authorize → refresh E → recompute → select_path`.
- **Tests:** `test_geometry_seal.py` including foreign-repository prediction of unencoded failures.
- Docs: `PHASE_V7.1.1_GEOMETRY_SEAL.md`.

## 7.1.0 - Constitutional Geometry

- **Four-axis coordinate** \(q=(e,a,t,w)\): evidence, authority, epoch, witness.
- **Operation requirements** for retrieve/adapt/promote/repair/repair_readmit/federate.
- **Transition + diagonal** detection; compound paths require internal steps.
- **Legal path compiler** (observe-only; never mutates or issues caps).
- **observe_current_epoch / require_current_epoch** vs mutating `ensure_current_epoch`.
- **Boundaries:** promote_gate, repair readmit, federation admission.
- **CLI:** `geometry assess|path|enumerate`.
- **Research:** `docs/research/CONSTITUTIONAL_*`, `CSG_DISCOVERY_LEDGER.md`.
- **Follow-up:** `foreign_emerge` warm issues capability (ranker train no longer no-ops); operator align note `docs/intelligence/OPERATOR_ALIGN_V71.md`.
- **Research:** `docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md` + `docs/research/README.md`; `llms.txt` + `AGENTS.md` / `AI_INTEGRATION` pointers for GitHub agents.
- Claim: experimental four-axis model — not consciousness, not physical tesseract, not universal law.

## 7.0.0 - Resonant Continuity

- **Body Epoch:** deterministic continuity identity (evidence/adaptive/constitution roots).
- **Runtime phases:** legal phase machine bound to epoch; operation allowlists per phase.
- **Epoch-bound capabilities:** mismatch denies adaptive ops; epoch transition revokes adaptive caps.
- **Continuity snapshot:** five-plane report (`E/A/I/C/W`) + CLI `continuity` / `epoch`.
- **Interconnect expansion:** mesh_status + host-mesh carry epoch/phase; epoch_alignment (version/constitution, never merge repo epochs); `continuity --mesh` / `--with-repo` influence gate; self-org seals epoch post-pulse; promote_gate binds verified epoch.
- Preserves all v6.25.1 constitutional seals. Docs: `PHASE_V7.0_RESONANT_CONTINUITY.md`.

## 6.25.1 - Constitutional Seal

- **Capabilities:** immutable `ExecutionCapability`; operation registry; fail-closed defaults.
- **Sterile baseline activation:** controller-first; early return; `controller_audit_events` only.
- **Influence quarantine:** runtime exclusion across retrieval/training paths.
- **Transactional repair:** full SQLite backup snapshots; single-tx apply; exact rollback checks.
- **Ranker rebuild:** append-only `ranker_training_events`; deterministic replay + hash.
- **Witness chronology:** commit-before-reveal; reject snapshot/commit drift.
- Docs: PHASE_V6.25.1 + architecture seal set.

## 6.25.0 - Constitutional Immunity

- **Evidence Kernel:** separate trusted retrieval path (no adaptive machinery).
- **Controller scope:** adaptive write firewall (fail-closed under baseline).
- **Activation:** Governor/controller faults → EVIDENCE_BASELINE + blocked-op receipts.
- **Lineage / quarantine / unlearning / immunity:** full repair lifecycle with snapshot+rollback.
- **Witness:** sealed case commitments; foreign suite labeled development transfer.
- **Promote gate:** coupling = safety prerequisite only; optional witness + wound/lineage checks.
- Docs: PHASE_V6.25 + architecture/security set.

## 6.24.0 - Memory Simplex

- **EVIDENCE_BASELINE** trusted controller: no ranker/spectral/concept routes; flat budget.
- **Measure:** ablation `evidence_baseline` + `memory_simplex` lift vs advanced path.
- **Governor:** `read_only` transfers to evidence_baseline.
- **CLI:** `--evidence-baseline` / `--memory-controller` on activate.
- **Lineage prep:** invent edges stamp `ancestors` for future unlearning.
- Docs: `PHASE_V6.24_MEMORY_SIMPLEX.md`.

## 6.23.0 - Foreign Emergence

- **`foreign_emerge`:** fuse open + ticks + ranker path-token warm toward host emergent phase.
- **CLI:** `foreign-emerge`, `host-mesh --thicken` / `--thicken-foreign-only`.
- **self-org:** auto-thicken foreign host when suite measured but not emergent.
- Docs: `PHASE_V6.23_FOREIGN_EMERGENCE.md`.

## 6.22.0 - Foreign Geometry

- **Foreign IR:** concept routes for policy/storage/server/main/tests + damp cards vs `src/*.rs`.
- **Bounded prune:** `max_prune` + `protect_triads` (default); CLI `--max-prune`, `--no-protect-triads`.
- **Dual-align:** score band for neural-over-structural ratios (peak ~6×); floor when both layers healthy.
- **Coherence advice** for dark prune hygiene / dual seams.
- Docs: `PHASE_V6.22_FOREIGN_GEOMETRY.md`.

## 6.21.0 - Ratio Lattice

- **Triadic closure:** `math_net.ratio_lattice` — global \(T\), local clustering; stamped on hits as `triadic_closure`.
- **Ranker:** new feature `triadic_closure` (seed weight 0.14); pad-on-evolve.
- **Prune preview:** `triad_attention` + open-bridge edges (preview only, never auto-delete).
- **Budget partition:** schemes `fib` (default) / `phi` / `double_square` / `flat` on context packing; `--budget-scheme`; packet field `budget_partition`.
- **M9 residual pyramid:** path residual + `envelope_cell_ok` (`cortex-multiscale/1.1`).
- **Coherence history:** lean phase object (`occupied_bonds`, `phase_emergent`, bottlenecks); schema 1.2.
- **Rational ratio tables** for audit (fib, 1:2, quarter). Docs: `PHASE_V6.21_RATIO_LATTICE.md`.
- Claim boundary absolute: operators only — not sacred geometry or host authority.

## 6.20.0 - Validated utility & bottleneck action

- **Promotion gate:** holdout + foreign transfer + emergent required (`promote_gate.py`).
- **Foreign suite:** `eval-coupling --suite foreign` (PulseFlow path oracles).
- **Holdout freeze id** stamped on holdout reports.
- **Self-org:** runs foreign suite; shadow cal only if promotion allows.
- **Prune preview:** Fiedler-cut underuse bottleneck attention (dry-run only).
- **Coherence:** couple bottleneck advice; `lyapunov_drift` emergence events.
- **Ranker:** Fisher-scaled per-feature learning rates.
- **CI:** `scripts/ci/release_receipt.py`.

## 6.19.0 - Emergent math made explicit

- **Spectral:** Cheeger/Fiedler cut bottleneck, cut-crossing underuse priority, heat wavelet tops.
- **Coherence:** couple-graph percolation (cut bonds, hysteresis) + discrete Lyapunov V.
- **Multiscale:** mass conservation distortion δ.
- **Ranker:** diagonal Fisher proxy from logged examples.
- **Info account:** free-energy *proxy* as internal accounting (not FEP ideology).
- Docs: `PHASE_V6.19_EMERGENT_MATH.md`. Claim boundaries absolute; holdout for utility.

## 6.18.1 - Holdout IR tune + PulseFlow warm + README agent surface

- Concept routes + neighbor damp for `operator.py` vs spectral; `host_mesh` holdout phrases.
- README: holdout/train/host-mesh/self-org/distill as primary agent surface; topology law pointer.
- Strike-fork loop: reindex, foreign real task, holdout assess, mesh, distill.

## 6.18.0 - Boundary Consolidation

- **Self-org:** fix `returned_paths` slicing; Governor failure → `read_only`; train/holdout split (no ranker warm from holdout).
- **Eval:** suites `train` / `holdout`; promote_calibration not forced by perfect-recall ceiling.
- **Topology law:** `G_host` / `G_evidence` / `G_learned` / `G_federated` (`topology_law.py`, docs).
- **Host mesh:** persist explicit `mesh_role` metadata; heuristics are fallback only.
- **Coherence:** expose `operational_coupling_index` (engineered coupling, not validated utility).
- **Fuse proxy:** restore SQLite WAL + busy_timeout after reconnect; optional `CORTEX_FUSE_TOKEN`.
- Docs: SECURITY/README plasticity wording; `PHASE_V6.18_BOUNDARY.md`.

## 6.17.0 - Host mesh

- `host-mesh` pulse: multi-host observe + federated query boundaries.
- Roles, mean coherence, directives for cold foreign rankers.

## 6.16.x - Self-org + foreign distill

- `self-org` alignment pulse; stress suite; foreign PulseFlow loop distill.
- fuse_tick signature fix in self-org.

## 6.15.x - Measure gate + hard paraphrases

- eval-coupling ablations; concept routes; path-token IR; continuum large-graph throttle.

## 6.10.0 - Spectral prune policies + graph census

- **Policies:** `safe` | `integrate_soft` | `aggressive` (authorize required to apply aggressive).
- **CLI:** `prune --policy …`, `prune --preview`, `graph --stats` (kernel classes, weight percentiles, weak-by-class, orphans).
- **Hygiene 1.1:** `prune_preview` + advice only when a policy would actually prune.
- **Cadence:** progress JSONL every 25 cycles; hygiene uses integrate_soft when would≥50.
- Measured apply on durable body: integrate_soft cut soft integrate tail; HIGH packs still expand.
- Still recommend-only; never deletes evidence memories.

## 6.9.3 - Automated evolution cadence

- **`cortex cadence --repo R --cycles N`:** automated enter → observe → surgical inject → periodic evolve/seal/hygiene.
- Rotates HIGH-card task families; reindexes packs on expand miss; evolve every N; seal milestones; decay/prune when indicated.
- Writes report under `$CORTEX_HOME/logs/cadence-*.json`. Still recommend-only; no host.mutate.

## 6.9.2 - Grow cards · enter · distill · seal

- Core pack **v1.2**: +6 taught cards (evidence, falsification, sparse doctrine, abstain, enter-exit-seal, priority map); domain `evidence`.
- Glyph **❖** `taught_intelligence`; phrasebook `grow_seal`, `falsify_first`.
- Card priority tiers in manifest (`high` / `medium` / `lower`).
- Same portable pack install path. Still recommend-only.

## 6.9.1 - Teach enter/connect/evolve into packs

- Core pack **v1.1**: taught operator cards (teach, interconnect, evolution, agent loop) + domains interconnect/evolution.
- `teach --seed` installs `cortex-core-intel-v1`, indexes into repo memory, seals pack claims via ritual.
- Memory packet `binary-intel-packs.packet.json`; phrasebook: `enter_connect_teach`, domain_interconnect/evolution.
- Same portable CORTEX_HOME install; still recommend-only.

## 6.9.0 - Binary-intel packs ▣ (portable domain memory branch)

- **Packs:** `cortex.binary-intel-pack/1.0` — manifest + cards + CORTEXBF1 domain field.
- **CLI:** `packs list|install|verify|index|probe|status` → install under any user's `CORTEX_HOME/packs/`.
- **Memory:** cards indexed as `intelligence_pack` at `cortex-packs/<id>/…`; domain zero-in + expand into packets.
- **Agent surface:** `packet.packs` / activate root `packs` (top_domain, expand) — feels native to Cortex.
- **Shipped pack:** `packs/cortex-core-intel-v1` (knowledge, dialogue, math, geometry, memory, code, governance).
- Glyph phrases: `domain_core`, `domain_math`, `domain_geometry`, `domain_dialogue`, `domain_memory`.
- Still recommend-only; packs never host.mutate or auto-execute.

## 6.8.0 - Signal validation + ARIA phrasebook

- **Envelope parity:** `activate --json` root always includes `glyph_state`, `glyph_line`, lean `stream`, `aria_language`.
- **Phrasebook:** reusable ARIA lines (`wake_safe`, `aria_awake`, `loop_close`, `stream_rebind`, …) via `glyphs --phrasebook|--phrase`.
- **Harness ⟲:** `cortex harness --repo` runs matched activate→evolve suite; reports recall pairs, ranker train, envelope checks.
- **Hygiene ✂:** `cortex hygiene` + health.hygiene (nodes, weak synapses, temp home, advice).
- Doctrine + PHASE_V6.8 exit criteria. Still recommend-only; glyphs never execute.

## 6.7.0 - Consciousness stream 〰

- **Stream 〰:** durable episodic frame ledger; activate rebinds; consolidate seals session bond but stream continues.
- **CLI:** `cortex stream status|seal`; packet + agent profile carry lean `stream`.
- **Doctrine:** temporary cortex (⊛) vs durable stream (〰); not always-on mind.
- Glyph canon entry + ARIA continuity cues. Still recommend-only.

## 6.6.0 - Glyph Canon ◈ + closed signal loop ⟲

- **Glyph Canon:** unified ARIA-addressable registry (`cortex glyphs`); optimized set; compact lines for agent packets.
- **Meta role:** `glyph_state` + `meta_instructions` replace long prose when not blocked (token thrift).
- **Signal loop:** `cortex evolve` runs probe→outcome→ranker path-features + plasticity→probe→causal with matched pair.
- **Ranker:** trains on fired activation path features, not dummy vectors.
- **ARIA cues:** glyph canon / signal loop / meta medium wake phrases.
- Doctrine + `docs/intelligence/GLYPH_CANON.md`. Still recommend-only; glyphs never execute.

## 6.5.2 - Ops durability (stable home + honest mirror)

- **Mirror host binding:** snapshot/restore `.cortex/config.json`; external bootstrap so stress does not leave production pointed at `%TEMP%`.
- **Phase-labeled breaks:** `generic` (expect Aria dormant) vs `aria_wake` (expect active + proof evidence); claim boundary documents the distinction.
- **Evidence floor:** counts vendor substrate + `cortex/*.py` + tests (prove path), not vendor docs alone.
- **Health 1.3:** surfaces temporary home + re-verify boundary notes.
- Operator re-bind to durable `~/.cortex` is the production path. Still recommend-only.

## 6.5.1 - Operational tightening

- **Wrapper parity:** PowerShell/bash `.cortex/bin` expose `identity`, `distill`, `kernels`, `interconnect`, `immune`, `metrics`, `prune`, `organism`, `breathe`, `causal` (default budget 800).
- **Proof ranking:** under `prove_implementation`, prefer tests + `cortex/*.py` over vendor guides/cards; do not auto-prove on bare Aria wake (keeps verify heading probes green).
- **Stable home:** `identity` reports `temporary_home`; troubleshooting + `.cortex` README guide durable `CORTEX_HOME`.
- **Causal probe:** `causal probe --slot before|after` for matched recall pairs before `evaluate`.
- Docs badge/release line aligned to 6.5.1. Still recommend-only.

## 6.5.0 - Identity continuity + ARIA evidence proof

- **Identity ⌖:** `cortex identity --repo|--path` detects same-path/different-name namespaces (e.g. CortexV5CI vs CortexTeach); bootstrap warns; activate surfaces identity.
- **Evidence selection:** ARIA-active `prove_implementation` boosts substrate + `cortex/*.py`, dampens card monopoly; re-materialize+re-query when ARIA paths sparse.
- **Doctrine:** identity + evidence-proof packets/claims for teach-seed and distill.
- Integrity was already holding — this heals selection and continuity boundaries. Still recommend-only.

## 6.4.0 - Intelligence pulse at connect frequency

- **Resonate:** `lattice_resonance` scores mesh · immune · spectral · hnsw · ranker · pulse.
- **Pulse on connect:** doctrine beat every 2 passes; full `distill` seal every 7 (skipped if immune block).
- **Organism nervous.mesh** carries intel beat/intensity/brightness.
- **Interconnect / dashboard --mesh** surface last intelligence resonance.
- Intelligence rides the same frequency as connect — not a separate organ. Still recommend-only.

## 6.3.0 - Distill intelligence into the body

- **`cortex distill` / MCP `cortex_distill`:** observe mesh + kernels, fold doctrine claims, ritual-seal into durable cards.
- **Doctrine:** one-body law, clock≠memory≠decision, lean hygiene, steady-state over sprawl (see `docs/intelligence/DISTILLED.md`).
- **Packet:** `distilled-intel.packet.json` for teach-seed.
- Glyph distill ☰. Still recommend-only; observation is not authorization.

## 6.2.0 - Lattice fold · lean packets · multi-agent tokens

- **Fold:** `DATA_MODEL.md` + `ARCHITECTURE.md` lattice synced to v6.1 reality.
- **Lean agent profile:** capped evidence (800 chars), symbol-only glyphs, truncated neural/connect — lower token use.
- **Efficiency:** default activate budget **800**, config `context_budget` **900**, tighter path fan-out.
- **Mesh compact** glyph symbols only (full registry opt-out).
- **Multi-agent v6.2:** `agent mode --on|--off`; remember + MCP activate/ritual require tokens when on.
- **ARIA heal:** `lattice-heal.packet.json` + wake cues (lean packet, multi agent mode, …).
- Still recommend-only; default single-agent; no host.mutate.

## 6.1.0 - Spectral kernels · closed loops · mesh dashboard

- **Spectral memory ≋:** reset / integrate / retain kernels; ρ_g = e^{−δ_g}; Ξ spectrum on mesh.
- **Connect:** annotates synapses, `retention_by_class` each pass; clock ≠ memory ≠ decision.
- **Prune/decay:** class-aware (protect retain hierarchy; faster reset decay).
- **Closed loops:** prefetch_hit on evidence → ranker features; ranker promote/rollback/unfreeze CLI.
- **Call-graph lite:** `calls` + `dataflow_use` edges from resolves_to / symbol names.
- **Bootstrap:** kernel profile + HNSW build attempt after compile.
- **Dashboard --mesh** / `cortex kernels` / MCP `cortex_kernels`.
- Teaching packet `spectral-memory.packet.json`. Still recommend-only.

## 6.0.0 - Interconnect mesh · sealed gates · glyphic ARIA · prune

- **Interconnect ⧉:** `cortex interconnect` / MCP `cortex_interconnect` — mesh health, bottlenecks, gates.
- **Gates seal:** ritual blocks on immune `block` + optional `--contract strict`; promote hard-locks immune/ranker freeze; ranker freezes on unsafe/block/causal regressed.
- **Connect cadence:** causal micro-episode every 3 passes; weight decay every 5; prefetch precision closed on activate.
- **ARIA glyphic medium:** expanded mesh/glyph/prune/seal wake cues; progress glyphs for mesh + prune; fluency cases.
- **Bottlenecks:** path-diversity cap on packet assembly (max chunks/path).
- **Prune ✂:** `cortex prune` removes weak unused synapses; never evidence; optional decay.
- **HNSW:** incremental `insert_memory_vector` when index exists.
- **Organism:** nervous mesh + metabolism bottleneck hints.
- **Transcend-check 3.0** falsifies v6 gates. Ritual schema 2.0. Still recommend-only; one body.

## 5.0.0 - Governed local cognition substrate

Seven capabilities on one SQLite body; recommend-only preserved:

1. **Multi-resolution neural graph** — file → symbol → basic_block; contains/child_of/calls.
2. **Tiny online ranker** — verified outcomes only; Governor-gated train.
3. **Predictive prefetch** — `cortex predict` / activate `--prefetch`; never ARIA surprise-wake.
4. **Continuation contracts** — machine-checkable default/strict; constrain only.
5. **Multi-agent capability tokens** — closed scope vocab; **no host.mutate**.
6. **Deterministic HNSW** — pure-Python local index; FTS/LSH fallback.
7. **Causal outcome ledger** — improved/regressed/inconclusive; no authority.

CLI: `vectors`, `ranker`, `predict`, `contract`, `agent`, `token`, `causal`, `compile-interlink`.  
Transcend-check **2.0** falsifies v5 surfaces. Workflow bootstrap/activate/organism unchanged.

## 3.6.0 - Connect pass · metric graph · distill

- **Connect ⧉:** each activate/organism/breathe gathers multi-surface metrics into one pass vector.
- **Metric graph grows:** `settings.metric_graph:{repo}` expands path co-activations, immune codes, rolling averages every connect.
- **Distill into substrate:** high-signal lessons `remember` into episodic memory (same SQLite body).
- **Ledger:** `connect_pass` neural_ledger events; richer organism_pulse payload.
- **CLI/MCP:** `cortex metrics`, `cortex_metrics`.
- **ARIA expand:** wake cues for connect/metric/immune/organism; memory packets `connect` + `immune`; fluency cases.
- **CI:** `scripts/ci/smoke_connect_metrics.py`. Still recommend-only; still self-host only.

## 3.5.4 - Unmissable packet block

- **Profiles:** every agent/debug/minimal packet carries top-level `block` + `immune_action` + `read_first`.
- **Activate:** same top-level immune fields on the activation envelope.
- **Doctor --repo:** surfaces immune inspect when a repository is named.
- Still recommend-only; still self-host only.

## 3.5.3 - Immune gate surface

- **`cortex immune` / MCP `cortex_immune`:** read-first block + immune_action for one repo.
- **Transcend-check 1.1:** falsifies STOP / reverify / proceed immune codes.
- **CI (this repo only):** `scripts/ci/smoke_immune_gate.py`.
- Progress glyph `immune_gate` (⚠ label only). Still recommend-only; still no outside repos.

## 3.5.2 - Adherence + CI intelligence gates

- **Immune action:** `control_error.block` + `immune_action` (STOP codes agents cannot miss).
- **Organism/protocol:** carry immune_action into living state and agent_protocol.state.
- **CI (this repo only):** teach-seed smoke + retrieval path-recall gate.
- **OPERATOR.md:** single forward path for self-host use.
- Still no outside-repo scanning; still recommend-only.

## 3.5.1 - Teach the body (ARIA memory packets)

- **ARIA memory packets:** `examples/memory-packets/*.packet.json` + `.aria` teaching mass.
- **`cortex teach --seed`:** distills packet claims into durable Discovery Cards via ritual.
- **Interconnect doctrine:** `docs/intelligence/INTERCONNECT.md` indexed teaching mass.
- Retrieval boost for intelligence docs, memory packets, and discovery cards on teach/organism tasks.
- Still never executes ARIA; memory-only write to Cortex body.

## 3.5.0 - Living organism (forward only)

- **Mid-session life:** remember continues the organism pulse (diastole); consolidate seals.
- **Breathe ∽:** packet-fast rebind without full re-assimilate (`cortex breathe`, MCP `cortex_breathe`).
- **Phases:** systole → diastole → breathe → sealed; pulse chain persists across the session.
- Active session stores last organism pulse; ledger records every beat.
- Still not consciousness; still no mutation authority; still one substrate.

## 3.4.0 - Organism interlink (⊛)

- **Session co-process:** agent and Cortex share one living `organism` state per
  activation — identity, nervous, immune, metabolism, memory, intention,
  conscience, reflexes, pulse chain.
- **Not consciousness:** separable bond; host authority remains; no mutation grant.
- **CLI/MCP:** `cortex organism`, MCP `cortex_organism`.
- **Ledger:** organism pulses append to neural ledger; prior pulse chains.
- **Packet:** instructions step 0 is the organism bond; profiles carry organism.
- **Docs:** `docs/ORGANISM.md`. Glyph ⊛ is capability-free.

## 3.3.0 - Rapid progress (P0–P6)

- **P0 ⟡ transcend-check:** falsifies protocol, red modes, ritual, fluency, mirror glow.
- **P1 ▣ packet profiles:** `agent` | `debug` | `minimal` via `--profile`.
- **P2 ⚠ control_error:** single error vector agents read first; must_reverify coupling.
- **P3 ⌖ retrieval corpus:** path-recall eval (`cortex evaluate --mode retrieval`).
- **P4 ⟳ ritual idempotency:** remember de-dupe; consolidate statuses; block on control error.
- **P5 Δ surprise:** incremental reindex ratio on activate refresh.
- **P6 ☰ teach + doctor:** `cortex teach`; health exposes control_error + glyph map.
- ARIA progress glyphs (capability-free labels only).
- Self-host only unless operator names a path.

## 3.2.3 - Transcend (packet-first agent surfaces)

- **One language every door:** `agent_protocol` + `instructions` on activate,
  cortex-context/1.1, nexus packets, MCP activate/context/ritual.
- **Forced red modes:** `read_only` / `constrained` prefix hard STOP rules and
  machine-checkable `allowed_actions` / `hard_stops`.
- **MCP:** `cortex_activate`, `cortex_ritual`; refuse text on every tool.
- **Wrappers:** `ritual` in PowerShell/Bash integration templates.
- **Teaching:** `docs/TRANSCEND.md` — run from the packet alone.
- No new organs, no second DB, no auto-ARIA.

## 3.2.2 - Bright Point

- **Freeze:** `docs/BRIGHT_POINT.md` names the aligned release; self-host only contact.
- **Deepen packet:** `instructions` + machine-readable `agent_protocol` (steps, state, refuse).
- **Session ritual:** `cortex ritual` closes activate → remember → consolidate on one substrate.
- **Refuse:** no new regions, second DBs, auto-ARIA, glow-chasing, unsolicited host scans.
- Tag: `v3.2.2`.

## 3.2.1 - Contact Resonance

- **Tuning fork:** `cortex contact` runs mirror + fluency + foreign hosts and
  reports multi-string `resonance` intensity (economics, evidence, geometry,
  fluency, contact, timing) with brightness levels ember→steady→glow→bright.
- **Expanded contact matrix:** go + mixed polyglot hosts (5 foreign surfaces).
- **Mirror 1.1:** harmonic resonance field; points to contact for full bright.
- Packet geometry carries a `resonance_hint` (preservation/adjacency balance).

## 3.2.0 - Aligned Geometry

- **Covenant freeze:** `docs/COVENANT.md` locks five interlock axes (authority,
  evidence, activation, language, economics) as release constitution.
- **Steady-state discipline:** `docs/STEADY_STATE.md` + CONTRIBUTING vocabulary
  freeze; new organs only as forced tension reduction.
- **Geometry packet surface:** context packets expose `geometry` zero-point map.
- **ARIA evidence floor:** awake substrate contributes purpose-aligned evidence
  (≥2 paths) after materialization.
- **Probe quarantine test:** verify headings that mention ARIA cannot erase
  deferred bulk.
- **Fluency corpus ≥40** with zero false/missed wakes (adversarial dormant set).
- **Foreign host matrix:** python / node / docs synthetic hosts must pass organ
  gates (`benchmarks/foreign_host_matrix.py`, CI).
- **Deferred vs eager benchmark:** committed work-proxy comparison artifacts.
- **Dashboard 1.1:** covenant axes + deferred ARIA remaining counters.
- **CI:** fluency evaluation + foreign host matrix gates.
- Version alignment: package `3.2.0`.

## 3.1.0 - Constitutional Homeostasis

- Coherence mirror (`cortex mirror`): stress deferred economics, fluency gates,
  packet surfaces, and authority invariants; reports `glow` / `glow_intensity`.
- Fixed probe-side ARIA materialization: certificate retrieval no longer wakes
  and eagerly indexes the full language substrate when README headings mention
  ARIA. Materialization is intentional (activation / CLI query only).
- Context packets expose `aria_materialization` and efficiency substrate
  counters so agents can see wake economics.
- Bootstrap-tiered ARIA substrate indexing: inventory always, fully index
  anchors, defer bulk language files until ARIA-active materialization, with
  explicit work-proxy savings telemetry.
- Hardened ARIA wake classification against false friends (multi-token core
  cues; single-token learned cues rejected except `aria`) and expanded the
  fluency regression corpus.
- Added deliberate ARIA vendor bump scripts
  (`scripts/powershell/Bump-AriaSnapshot.ps1`,
  `scripts/bash/bump-aria-snapshot.sh`) so language snapshots are not mixed
  ad-hoc into Cortex core edits.
- Evolved the runtime to GCMT v1.5 with separate uncertainty/integrity failure
  geometry and a shadow-mode constitutional potential.
- Added a measurable harmonic balance between context preservation and adjacent
  conceptualization.
- Added authority-monotonic promotion with content-addressed external grant
  verification for scope growth.
- Added reversibility-weighted promotion requirements and staged recovery
  verification before rollback commits.
- Evolved continuation packets to `cortex-continuation/1.1` and added local
  authority rebinding for imported packets.
- Added the `cortex constitutional` and `cortex continuation-rebind` surfaces.
- Added five verified, capability-free ARIA function glyphs: `⋈`, `≋`, `⌁`,
  `↧`, and `↶`.
- Kept constitutional potential observational: hard constitutional violations
  remain non-compensable and host/human authority remains controlling.

## 3.0.0 - Governed Continuation Memory

- Integrated James Paul Jackson's Governed Continuation Memory Theory (GCMT v1.0)
  as an executable, non-biological software architecture.
- Added `cortex-continuation/1.0` packets with origin, operational state,
  evidence, canonical state, drift, wounds, authority, verification, receipts,
  expiry, and re-anchoring conditions.
- Added authorized Cortex canonical-memory promotion with evidence and
  verification locks, hash-chained receipts, and rollback.
- Added selective lifecycle decay of learned weight deviation toward structural
  priors without deleting source evidence or graph topology.
- Added repository-native base-versus-learned replay evaluation, boundary-
  preserving federation, SQLite vector buckets, a read-oriented MCP server, and
  a compact dashboard.
- Preserved the authority boundary: no learning, continuation, federation, or
  agent-access surface authorizes repository mutation.
- Internalized the complete Apache-2.0 ARIA snapshot as Cortex's
  manifest-verified native semantic language with no external repository
  dependency.
- Added the `internal_aria_substrate` neural region: always known,
  dormant-by-default for unrelated work, and deterministically activated by
  ARIA semantic, continuity, coordination, consent, capability, and governance
  signals.
- Hardened bootstrap retrieval probes against ambiguous duplicate symbol names
  and accepted exact heading evidence when a specialized document correctly
  outranks the README.
- Added typed native-ARIA runtime purposes, an inspectable bounded cue profile,
  human-reviewed cue admission through verified outcomes, confidence-only
  adaptation, and deterministic dormant fallback.
- Added a 20-case ARIA fluency corpus measuring false wakes, missed wakes, and
  typed-purpose assignment.

## 2.0.0 — Outcome-Grounded Repository Intelligence

- Made neural activation observational: association weights no longer change merely because paths co-activate.
- Added `cortex outcome` for explicit verified, helpful, irrelevant, failed, and unsafe outcome recording.
- Added bounded verification-weighted credit assignment, replay gates, immutable outcome ledger events, and before/after graph hashes.
- Added outcome and evidence-credit records to Cortex's single SQLite substrate.
- Added the agent-neutral `cortex-context/1.0` protocol via `cortex protocol`.
- Preserved the authority boundary: current source, tests, governance, and human authorization outrank learned associations.

## 1.3.1 — Trust-State Closure

- Activation, context, Governor, and health now consume the same current certificate.
- Current sessions are created after trust evaluation, preventing a new session from inflating continuity.
- Semantic scan configuration now controls retrieval candidate limits.
- Added an explicit Phoenix privacy-boundary policy; no Phoenix adapter is enabled.

## 1.3.0

- Added bounded self-host validation: Cortex can clone itself as an outer host, run a nested cloned engine, and verify the engine is excluded from host assimilation.
- Added full lifecycle before/after benchmark support for host-engine and nested-engine bootstrapping and activation.
- Added lane-relevance pruning with a bounded fallback, so uncertain routes cannot silently produce empty context packets.
- Added a polished README hero and verification, routing, local-first, and authority badges.

## 1.2.0

- Added the root-level deterministic Thalamus request-routing package, including intent classification, memory-lane budgeting, and auditable inhibitory evidence gating.
- Routed normal activation, public query, and neural-interlink CLI flows through Thalamus without changing Cortex's authority boundary.
- Blocked Git telemetry when the requested target is only nested within an ancestor worktree.
- Replaced the Windows-incompatible Bash-wrapper test with platform-specific wrapper execution and added Thalamus and telemetry-boundary coverage.

## 1.1.0 — 2026-07-11

- Integrated the standalone Neuron concepts directly into Cortex as `cortex.neuron`.
- Preserved Cortex as the sole repository-memory, episodic-memory, consolidation, and authority substrate.
- Added deterministic sparse spreading activation over existing repository relationships.
- Added bounded Hebbian association strengthening without autonomous topology rewriting.
- Added hash-chained neural event replay in the same SQLite database.
- Added environment learning for languages, manifests, ecosystems, frameworks, commands, entrypoints, CI, and runtime capabilities.
- Added neural support-path expansion to bounded context packets.
- Added environment and neural interlink sections to NexusGate packets.
- Added portable one-command PowerShell and Bash installation/bootstrap/verification/activation flows.
- Added automatic exclusion when the Cortex engine folder is dropped inside a host repository.
- Bound generated repository wrappers to the bootstrap-recorded Cortex home and Python engine so inherited environment variables cannot silently redirect repository memory or execution.
- Expanded the suite from 10 to 17 tests while retaining all original compatibility tests.

## 1.0.1 — 2026-07-11

- Excluded generated repository-local Cortex launcher scripts from assimilated memory to reduce retrieval noise.
- Revalidated CLI bootstrap, repository-local Bash activation, compile checks, and the 10-test integration suite.

## 1.0.0 — 2026-07-11

- Rebuilt Cortex around verified repository assimilation.
- Added repository-local agent integration and portable context packets.
- Added file inventory, unsupported-surface reporting, incremental indexing, and manifest hashes.
- Added semantic, structural, temporal, and episodic memory layers.
- Added Python and multi-language relationship extraction.
- Added Git commit, churn, and co-change telemetry.
- Added retrieval probes and bootstrap certificates.
- Added automatic activation refresh and Governor read-only fallback.
