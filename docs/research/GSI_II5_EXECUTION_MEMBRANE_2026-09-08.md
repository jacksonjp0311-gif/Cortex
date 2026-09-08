# GSI-II.5 — Execution membrane and cross-binding closure

September 8, 2026 · product `10.0.0a39`.

Reviewed source baseline: `e162f53095a244991e96e566abdd7d87406120c2`.
The successor revision is evaluated by its own exact-head CI after publication.

## Scope

II.5 closes the last deterministic boundary before the uncommissioned GSI-III
same-model history experiment. It does not execute a provider, mutate Cortex,
or establish history utility.

The confirmatory path is now conceptually:

```text
ExecutionLock
  -> canonical A/B/C assignment
  -> frozen treatment/history
  -> exact candidate context
  -> candidate receipt
  -> search episode
```

## Closure

`execution_readiness()` accepts only the declared schemas for execution
contract, task set, model runtime, randomization, analysis plan, common
baseline, treatment, and sham match. A generic sealed object cannot satisfy a
component slot. `execution_lock()` remains non-authorizing; its component
hashes are checked against canonical Store objects before `run_empirical()` may
invoke candidate generation.

Confirmatory randomization requires exactly one A, B, and C assignment for each
task. An assignment receipt binds the task and arm to the frozen randomization
plan and treatment. Arm A remains empty; B and C require non-empty canonical
history. B must carry a PASSing sham-match receipt. Sham and applicable history
must match on evidence-type and schema distributions in addition to declared
size tolerances.

Search episodes resolve canonical assignment, candidate, context, trial and
execution receipts. Candidate/context, trial/context, trial/treatment,
assignment/task/arm, and runtime identities are cross-checked. Candidate,
provider-call, token and wall-clock budgets are machine-evaluated; a violation
produces a held episode rather than a normal result.

Semantic holdout identity optionally includes explicitly declared fixture/data
digests. No whole-filesystem dependency discovery is attempted.

## Evidence boundary

The II.5 controls are 21 deterministic zero-provider-call mechanism checks.
They establish execution-membrane mechanics within declared controls only.
They do not establish a live treatment effect, inherited-history utility,
cumulative self-improvement, general competence, or production autonomy.

Historical v1 and II.4 paths remain reconstructable; their receipts are not
rewritten. The GSI-III execution document remains `EXECUTION_DRAFT` until exact
model, task, budget, treatment, assignment, analysis, CI and host-authorization
values are frozen.

## Claim ceiling

After exact-head CI for this revision, the bounded claim is:

> GSI confirmatory execution membrane and causal cross-binding mechanics
> verified in deterministic controls.

`gsi.history_utility`, `history_utility_established`, and
`cumulative_self_improvement_established` remain false or not established.
