# Repair repeatability before another difficulty transition

Status: **paid repeat held before invocation; instrument audit substituted**.
Product version remains `10.0.0a39`.
Starting source: `fe7dd24d2c39ce7fe10323f7324e02c11e946496`.

## Pre-execution finding and amended plan

Inspection of the preserved failing process observation found an unstated
expectation: both keys' first tokens must equal `1`. Another private assertion
requires a `next_tokens` field. Neither requirement appears in the frozen
public contract, which permits a global monotonically increasing counter.
The archived model repair uses that permitted strategy.

Consequently **do not spend the four calls below on the known-biased instrument**.
Instead, before any new inference:

1. Test both the host per-key reference and archived global-counter repair
   against the original evaluator; include six deliberately broken variants.
2. Keep public tasks unchanged; create new private evaluator commitments whose
   assertions test monotonicity, idempotence, expiry, ownership and atomicity,
   without requiring one counter layout or exact token values.
3. Require both positive controls to pass and all negative controls to fail.
4. Commission the corrected reference forge and locally replay all four
   archived outputs. Label this **post-hoc instrument auditing**, not new model
   performance, calibration, transfer, training or self-improvement evidence.
5. Record an exact-commitment challenge that blocks new inference under the old
   evaluator. Preserve historical reconstruction and scores. A corrected
   evaluator has a new identity; it cannot be passed off as a same-test repeat.

The repeatability mechanism below remains tested but **not live-executed**.
Future fresh-case confirmation must use a separately frozen, audited instrument.

## Why this step

The alpha.39 baseline solved three of four different tasks. Its frozen policy
called that a ceiling. The mathematical audit showed why that is too little
information to keep changing difficulty. Preserve that historical receipt;
do not reinterpret it as a newly preregistered experiment.

Before spending eight or more calls on fresh cases, spend **four** checking
whether the observed failure repeats under the same observable conditions.
This is a bounded preliminary step toward fresh-case sequential confirmation,
not a substitute for it. Do not add more agents, autonomy, UI or a release.

## Frozen protocol

- Corpus: the exact four alpha.38 tasks and their private evaluator commitments.
- Origin: alpha.39 result `36e11f0edfd1d30172af554a1adc18078041a6ad383e145d96320f66d4892090`.
- Reasoning engine: supplied at launch; must match the origin's canonical model
  and adapter provenance. No model identity enters a core decision rule.
- Four new native-runtime invocations, one per task, same order, one iteration,
  task-only context, no tools, no prior answers or private tests in the prompt.
- Provider configuration remains the existing adapter's defaults. No provider
  seed, temperature or weight revision is pinned; this limitation survives in
  the frozen receipt. Compare hashes of inference, compilation and evaluation
  source against the origin before proceeding.
- Freeze the canonical policy before invocation. A unique Store execution claim
  prevents repeating this run ID, including after a partial failure. No automatic
  retries, exclusions, best-of selection or new difficulty generation.
- Candidate programs run in the existing disposable evaluator worktrees.
  These are **not an OS sandbox**. The benchmark does not grant tool or source
  integration authority to the model.

## Mathematics and decisions

For each fixed task i, record the original and repeated binary outcomes
`(Y_i, Y'_i)`. Report agreement and the complete four-row table:

`changed = sum[ Y_i != Y'_i ]`

`repeated_failures = sum[ Y_i = 0 and Y'_i = 0 ]`

There are **four distinct tasks and eight invocation observations**, not eight
independent task samples. No pooled binomial test, p-value, population success
estimate or treatment-effect claim is justified here. Runtime defaults and
provider weight identity also constrain repeatability interpretation.

Predeclared next steps:

| Observation | Next work, not automatic execution |
|---|---|
| Failure repeats | Inspect the two repairs against the same requirement; formulate a narrowly supported lesson hypothesis. |
| Outcome changes | Preserve both outcomes; measure variability on fresh cases before changing difficulty. |
| Everything succeeds | Record the ceiling on this panel; design a fresh discriminative corpus, not a positive transfer claim. |

Only after fresh-case confirmation should a separately frozen task-only / sham /
relevant-lesson comparison test semantic benefit. This run cannot promote memory
or competence, integrate a patch, or establish general Cortex improvement.

## Verification and evidence

Extend the existing structured repair runner and verifier; keep legacy `1.0`
receipts intact. New preregistrations use `1.1` with a fixed repeatability policy.
Verify exact prior/result/corpus/evaluator/model binding, fresh trajectory IDs,
chronology after the execution claim, reconstructed per-task outcomes, and all
authority flags. Reject changed policies, unrelated contracts, trajectory replay,
forged aggregate counts and duplicate execution before making paid calls.

Run focused repair/mathematical regression tests, Ruff, targeted compileall and
`git diff --check`. Freeze and execute with separate CLI commands; preserve both
public reports. No full-suite rerun and no paid calls in CI.

Results will be reported in a separate document after execution. Unknown,
failure and null outcomes remain valid results, not reasons to rerun silently.
