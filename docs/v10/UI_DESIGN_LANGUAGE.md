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
marks hierarchy, cyan marks live telemetry, and cybernetic orange marks active
energy or an intentional operator action. Verified green is reserved for
canonical verification; red is reserved for real failure or blocking state.

Glow is a state signal. Active computation may pulse; inactive panels do not.
Typography separates readable conversation from compact monospace telemetry.
The 2D lattice contains only nodes backed by runtime events. Alpha.2 therefore
shows one Cortex node unless real subagent events exist.

Desktop uses lattice, chat, intelligence, and operator regions. At smaller
breakpoints the lattice becomes a compact conversation strip, intelligence
moves to a drawer, and operator tabs remain horizontally accessible. The same
truthful state is preserved rather than replaced by mobile-only estimates.
