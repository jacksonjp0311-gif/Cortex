# Phase v8.8 — Cross-Instantiation Memory Trials

## Purpose

v8.7 rehydrates memory responsibly.

v8.8 **measures** whether that rehydration helps a *new* temporary cortex:

```text
A — raw repository
B — ordinary summary
C — unfiltered admitted memories
D — governed memory projection
E — projection + memory-use feedback
```

## Gains

```text
G_rehydration = U_D − U_A
G_credit      = U_E − U_D
```

`U` is a deterministic probe utility over declared ground-truth substrings
(orientation, constraint retention, task success, precision, cost, inappropriate use).

Not model fluency. Not consciousness.

## Law

```text
matched arms
deterministic scoring
no host mutation
no execution
no learned retrieval weights yet
```

## CLI

```powershell
python -m cortex memory trial --repo R --task "..." --json
python -m cortex memory trial-status --repo R --json
```

## Next

Operational use of trial feedback to refine projection budgets — still without
letting utility rewrite truth status.
