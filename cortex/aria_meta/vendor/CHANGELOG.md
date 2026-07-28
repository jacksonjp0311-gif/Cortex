# Changelog

All notable changes to ARIA are recorded here. The compiler, language specification, and container contract are versioned independently.

## Cooperative Agent Mesh alpha.17

- Added `aria.cooperative-mesh/1` records over one shared state, distinct member artifacts, and unique provider-bridge identities.
- Required producer, independent critic, and human roles with challenge-and-reconcile coordination.
- Made material disagreement block closure and require human resolution.
- Prohibited self-approval, manufactured consensus, shared authority, and capability aggregation.
- Added `aria mesh create|verify`, a schema, examples, an ARIA plan, documentation, and an eight-gate lattice.

## Provider Bridge Membrane alpha.16

- Added `aria.provider-bridge/1` envelopes binding handoff, provider, model, operation, consent, requested capabilities, and an explicit capability ceiling.
- Deterministically rejected capability requests outside the declared ceiling.
- Kept provider transport deferred: no network call, payload, capability activation, or authority occurs in the membrane.
- Added `aria bridge create|verify`, a schema, examples, an ARIA plan, documentation, and an eight-gate lattice.

## Portable Session Handoff alpha.15

- Added `aria.session-handoff/1` artifacts for continuation between distinct AI participants.
- Limited handoff content to typed artifact references and a declared continuation boundary.
- Explicitly excluded prompts, secrets, credentials, private payloads, and unrelated history.
- Prohibited transfer of consent, capability, or authority.
- Added `aria handoff create|verify`, a schema, examples, an ARIA plan, documentation, and an eight-gate lattice.

## Deterministic Semantic Replay alpha.14

- Added `aria.semantic-replay/1` records binding handshake, baseline, intent, interpretation, proposal, consent, policy, evidence, and terminal state.
- Added causal comparison that returns coherence or the first exact drift boundary.
- Made replay verify-only and prohibited repeated external effects or authority.
- Added `aria replay create|verify`, a schema, examples, an ARIA plan, documentation, and an eight-gate lattice.
- Raised aggregate conformance across alpha.14–17 to `500/500` across twenty lattices.

## Agent Semantic Handshake alpha.13

- Added `ARIA-CONNECT.json` as a model-neutral, machine-readable connection contract with shared vocabulary, explicit completion conditions, valid commands, invariants, and a canonical read order.
- Added deterministic `aria handshake --json` discovery that binds the contract, runtime map, agent guide, manifest state, next action, and zero-authority session boundary with exact resource and record digests.
- Formalized seamless integration as `discover → orient → verify → align → propose`, keeping inference low without making authority ambient.
- Added schemas for the static connection contract and emitted handshake.
- Added an eight-gate Agent Handshake lattice and raised aggregate conformance to `468/468` across sixteen lattices.
- Updated the README, agent bootstrap, runtime discovery map, AI bridge documentation, and repository hero around the same connection identity.

## Project surface: README system makeover

- Rebuilt the repository front door around ARIA's shared human-machine semantics, verified runtime, trust model, governed evolution, operator CLI, and research path.
- Added deterministic, accessible, repository-owned hero and architecture SVGs.
- Added GitHub-native compiler, governance, and evolution diagrams with explicit evidence/authority boundaries.
- Replaced the duplicated long-form manual with a curated quick start, capability map, documentation routes, AI-agent guidance, and current verified frontier.
- Preserved alpha.12 release and conformance claims without expanding runtime or repository authority.

## Consent and Admission Receipts alpha.12

- Added content-addressed `aria.semantic-consent/1` artifacts over exact proposal, intent, scope, rollback, producer, approver, decision, and authority acknowledgements.
- Added deterministic `aria.admission-receipt/1` verdicts reconstructed from eight explicit obligations.
- Rejected self-approval, untrusted approval, proposal or scope drift, stale baselines, missing authority acknowledgement, and tampering.
- Preserved withheld consent as valid rejection evidence.
- Kept admission non-mutating and capability-free; admitted receipts stop at the existing governed evolution-planning boundary.
- Added `aria admit consent|verify`, ADR 013, an executable ARIA evolution plan, and a 24-gate lattice.
- Raised aggregate conformance to `460/460` across fifteen lattices.

## Semantic Proposal Bundles alpha.11

- Added canonical `aria.semantic-proposal/1` bundles between verified intent and governed repository mutation.
- Bound proposer, baseline, semantic subject, every language-dimension delta, exact changed paths, proof obligations, generated tests, compatibility, rollback, and optional alpha.10 receipt references.
- Made proposals explicitly unapproved, non-executable, and authority-free; rejected embedded approval and implicit authority expansion.
- Added digest, path, rollback, compatibility, evidence-reference, and tamper verification.
- Added `aria semantic propose|verify`, ADR 012, an executable ARIA evolution plan, and a 20-gate lattice.
- Raised aggregate conformance to `436/436` across fourteen lattices.

