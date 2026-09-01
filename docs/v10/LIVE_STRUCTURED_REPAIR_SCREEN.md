# Alpha.34 — External-Private Structured Repair Baseline

Status before live execution: `STRUCTURED_REPAIR_SCREEN_READY`

## Purpose

Alpha.34 measures a frontier model on fresh executable defects without
confounding repair reasoning with hand-authored Git diff coordinates. It also
closes the alpha.31 private-material wound prospectively: task specifications,
external tests, and reference repairs originate outside the repository and the
private evaluator bundle remains in the host credential vault.

This is a development baseline screen, not a semantic-treatment experiment.

## Canonical path

```text
external private specification
  → answer-free public corpus
  → baseline/reference evaluator contrast
  → frozen live adapter provenance
  → task + buggy source only
  → structured edit intent
  → deterministic Cortex diff compiler
  → isolated candidate worktree
  → withheld executable evaluator
  → canonical case/result receipts
```

The response contract accepts exactly:

```json
{
  "schema_version": "cortex-edit-intent/1.0",
  "summary": "public repair summary",
  "edits": [
    {"path": "module.py", "old": "exact unique source", "new": "replacement"}
  ]
}
```

Unknown fields, escaped paths, ambiguous preimages, stale preimages, malformed
JSON, and non-unique replacements fail closed. Compilation does not grant
mutation or execution authority.

## Frozen measurement rule

Exactly four no-tool task-only calls are allowed. The unchanged baseline and
candidate are measured under the same host-private evaluator.

```text
0–1 / 4 → screening floor
2 / 4   → structured baseline calibrated
3–4 / 4 → screening ceiling
```

Only `2/4` recommends freezing a separately authorized sham-versus-relevant
semantic treatment. Other outcomes change task difficulty under a new seal.

## Evidence and authority boundary

- Private tests and reference repairs are absent from Git and model context.
- Model/provider identity is provenance, never authority.
- Model assertions of success do not affect scoring.
- The active repository tree is not mutated.
- `host_mutate_authorized = false`
- `execution_authorized = false`
- `memory_admission_authorized = false`
- `policy_effect = false`
- Semantic transfer and general improvement remain unestablished.

## Focused verification

The phase uses the alpha.32–34 repair chain tests, lint, targeted compile, and
`git diff --check`. A live result is documented only after exactly four calls
execute and the complete receipt graph reconstructs successfully.
