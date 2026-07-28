# ARIA Traceflow

Traceflow is the shared event protocol between ARIA programs, the bytecode VM, and the CLI renderer.

```aria
signal pulse "language core"
signal pass "memory online"
```

The compiler emits `SIGNAL` bytecode with a validated state. The VM records a structured event and, when attached to the CLI, renders it through the descending tree. Signal states are presentation-safe and reuse the `console.emit` capability gate; they do not grant authority or change control flow.

Traceflow keeps the language and CLI synchronized: a future GUI, log collector, or agent bridge can consume the same event objects without parsing terminal text.