## Per-Card Execution Evidence alpha.10

- Added canonical `aria.card-execution-evidence/1` receipts for completed and fractured Map, Filter, and Reduce exercises.
- Bound each receipt to the verified card, compiler/runtime, source, semantic IR, exact artifact bytes, effect graph, policy, and admission-test contract.
- Derived outcomes from verified terminal Event Spine states instead of accepting operation-supplied success assertions.
- Embedded privacy-filtered SignalSubsets containing only terminal-event identity fields and explicit exclusions.
- Recorded bounded aggregate counts while excluding elements, mapped values, filter payloads, initial values, accumulators, output text, event data, and projections.
- Classified evidence as observational and rejected every authority or capability claim.
- Added persistent `evidence.card.execution` linkage events with exact replay and tamper rejection.
- Reverified the exact workspace Event Spine after suite-level module reloads before sealing aggregate conformance closure.
- Canonicalized materialized PowerShell 7 `DateTime` event timestamps back to exact UTC text before receipt hashing.
- Added a 20-gate Per-Card Execution Evidence lattice and raised aggregate conformance to `416/416` across thirteen lattices.

## Verified Reduce alpha.9

- Governed implementation through an executable ARIA plan plus a content-addressed intent, interpretation, human approval, independent challenge, and derived satisfied proof.
- Activated `Σ(sequence, Reducer, initial)` with exact `(A,T) → A` continuity and deterministic left-fold order.
- Added explicit independently verified `REDUCE` bytecode without adding capability or policy authority.
- Proved empty, single, cross-type accumulator, non-associative order, fracture, determinism, and full Map-Filter-Reduce composition.
- Preserved value privacy by excluding elements, initial values, and accumulators from Event Spine evidence.
- Cached the verified semantic-cue registry and removed duplicate verification of internally constructed events.
- Added exact hash-chained event batching in 32-record chunks with replay and tamper-rejection coverage.
- Reduced the persistent 256-element benchmark from about 79 seconds to about 17 seconds while retaining and replaying all 258 events.
- Added a 27-gate Verified Reduce lattice, expanded Signal Integrity to 27 gates, and raised aggregate conformance to `396/396`.

## Verified Filter alpha.8

- Activated the sealed `⫰ algorithm.filter` card as ARIA's second sequence algorithm.
- Added the exact `⫰(sequence, Predicate)` surface with compile-time predicate identity.
- Required an exact unary `T → Bool` predicate proven pure through the transitive effect graph.
- Added independently verified `FILTER` bytecode without adding a capability or policy permission.
- Preserved source order and input immutability across zero, some, all, and empty selections.
- Emitted value-free filter start, measured iteration, completion, and fracture evidence with completed and selected counts.
- Proved deterministic Map/Filter composition through explicit runtime operation boundaries.
- Added a 24-gate Verified Filter lattice and expanded aggregate conformance to `368/368`.

## Verified Map alpha.7

- Activated the sealed `⨯ algorithm.map` card as ARIA's first sequence algorithm.
- Added the exact `⨯(sequence, Transform)` surface with compile-time transform identity.
- Added independent semantic, effect-graph, bytecode, verifier, and VM contracts for unary pure transforms.
- Added the pure `MAP` opcode without adding a capability or policy permission.
- Preserved sequence order, cardinality, scalar element types, deterministic execution, and existing resource ceilings.
- Emitted value-free map start, measured iteration, completion, and fracture evidence through Event Spine v3.
- Replaced repeated full-ledger append parsing with validated ledger-byte identity and locked tail verification.
- Added a 22-gate Verified Map lattice and expanded aggregate conformance to `344/344`.

## Integration Closure alpha.5.1

- Extended the deterministic effect graph with a reserved `$entry` node covering the executable entry flow.
- Propagated entry calls, effects, and capability requirements through the same fixed-point closure used by functions.
- Preserved independent source/bytecode reconstruction so resealed false entry summaries are rejected.
- Added artifact-derived `aria.intent-program-summary/1.0` records bound to verified container and effect-graph identities.
- Made `aria test` execute all seven established lattices as one 276-gate command.
- Removed duplicate dedicated-suite invocations from CI while preserving the same coverage on all supported hosts.
- Synchronized runtime discovery, README status, operator version output, documentation, and the integration plan.
- Added no opcode, policy effect, capability permission, or algorithm activation.

## Intent Verification alpha.25

