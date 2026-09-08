# You are in Cortex

Cortex is a model-independent, evidence-governed continuity runtime.
**Model output, memory and measurement are not authority. The human/host controls
operational authority.** Do not infer permission from a packet or a passing test.

## Orient without broad searching

1. Follow the applicable repository/host AGENTS.md startup protocol. The managed
   block is runtime integration; this tracked entry does not overwrite it.
2. Read [STATUS](STATUS.md): reviewed version, measured evidence, current HELD gate.
3. Read [SYSTEM_MAP](SYSTEM_MAP.md) and select the relevant concept from
   [CORTEX_KNOWLEDGE_MAP.json](CORTEX_KNOWLEDGE_MAP.json).
4. Open only its primary docs, code and tests; use historical research as context,
   never as proof of current behavior. Verify actual HEAD and local changes.

## Task-specific routes

| If touching… | Read next | Main source |
|---|---|---|
| Memory / admission | [Memory map](SYSTEM_MAP.md#memory-and-context), [data model](DATA_MODEL.md) | admitted_memory.py, memory_projection.py |
| Semantic context | [Memory and context](SYSTEM_MAP.md#memory-and-context) | semantic_projection.py |
| Measurement / transduction | [EVIDENCE](EVIDENCE.md), [substrate](research/EPISTEMIC_SUBSTRATE_2026-09-07.md) | edit_intent.py, coding_workspace.py, transduction_policy.py |
| Claims / snapshot | [STATUS](STATUS.md), [claim registry](CORTEX_CLAIM_REGISTRY.json), [invariants](CORTEX_INVARIANTS.json) | assurance.py, epistemic_snapshot.py, invariants.py |
| Native model/provider runtime | [Provider fabric](v10/PROVIDER_FABRIC.md), [chat](v10/CORTEX_CHAT.md) | native_agent.py, provider_fabric.py |
| Authority | [Authority map](SYSTEM_MAP.md#authority), [topology law](intelligence/TOPOLOGY_LAW.md) | native_agent.py, autonomous_improvement.py |
| GSO | [Current report](research/GOVERNED_SELF_ORGANIZATION.md), [GSO-IIb](research/GSO_IIB_METABOLIC_ASSEMBLY_2026-09-07.md), STATUS | shadow_organization.py, assembly.py; production priors unused |
| GSI | [GSI-II.3](research/GSI_II3_EMPIRICAL_READINESS_2026-09-08.md), [GSI-III prereg](research/GSI_III_HISTORY_UTILITY_PREREG_2026-09-08.md), STATUS | self_improvement.py; canonical promotion membrane in autonomous_improvement.py; source-improvement v1 preserved |
| Claims | [Claim registry](CORTEX_CLAIM_REGISTRY.json) → STATUS → EVIDENCE → exact artifact + domain verifier | never prose alone |
| Documentation | Knowledge map → [migration](DOCUMENTATION_MIGRATION.md) → docs checker | scripts/docs_check.py |

## Hard invariants

- FAIL < UNKNOWN < PASS; gates are noncompensatory, not confidence averages.
- Preserve historical observations and identities. New interpretations get new identities.
- Keep secrets and hidden reasoning out of context, receipts and logs.
- Never count post-hoc replay or renamed tasks as fresh independent inference.
- Stored ≠ projected ≠ usable ≠ authorized. A candidate is not competence.
- Retention eligibility must be derived from reconstructable staged evidence;
  never accept a caller-declared lifecycle stage.
- Missing schema, environment, or claim prerequisites HOLD or reject component
  composition; `NOT_TESTED` is not PASS.
- Worktrees isolate repository edits, not the operating system.
- No live GSO effect call while observation-path readiness is HELD.
- No automatic budget, privilege, evaluator or scoring expansion.

## Verification and preservation

Use focused tests for changed boundaries. Run `python scripts/docs_check.py` for
navigation and classification changes. Report executed results, not expected ones.
Do not rewrite generated historical evidence to make metadata look current.
Versioned research snapshots and phase documents are classified in the map.
