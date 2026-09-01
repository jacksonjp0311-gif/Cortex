# Alpha.31 — Answer-Sealed Executable Repair Forge

Version: `10.0.0-alpha.31`

Alpha.30 closed the synthetic semantic benchmark after a final prospective
screen. Alpha.31 moves the measurement surface to executable program behavior.
It spends zero model calls.

## Implemented path

```text
public defect + buggy source
        ↓
private external test commitment
        ↓
same frozen Git HEAD
   ┌────┴────┐
baseline  reference candidate
   ↓            ↓
 must fail    must pass
        ↓
canonical counterfactual receipt
```

The corpus contains four development cases:

1. stale cache invalidation;
2. generation-zero guard bypass;
3. publication before validation;
4. invalid-first deduplication suppression.

The committed public corpus contains the task, buggy source, visible-file
allowlist, and a salted evaluator commitment. The external test, commitment
salt, and reference patch are stored together in the host credential vault.
They are absent from the model-visible context and committed artifact.

Legacy disclosure: the alpha.31 implementation source embedded the original
private strings. Alpha.33 removes that path and retires this corpus from future
held-out trials. The alpha.32 model had no tools and did not receive the private
material, so its development observation remains intact.

## Reused constitutional machinery

Alpha.31 composes, rather than duplicates, the alpha.4/alpha.5 source path:

- `create_patch_proposal` canonicalizes exact diffs and preimages;
- `verify_patch_in_isolated_worktree` runs the host evaluator off-tree;
- `run_source_improvement_trial` evaluates unchanged baseline and exact
  candidate from the same source commit;
- `verify_source_improvement_result` reconstructs the classification.

For each forged task the commissioning requirement is:

```text
baseline = FAIL ∧ reference_candidate = PASS
```

This means the frozen evaluator can detect the declared repair. It does not
mean a model can discover that repair.

## Evidence and authority boundary

The commissioning artifact must report:

- four measured reference repairs;
- zero model calls;
- no private evaluator material in the artifact;
- no active-tree mutation;
- all authority flags false.

`REPAIR_MEASURED` applies only to a particular reference patch on one task.
General self-improvement, semantic transfer, and model repair competence remain
unestablished.

## Next experiment

The next separately authorized phase may freeze a frontier-model task-only
screen over these public tasks. The model receives the defect description and
buggy source, never the external tests or reference patch. Its proposed diff
must run through the existing isolated counterfactual evaluator. Baseline
difficulty must be measured before any Cortex lesson treatment is introduced.
