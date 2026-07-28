# Replay and Semantic Diff alpha.18

ARIA can now verify not only that a graph transition is valid, but that its history is coherent and reproducible.

```text
initial graph
  → transition 1
  → transition 2
  → ...
  → chain head
```

Every transition is content-addressed and linked to its parent.

## Semantic graph diff

Text diff answers which lines changed. Semantic graph diff answers which graph entities changed.

```text
nodes.added
nodes.removed
nodes.modified
edges.added
edges.removed
edges.modified
```

Each diff carries the verified before and after graph digests.

## Replay transition

A transition records:

- sequence number;
- parent transition identity;
- complete guarded rule;
- granted capabilities;
- before digest;
- after digest;
- semantic graph diff;
- SHA-256 transition identity.

The transition identity is computed from every field except the identity itself.

## Chain verification

The chain verifier rejects:

- unsupported transition schemas;
- non-positive sequence numbers;
- missing parent identities;
- transition identity mismatches;
- sequence gaps;
- parent-link fractures;
- before-digest fractures.

A valid chain has one deterministic head and one deterministic final graph digest.

## Deterministic replay

Replay starts from an independently verified graph and reapplies every recorded rule under its recorded capability set.

At every transition, ARIA verifies:

```text
current digest == recorded before digest
rewrite commits
computed after digest == recorded after digest
```

Any mismatch produces replay divergence and halts without pretending the history is coherent.

## Historical state

`Get-AriaGraphStateAt` replays through a requested sequence number.

```text
sequence 0 → original graph
sequence N → graph after transition N
```

This is deterministic reconstruction, not mutable snapshots hidden outside the evidence chain.

## Operator questions

Alpha.18 makes these questions mechanically answerable:

```text
What changed?
Which graph entities changed?
Which rule caused the change?
Which capabilities authorized it?
Does the parent chain remain intact?
Can the state be reconstructed?
Does replay produce the recorded digest?
```

## Evolution invariant

A transition is evidence only when its identity, parent linkage, graph digests, semantic diff, and deterministic replay all agree.