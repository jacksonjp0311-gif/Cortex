# Current Cortex status

Canonical current status · reviewed September 6, 2026 · product **10.0.0a39**.
Runtime revision anchor: `6f134f15a88123b690094daa642f2aee5a5a5c8f`.
Initial review baseline: `ad29b81a2b961294368fa795998fefd1134a4b5b`.
The anchor is the reviewed baseline, not a self-referential claim that this document
contains its own final commit. Use `git rev-parse HEAD` for checkout identity and
[knowledge map](CORTEX_KNOWLEDGE_MAP.json) for version/content drift checks.

## Current gate

**CURRENT: transduction assurance. NEXT: complete observation binding.**
Strict compiler v2 rejects non-string edits and represents missing terminal
newlines explicitly. Compiler v1 remains reconstructable for historical objects.
Isolated verification v1.1 records applied target hashes before execution and
holds candidates changed by the evaluator. The [revision report](research/TRANSDUCTION_REVISION_2026-09-06.md)
links focused tests and the new zero-call control artifact.

These changes close the three sampled counterexamples, not universal path
assurance. Structured-screen reconstruction still lacks full compiler-to-observed
artifact binding; raw observation transport remains bounded/lossy; worktrees are
not OS sandboxes. No shadow organization kernel or new live experiment is commissioned.

| Area | Evidence-supported disposition | Where to verify |
|---|---|---|
| Store / native runtime / memory | VERIFIED within tests | [System map](SYSTEM_MAP.md) |
| Provider-backed inference | Historical LIVE EMPIRICAL; not provider-attested | [Fixed cohort](research/FIXED_L3_COHORT_2026-09-06.md) |
| Original fixed L3 outcome | 3/4 + 2/4 = **5/8**, transport-confounded | [Stage 0](../benchmarks/results/fixed_l3_stage0_2026-09-06.json), [stage 1](../benchmarks/results/fixed_l3_stage1_2026-09-06.json) |
| Archived candidate replay | Zero new calls; three passed unchanged tests | [Transport audit](../benchmarks/results/fixed_l3_transport_audit_2026-09-06.json) |
| Initial GSO audit | Historical HELD, 13/16 expectations | [Original audit](../benchmarks/results/gso_transduction_committed_check_2026-09-06.json) |
| Current finite controls | Bounded revision, see exact executed receipt | [Revision](research/TRANSDUCTION_REVISION_2026-09-06.md) |
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

Bind reconstructed compiler output to applied-before-evaluation artifacts and
freeze observation-path/instrument requirements prospectively. Then audit faults
and contamination. Only after explicit readiness may shadow retention be tested;
only after that may a fresh matched effect study be proposed.
