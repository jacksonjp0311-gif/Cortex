# Capability Security

ARIA uses named capabilities to make authority part of the program model.

A capability declaration describes an effect and scope. Repository policy independently approves or denies that effect. A flow must activate the capability with `require` before the matching host opcode.

This creates three separate checks:

1. **Declaration:** the program admits it needs authority.
2. **Policy:** the operator/repository permits the authority.
3. **Activation:** the execution path explicitly crosses the boundary.

The default policy denies filesystem writes, process execution, and networking. Specification 0.4.0 includes no process or network opcode, so policy changes alone cannot activate nonexistent machinery.

Path confinement canonicalizes the workspace, capability scope, and requested path, then rejects lexical traversal outside either boundary.

## Path confinement

Filesystem paths are made absolute relative to the selected workspace and capability scope. The compiler rejects rooted scopes and explicit `..` traversal; the runtime rejects lexical escape from the workspace or capability scope.

This alpha does not claim to be an operating-system sandbox. Reparse points, junctions, symbolic links, filesystem races, and unrelated host processes remain part of the host threat model. Do not enable write authority for untrusted or adversarial workspaces.

## Effect budgets

Policy effects may declare a positive `maxBytes` budget. The VM enforces these limits for console output, persistent memory, filesystem reads, and filesystem writes. Limits are checked again at execution time and do not rely only on compilation.
