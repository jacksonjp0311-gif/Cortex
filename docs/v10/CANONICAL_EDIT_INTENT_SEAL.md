# Alpha.33 — Canonical Edit Intent & Private Corpus Closure

Version: `10.0.0-alpha.33`

Alpha.32 exposed two independent surfaces:

```text
repair semantics        model described the intended edits in 4/4 cases
patch transport         only 2/4 outputs were applicable Git diffs
```

The immutable executable score remains `2/4`. Producing an applicable change
was part of the frozen contract, so the two invalid diffs remain failures.

## Structured edit intent

Alpha.33 adds a provider-neutral cognitive representation:

```json
{
  "schema_version": "cortex-structured-edit-intent/1.0",
  "summary": "bounded public purpose",
  "edits": [
    {"path": "module.py", "old": "exact preimage", "new": "exact postimage"}
  ]
}
```

Cortex requires each preimage to resolve exactly once inside a host-declared
target scope. It then computes unified-diff coordinates deterministically and
passes the result through the existing canonical patch-proposal boundary.

This separates:

```text
model responsibility   choose the semantic source transformation
Cortex responsibility  compile exact patch syntax and bind preimages
host responsibility    authorize any execution or mutation
```

Unknown fields, caller success values, ambiguous preimages, path escapes,
stale files, and empty transformations fail closed.

## Private-corpus correction

The alpha.31 public artifact did not contain external tests or reference
patches, and the alpha.32 no-tool model request did not receive them. However,
the alpha.31 forge implementation embedded those strings in its source. They
therefore exist in public Git history.

Consequences:

- alpha.32's observed no-tool 2/4 result remains valid;
- historical scores are not rewritten;
- the corpus is not reusable as genuinely held-out evidence;
- future private corpus specifications must enter the forge from a path outside
  the repository and be persisted only in the host credential vault.

The corrected forge now enforces that external input boundary. Unit tests use
separate toy fixtures, never the historical live corpus.

## Next experiment

No treatment trial opens from the compromised development corpus. The next
phase must forge a new externally supplied private corpus, freeze a structured-
intent task-only screen, and only then decide whether a sham/relevant semantic
treatment is statistically justified.
