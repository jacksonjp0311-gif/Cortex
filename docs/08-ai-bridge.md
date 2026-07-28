# AI Bridge Architecture

ARIA's deterministic core and an AI model have different jobs.

## AI responsibilities

- translate human intent into proposed ARIA;
- inspect graph, memory schemas, diagnostics, and repository state;
- explain failed gates;
- propose patches and tests;
- estimate uncertainty and cite evidence.

## Compiler responsibilities

- parse exact syntax;
- resolve names and types;
- enforce authority;
- produce deterministic bytecode;
- verify containers;
- execute defined opcodes only.

## Current discovery protocol

ARIA now begins provider-neutral integration with:

```powershell
.\aria.cmd handshake --json
```

`ARIA-CONNECT.json` defines the shared vocabulary, ordered synchronization
phases, read order, commands, invariants, and authority boundary. The handshake
binds that contract to the runtime map, agent guide, and actual repository
manifest state with exact digests.

The handshake stops at shared orientation. It does not call a model, transport
private context, grant a capability, or approve a proposal.

## Future provider transport

A future external-provider bridge should exchange a signed proposal envelope
containing intent, source diff, requested capabilities, evidence, expected
tests, and rollback plan. The compiler validates the resulting ARIA exactly as
it validates human-authored source.

No model probability, role name, or glyph grants authority. Only a valid capability accepted by policy and activated in deterministic execution can cross a host boundary.
