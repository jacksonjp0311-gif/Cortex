# ARIA Language Charter

ARIA is a graph-native local execution language designed for shared operation by humans and AI systems.

## Non-negotiable principles

1. **Deterministic authority:** AI output is input to the compiler, never a substitute for validation.
2. **Dual notation:** glyph and textual surfaces round-trip through one canonical semantic representation.
3. **Local-first execution:** host effects are explicit and denied by default.
4. **Visible memory:** durable state is declared, inspectable, exportable, and erasable.
5. **Content-addressed builds:** source, IR, policy, and executable identities are cryptographic digests.
6. **Open specification:** independent implementations can conform without using the bootstrap code.
7. **Accessible glyphs:** every glyph has a stable textual token and spoken semantic name.
8. **Reversible evolution:** language and program versions are explicit; incompatible changes require version transitions.

The bootstrap implementation is intentionally small. A revolutionary language begins with unusually clear invariants, not an unusually large feature list.
