# Governed Tool Fabric

Version: `10.0.0-alpha.6`

## Purpose

The tool fabric lets temporary, replaceable reasoning models request bounded
host capabilities without making those models the source of capability,
permission, truth, or durable authority.

```text
model tool intent
  -> resolve host manifest
  -> validate exact arguments
  -> verify current host grant
  -> execute bounded handler
  -> seal untrusted observation
  -> bind receipt into trajectory
```

## Canonical objects

`ToolManifest` is host-owned and content-addressed. Its hash covers the tool ID
and version, input/output schemas, authority class, declared side effects,
cancellation support, and network/secret-access declarations. Provider-facing
tool definitions are projections of this canonical object; provider syntax is
not Cortex semantics.

`CapabilityGrant` is a non-delegable, per-turn host decision. Its hash covers
the principal and purpose, workspace root, allowed tool IDs, exact executable
argument vectors, issuance/expiry, output and duration limits, call budget, and
total tool-time budget. It explicitly carries no standing execution, host
mutation, memory-admission, or policy authority.

`ToolExecutionReceipt` binds:

- tool call ID, manifest ID/version/hash, and authority class;
- capability-grant hash;
- exact arguments and argument hash;
- exact public output and output hash;
- completion state and measured chronology;
- closed authority flags.

The receipt is persisted inside the immutable native-agent trajectory, whose
deep verifier reconstructs the request/result/event relationship and the
symbiotic ledger chain.

## Permission law

```text
request != permission
registered capability != active grant
completed execution != task success
tool observation != truth
historical grant != present authority
```

A model can name only tools exposed by the current grant. A malicious or
malformed call to an unknown tool produces a typed denial. Extra Boolean-shaped
claims such as `approved=true` fail schema validation. They never open a gate.

## Cancellation and budgets

Filesystem traversal checks cancellation while enumerating. Terminal execution
uses an exact, shell-free argument vector and is polled through a cancellable
subprocess boundary. Operator cancellation terminates the process and seals a
`cancelled` receipt. Tool-call count, cumulative tool time, command duration,
and output size are independently bounded.

## UI and provider boundary

The loopback service exposes a read-only `/v1/tools` catalog so the operator can
inspect registered manifests and hashes. The interface displays actual tool
events and their manifest/authority binding. It cannot add tools or modify
grants. Models remain provider-neutral; the catalog contains no default model,
provider SDK identity, or model-owned registration path.

## Claim boundary

Alpha.6 establishes a reconstructable, bounded tool-execution substrate. It
does not prove tool output is correct, grant autonomous execution, admit tool
results to memory, distribute competence, create a swarm, establish
consciousness, or demonstrate self-improvement. Those require separate
evidence and authority protocols.
