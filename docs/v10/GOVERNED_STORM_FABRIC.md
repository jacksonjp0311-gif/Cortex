# Governed Cortex Storm Fabric

Version: `10.0.0-alpha.7`

## Purpose

Cortex Storm is the first bounded multi-agent coordination layer over the
native Cortex runtime. It does not introduce a second runtime, a fixed model,
or autonomous authority. It lets the host assign several narrow tasks to
replaceable reasoning engines and reconstruct exactly what each engine
observed.

```text
operator objective
  -> host Storm grant
  -> canonical agent manifests
  -> exact child task contracts
  -> bounded parallel native-agent trajectories
  -> untrusted child observations
  -> deep trajectory verification
  -> immutable Storm summary
```

## Constitutional law

Delegation is a typed edge, not an authority diagonal. Let the host ceiling be
`G` and child grant `g_i`. Every dispatched child must satisfy:

```text
tools(g_i) ⊆ tools(agent_i) ⊆ tools(G)
budget(g_i) ≤ budget(G)
principal(g_i) = identity(agent_i)
epoch(child_i) = epoch(Storm)
continuity(child_i) = session(Storm)
```

All child grants are nondelegable. A model cannot create an `AgentManifest`,
mint a `StormGrant`, widen a child grant, or dispatch another child.

## Identity and model independence

`AgentManifest` binds an agent ID, role, purpose, permitted tool IDs, and
required public capabilities. Provider family and model ID are deliberately
absent. The exact model remains visible in the child's native trajectory as
provenance, so replacing a model changes runtime provenance without changing
the semantic agent contract.

## Observation law

Deep verification proves that a child trajectory is canonical, hash-bound,
current to the Storm epoch, and attached to the correct Storm continuity. It
does not prove the child's prose is correct.

```text
trajectory_valid = true
  does not imply
observation_true = true
```

Every `storm_agent_observation` therefore carries:

- `trusted=false`;
- `verification_required=true`;
- its task-contract, manifest, observation, and trajectory hashes;
- all authority flags closed.

Later phases may add independent synthesis and conflict evaluation. They may
not retroactively reinterpret these observations as truth.

## Budgets and cancellation

The host grant bounds agent count, concurrency, per-agent iterations, tool
calls, cumulative tool time, and total Storm wall time. Operator cancellation
and wall-budget expiry propagate into native provider/tool cancellation.
Pre-cancelled tasks never invoke a model.

## Event contract

Storm emits one hash-linked public lifecycle stream:

```text
storm.started
agent.spawned
agent.started
agent.child.event
agent.completed | agent.failed
storm.completed
```

These events are suitable for the native Cortex lattice. The renderer must
create nodes only from real events and must not invent inactive agents.

## Persistence and verification

The existing immutable symbiotic ledger stores:

1. `storm_plan` - objective, ceiling, manifests, and exact contracts;
2. `storm_agent_observation` - one typed result per child;
3. `storm_summary` - ordered observation identities and the Storm event chain.

`verify_storm_session()` reloads the ledger and verifies content hashes, Storm
grant identity, manifest/task identities, child native trajectories, body
epoch, continuity ID, observation ordering, event linkage, and authority
closure.

## Current boundary

Alpha.7 is a governed coordination substrate. It does not yet let the chat
model choose its own team, expose an autonomous Storm button, synthesize a
consensus claim, promote child results, or modify Cortex. The read-only
`/v1/storm` surface reports what the runtime can support; actual dispatch
remains a host-controlled Python boundary.

No result grants host mutation, execution authority, memory admission,
competence promotion, policy effect, cognition, consciousness, or autonomous
self-improvement.
