# Fixed L3 development cohort — September 6, 2026

Baseline: `f2c6798029eebde9eee2e93b189321c1b3a3d65a`.
Product remains `10.0.0a39`. No treatment effect is being tested.

## Prospective design

Complete eight authored multi-file temporal/state defects. Audit every evaluator
before inference, then freeze **both** four-case panels and their exact assignment.
Each evaluator must accept two distinct allowed repairs and reject at least one
known-broken control. Host labels are bounded judgments, not semantic proof.

| Stage | Fixed cases |
|---|---|
| Screening — 4 calls | Retry after commit; atomic projection offset; superseded expiry; catalog tenant partition |
| Conditional confirmation — 4 fresh calls | Equal-timestamp synchronization; checkpoint replay boundary; superseded job delivery; disjoint transaction merge |

The catalog case was previously audited without model calls. Other cases are newly
authored. L3 denotes cross-module/temporal structure, **not empirically established
difficulty**. These are development fixtures, not production incident replication.
Exact source differs across cases; semantic/statistical independence is unproven.
Assignment is authored order, not randomized, and is frozen before any model output.

The initial code is small enough for bounded no-tool inspection. Every model sees
the same type of task-only prompt, public behavioral contract and source-file map.
Private tests, reference patches, control labels and results do not enter prompts.

## Stopping rule and budget

\[
N_{max}=4+4=8,\quad
\operatorname{Confirm}\iff 0<S_{screen}<4.
\]

Zero or four initial successes stop at the initial panel. One, two or three
successes permit exactly four additional, already frozen fresh tasks at L3.
No task edits, automatic difficulty moves, reruns, best-of answers, tools, or
semantic lessons. Each native run has one iteration. A partial execution spends
its one-shot stage claim and is held rather than silently retried.

The existing sequential helper's `confirmation_cases=8` means **eight total
cases**, not eight additional calls. At n=8, 3–5 successes select a development
region under the fixed 30–70% heuristic. That is not population calibration,
statistical significance, transfer, competence, or proof of Cortex benefit.

Runtime provider/model and adapter provenance are bound in both stage receipts.
Use the existing operator-selected model; no provider/model is coded into the
cohort policy. Serving revision and provider default generation parameters remain
unattested limitations. Report actual provider token usage where available.

## Implementation

`repair_calibration_cohort.py` composes the existing 1.3 structured screens.
It binds their canonical receipts, source commit, model/provenance, tool and
context policy, response schema, fixed stratum and eight source fingerprints.
Both instrument audits must belong to the declared source. Cohort freezing
rejects already-started screens. Stage execution rejects source-HEAD drift.

The host-facing runner refuses premature/unnecessary confirmation. Reconstruction
independently verifies each native screen, the cohort-before-execution chronology,
and screening-result-before-confirmation chronology. Standalone lower-level calls
cannot retrospectively qualify an out-of-order cohort. The lower-level one-shot
claims enforce no duplicate paid stage even under concurrent wrapper calls.

This is not a new authority system. All authority-effect flags remain false.
Detached worktrees are not an OS sandbox. Existing historical receipts are read,
not rewritten. A/B/C treatment remains held until a defensible development region
and a separately frozen experiment exist.

## Verification and outcomes

Record exact zero-call controls, tests, source identities, calls and results below
after execution. A failed control holds inference; a ceiling is preserved as a
ceiling. No evaluator will be changed after inspecting model answers.
