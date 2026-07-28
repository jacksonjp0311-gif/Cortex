# Lexical Scope and Function Frames

ARIA represents lexical scope as an ordered stack of maps.

## Lookup

Search maps from the innermost scope to the root. `let` writes only to the current map. `set` updates the first matching map and fails when no binding exists.

## Structured scopes

- Entry flows begin with one root map.
- Each `if` or `else` branch adds one child map.
- Each repeat iteration adds one child map containing the zero-based iterator.
- Each function call creates a fresh root map populated only with typed parameters.

## Authority isolation

Activated capabilities are copied into structured child execution where appropriate but do not leak out of branches or loops. Function calls begin with an empty capability activation table. This makes authority acquisition explicit inside the callable unit.

## Call safety

The verifier checks parameter count and types. The VM repeats those checks, enforces a maximum depth of 64 frames, and validates the returned concrete value against the declared return type.
