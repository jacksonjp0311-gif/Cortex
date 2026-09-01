# Cortex v10 — Native Agent Runtime

Version: `10.0.0-alpha.22`

Cortex v10 closes one bounded operational loop:

```text
human task
  -> verified Cortex context
  -> replaceable model adapter
  -> structured tool request
  -> host-approved tool execution
  -> untrusted tool result
  -> model continuation
  -> public final answer
  -> immutable Cortex trajectory
```

The model supplies temporary cognition. Cortex supplies durable context,
identity, evidence, ordering, and audit. The host supplies authority. None of
those roles may impersonate another.

Alpha.2 adds a loopback-only Cortex graphical interface, persistent
conversations, live OpenAI/xAI/OpenRouter model discovery, OS-vault-backed
credentials, streamed public output, and real cancellation while preserving
the alpha.1 circulation and evidence boundary. It does not add a second memory
system, autonomous memory admission, skills, delegation, cron, remote gateway
channels, or browser-control authority.

Alpha.6 closes the first governed tool-fabric boundary. Host-registered,
provider-neutral manifests define exact input/output schemas, authority class,
side effects, and cancellation behavior. Per-turn host grants are bounded by
workspace, tool set, exact command vectors, time, and call count. Each result is
an immutable, hash-bound observation—not truth, memory, or standing authority.

Alpha.7 begins governed Cortex Storm coordination. Host-declared agent
manifests and a nondelegable Storm ceiling bind bounded parallel native-agent
runs to exact task contracts. Child answers return as untrusted observations;
deep trajectory verification does not make their semantic claims true.

Alpha.8 composes Storm with isolated verification, counterfactual source
measurement, candidate tournaments, signed policy envelopes, canary rollback,
parent-generation verification, and historical improvement episodes. Autonomy
is real inside the signed envelope and nonexistent outside it.

Alpha.9 closes the canonical campaign boundary. Storm input is reconstructed
from its immutable summary, promotion reloads the persisted tournament and
trial, policies bind to a current body epoch and support immutable revocation,
and signed canaries run in an isolated candidate worktree before the active
tree is touched. The web service stays observational until Cortex has a
separately authenticated host-control protocol.

Alpha.10 closes authenticated host control, guarded execution, recoverable
integration, and the native operator interconnect. Short-lived control sessions
bind principal, exact loopback origin, CSRF proof, body epoch, action scope,
request hash, and a unique nonce. Canonical workers reverify signed policy and
Storm evidence and emit chained leases, checkpoints, and terminal receipts.
Candidate changes are committed off-tree, fast-forwarded only after a second
host action, and recoverable through a verified history-preserving revert. The
web mutation surface accepts only these authenticated operations; it grants no
standing authority to models or callers.

Alpha.11 makes those one-shot control capabilities revocable through their
entire lifetime. Spending an action rechecks its canonical parent session,
expiry, revocation, epoch, request, and unique database consumption. Campaign
reads reconstruct and verify every lifecycle edge. The canonical campaign
worker may run through a fixed subprocess entry point, with immutable launch
and exit observations that distinguish an OS process exit from campaign
success or integration authority.

Alpha.12 freezes a paired autonomy differential over the same model adapter,
source commit, evaluator, tools, capability profile, and resource budgets. A
task-only control and Cortex-governed treatment are randomized within every
case, independently evaluated, and reconstructed from canonical trajectories.
Exact matched-pairs inference and a separately reported efficiency denominator
prevent a plausible answer, raw success Boolean, or cheap synthetic contrast
from becoming empirical legitimacy.

Alpha.13 commissions that instrument through one runtime-selected live model
using a two-case/four-call pilot. The model is read from explicit operator
selection or Cortex UI settings, the external adapter boundary is canonically
registered, and the resulting panel remains underpowered by construction.

Alpha.14 closes the semantic projection seam exposed by that null result.
Canonical admitted memories now reach transient cognition as bounded public
lessons carrying their exact memory receipt, evidence roots, content hash,
projection proof, and unresolved completeness states. A noncompensatory
`Theta_P=min(V,S,A,F,C)` gate blocks unresolved identity, semantic mismatch,
irrelevance, stale state, or contradiction. Proof form and cognitive form
remain distinct; neither grants authority.

Alpha.15 adds a zero-call readiness pulse before the three-arm transfer trial.
It independently audits whether the live ledger contains modern semantic
lessons, a distinct relevant/sham pair, and canonical non-ceiling calibration.
The first pulse found six legacy-partial memories and zero modern projectable
lessons, so it spent zero model calls and narrowed the next action to generating
new verified source experience.

Alpha.16 commissions that modern source-experience path without paid inference
and seeds the epistemic kernel. Immutable bitemporal evidence events now fold
into four-valued support (`TRUE`, `FALSE`, `NEITHER`, `BOTH`), and a bounded
compiler retains the minimum representatives needed to preserve each requested
claim state and its conflicts. Authority remains a separate unresolved gate.
The structural fixture passed; empirical semantic transfer remains untested.

Alpha.17 adds a distinct independently witnessed sham lesson and seals a
three-level cache-coherence calibration corpus without its private answer key.
The preflight authorizes nothing and spends no calls. It permits a future
operator to run only a four-call task-only screen; caller success flags cannot
become calibration evidence, and a new authorization is required before any
confirmation or semantic treatment trial.

Alpha.18 executes that bounded screen through an explicitly selected,
host-registered frontier model. Four task-only level-two trajectories were
independently reconstructed and all four passed, producing a screening ceiling
rather than a calibrated task band. Cortex therefore stops after four calls,
records `move_harder`, and makes no semantic-transfer or improvement claim.

