# Cortex v10 — Native Agent Runtime

Version: `10.0.0-alpha.12`

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

Alpha.12 proves that the local interface, provider-neutral runtime path, and
host-frozen paired source comparison are
executable and auditable with deterministic provider fixtures. It does not
prove cognition, consciousness, competence improvement, autonomous authority,
safe execution of arbitrary tools, self-improvement, or live cross-provider
model quality. The new autonomy differential is structurally verified; no live
empirical autonomy advantage was executed or established in this release.
