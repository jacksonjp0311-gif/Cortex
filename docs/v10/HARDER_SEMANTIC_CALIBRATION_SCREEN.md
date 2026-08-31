# Cortex v10.0.0-alpha.19 — Harder Semantic Calibration Screen

Alpha.19 follows the canonical alpha.18 `move_harder` disposition without
opening a semantic-treatment trial.

## Causal binding

The follow-up preregistration resolves the immutable alpha.18 result and its
preregistration. It accepts level three only because the prior level-two screen
was a reconstructed 4/4 ceiling. A missing receipt, caller result, wrong level,
different model identity, or non-live adapter fails closed.

Alpha.18 intentionally did not persist its private answer key. Alpha.19 cannot
pretend that key still exists. It therefore uses a new random answer seal and
records `corpus_continuity = new_development_seal`. This preserves honesty but
makes the run development-only and non-confirmatory.

## Result

| Quantity | Alpha.18 | Alpha.19 |
|---|---:|---:|
| Difficulty level | 2 | 3 |
| Calls | 4 | 4 |
| Successes | 4 | 4 |
| Success rate | 1.00 | 1.00 |
| State | ceiling | ceiling |

Both screens used `OpenAI / gpt-5.6-sol`, no tools, task-only context, exact
one-token evaluation, and canonical trajectory reconstruction.

## Geometry decision

The intended information band is

\[
0.30 \leq \hat p \leq 0.70.
\]

Neither available screened level entered it. The maximum existing level is
therefore exhausted for this model:

\[
\operatorname{ChoiceRecognition}(M,T_2)
=
\operatorname{ChoiceRecognition}(M,T_3)
=1.
\]

The next action is not another longer multiple-choice question. It is a new
open-response latent-cause forge with independently frozen atomic evaluation:

```text
symptom + bounded evidence
  -> model-generated causal mechanism
  -> required causal atoms
  -> forbidden unsupported atoms
  -> independent exact/structured evaluator
```

Only after task-only performance enters a non-floor/non-ceiling band may Cortex
compare task-only, verified sham, and verified relevant semantic lessons.

Calibration, semantic transfer, and model improvement remain unestablished.
All authority flags remain false. No additional calls were made after the
four-call ceiling was observed.
