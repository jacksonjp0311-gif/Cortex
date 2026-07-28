# Oscillator Buffer alpha.12

ARIA now exposes one universal buffering motion:

```text
∿ github.push  ⟦∙∙∙·◆·∙∙∙∙∙∙∙∙∙∙∙∙⟧
```

The pulse oscillates across a fixed rectangular field. It is visually alien, but retains the familiar semantics of a progress indicator: motion means work is still active.

## Contract

- The oscillator appears only while output is intentionally buffered.
- The same terminal line is rewritten with carriage-return motion.
- Completion clears the oscillator before PASS, REJECT, WARN, or FAIL is rendered.
- CI, redirected output, and `ARIA_NO_ANIMATION=1` suppress animation.
- `ARIA_VERBOSE=1` still exposes native buffered output after the operation.
- `New-AriaBufferState`, `Step-AriaBuffer`, `Write-AriaBufferFrame`, and `Stop-AriaBuffer` are the universal primitives for future compiler, verifier, provider, and runtime buffering.

Gitflow is the first subsystem migrated to the universal primitive.