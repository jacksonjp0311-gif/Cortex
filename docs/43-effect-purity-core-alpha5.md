# Effect Graph & Purity Core alpha.5

ARIA alpha.5 connects function bodies, call topology, capability requirements,
semantic IR, bytecode metadata, independent verification, VM admission, glyph
proof obligations, and the operator surface through one deterministic effect
graph.

## Contract

```text
function body
→ direct effects and capability requirements
→ direct call edges
→ transitive fixed-point closure
→ sealed function purity summary
→ sealed program effect graph
→ semantic IR and bytecode projection
→ independent derivation by the verifier
→ VM admission
```

Each function receives an `aria.function-effect-summary` containing:

- direct calls;
- direct effects;
- direct capability requirements;
- transitive effects;
- transitive capability requirements;
- `pure` or `effectful` classification;
- recursive-cycle membership;
- a SHA-256 identity.

The program receives an `aria.effect-graph` containing all summaries in ordinal
function-name order and a graph digest.

Integration Closure alpha.5.1 adds the reserved `$entry` summary to this graph.
It is derived from the executable entry flow and participates in transitive call
closure, so the operator view now represents whole-program effects rather than
named functions alone. This advances `aria.effect-graph` to version 2; function
summary records remain version 1.

## Effect roots

The alpha.5 analyzer recognizes the established runtime effects:

| Source operations | Effect |
|---|---|
| `emit`, `signal`, connection protocol operations | `console.emit` |
| `remember` | `memory.write` |
| `recall` | `memory.read` |
| `read` | `fs.read` |
| `write` | `fs.write` |
| `dispatch` | `agent.dispatch` |

`require` contributes a capability requirement. A function is pure only when
its complete transitive effect and capability sets are both empty.

## Recursive cycles

Cycles are handled through a monotone fixed-point closure. Effects and
capabilities only accumulate from known callees, so the closure converges within
a deterministic function-count bound. Every function that can reach itself is
marked `recursive`.

Recursion does not gain new authority. A later algorithm admission may impose a
stricter non-recursive requirement without changing this graph.

## Independent verification

The compiler projects the source-derived graph into bytecode. The bytecode
verifier then reconstructs a second graph from executable instructions and
rejects:

- invalid summary or graph digests;
- unsorted or duplicate semantic sets;
- unknown call edges;
- a graph that does not match executable instructions;
- a function summary that differs from the sealed graph.

The VM executes only after this verification succeeds and exposes the admitted
graph in its result metadata.

## Operator surface

```powershell
./aria.ps1 effects ./examples/effect-purity.aria
./aria.ps1 effects ./path/to/program.ariac
```

The default view is bounded: purity, recursion, calls, effects, and capability
requirements. Raw artifacts remain available through established inspection and
verbose paths.

## Algorithm boundary

`algorithm.map`, `algorithm.filter`, and `algorithm.reduce` remain `specified`.
Their card tests now explicitly require deterministic effect-graph proof for the
transform, predicate, or reducer function. No algorithm executes in alpha.5.

## Authority statement

Alpha.5 adds:

- no opcode;
- no source syntax;
- no policy effect;
- no capability permission;
- no ambient function value;
- no closure capture;
- no algorithm activation.

The graph describes existing authority dependencies. It does not grant them.

## Exit lattice

The dedicated lattice verifies direct and transitive effects, direct and
transitive capability requirements, pure and effectful call chains,
deterministic ordering and identity, recursive-cycle convergence, source and
bytecode parity, verifier tamper rejection, VM admission, glyph proof binding,
and zero authority expansion.

After remote attestation, alpha.6 may implement and verify `⨯ algorithm.map`
against this purity substrate.
