# Fresh audited repair screen — prospective protocol

Starting commit: `115ce7977f656641ab0192bbdac83db1177c699b`.
Product version remains `10.0.0a39`; this is an experiment, not a release.

## Question and budget

Can the selected model repair four newly authored, interaction-heavy modules
when the evaluators have first survived alternate-implementation controls?

This is **task-only development screening**, not a test of Cortex benefit.
Maximum: four new model invocations, one iteration each, zero tools, no automatic
retry, no best-of selection. The host's existing live provider/model is selected
at launch and bound in the canonical preregistration. Provider defaults and
unattested serving revisions remain limitations; no identity is hard-coded in
the core policy. No previous answers, lessons or private evaluators enter prompts.

## Fresh corpus

| Case | Interacting requirements |
|---|---|
| Versioned batch map | Atomic compare-and-swap, retained tombstone revisions, monotonic tokens, deep snapshot ownership |
| Transactional inbox | Persistent deduplication, FIFO, whole-batch rejection, payload ownership |
| Event-time window | Exclusive expiration boundary, monotonic watermark, atomic conflict rejection, expired-ID reuse |
| Dependency batch | Forward references, cycles, atomic registration, completed dependencies, caller-owned list mutation |

These are four authored development examples, not a random population sample or
an independently replicated production-repository corpus. Previous tasks and
archived answers do not count toward their sample size.

Before inference, each evaluator must accept two distinct permitted repairs and
reject three deliberately broken variants. Requirement-to-assertion mapping
and all reference repairs must also pass. Expected control labels remain
host-reviewed, not a general semantic-entailment proof. Private tests/reference
patches stay outside Git and in host secret storage; publish only public tasks,
commitments and bounded audit results.

## Decision fixed before outcomes

Use the existing `assess_sequential_level` policy: screening n=4, confirmation
n=8, developmental target band 0.30–0.70. This invocation executes **only the
initial four**. Confirmation requires separately frozen fresh cases, not repeats.

| Initial outcome | Disposition |
|---|---|
| 0/4 | Screening floor; inspect failures before choosing a fresh level |
| 1/4, 2/4 or 3/4 | Screening candidate; collect confirmation cases at fixed difficulty |
| 4/4 | Screening ceiling on this panel; no transfer claim and no automatic harder run |

No four-case result is called calibrated. No p-value or population inference is
claimed from this hand-selected sample. No result authorizes competence promotion,
source integration, memory admission or policy mutation.

## Implementation and verification

Extend the current structured runner with preregistration `1.2`, binding the
complete control audit to every frozen evaluator. Reuse the one-shot Store
execution claim and sequential calibration helper. Historical `1.0`/`1.1`
interpretations remain unchanged; known challenged commitments remain blocked.

Focused tests must cover missing controls, wrong corpus/commitments, forged
control success, and attempted four-case calibration. Run existing nearby
regressions, Ruff, targeted compileall and diff hygiene. No full-suite run.
Freeze implementation/source identity and policy before any live call. Preserve
all outcomes and record exact executed calls, usage and canonical verification.

If the instrument fails, hold inference and report the failure. Passing controls
only covers these examples; it does not establish complete evaluator soundness.
