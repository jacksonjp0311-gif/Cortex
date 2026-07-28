# Migration from the AEL Operator Prototype

The prior AEL operator surface proved local shell integration, repository telemetry, and a visual graph. ARIA starts over at the language boundary.

## Retained ideas

- local-first operation;
- an operator-visible semantic graph;
- explicit agent, repository, artifact, memory, and policy concepts;
- future integration with an operator surface.

## Replaced architecture

- PowerShell is no longer the product surface; it is the bootstrap host.
- Graph declarations are compiled metadata rather than browser-only state.
- ARIA source compiles to a verified `.ariac` artifact.
- Memory and authority are language constructs.
- The compiler gate determines whether a program can execute.

The old dashboard can later become ARIA Studio by consuming `.ariac` graph metadata and VM events. It should not define language semantics.
