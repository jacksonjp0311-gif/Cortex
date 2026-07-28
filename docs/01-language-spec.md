# ARIA Language Specification 0.4.0

This document is normative for the ARIA `0.1.0-alpha.14` bootstrap implementation. Where prose and the machine-readable grammar disagree, `grammar/aria.ebnf`, `grammar/opcodes.json`, and the aggregate conformance suite define the executable contract for this alpha.

## 1. Source form

ARIA source is UTF-8, normalized to LF line endings. `#` begins a comment outside a quoted string. Textual identifiers use the restricted ASCII profile defined in `grammar/aria.ebnf`; glyphs are Unicode aliases validated through `grammar/glyphs.json`.

Every program declares a locked language version, program identity, semantic version, and entry flow. A module declaration is optional metadata in 0.4.0.

```aria
aria 0.4.0
module Example.Core version 0.1.0
program Example version 0.1.0
entry Main
```

Module identity is stored in bytecode and provenance. External imports are not part of 0.4.0.

## 2. Scalar types

The bootstrap scalar types are:

| Type | Meaning |
|---|---|
| `Text` | UTF-8 text value |
| `Number` | deterministic integer or decimal numeric value |
| `Bool` | `true` or `false` |
| `Null` | absence of a value |
| `Any` | explicit dynamic escape hatch |

`Any` is assignable to and from all bootstrap scalar types. Narrow types should be preferred because the compiler, bytecode verifier, and VM independently enforce them.

### 2.1 Bounded immutable sequences

`Sequence<Text>`, `Sequence<Number>`, `Sequence<Bool>`, and
`Sequence<Null>` are flat immutable structured values. Literals must be
homogeneous, preserve authored order, and remain within the element and encoded
byte ceilings in `aria.lock.json`. Empty literals require an explicit concrete
sequence type. Nested sequences, mutation, implicit coercion, and algorithm
execution are not part of this release.

## 3. Expressions

Expressions support literals, identifiers, function calls, parentheses, unary operators, and binary operators. Precedence from strongest to weakest is:

1. function call and parentheses;
2. unary `not` and unary `-`;
3. `*` and `/`;
4. `+` and `-`;
5. `<`, `<=`, `>`, `>=`;
6. `==`, `!=`;
7. `and`;
8. `or`.

The verified call glyph `▷` is an alias for ordinary function invocation, `↩`
is an alias for `return`, and `≫` lowers a left-to-right unary pipeline into
nested ordinary calls. These glyphs add no opcode or authority.

`+` accepts `Number + Number` or `Text + Text`. Ordering operators require numbers. Boolean operators require booleans. Equality requires compatible types. Function arguments evaluate left to right.

## 4. Bindings and lexical scope

```aria
let total: Number = 2 + 3
set total = total * 2
```

`let` creates a binding in the current lexical scope. The type may be inferred when omitted. `set` mutates the nearest existing binding and cannot create a new variable. The bootstrap disallows shadowing an existing visible binding.

Bindings created inside `if`, `else`, or `repeat` blocks do not escape those blocks.

## 5. Functions

```aria
function Add(left: Number, right: Number) -> Number {
  return left + right
}
```

Functions have typed parameters and exactly one declared return type. Calls use lexical local frames and may nest to a maximum runtime depth of 64. Non-`Null` functions must visibly return on every branch recognized by the bootstrap analyzer. `halt` is invalid inside a function. A `Null` function may use `return` without an expression.

Functions do not inherit activated host capabilities from callers. Authority must be explicitly activated inside the function body.

## 6. Conditional execution

```aria
if total >= 5 {
  signal pass "threshold reached"
} else {
  signal warn "below threshold"
}
```

The condition must be `Bool`. Branches execute in child lexical scopes. Structured bytecode stores branches as nested instruction arrays rather than unverified numeric jumps.

## 7. Bounded iteration

```aria
repeat 4 as index {
  emit index
}
```

