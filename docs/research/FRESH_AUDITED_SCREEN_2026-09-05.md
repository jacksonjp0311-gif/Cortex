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

## Executed result

**Four new live calls, four successful repairs, screening ceiling.** No additional
call or harder run was launched. This is distinct from the earlier same-answer,
post-hoc evaluator correction. Version remains `10.0.0a39`.

| Case | Intent compilation | Frozen evaluator |
|---|---|---|
| Versioned batch map | Pass | Pass |
| Transactional inbox | Pass | Pass |
| Event-time window | Pass | Pass |
| Dependency batch | Pass | Pass |

Before inference, all **20 controls** matched their host-reviewed labels: eight
permitted implementations passed and twelve mutants failed. All four reference
repairs measured baseline failure → candidate pass; 16 public requirements
mapped to 10 private assertion groups. This coverage is finite, not exhaustive.

The runtime selected **OpenAI / gpt-5.6-sol** through the existing Provider Fabric.
Evidence class: `live_empirical`, without cryptographic provider attestation.
Serving version/configuration remain provider-declared/defaults, not an exact
model-weight commitment. Calls used one iteration and zero agent tools each.
The host evaluator ran candidate tests locally in disposable repositories;
this is **not an OS security sandbox**.

Canonical reconstruction returned `valid=true`, `errors=[]`. Its scope is
receipt integrity and experiment bindings; it did not rerun external inference.
All four model outputs compiled. Provider-reported usage totaled **3,830 input +
3,707 output = 7,537 tokens**. The report maps `prompt_tokens` and
`completion_tokens` from the existing response receipts into normalized labels.
The initial report projection looked only for normalized keys and returned null;
correcting that public summary required no new calls or canonical receipt edits.
No verified dollar price is asserted.

### Mathematical interpretation

For observed successes \(s\) in the initial \(n=4\) screen:

\[
\operatorname{Next}(s)=
\begin{cases}
\text{inspect floor}, & s=0,\\
\text{collect fresh confirmation at this level}, & 0<s<4,\\
\text{hold ceiling panel out of transfer testing}, & s=4.
\end{cases}
\]

The recorded helper recommends `move_harder` for a ceiling; that is advisory,
not permission to launch calls. Every initial outcome has
`baseline_calibrated=false`. The 30–70% band applies to the separately planned
confirmation stage; it cannot turn a mixed four-case screen into calibration.

The observed baseline \(\hat p_A=1\) leaves no observed positive binary headroom
on these cases. It does **not** establish population success probability 1.
There was no semantic-treatment arm, so neither \(G_C\) nor lesson-transfer
benefit was measured. No training, competence promotion or self-improvement
claim follows from this result.

### What this changes for the next experiment

The evaluator controls worked on the tested alternatives, but adding interacting
requirements still did not produce a discriminative panel. These are small
single-file modules built by mutating working implementations; some defects
remain conspicuous (for example a disabled guard). Complexity of the prose is
not evidence of task difficulty. The results do not isolate why the model passed.

Do not spend another batch simply adding requirements to these templates.
First prepare a small, separately reviewed development corpus of realistic
defects with nontrivial localization, explicit contracts, alternate valid repairs
and negative controls. Inspect it locally before authorizing fresh screening.
Keep source lessons and eventual held-out transfer tasks separate. No new corpus
or further paid run is claimed here.

### Engineering verification

- Circulation-adjacent repair/control regressions: **22 passed in 102.26s**.
- Sequential calibration regression suite: **7 passed in 0.13s**.
- Final rerun of the new audited-screen integration test: **1 passed,
  8 deselected in 23.62s** (a repeat, not another distinct test).
- Public benchmark-inventory classification tests: **3 passed in 0.09s**.
- Ruff, targeted compileall and `git diff --check` run; no full repository suite.
- Four live calls completed; zero automatic retry or follow-on call.
- No credentials, private tests or reference patches committed. Host keys and
  private evaluator material remain in the host vault/outside Git.

### Evidence identities

| Surface | Identity |
|---|---|
| Frozen runtime source | `a95522803605fd1fdf52816c07da056801c9efeb` |
| Fresh corpus | `f88ac380c38b37f04b68764b94a3510193f24faed8ead7bfee2bcdcebc71248b` |
| Control audit | `81764b5deb781d67caf1440fdc423bf2208416e43b0a97ba43e9f0b4997c5389` |
| Preregistration receipt | `aae10a89361033845dbe10dc998abbeeb5b0918873ce5a58e0cf4197fddbd046` |
| Result receipt | `cf4757d19424538a7d2bd8faf7befcba31a23d8741459b47289e06a2ddb899fc` |

Public artifacts: [forge and controls](../../benchmarks/results/fresh_audited_forge_2026-09-05.json),
[frozen protocol](../../benchmarks/results/fresh_audited_screen_prereg_2026-09-05.json),
[live result](../../benchmarks/results/fresh_audited_screen_result_2026-09-05.json).
The artifact inventory classifies these separately; inventory metadata is not
a substitute for reconstruction from the local immutable ledger.
