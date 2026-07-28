# Graph Execution alpha.17

ARIA graph execution is transactional, typed, capability-gated, and content-addressed.

```text
typed graph
  → pattern match
  → guard
  → capability verification
  → candidate rewrite
  → full graph validation
  → commit or rollback
  → typed event evidence
```

## Graph schema

A graph schema declares valid node types and valid edge endpoint combinations.

```text
User ─requests→ Resource
User ─access──→ Resource
```

The verifier rejects:

- unknown node types;
- unknown edge types;
- duplicate node or edge identities;
- dangling edges;
- invalid source/target type combinations.

## Patterns

Alpha.17 patterns bind one typed source node, one typed edge, and one typed target node.

```text
User(status=active) ─requests→ Resource
```

Matches are returned as explicit `source`, `edge`, and `target` bindings.

## Guards

Alpha.17 supports deterministic equality guards.

```text
source.status == active
```

Unknown guard kinds are rejected. A false guard leaves graph identity unchanged.

## Rewrite operations

The initial rewrite instruction set is intentionally narrow:

```text
remove.edge
add.edge
```

Every operation is applied to a candidate copy. The original graph is not mutated.

## Transaction and rollback

A rewrite commits only when the resulting candidate graph passes complete validation.

```text
invalid candidate
  → reject
  → discard candidate
  → preserve original graph digest
```

Rollback is structural because mutation occurs only on the candidate.

## Capability

Graph mutation requires explicit authority, such as:

```text
cap:graph.write
```

Missing capability produces `E_GRAPH_CAPABILITY`.

## Evidence

A committed rewrite emits a content-addressed event:

```json
{
  "type": "aria.graph.rewrite.committed",
  "rule": "grant_access",
  "beforeDigest": "...",
  "afterDigest": "...",
  "capabilities": ["cap:graph.write"],
  "matchedNodes": ["user:42", "resource:7"],
  "transaction": "sha256:..."
}
```

## Signal Intelligence

`Invoke-AriaGraphRewriteBuffered` routes a rewrite through Signalflow when the display module is available.

```text
graph.rewrite.grant_access
  → Bufferflow
  → transactional rewrite
  → Signalflow receipt
```

The graph result remains typed and content-addressed; the animation is an operator projection of the causal operation.