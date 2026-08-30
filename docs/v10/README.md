# Cortex v10 — Native Agent Runtime

Version target: `10.0.0-alpha.9`

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

Alpha.10 is now in development. Its first landed boundary is a short-lived,
principal-authenticated, loopback-only campaign-control session with exact
origin and CSRF binding, epoch freshness, immutable revocation, and
replay-resistant one-shot action authorization. No web mutation endpoint is
opened by this foundation.

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

Alpha.9 proves that the local interface, provider-neutral runtime path, and
host-frozen paired source comparison are
executable and auditable with deterministic provider fixtures. It does not
prove cognition, consciousness, competence improvement, autonomous authority,
safe execution of arbitrary tools, self-improvement, or live cross-provider
model quality.
