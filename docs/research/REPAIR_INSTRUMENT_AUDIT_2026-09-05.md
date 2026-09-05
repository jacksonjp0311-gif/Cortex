# Repair instrument audit — September 5, 2026

**Outcome: evaluator defect reproduced and corrected; zero new model calls.**

The [prospective repeat plan](REPAIR_REPEATABILITY_PLAN_2026-09-05.md) was amended
before any paid invocation. Implementation source:
`506ac8e25e9e729750da55e6ef6517b0ed918160`. Product remains `10.0.0a39`.

## What actually failed

Alpha.39's `atomic_expiring_reservations` public contract requires a newly issued
token to exceed every prior token **for that key**. It does not require tokens
to begin at 1 independently for each key or a particular counter field.

The archived repair used a global increasing counter, an allowed strategy.
The private evaluator instead asserted exact first/next token values and read
an internal `next_tokens` field. The original observation failed on that exact
value assertion. The generic assertion-to-requirement mapping had verified
lineage and coverage, **not whether the assertion followed from the requirement**.

This is an instrument defect, not evidence of a general concurrency weakness,
a missing training step, or an inability to repair the stated task.

## Executed local experiment

The old and corrected evaluators were tested against the same eight controls:

| Control | Expected | Old | Corrected |
|---|---|---|---|
| Host per-key reference | Pass | Pass | Pass |
| Archived global-counter repair | Pass | Fail | Pass |
| Invalid TTL accepted | Fail | Fail | Fail |
| Owner conflict ignored | Fail | Fail | Fail |
| Same-owner lease renewed | Fail | Fail | Fail |
| Tokens reused | Fail | Fail | Fail |
| Wrong-owner release accepted | Fail | Fail | Fail |
| Counter mutated on refusal | Fail | Fail | Fail |

Expected labels are host-reviewed against the public contract. They are not a
new semantic theorem prover. Negative controls prove rejection of these tested
defects; they do not prove complete mutant coverage or absence of all evaluator
bias. The corrected tests use token relationships, state snapshots and expiry
behavior rather than one implementation's exact token layout.

All four reference repairs passed the corrected forge while their unchanged
baselines failed. All public requirements and buggy source files stayed the
same. Private evaluator commitments changed and remain in the host vault;
private assertions/reference patches are not in the published artifacts.

We then replayed existing canonical public model answers, without invoking a
model or modifying those answers:

| Archived task | Original recorded result | Corrected-evaluator reanalysis |
|---|---|---|
| Idempotent transfer ledger | Pass | Pass |
| Revision-aware negative cache | Pass | Pass |
| Owned per-key snapshot map | Pass | Pass |
| Atomic expiring reservations | Fail | Pass |

**This is post-hoc instrument auditing.** It is not a new live `4/4` run,
confirmation, an unbiased population estimate, semantic transfer or Cortex
improvement. Alpha.39's immutable `3/4` result remains unchanged and verifiable;
its interpretation now carries an independently recorded instrument challenge.
The originating model need not be available to perform this reanalysis.

## Integrated changes

- `contract_aligned_repair.audit_contract_aligned_controls` runs two or more
  distinct permitted repairs plus negative controls through the existing
  evaluator. Any expectation mismatch holds the panel; successful cases cannot
  compensate for a failed one. Audit evidence is typed `local_instrument_audit`.
- `structured_repair_screen` checks exact evaluator challenges before freezing
  or executing new calls. A later caller `resolved` flag cannot silently reopen
  the same commitment. Corrected tests need a new commitment. Historical
  verification deliberately remains separate from present eligibility.
- The shared runner also supports frozen fixed-corpus repeatability, with fresh
  trajectory/chronology checks, exact prior/corpus/model/evaluator binding and an
  atomic one-shot execution claim. This mechanism passed structural tests but
  **was not live-executed**. A changed evaluator cannot masquerade as a repeat.
- Benchmark metadata now accepts hash-valid aligned forges by their schema
  contract rather than requiring alpha.36's particular assertion counts.

Detached evaluator worktrees isolate repository changes, **not the host OS**.
No production source integration, model tool grant, memory admission or policy
mutation was authorized by these receipts. Internal reconstruction is not
external replication or provider attestation.

## Evidence references

- [Public audit receipt](../../benchmarks/results/repair_instrument_revision_2026-09-05.json)
  — `85f4da8eb66522780dd4f170f561374e9b8c776a55b4e246414f36050ee9769d`.
- Challenge receipt — `6321be435050daf8f537d9a17efb729d2eee6252fe7ec0af334ac8f794606c95`.
- [Corrected public forge](../../benchmarks/results/repair_corrected_forge_2026-09-05.json)
  — result `1f6e8eb5e89590d12413333af38235fb00011b35402380d23155eb5a13837dc2`.
- Corrected corpus — `fc18c0387bf653adff28a37060f6f1da65cc895fcdb7b6b50c66b02d1f288a57`.

Exact hidden-corpus replay requires the host vault and retained private runner;
the runner hash is recorded. Public regression tests use small independent
examples. This is not yet independently reproducible external evidence.

## Verification

Executed: **51 focused tests passed in 68.83 seconds** across mathematical
contracts, epistemic kernel, structured repair, contract-aligned repair,
information calibration and evaluator-control tests. Ruff, targeted compileall
and `git diff --check` passed. No full-suite run; no paid inference; no keys or
private evaluator/reference code committed. The zero-call audit ran both
eight-control panels, a four-reference forge and four archived-output replays.
The real host ledger was also checked: both freeze and execution reject the
challenged evaluator before constructing a model runtime, while the original
receipt still reconstructs. The regenerated result inventory classifies the new
audit as local archived reanalysis, not live empirical performance.

## Next experiment — bounded, not automatic

1. Review alternative allowed implementations before commissioning each fresh
   task family. Do not train a model to imitate an evaluator's private layout.
2. Freeze a fresh development corpus and sequential policy before new inference.
   Keep difficulty fixed while confirming mixed observations; do not count
   repeated tasks as independent cases. Neither alpha.39 nor this reanalysis is
   a retrospectively preregistered confirmation sample.
3. When fresh tasks have useful outcome variation, freeze a separate task-only /
   governed-sham / relevant-lesson comparison. Report `relevant - sham` and costs.

The progress in this run is a more trustworthy measurement process. Positive
causal semantic transfer remains **not established**.
