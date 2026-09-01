# Alpha.32 — Live Executable Repair Screen

Version: `10.0.0-alpha.32`

Alpha.32 is Cortex's first frontier-model screen where success is defined by
executable behavior rather than a semantic answer ruler.

```text
task + buggy source
       ↓
frontier model (no tools)
       ↓
exact unified diff proposal
       ↓
frozen external test
  baseline vs isolated candidate
       ↓
canonical repair observation
```

The screen freezes exactly four calls. The model sees `TASK.md` and
`module.py`; it never sees `external_test.py`, the reference patch, commitment
salt, or evaluator result. A response cannot report its own success.

Malformed, non-applying, out-of-scope, or failing patches remain measured
candidate failures. A valid proposal is parsed by the existing coding-workspace
boundary and executed only in a detached temporary worktree. The active Cortex
tree is never a candidate workspace.

## Sequential interpretation

With four cases, only `2/4` lies in the predeclared 30–70% information window:

```text
0–1 / 4  screening floor   → forge easier executable tasks
2 / 4    calibrated band   → freeze sham/relevant treatment
3–4 / 4  screening ceiling → forge harder executable tasks
```

This phase tests task-only model repair ability. It does not project Cortex
memory or competence and cannot establish semantic transfer, general
self-improvement, or authorization to integrate a patch.
