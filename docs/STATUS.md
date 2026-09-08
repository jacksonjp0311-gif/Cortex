# Current Cortex status

Canonical current status · reviewed September 7, 2026 · product **10.0.0a39**.
Runtime revision anchor: `89779803ef48f94816172929bd08be86dc148e8a`.
Public HEAD at GSI-II.2 implementation start: `8e05bd171b2ac5f3c73d9534298be7f6c2c2a753`
("Close GSI-II cumulative loop mechanics").
That revision's exact-head matrix completed success:
[CI run 34164000790](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34164000790).
Initial review baseline: `ad29b81a2b961294368fa795998fefd1134a4b5b`.
The anchor is the reviewed baseline, not a self-referential claim that this document
contains its own final commit. Use `git rev-parse HEAD` for checkout identity and
[knowledge map](CORTEX_KNOWLEDGE_MAP.json) for version/content drift checks.
Exact-head CI for the GSI-II.2 revision must be re-checked after push; do not treat a queued or in-progress matrix as passed.

## Current gate

**CURRENT: GSI-II.2 proof-chain mechanics verified in deterministic controls; exact-head CI pending. NEXT: live provider GSI trial and GSO-III remain unauthorized.**

### Platform health and substrate at b0106c7

[CI run 34077635691](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34077635691)
completed **success** on the declared matrix: Windows/Ubuntu × Python 3.10/3.12/3.13.
`PLATFORM_HEALTH = PASS_WITHIN_DECLARED_MATRIX` at
`b0106c762b5784a33259141b9c1e5de35de17dce`. Public `main` later moved only by a
star-lattice metrics refresh (`ba927df`); that is not a product-source revision.
Substrate HEAD `89779803ef48f94816172929bd08be86dc148e8a` then passed the same
declared matrix: [run 34090571873](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34090571873).

A prior read-only audit found that `_compiled_case_errors` does not reject
successful-but-incomplete capture, successful-but-timed-out capture, negative
byte lengths, or `authority_effect=true` environments. That historical helper
identity is unchanged. Derived inspection is now
`cortex-observation-conformance/1.0` and does not silently upgrade archived
verifiers.

Prospective `TransductionPolicy` is frozen before compilation.
`TransductionReceipt` must satisfy that policy. Subject, instrument and
environment identities are separate. Observation-surface enforcement is
worktree-file CHECKED and otherwise DECLARATIVE_ONLY. Bounded streaming capture
(`cortex-host-raw-observation/1.2`) hashes incrementally; process-tree cleanup
remains UNKNOWN. Claims live in [CORTEX_CLAIM_REGISTRY.json](CORTEX_CLAIM_REGISTRY.json).
Assurance cases and typed debt cannot grant authority. Epistemic snapshots and
context packets are derived. Shadow organization, mechanical recursive closure
and bounded self-stabilization are production-inert. See
[epistemic substrate](research/EPISTEMIC_SUBSTRATE_2026-09-07.md).

GSO-II adds a non-authoritative invariant registry, snapshot checkout/source
binding, independent receipt attestation, preserved v2 intent identity, a
withheld navigation generalization panel, and recovery from corrupted state
without being handed disturbance names. Process-tree cleanup is attempted
(`taskkill /T` on Windows, `killpg` on POSIX) and still not a universal
guarantee. Experiment subprocesses use an explicit environment allowlist.
Network and external-path isolation remain UNENFORCED / DECLARATIVE_ONLY.
See [GSO-II](research/GSO_II_INVARIANT_CLOSURE_2026-09-07.md) and
[invariants](CORTEX_INVARIANTS.json).

GSI-II adds `cortex/self_improvement.py` beside preserved source-improvement v1.
GSI-II.1 closes the loop: withheld metric comparison, strict attestation,
workload vs constitutional gates, identity-persistent constraints with machine
enforcement, historical success reuse, generation adjacency, and post-promotion
remeasurement through existing canary/apply/rollback. Two synthetic generations
verify mechanics only. `cumulative_self_improvement_established` remains false.
No live provider trial was run.
See [GSI-II](research/GSI_II_CUMULATIVE_GOVERNED_SELF_IMPROVEMENT_2026-09-07.md)
and [GSI-II.1](research/GSI_II1_CUMULATIVE_LOOP_CLOSURE_2026-09-07.md).

