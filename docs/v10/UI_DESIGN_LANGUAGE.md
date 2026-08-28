# UI Design Language

Alpha 1 is headless. A future TUI, desktop app, web UI, or messaging gateway
must consume the same versioned public event stream.

The interface vocabulary is evidence-first:

- context is projected, not “known”;
- tools are requested, granted or denied, then observed;
- results are untrusted until independently evaluated;
- authority is displayed separately from model confidence;
- receipt and chain verification are visible;
- UNKNOWN is never rendered as PASS.

UI controls may request interruption or permission decisions through future
typed commands. They may not mutate canonical runtime state directly.