The repeat count must be an integer from 0 through 10,000. The iterator is a zero-based `Number` local to each iteration. Literal bounds are rejected during semantic analysis; dynamic bounds are rechecked by the VM.

## 8. Memory

```aria
memory Project {
  revision: Number = 0
  status: Text = "new"
}
```

Memory defaults must be scalar literals. `remember` updates a declared field and `recall` loads one into a local binding.

```aria
remember Project.revision = 1
recall Project.status -> state: Text
```

Durable state is stored separately under `.aria/state/<Program>.memory.json`. Persisted values are revalidated against the compiled memory type table before execution.

## 9. Capabilities and host effects

```aria
capability RepoRead {
  effect = "fs.read"
  scope = "."
}
```

A host effect requires all of the following:

1. a declared capability;
2. an allowing policy entry;
3. an executed `require CapabilityName` instruction;
4. a target confined to the workspace and capability scope;
5. execution-time policy revalidation.

Declaring or granting a capability does not activate it. Capability activation does not escape a structured branch, repeat body, or function call frame.

## 10. Agents and dispatch

```aria
agent Architect {
}

flow Main {
  dispatch Architect <- "inspect repository graph"
  halt
}
```

An agent is a declared principal. `dispatch` requires a `Text` task and emits a deterministic structured event after policy validation. It does not call a model, spawn a process, or grant authority. Provider integration belongs to the future ARIA Bridge.



## 11. Connection contracts

A connection is a declared ontology linking a human operator identity, a declared agent identity, and a protocol.

```aria
connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}
```

Specification 0.4.0 defines one protocol, `intent-proposal-consent`. Its runtime lifecycle is:

1. `connect ConnectionName`
2. `intent ConnectionName <- Text`
3. `propose ConnectionName <- Text`
4. `consent ConnectionName <- Bool`
5. `disconnect ConnectionName`

The VM enforces this order. `false` consent is a valid, safe outcome and grants no authority. Connection events remain local structured events; they do not contact a model, network, or subprocess.

## 12. Graphs and glyphs

```aria
graph System {
  node ◉ operator human
  node ⟁ agent architect
  node ▧ repository workspace
  link human -> architect as authorizes
  link architect -> workspace as observes
}
```

Glyphs are semantic aliases. The stable identity is the registered node kind and identifier, not font rendering. Graph declarations are preserved as bytecode metadata and can be rendered by the CLI.

## 13. Executable statements

Specification 0.4.0 supports:

- `emit expression`
- `signal pulse|pass|warn|fail|info expression`
- `let name [: Type] = expression`
- `set name = expression`
- `remember Memory.key = expression`
- `recall Memory.key -> name [: Type]`
- `require Capability`
- `assert expression`
- `read pathExpression -> name`
- `write pathExpression <- expression`
- `dispatch Agent <- expression`
- `connect Connection`
- `intent Connection <- expression`
- `propose Connection <- expression`
- `consent Connection <- expression`
- `disconnect Connection`
- `if expression { ... } else { ... }`
- `repeat expression as iterator { ... }`
- `return [expression]`
- `halt`

If an entry flow omits a final `halt`, the compiler appends one deterministically.

## 14. Required rejection behavior

A conforming implementation must reject malformed syntax, duplicate declarations, unresolved symbols, invalid glyph aliases, incompatible types, unsafe repeat bounds, missing returns, unverified bytecode, policy-denied effects, unauthorized paths, incompatible locked versions, corrupted containers, and persisted memory that violates its declared type.

## 15. Whole-program effect proof

Every admitted artifact contains `aria.effect-graph` version 2. The reserved
`$entry` summary covers the executable entry flow; named summaries cover
functions. Direct calls, effects, and capability requirements are closed
transitively through a bounded fixed-point calculation. The bytecode verifier
independently reconstructs the complete graph from instructions and rejects
metadata drift. Purity is derived from empty transitive effect and capability
sets and cannot be asserted by source text.
