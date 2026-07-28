# Typed Authority Core alpha.16

ARIA 0.2 begins by making the semantic core stricter than the bootstrap host.

## Invariants

```text
AI proposes.
Types constrain meaning.
Effects declare intent.
Capabilities grant authority.
The independent verifier decides artifact acceptance.
```

Alpha.16 introduces:

- a canonical type lattice;
- generic `List`, `Option`, and `Result` types;
- record and function types;
- lexical scopes;
- immutable bindings by default;
- structured errors with stable codes and evidence;
- typed function signatures;
- arity and argument checks;
- branch exhaustiveness checks;
- effect-to-capability verification;
- host-neutral typed IR;
- canonical serialization and SHA-256 identity;
- an IR verifier independent of the compiler.

## Type lattice

Primitive types:

```text
Unit Bool Int Float Text Bytes Node Edge
```

Constructed types:

```text
List<T>
Option<T>
Result<T,E>
Record{name:T,...}
Fn(T,...)->R
```

Canonical type strings are deterministic and suitable for fixtures, diagnostics, and artifact identity.

## Immutability

Bindings are immutable unless explicitly declared mutable.

```text
immutable assignment → E_BIND_IMMUTABLE
type-changing assignment → E_TYPE_ASSIGN
unknown binding → E_BIND_UNKNOWN
```

Mutation is never implied by host-language assignment behavior.

## Structured errors

A semantic failure is a typed value:

```json
{
  "code": "E_CAPABILITY_MISSING",
  "message": "Function 'send' requires capability 'cap:network'.",
  "path": "$.capabilities",
  "evidence": {
    "required": "cap:network"
  }
}
```

Stable error codes allow humans, tests, and AI agents to reason about rejection without scraping prose.

## Effects and capabilities

Effects declare what a function intends to do. Capabilities decide whether that authority is available.

```text
memory.read      → cap:memory.read
memory.write     → cap:memory.write
network.send     → cap:network
filesystem.read  → cap:filesystem.read
filesystem.write → cap:filesystem.write
provider.invoke  → cap:provider
```

A valid function with missing authority is rejected.

## Independent typed IR

The verifier consumes `aria.typed-ir/0.2` JSON documents. It does not call the compiler and does not depend on compiler-internal objects.

Verification includes:

- schema version;
- entry-function existence;
- duplicate function rejection;
- effect/capability consistency;
- opcode allow-list;
- deterministic canonical JSON;
- SHA-256 digest calculation;
- optional declared-digest verification.

This is the first step toward a second implementation outside PowerShell.

## Evolution rule

Every future language construct must add at least one new rejection condition to the verifier or semantic validator.

Surface growth without stronger rejection is not sufficient evolution.