- Added canonical, content-addressed intent, interpretation, approval, challenge, program-summary, evidence, and proof artifacts.
- Added `aria intent verify <bundle.json>` with persistent satisfied or rejected proof records.
- Derived required outcomes, forbidden outcomes, effect ceilings, and acceptance-evidence obligations without accepting a model-supplied satisfaction assertion.
- Required exact human approval of the intent and interpretation identities.
- Gated material ambiguity and independent-critic disagreement on explicit human resolutions.
- Rejected self-challenge, omitted obligations, excess authority, tampered identities, and evidence bound to another program.
- Added eight JSON schemas, a complete release example, architecture documentation, and thirteen adversarial gates.
- Expanded conformance to 192 deterministic gates.

## Evolution Verification alpha.24

- Added `aria evolve verify <proposal-id>` as a non-mutating authorization command.
- Reloaded and re-verified every persisted plan, proposal, and snapshot identity.
- Rejected current-commit and affected-workspace drift.
- Resolved root and delegated capability bundles against explicit issuer trust.
- Required separate human authorization from an explicitly trusted authorizer.
- Appended authorization, authority-decision, governed-event, and verification records without rewriting the plan.
- Added three verification schemas and ten authorization-focused gates.
- Expanded conformance to 179 deterministic gates.

## Evolution Planning alpha.23

- Added `aria evolve plan <request.json>` as a non-mutating planning command.
- Bound requested changes to exact Git and file-content identities.
- Persisted request, proposal, original/candidate snapshots, and plan records under `.aria/evolution/`.
- Required semantic diff and executable rollback proof before recording a plan.
- Kept every generated plan in `awaiting-authorization` state.
- Added request and plan-record schemas plus ten rejection-focused gates.
- Expanded conformance to 169 deterministic gates.

## Source Core alpha.22

- Closed ordinary source types to `Int`, `Text`, and `Bool`.
- Rejected direct and mutual recursion before evaluation.
- Defined `Int` as a checked signed 64-bit value with structured overflow and division-by-zero failures.
- Preserved source line and column coordinates through the AST and structured diagnostics.
- Distinguished parse, type, and runtime rejection codes.
- Expanded conformance to 159 deterministic gates.

## 0.1.0-alpha.5 — Connectflow

- Advanced the language lock to specification `0.4.0`.
- Added first-class connection declarations with operator, agent, and protocol identities.
- Added `connect`, `intent`, `propose`, `consent`, and `disconnect` statements.
- Added five verified connection opcodes and VM lifecycle enforcement.
- Added deterministic connection events and the `aria connect` CLI command.
- Added `REJECT` as a successful operator outcome for withheld consent or expected denial.
- Fixed quiet compiler gates so negative conformance probes do not render as failed tests.
- Expanded conformance to 42 deterministic gates.

## 0.1.0-alpha.4 — Coreflow

- Advanced the language lock to specification `0.3.0`.
- Added scalar types, inferred and explicit bindings, assignment, and typed memory fields.
- Added host-independent expression parsing with arithmetic, comparison, Boolean, unary, and call expressions.
- Added typed functions, local frames, returns, lexical `if/else`, and bounded `repeat`.
- Added module identity metadata and deterministic agent-dispatch events.
- Expanded the opcode registry to 32 instructions and added structured control bytecode.
- Hardened the verifier against arithmetic type confusion, invalid call contracts, non-text agent tasks, and malformed structured sequences.
- Revalidated function returns and persisted memory types in the VM.
- Added Coreflow examples, algorithms, cross-domain discoveries, ADR 0005, and 34 conformance gates.

## 0.1.0-alpha.3 — Traceflow

- Added `signal pulse|pass|warn|fail|info` as a language primitive.
- Added verified `SIGNAL` bytecode and structured VM events.
- Added descending tree rendering, `trace`, `graph`, and related CLI aliases.
- Advanced the language specification to `0.2.0` and expanded conformance to 23 gates.

## 0.1.0-alpha.2 — Operator renderer

- Added the ARIA diamond operator renderer with ANSI-aware colors and pulsing active glyphs.
- Styled doctor, gate, compile, run, test, install, manifest, and verification workflows.
- Added concise normal output and `-VerboseOutput` / `ARIA_VERBOSE=1` diagnostics.
- Suppressed PowerShell unapproved-verb import warnings at the CLI boundary.
- Fixed Windows PowerShell 5.1 UTF-8 glyph parsing, blank-line lexing, scalar array unrolling, and path-comparison compatibility.

## 0.1.0-alpha.1 — Bootstrap

- Added the Windows PowerShell 5.1-compatible compiler and virtual machine.
- Added validated glyph aliases and semantic graph metadata.
- Added deterministic gzip-compressed `.ariac` containers with SHA-256 integrity.
- Added explicit durable memory outside compiled artifacts.
- Added deny-by-default capability policy and repository-confined file access.
- Added compiler/spec/container locks, hostile-bytecode verification, repository manifests, schemas, examples, and research documentation.