Alpha.19 binds a newly sealed level-three development panel to the canonical
alpha.18 `move_harder` receipt and repeats the same four-call task-only screen.
The selected frontier model again scored 4/4. Cortex therefore retires the
multiple-choice ladder for this model and requires an open-response,
latent-cause task forge before any semantic-treatment calls.

Alpha.20 builds that zero-call forge. Sixteen open-response cases span four
causal depths. The model must generate a cause, repair principle, exact causal
evidence IDs, and uncertainty state as public JSON. A private host-vault
contract independently checks required causal clauses, forbidden unsupported
claims, and evidence ordering. The public corpus carries commitments only.

Alpha.21 adds the bounded live executor. It retrieves the exact private
contract from the host vault, freezes four level-three task-only calls, and
reconstructs every atomic score from immutable native-agent trajectories.
Malformed public JSON remains UNKNOWN and holds the screen rather than being
silently converted to FAIL. The first run scored 0/4 under the frozen exact-
phrase evaluator, but a zero-call audit found lexical-only failures in all four
cases and strong brittleness signals in two. The raw result remains unchanged;
task difficulty and semantic correctness are both unresolved. A new
paraphrase-robust evaluator must be frozen before more calls.

Alpha.22 freezes that replacement without invoking a model. The v2 evaluator
uses host-controlled semantic atoms for causal timing, actor, stale-state
transition, and repair ordering while preserving exact evidence and response
bindings. Its deterministic positive/adversarial panel must pass before the
private v2 contract enters the OS credential vault. Historical alpha.21
responses may be inspected only in post-hoc shadow mode; their scores remain
immutable and calibration remains unresolved. Commissioning passed all 67
deterministic checks. The four historical outputs passed v2 in shadow mode,
confirming the original lexical wound without retroactively changing evidence.

## Documents

- [Architecture](ARCHITECTURE.md)
- [Hermes extraction audit](HERMES_EXTRACTION_AUDIT.md)
- [Agent protocol](AGENT_PROTOCOL.md)
- [Tool security](TOOL_SECURITY.md)
- [Governed tool fabric](GOVERNED_TOOL_FABRIC.md)
- [Governed Storm fabric](GOVERNED_STORM_FABRIC.md)
- [Governed autonomous improvement](GOVERNED_AUTONOMOUS_IMPROVEMENT.md)
- [Canonical autonomous campaign seal](CANONICAL_AUTONOMOUS_CAMPAIGN.md)
- [Authenticated campaign control](AUTHENTICATED_CAMPAIGN_CONTROL.md)
- [Revocable capability and worker seal](REVOCABLE_CAPABILITY_WORKER_SEAL.md)
- [Governed autonomy differential](GOVERNED_AUTONOMY_DIFFERENTIAL.md)
- [Live autonomy pilot](LIVE_AUTONOMY_PILOT.md)
- [Verified semantic projection and causal transfer](VERIFIED_SEMANTIC_PROJECTION.md)
- [Semantic transfer readiness pulse](SEMANTIC_TRANSFER_READINESS.md)
- [Epistemic kernel seed](EPISTEMIC_KERNEL_SEED.md)
- [Sham-controlled semantic calibration](SHAM_CONTROLLED_SEMANTIC_CALIBRATION.md)
- [Live semantic calibration screen](LIVE_SEMANTIC_CALIBRATION_SCREEN.md)
- [Harder semantic calibration screen](HARDER_SEMANTIC_CALIBRATION_SCREEN.md)
- [Open-response latent-cause forge](OPEN_RESPONSE_LATENT_CAUSE_FORGE.md)
- [Live open-response calibration screen](LIVE_OPEN_RESPONSE_CALIBRATION_SCREEN.md)
- [Semantic causal evaluator v2](SEMANTIC_CAUSAL_EVALUATOR_V2.md)
- [Governed coding workspace](GOVERNED_CODING_WORKSPACE.md)
- [Verified improvement circulation](VERIFIED_IMPROVEMENT_CIRCULATION.md)
- [Counterfactual source improvement](COUNTERFACTUAL_SOURCE_IMPROVEMENT.md)
- [Provider interface](PROVIDER_INTERFACE.md)
- [Cortex runtime bridge](CORTEX_RUNTIME_BRIDGE.md)
- [UI design language](UI_DESIGN_LANGUAGE.md)
- [Native interface plan](NATIVE_INTERFACE_PLAN.md)
- [UI architecture](UI_ARCHITECTURE.md)
- [Provider fabric](PROVIDER_FABRIC.md)
- [Secret storage](SECRET_STORAGE.md)
- [Model discovery](MODEL_DISCOVERY.md)
- [Cortex chat](CORTEX_CHAT.md)
- [Benchmark plan](BENCHMARK_PLAN.md)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)

## Claim boundary

Alpha.15 proves that the local interface, provider-neutral runtime path, and
host-frozen paired source comparison are
executable and auditable with deterministic provider fixtures. It does not
prove cognition, consciousness, competence improvement, autonomous authority,
safe execution of arbitrary tools, self-improvement, or live cross-provider
model quality. The autonomy differential is structurally verified. A live
pilot may verify paired execution, but it is not a powered or replicated
empirical autonomy-advantage result.
The semantic projection bridge is mechanically verified, while a live
three-arm relevant-versus-sham causal transfer trial remains not executed.
The readiness pulse is advisory and fail-closed; it cannot turn legacy memory
or caller-declared task families into empirical legitimacy.
