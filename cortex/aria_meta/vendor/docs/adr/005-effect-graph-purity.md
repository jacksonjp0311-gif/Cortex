# ADR-005: Deterministic Effect Graph and Purity Proof

## Status

Accepted for ARIA alpha.5.

## Context

ARIA has immutable typed sequences, but sequence algorithms must not execute
arbitrary functions under a false claim of purity. Purity cannot be inferred
from a function's surface name or card declaration. It must be derived from the
function body and every function reachable through its call graph.

## Decision

ARIA will use a content-addressed program effect graph.

The compiler derives direct calls, effects, and capability requirements from the
source AST. A monotone fixed-point pass computes transitive closure. Summaries
are sorted ordinally, classified as `pure` or `effectful`, marked for recursion,
and sealed with SHA-256.

The compiler stores this graph in semantic IR and bytecode. The bytecode
verifier independently reconstructs the graph from executable instructions and
requires canonical equality with the declared graph and each projected function
summary.

## Purity rule

```text
pure(function)
⇔ transitiveEffects(function) = ∅
∧ transitiveCapabilities(function) = ∅
```

Capability requirements make a function effectful even when the capability is
not exercised on every visible path. This is conservative by design.

## Cycle rule

Recursive strongly connected regions are not rejected merely for being cycles.
The finite effect and capability sets converge monotonically. Cycle membership
is recorded so later semantic contracts can impose narrower eligibility.

## Consequences

- Purity becomes evidence derived from code rather than a claim.
- Equivalent source and bytecode carry the same effect identity.
- Tampered executable metadata is independently detectable.
- Algorithm cards can require a verified function summary.
- No new runtime authority is introduced.
- The graph format becomes part of the native-core differential oracle.

## Rejected alternatives

### Trust compiler metadata without reconstruction

Rejected because a modified artifact could understate effects.

### Treat capability declarations as pure until used

Rejected because admission must conservatively account for requested authority.

### Add purity annotations first

Rejected because annotations are claims, not proofs. A future annotation may
constrain or document inferred behavior, but it cannot override the graph.

### Reject every recursive function

Rejected at this layer because recursion and purity are distinct properties.
The graph records both. Individual algorithms may later reject recursion.
