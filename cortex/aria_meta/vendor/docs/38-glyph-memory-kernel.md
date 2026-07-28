# Glyph Memory Kernel alpha.1

## Intent

ARIA is evolving from a glyphic execution surface into a governed
meta-composition system. The transition must preserve the existing law:

> A symbol may express an operation, but it does not grant execution authority.

The Glyph Memory Kernel introduces a canonical memory card for each new glyph.
Cards are content-addressed, typed, classified by purity and effect, bound to a
lowering target, and admitted through verification.

## Alignment boundary

This phase does not add new VM opcodes or claim that the sequence algorithms
already execute. It establishes the verified substrate first.

Two function cards are marked `verified` because they lower to the existing
`CALL` and `RETURN` machinery:

- `▷` — `function.invoke`
- `↩` — `function.return`

At the alpha.1 milestone, four cards were marked `specified` and could not
activate until their compiler and runtime implementations gained dedicated
gates:

- `≫` — `composition.pipe`
- `⨯` — `algorithm.map`
- `⫰` — `algorithm.filter`
- `Σ` — `algorithm.reduce`

## Card contract

Each `aria.glyph-card/1` record declares:

- stable identity and one collision-free symbol;
- spoken and semantic meaning;
- family, category, fixity, and arity;
- typed inputs and output;
- purity, determinism, effects, and capabilities;
- canonical lowering kind and target;
- lifecycle status;
- required test claims;
- SHA-256 identity.

The registry also reserves every symbol already used by ARIA. Existing
collisions are recorded as legacy semantic roots rather than silently
reassigned. New cards are rejected when they reuse a reserved symbol.

## Activation memory

A verified card may produce an `aria.glyph-activation/1` receipt only when:

1. the card identity verifies;
2. the card status is `verified`;
3. policy returns `allow`;
4. at least one test passed;
5. no test failed.

Activation receipts are appended to:

```text
.aria/memory/glyph-memory.ndjson
```

The ledger is local runtime state, not language authority. Every record is
content-addressed and reverified during replay.

## Intent contract

`plans/glyph-memory-kernel-alpha1.aria` binds the human intent, bounded
proposal, explicit consent, and deterministic closure used by this evolution.

## CLI surface

```powershell
.\aria.cmd glyph list
.\aria.cmd glyph verify function.invoke
.\aria.cmd glyph activate function.invoke
.\aria.cmd glyph memory
```

`glyph activate` admits a verified card into local operator memory. It does not
issue capabilities, expand policy, modify source, or execute a candidate
algorithm.

## Next bounded evolution

After this kernel is remotely attested:

1. lower `▷` and `↩` from glyph source into existing function operations;
2. add typed composition IR for `≫`;
3. implement `map`, `filter`, and `reduce` as verified pure primitives;
4. record execution evidence per card through Event Spine and SignalSubset;
5. allow the AI to propose card compositions without granting it authority to
   approve or merge them.
