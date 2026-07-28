# Glyph Registry 0.1

Glyphs are compact semantic aliases. They are not inferred from appearance and are never the sole stored identity.

| Glyph | Stable name | Node kind | Meaning |
|---|---|---|---|
| `⌬` | system | system | Complete execution environment |
| `◉` | operator | operator | Human authority and observation |
| `⟁` | agent | agent | AI or autonomous principal |
| `▧` | repository | repository | Versioned code/data workspace |
| `ϟ` | service | service | Deterministic executable service |
| `◇` | surface | surface | Human or machine interface |
| `⊙` | memory | memory | Explicit state store |
| `◆` | artifact | artifact | Produced file, patch, report, or build |
| `⛨` | policy | policy | Authority boundary and rules |
| `∿` | stream | stream | Events, messages, or telemetry |

## Glyph invariants

- The compiler stores `nodeKind`, `name`, and `glyph` separately.
- An unknown glyph may be rendered, but it does not create a new node kind without a registry extension.
- A text-only tool can use stable names and preserve semantics.
- Screen readers and AI systems should consume stable names, not attempt visual classification.
- Future compositional operator glyphs require arity, type, and execution definitions before standardization.

## Machine-readable contract

The authoritative bootstrap registry is [`grammar/glyphs.json`](../grammar/glyphs.json), validated by [`schemas/aria-glyph-registry.schema.json`](../schemas/aria-glyph-registry.schema.json). Compiler implementations must consume stable IDs and symbols from that contract rather than infer meaning from visual appearance.