GSI-II.2 reconstructs constitutional gates from evidence, shares one authenticated
promotion membrane with alpha.8, promotes the exact attested proposal, reapplies
the full frozen improvement disposition after live application, types bounded
experiment-evidence influence, limits exclusion predicates to candidate-causal
failures, and reconstructs realized-generation chains from canonical Store
receipts. Incommensurable utilities remain a vector. Holdout capability
separation is interface-only and live-provider eligibility remains false. See
[GSI-II.2](research/GSI_II2_PROOF_CHAIN_CLOSURE_2026-09-07.md).

No live retention-utility or model-turnover heredity experiment was run.
[GSO-III](research/GSO_III_RETENTION_UTILITY_PREREG.md) is preregistered only.

The current GSO-IIb tightening makes component composition fail closed: type
and schema compatibility are independent gates, missing or `NOT_TESTED`
environment state remains `UNKNOWN`, and only bounded positive claim states
satisfy claim dependencies. Retention candidates can no longer declare
themselves `RETENTION_ELIGIBLE`; eligibility is reconstructed across adjacent
`PROPOSED -> OBSERVED -> VERIFIED -> REPLICATED -> RETENTION_ELIGIBLE`
transitions. The zero-call assembly control now changes candidate ranking, not
only a topology identity hash. Its lifecycle evidence is explicitly synthetic;
external receipt authenticity and retention utility remain **NOT TESTED**.

## Preserved historical gate chronology

The records below preserve earlier gate states. They are not descriptions of
the current runtime when a later statement above supersedes them.

GSO-Ib read-in at `61869b68348efe85b114fb7bb7c2d986fb4295b3`:
[exact-HEAD CI](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34063844849)
passed five matrix coordinates but failed Windows/Python 3.10 in two raw-observation
tests. The traceback localized a broad subprocess mock intercepting Python's
own platform discovery, returning bytes to a text parser. This is a test-harness
failure, distinct from the earlier Store race. Mocks now intercept only their
declared fixture/Git command and delegate unrelated subprocesses unchanged.
Controls explicitly exercise cold platform discovery and a text-mode discovery
subprocess. Platform closure remains **HELD** until the corrected matrix passes;
prospective-policy, assurance-case, snapshot and shadow gates are not declared
complete by this repair. No runtime schemas or historical observations changed.

Gate A audit of `d80d020000b443d4313203e5479568ea5a6b1ca5`:
[CI run 34034718191](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34034718191)
failed only Windows/Python 3.10; the other five matrix coordinates passed.
`test_parallel_nonce_is_database_exactly_once` encountered interleaved Store
trigger replacement (`trigger ... already exists`), followed by a leaked handle
during Windows cleanup. This is a concurrency defect, not evidence that Python
3.10 support should be removed. Schema replacement now uses one SQLite write
transaction; constructor failure closes the connection and rolls back that
transaction. Regression controls cover contended opens and failed initialization
restoring receipt guards. Historical receipt contents are unchanged.

Local validation: 43 focused Store/control/receipt tests passed on Windows
Python 3.12.2; 37 focused tests passed on Windows Python 3.10.20 (the failed CI
coordinate used 3.10.11). Four documentation checker tests and canonical-map
validation also passed. These are deterministic controls, with zero model calls.
The matrix now includes the new initialization controls explicitly.

The corrected full remote matrix at `b0106c7` is now **PASS_WITHIN_DECLARED_MATRIX**.
This repair does not claim to serialize every legacy migration or prove universal
concurrent migration safety.

Strict compiler v2 rejects non-string edits and represents missing terminal
newlines explicitly. Compiler v1 remains reconstructable for historical objects.
Isolated verification v1.1 records applied target hashes before execution and
holds candidates changed by the evaluator. The [revision report](research/TRANSDUCTION_REVISION_2026-09-06.md)
links focused tests and the new zero-call control artifact.

At that revision, the changes closed three sampled counterexamples, not
universal path assurance. Structured-screen reconstruction still lacked full
compiler-to-observed artifact binding; worktrees were not OS sandboxes, and no
shadow organization kernel or new live experiment was commissioned.

Parallel engineering while CI is pending: isolated verification v1.3 now records
separate stdout/stderr SHA-256 digests and byte lengths, return code, duration,
timeout and capture-completeness state before producing a lossy bounded preview.
Timeout hashes describe partial capture only. Four new zero-call controls cover
lossy decoding, truncation, real binary subprocess capture, and partial timeout
capture. Together with workspace and transduction controls, 14 focused tests pass.
Historical v1.1 observations are not retroactively upgraded. This is raw capture
identity, not complete observation binding. Raw observation v1.1 additionally
binds a bounded environment identity: OS family/release, architecture, Python
implementation/version, Git version where available, and subprocess execution
policy. It does not capture hostnames, filesystem paths, or environment variables.
Dependency state, non-Python toolchain and inherited process environment remain
unresolved; no full environment-applicability claim follows. Four environment
controls cover runtime differences, missing Git, Git timeout and observation
binding. Compiler-to-applied equality in structured-screen receipts remains unresolved:
compiler postimages are normalized text hashes, while applied postimages are raw
byte hashes. These representations require an explicit transformation contract.
At that historical revision, captured streams were buffered in memory and
output resource limits remained an explicit gap. The current bounded streaming
capture is described in the current-state section above.

