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
| Host authority | [native_agent.py](../cortex/native_agent.py)<br/>[autonomous_improvement.py](../cortex/autonomous_improvement.py)<br/>[self_improvement.py](../cortex/self_improvement.py)<br/>[causal_treatment.py](../cortex/causal_treatment.py) | [TOPOLOGY_LAW.md](../docs/intelligence/TOPOLOGY_LAW.md)<br/>[GSI-II.4](research/GSI_II4_CAUSAL_TREATMENT_INTEGRATION_2026-09-08.md) | [test_v100_native_agent.py](../tests/test_v100_native_agent.py)<br/>[test_gsi_ii.py](../tests/test_gsi_ii.py)<br/>[test_gsi_ii1.py](../tests/test_gsi_ii1.py)<br/>[test_gsi_ii2.py](../tests/test_gsi_ii2.py)<br/>[test_gsi_ii3.py](../tests/test_gsi_ii3.py)<br/>[test_gsi_ii4.py](../tests/test_gsi_ii4.py) | Deterministic treatment-delivery mechanics only | MECHANISM TESTED; HOST CONTROL |
| Structured repair | [structured_repair_screen.py](../cortex/structured_repair_screen.py)<br/>[repair_calibration_cohort.py](../cortex/repair_calibration_cohort.py)<br/>[executable_repair_forge.py](../cortex/executable_repair_forge.py) | [FIXED_L3_COHORT_2026-09-06.md](../docs/research/FIXED_L3_COHORT_2026-09-06.md) | [test_repair_calibration_cohort.py](../tests/test_repair_calibration_cohort.py)<br/>[test_multifile_instrument_frontier.py](../tests/test_multifile_instrument_frontier.py) | [fixed_l3_stage0_2026-09-06.json](../benchmarks/results/fixed_l3_stage0_2026-09-06.json)<br/>[fixed_l3_stage1_2026-09-06.json](../benchmarks/results/fixed_l3_stage1_2026-09-06.json) | HISTORICAL 5/8; FRONTIER HELD |
| Competence candidates | [competence.py](../cortex/competence.py)<br/>[competence_revision.py](../cortex/competence_revision.py) | [EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md](../docs/research/EPISTEMIC_INSTRUMENTATION_AND_EVIDENCE_GOVERNED_STATE.md) | [test_v91_competence.py](../tests/test_v91_competence.py) | No dedicated empirical artifact; see tests | GENERAL COMPETENCE NOT ESTABLISHED |
| Transduction policy / receipt | [transduction_policy.py](../cortex/transduction_policy.py)<br/>[observation_capture.py](../cortex/observation_capture.py) | [EPISTEMIC_SUBSTRATE_2026-09-07.md](../docs/research/EPISTEMIC_SUBSTRATE_2026-09-07.md) | [test_epistemic_substrate.py](../tests/test_epistemic_substrate.py) | Zero-call adversarial panel | PRELIMINARY WITHIN TESTS |
| Claim / assurance | [assurance.py](../cortex/assurance.py)<br/>[invariants.py](../cortex/invariants.py)<br/>[CORTEX_CLAIM_REGISTRY.json](../docs/CORTEX_CLAIM_REGISTRY.json) | [STATUS.md](STATUS.md)<br/>[CORTEX_INVARIANTS.json](CORTEX_INVARIANTS.json) | [test_gso_ii.py](../tests/test_gso_ii.py) | Derived claim surface | PRELIMINARY WITHIN TESTS |
| Epistemic snapshot | [epistemic_snapshot.py](../cortex/epistemic_snapshot.py) | [AGENT_START.md](AGENT_START.md) | [test_epistemic_substrate.py](../tests/test_epistemic_substrate.py) | Finite navigation panel | PRELIMINARY WITHIN TESTS |
| Governed cumulative organization | [shadow_organization.py](../cortex/shadow_organization.py)<br/>[assembly.py](../cortex/assembly.py) | [GOVERNED_SELF_ORGANIZATION.md](../docs/research/GOVERNED_SELF_ORGANIZATION.md)<br/>[GSO-IIb](research/GSO_IIB_METABOLIC_ASSEMBLY_2026-09-07.md) | [test_metabolic_assembly.py](../tests/test_metabolic_assembly.py) | [gso_historical_path_inspection_2026-09-06.json](../benchmarks/results/gso_historical_path_inspection_2026-09-06.json) | HELD; MECHANICAL SHADOW ASSEMBLY ONLY |

## Epistemic topology (architectural hypothesis)

Evidence → canonicality → relationships → retrieval → context → cognition.
Correctly stored material can still produce wrong context when current and
historical sources compete for the same canonical role. The knowledge map is a
version-controlled index, **not runtime memory or a second truth database**.

A future navigation-fidelity metric is correct canonical retrievals / tested
navigation tasks. No population measurement is claimed here. Organizational heredity
would additionally require proven causal influence from retained state to fresh
behavior; map relationships do not establish that influence.

CURRENT: GSI-II.4 causal-treatment delivery and execution-lock mechanics in deterministic controls; production unused.
NEXT: GSO-III fresh retention utility only after external lifecycle-evidence
authenticity, isolation/applicability, and invariant gates are explicit, and
only with a new authorization. FUTURE: heredity after replicated utility. None
of those later stages follows merely from this diagram.

