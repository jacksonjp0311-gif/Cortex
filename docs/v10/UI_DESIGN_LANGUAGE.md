# UI Design Language

Alpha.2 implements the first Cortex-native operator console. It consumes the
same versioned public event stream as every future TUI, native shell, or
messaging gateway.

The interface vocabulary is evidence-first:

- context is projected, not “known”;
- tools are requested, granted or denied, then observed;
- results are untrusted until independently evaluated;
- authority is displayed separately from model confidence;
- receipt and chain verification are visible;
- UNKNOWN is never rendered as PASS.

UI controls may request interruption or permission decisions through future
typed commands. They may not mutate canonical runtime state directly.

## Visual system

The graphite and near-black foundation represents inactive structure. Ice blue
marks hierarchy, cyan marks live telemetry, and electric violet marks active
energy or an intentional operator action. The blue-to-violet transition is the
visual language of Cortex circulation. Verified green is reserved for
canonical verification; red is reserved for real failure or blocking state.

Glow is a state signal. Active computation may pulse; inactive panels do not.
Typography separates readable conversation from compact monospace telemetry.
The central plasma core is a state instrument. Its ambient, context, thinking,
streaming, tool, interrupt, and failure modes are selected only from runtime
events. Motion never implies confidence, cognition quality, or authority.

Desktop uses telemetry, core/chat, intelligence, and optional operator regions.
At smaller breakpoints telemetry becomes a compact grid, intelligence moves to
a drawer, and the same truthful state is preserved rather than replaced by
mobile-only estimates.
