# ARIA Design Discoveries

1. **The glyph cannot be the opcode.** Fonts, normalization, keyboards, and accessibility make a direct visual-to-machine identity brittle. A glyph maps to a stable semantic identifier.
2. **Visual layout cannot define program identity.** Coordinates are editor state; canonical graph identity comes from nodes, typed edges, attributes, and stable names.
3. **Memory cannot live inside the executable.** Embedding live memory destroys reproducibility and risks exporting private state when artifacts are shared.
4. **Capability declaration is not capability possession.** Authority requires declaration, policy approval, runtime activation, and target confinement.
5. **Integrity is not validity.** A correct checksum proves byte identity, not stack safety, semantic compatibility, or authorized behavior. The VM must verify both the container and bytecode.
6. **AI cannot define compiler truth.** A model may infer intent and propose programs; only deterministic rules can grant validity or authority.
7. **A bootstrap host is not a parent language.** PowerShell implements the first compiler and VM, but ARIA semantics, artifacts, and conformance rules are independent contracts.
8. **Compression is not compilation.** ARIA creates validated bytecode before gzip packages it. The container records this distinction.
9. **Reproducibility and provenance need separate artifacts.** The executable excludes time; provenance records time and build context.
10. **Graph-native does not mean graph-only.** Sequential flows are easier to validate and replay. Graph rewriting should arrive after the deterministic core.
11. **The policy must be weaker than the host.** ARIA should expose a small audited effect set rather than forward arbitrary PowerShell or operating-system calls.
12. **Runtime checks remain necessary after compilation.** Policies and artifacts can be changed independently; defense in depth requires checks at gate, decoder, verifier, and effect execution.
13. **Agent declarations are not agents.** An agent node becomes operational only when ARIA defines principal identity, grants, proposal format, scheduling, and lifecycle semantics.
14. **The first revolutionary feature is inspectable authority.** Novel syntax without visible, enforceable authority would be aesthetic rather than structural innovation.
15. **The second revolutionary feature is shared representation.** Human, AI, compiler, debugger, and repository should operate on the same canonical semantic model rather than separate approximations.