An opt-in `compilation=` path in isolated verification now reconstructs compiler
identity and binds a prospective transduction contract to source HEAD, intent,
compiler implementation files, proposal, preimages, expected postimages, host
verification contract and bounded environment. It requires exact UTF-8/LF bytes;
CR-containing preimages are unsupported, not normalized. Applied bytes must equal
compiler expected bytes before evaluator execution; target mutations afterward
hold the path. This is verification v2.0, not a retroactive upgrade of historical
receipts. New structured repair case/result v2 records now supply this compilation
object and preserve it for zero-execution reconstruction from archived model
output. Their verifier checks compiled patch identity, expected/applied/post-run
hashes on successful observations, environment identity and raw observation
bindings. Legacy v1 records retain their historical reconstruction path. New
compiled fixtures write exact UTF-8 bytes and disable Git autocrlf locally;
legacy fixture behavior is unchanged. This is a delivery-path revision, not new
live evidence or permission to rerun an exhausted cohort.
No evaluator-validity, OS isolation, or general cognitive inference follows.

| Area | Evidence-supported disposition | Where to verify |
|---|---|---|
| Store / native runtime / memory | VERIFIED within tests | [System map](SYSTEM_MAP.md) |
| Provider-backed inference | Historical LIVE EMPIRICAL; not provider-attested | [Fixed cohort](research/FIXED_L3_COHORT_2026-09-06.md) |
| Original fixed L3 outcome | 3/4 + 2/4 = **5/8**, transport-confounded | [Stage 0](../benchmarks/results/fixed_l3_stage0_2026-09-06.json), [stage 1](../benchmarks/results/fixed_l3_stage1_2026-09-06.json) |
| Archived candidate replay | Zero new calls; three passed unchanged tests | [Transport audit](../benchmarks/results/fixed_l3_transport_audit_2026-09-06.json) |
| Initial GSO audit | Historical HELD, 13/16 expectations | [Original audit](../benchmarks/results/gso_transduction_committed_check_2026-09-06.json) |
| Declared CI matrix at b0106c7 | PASS_WITHIN_DECLARED_MATRIX | [run 34077635691](https://github.com/jacksonjp0311-gif/Cortex/actions/runs/34077635691) |
| Current finite controls | Bounded revision, see exact executed receipt | [Revision](research/TRANSDUCTION_REVISION_2026-09-06.md) |
| Prospective policy / receipt | PRELIMINARY within tests | [Substrate](research/EPISTEMIC_SUBSTRATE_2026-09-07.md), [claims](CORTEX_CLAIM_REGISTRY.json) |
| Mechanical recursive closure | PRELIMINARY within synthetic zero-call controls; behavioral ranking delta, not utility | [Shadow kernel](../cortex/shadow_organization.py) |
| Retention utility / heredity | NOT ESTABLISHED | [GSO report](research/GOVERNED_SELF_ORGANIZATION.md) |
| Reasoning frontier | NOT ESTABLISHED | [GSO report](research/GOVERNED_SELF_ORGANIZATION.md) |
| Semantic treatment gain | NOT ESTABLISHED | [Evidence guide](EVIDENCE.md) |
| Cumulative organization / heredity | NOT ESTABLISHED | [Research roadmap](research/README.md) |

A historical valid receipt remains valid as a record even when its interpretation
is challenged. The exhausted eight-task cohort must not be rerun as fresh data.
Null, failed and post-hoc evidence remain separate. No population accuracy,
consciousness, general competence or autonomous source authority follows.

## Authority

Humans/hosts issue capabilities and approve operational effect. Evidence, memory,
model confidence and passing tests cannot widen those grants. Research metadata
has closed mutation, execution, admission, policy and adaptation authority.

## Next threshold

OS isolation, process-tree cleanup, and full environment applicability remain
UNKNOWN/HELD. Do not run a live retention-utility or model-turnover heredity
experiment until those applicability gates are explicit and a new authorization
is issued. Production runtime must not consume shadow priors.
