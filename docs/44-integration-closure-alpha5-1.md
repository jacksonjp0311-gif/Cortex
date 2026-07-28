# Integration Closure alpha.5.1

## Intent

Close the boundaries between whole-program effects, intent authority,
conformance, release discovery, and operator truth before activating an
algorithm glyph.

## Whole-program effect graph

The effect graph now contains a reserved `$entry` node derived from the
executable entry flow. It participates in the same direct-call analysis and
transitive fixed-point closure as named functions. The graph format advances to
version 2 so consumers cannot silently apply function-only version 1 semantics.

```text
entry source statements
→ direct calls, effects, and capabilities
→ transitive function closure
→ sealed $entry summary
→ bytecode projection
→ independent bytecode reconstruction
→ VM admission
```

`$entry` cannot be authored as an identifier, so it cannot collide with a
source function. A program that emits or writes memory can no longer present an
empty operator effect view.

## Artifact-derived intent authority

`New-AriaIntentProgramSummaryFromArtifact` consumes container bytes, verifies
their integrity and bytecode, validates the admitted effect graph, then derives:

- the exact container SHA-256 identity;
- the exact effect-graph identity;
- the union of requested transitive effects;
- a content-addressed `aria.intent-program-summary/1.0`.

This closes the self-reported authority gap. Outcomes and external evidence are
still supplied separately and remain part of the explicit trust boundary.

## Unified conformance

`aria test` is now the complete local admission command:

| Lattice | Gates |
|---|---:|
| Core conformance | 202 |
| Glyph memory | 8 |
| Glyph lowering | 12 |
| Typed composition | 15 |
| Sequence core | 15 |
| Effect and purity | 18 |
| Integration closure | 6 |
| **Total** | **276** |

CI calls this same aggregate command on PowerShell 7 for Windows and Linux and
on Windows PowerShell 5.1.

## Authority boundary

Alpha.5.1 adds no opcode, source authority, policy effect, capability,
algorithm implementation, or glyph activation. `map`, `filter`, and `reduce`
remain specified and inactive.

## Next bounded evolution

Verified Map (renumbered alpha.7 after Semantic Projection Core alpha.6) may consume:

- bounded immutable `Sequence<T>`;
- a verified transform-function summary;
- a complete entry and function effect graph;
- artifact-derived intent authority;
- one aggregate local and remote admission command.
