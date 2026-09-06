# Cortex system map

Canonical bird's-eye architecture. [Status](STATUS.md) owns claims; this map owns
navigation. Every row links actual code and tests; absent empirical evidence is
explicit, not filled with inferred success.

```text
HOST AUTHORITY ──────────────── bounds operational effect
         │
CLI / chat / external agent
         ↓
Native runtime ↔ provider fabric
         ↑                 ↓
Memory → semantic context → candidate
  ↑                          ↓
Store / epistemic state ← observation / assured measurement
  ↑                          ↓
  └──── governed retention ← selection   [cumulative loop: RESEARCH / HELD]
```

## Memory and context

Admission, selection and semantic projection remain separate. Messages are session
records, not automatic durable memory. The epistemic kernel's bounded compiler is
not evidence of model decision equivalence.

## Authority

Host grants bound tools and commands. Model confidence, receipt integrity and
research outcomes cannot grant operational effect. Source-improvement machinery
requires separate host policy. No production GSO loop is commissioned.

## Concept traces

| Concept | Code | Primary docs | Tests | Evidence / gap | Claim |
|---|---|---|---|---|---|
| Store / receipts | [store.py](../cortex/store.py) | [DATA_MODEL.md](../docs/DATA_MODEL.md) | [test_symbiosis_ledger.py](../tests/test_symbiosis_ledger.py) | [fixed_l3_stage0_2026-09-06.json](../benchmarks/results/fixed_l3_stage0_2026-09-06.json) | VERIFIED WITHIN TESTS |
| Governed memory | [admitted_memory.py](../cortex/admitted_memory.py)<br/>[memory_projection.py](../cortex/memory_projection.py) | [DATA_MODEL.md](../docs/DATA_MODEL.md) | [test_admitted_memory.py](../tests/test_admitted_memory.py) | No dedicated empirical artifact; see tests | VERIFIED WITHIN TESTS |
| Semantic projection | [semantic_projection.py](../cortex/semantic_projection.py) | [EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md](../docs/research/EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md) | [test_v100_alpha14_semantic_projection.py](../tests/test_v100_alpha14_semantic_projection.py) | No dedicated empirical artifact; see tests | UTILITY NOT ESTABLISHED |
| Epistemic state | [epistemic_kernel.py](../cortex/epistemic_kernel.py) | [MATHEMATICAL_CONTRACT_AUDIT_2026-09-04.md](../docs/research/MATHEMATICAL_CONTRACT_AUDIT_2026-09-04.md) | [test_v100_alpha16_epistemic_kernel.py](../tests/test_v100_alpha16_epistemic_kernel.py) | No dedicated empirical artifact; see tests | VERIFIED WITHIN TESTS |
| Instrument assurance | [epistemic_instrumentation.py](../cortex/epistemic_instrumentation.py)<br/>[contract_aligned_repair.py](../cortex/contract_aligned_repair.py) | [EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md](../docs/research/EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md) | [test_epistemic_instrumentation.py](../tests/test_epistemic_instrumentation.py) | [fixed_l3_forge_2026-09-06.json](../benchmarks/results/fixed_l3_forge_2026-09-06.json) | BOUNDED CONTROLS |
| Transduction assurance | [edit_intent.py](../cortex/edit_intent.py)<br/>[coding_workspace.py](../cortex/coding_workspace.py) | [TRANSDUCTION_REVISION_2026-09-06.md](../docs/research/TRANSDUCTION_REVISION_2026-09-06.md) | [test_transduction_assurance.py](../tests/test_transduction_assurance.py)<br/>[test_patch_transport.py](../tests/test_patch_transport.py) | [gso_transduction_revision_2026-09-06.json](../benchmarks/results/gso_transduction_revision_2026-09-06.json) | COMPLETE PATH HELD |
| Native agent runtime | [native_agent.py](../cortex/native_agent.py)<br/>[chat_service.py](../cortex/chat_service.py) | [README.md](../docs/v10/README.md)<br/>[CORTEX_CHAT.md](../docs/v10/CORTEX_CHAT.md) | [test_v100_native_agent.py](../tests/test_v100_native_agent.py) | [fixed_l3_stage0_2026-09-06.json](../benchmarks/results/fixed_l3_stage0_2026-09-06.json) | BOUNDED LIVE EVIDENCE |
| Provider fabric | [provider_fabric.py](../cortex/provider_fabric.py)<br/>[secret_store.py](../cortex/secret_store.py) | [PROVIDER_FABRIC.md](../docs/v10/PROVIDER_FABRIC.md)<br/>[SECRET_STORAGE.md](../docs/v10/SECRET_STORAGE.md) | [test_v100_alpha2_interface.py](../tests/test_v100_alpha2_interface.py) | No dedicated empirical artifact; see tests | LIVE PATHS NOT ALL PROVIDERS RETESTED |
| Host authority | [native_agent.py](../cortex/native_agent.py)<br/>[autonomous_improvement.py](../cortex/autonomous_improvement.py) | [TOPOLOGY_LAW.md](../docs/intelligence/TOPOLOGY_LAW.md)<br/>[SECURITY.md](../SECURITY.md) | [test_v100_native_agent.py](../tests/test_v100_native_agent.py) | No dedicated empirical artifact; see tests | MECHANISM TESTED; HOST CONTROL |
| Structured repair | [structured_repair_screen.py](../cortex/structured_repair_screen.py)<br/>[repair_calibration_cohort.py](../cortex/repair_calibration_cohort.py)<br/>[executable_repair_forge.py](../cortex/executable_repair_forge.py) | [FIXED_L3_COHORT_2026-09-06.md](../docs/research/FIXED_L3_COHORT_2026-09-06.md) | [test_repair_calibration_cohort.py](../tests/test_repair_calibration_cohort.py)<br/>[test_multifile_instrument_frontier.py](../tests/test_multifile_instrument_frontier.py) | [fixed_l3_stage0_2026-09-06.json](../benchmarks/results/fixed_l3_stage0_2026-09-06.json)<br/>[fixed_l3_stage1_2026-09-06.json](../benchmarks/results/fixed_l3_stage1_2026-09-06.json) | HISTORICAL 5/8; FRONTIER HELD |
| Competence candidates | [competence.py](../cortex/competence.py)<br/>[competence_revision.py](../cortex/competence_revision.py) | [EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md](../docs/research/EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md) | [test_v91_competence.py](../tests/test_v91_competence.py) | No dedicated empirical artifact; see tests | GENERAL COMPETENCE NOT ESTABLISHED |
| Governed cumulative organization | PLANNED — no implementation | [GOVERNED_SELF_ORGANIZATION.md](../docs/research/GOVERNED_SELF_ORGANIZATION.md) | No cycle test | [gso_historical_path_inspection_2026-09-06.json](../benchmarks/results/gso_historical_path_inspection_2026-09-06.json) | HELD; NO RECURSIVE EFFECT |

## Epistemic topology (architectural hypothesis)

Evidence → canonicality → relationships → retrieval → context → cognition.
Correctly stored material can still produce wrong context when current and
historical sources compete for the same canonical role. The knowledge map is a
version-controlled index, **not runtime memory or a second truth database**.

A future navigation-fidelity metric is correct canonical retrievals / tested
navigation tasks. No population measurement is claimed here. Organizational heredity
would additionally require proven causal influence from retained state to fresh
behavior; map relationships do not establish that influence.

CURRENT: transduction closure. NEXT: full observation binding and shadow kernel.
FUTURE: mechanical recursion → homeostasis → matched retention → second-cycle
replication → organizational heredity/model ecology → bounded active adaptation.
All later stages remain planned; none follows merely from this diagram.

