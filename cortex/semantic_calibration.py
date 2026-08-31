"""Sham-controlled, answer-sealed semantic-transfer calibration preflight.

This module makes no provider calls. It freezes the smallest live screening
plan that could locate a non-ceiling task level. Outcomes must later arrive
through canonical model-circulation reconstruction, never caller booleans.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import __version__
from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance, verify_adapter_provenance
from .evaluation import TaskEvaluationContract, evaluate_task_result
from .information_calibration import assess_sequential_level
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-semantic-calibration-preflight/1.0"
CORPUS_SCHEMA = "cortex-semantic-calibration-corpus/1.0"
PRIVATE_KEY_SCHEMA = "cortex-semantic-calibration-answer-key/1.0"
CLAIM_BOUNDARY = (
    "This preflight seals development calibration material only. It does not "
    "establish semantic transfer, model improvement, or execution authority."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _case(
    level: int, variant: int, prompt: str, answer: str, *, secret_seed: str
) -> tuple[dict[str, Any], str]:
    identity = {
        "family": "cache_coherence_repair",
        "difficulty_level": int(level),
        "variant": int(variant),
        "prompt": str(prompt),
    }
    case_id = f"scr_{_sha(identity)[:20]}"
    public = {
        **identity,
        "case_id": case_id,
        "response_contract": "Return exactly one option token: A, B, C, or D.",
        "answer_commitment": _sha(
            {"case_id": case_id, "answer": answer, "secret_seed": secret_seed}
        ),
        "development_only": True,
    }
    return public, answer


def build_semantic_calibration_bundle(*, secret_seed: str) -> dict[str, Any]:
    """Build three disjoint difficulty levels with four variants per level."""
    if not str(secret_seed).strip():
        raise ValueError("secret_seed is required")
    templates = {
        1: [
            ("A service writes a new value, then reads an old value from its local cache. Which action best restores coherence? A invalidate the cache before reread; B retry the write unchanged; C rename the field; D increase logging.", "A"),
            ("After configuration mutation, a cached parser result is stale. Choose the relevant repair. A add a comment; B clear the cache before parsing again; C sort keys; D increase timeout.", "B"),
            ("A memoized lookup survives a successful update and returns the prior record. Choose the repair. A change formatting; B add retries; C invalidate memoized state before lookup; D suppress the assertion.", "C"),
            ("A local snapshot remains after mutation and the next read uses it. Choose the repair. A expand the buffer; B rename the snapshot; C delay shutdown; D invalidate the snapshot before reread.", "D"),
        ],
        2: [
            ("write() updates the database. read() first checks object_cache and returns a pre-write object. Tests pass in isolation but fail when write and read share a process. A invalidate object_cache on successful write; B randomize test order; C catch the assertion; D lengthen the transaction.", "A"),
            ("A deployment changes policy version 7 to 8. resolve_policy() continues returning version 7 until restart because its process map is populated before the change. A restart every request; B evict the keyed map entry after committed mutation; C ignore version; D duplicate the map.", "B"),
            ("update_schema() commits, yet describe() returns the old schema from a lazy singleton. A add sleep; B retry commit; C invalidate the singleton at the mutation boundary; D hide the mismatch.", "C"),
            ("A successful feature toggle update is followed by an old value only in long-lived workers; fresh workers are correct. A widen lock; B reorder imports; C change serializer; D clear worker-local cached state after update.", "D"),
        ],
        3: [
            ("A versioned read-through cache uses key (tenant,id) while mutation advances an unkeyed generation counter. Old entries remain addressable and no exception occurs. Choose the smallest causal repair. A bind cache validity to the generation and evict on mutation; B retry network reads; C enlarge cache; D suppress old values.", "A"),
            ("Two layers cache the same object. Mutation invalidates L1, but a later L1 miss repopulates from stale L2. A invalidate only L1 twice; B invalidate or version both cache layers at commit; C add tracing; D increase TTL.", "B"),
            ("A transaction callback evicts a cache before commit; another reader repopulates the old value before commit completes. After commit the stale entry survives. A move eviction earlier; B disable tests; C evict after successful commit or version entries; D add a print.", "C"),
            ("A derived index is rebuilt from an object cache after source mutation. The source write is correct, but the cache still contains the previous graph. A rebuild more often from the same cache; B add a second index; C reorder output; D invalidate the source cache before rebuilding the index.", "D"),
        ],
    }
    public_cases: list[dict[str, Any]] = []
    answers: dict[str, str] = {}
    for level, rows in templates.items():
        for variant, (prompt, answer) in enumerate(rows, 1):
            public, expected = _case(
                level, variant, prompt, answer, secret_seed=str(secret_seed)
            )
            public_cases.append(public)
            answers[public["case_id"]] = expected
    key_material = {
        "schema_version": PRIVATE_KEY_SCHEMA,
        "secret_seed_commitment": _sha(str(secret_seed)),
        "answers": answers,
    }
    public_material = {
        "schema_version": CORPUS_SCHEMA,
        "version": __version__,
        "family": "cache_coherence_repair",
        "levels": [1, 2, 3],
        "variants_per_level": 4,
        "case_count": len(public_cases),
        "initial_screen_level": 2,
        "initial_screen_case_ids": [
            row["case_id"] for row in public_cases if row["difficulty_level"] == 2
        ],
        "cases": public_cases,
        "answer_key_commitment": _sha(key_material),
        "secret_seed_commitment": _sha(str(secret_seed)),
        "answers_present": False,
        "development_only": True,
        "confirmatory_eligible": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    manifest = {**public_material, "corpus_hash": _sha(public_material)}
    return {"manifest": manifest, "answer_key": key_material}


def verify_semantic_calibration_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else None
    answer_key = bundle.get("answer_key") if isinstance(bundle, Mapping) else None
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(answer_key, Mapping):
        return {"valid": False, "state": "fail", "errors": ["bundle_shape_invalid"]}
    material = {key: value for key, value in manifest.items() if key != "corpus_hash"}
    if manifest.get("schema_version") != CORPUS_SCHEMA:
        errors.append("corpus_schema_invalid")
    if manifest.get("corpus_hash") != _sha(material):
        errors.append("corpus_hash_invalid")
    if manifest.get("answer_key_commitment") != _sha(answer_key):
        errors.append("answer_key_commitment_invalid")
    cases = manifest.get("cases") if isinstance(manifest.get("cases"), list) else []
    if any("answer" in row or "expected" in row for row in cases):
        errors.append("answer_leaked_into_public_manifest")
    case_ids = {str(row.get("case_id") or "") for row in cases}
    answer_ids = {str(key) for key in (answer_key.get("answers") or {})}
    if case_ids != answer_ids:
        errors.append("answer_key_case_binding_invalid")
    if manifest.get("development_only") is not True or manifest.get("confirmatory_eligible") is not False:
        errors.append("development_boundary_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


def build_semantic_calibration_preflight(
    lesson_pair: Mapping[str, Any], bundle: Mapping[str, Any]
) -> dict[str, Any]:
    """Freeze a four-call screen; source and outcomes cannot open transfer."""
    bundle_check = verify_semantic_calibration_bundle(bundle)
    pair_pass = bool(
        lesson_pair.get("state") == "STRUCTURAL_LESSON_PAIR_PASS"
        and lesson_pair.get("semantic_distinctness") == "pass"
        and lesson_pair.get("witness_distinctness") == "pass"
        and lesson_pair.get("evidence_class") == "synthetic"
        and lesson_pair.get("empirical_transfer_established") is False
    )
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else {}
    ready = pair_pass and bundle_check["valid"]
    material = {
        "schema_version": SCHEMA,
        "version": __version__,
        "state": "LIVE_CALIBRATION_SCREEN_READY" if ready else "CALIBRATION_PREFLIGHT_HELD",
        "lesson_pair": {
            "relevant_competence_id": (lesson_pair.get("relevant") or {}).get("competence_id"),
            "sham_competence_id": (lesson_pair.get("sham") or {}).get("competence_id"),
            "evidence_class": lesson_pair.get("evidence_class"),
            "empirical": False,
        },
        "corpus_hash": manifest.get("corpus_hash"),
        "answer_key_commitment": manifest.get("answer_key_commitment"),
        "initial_screen_case_ids": list(manifest.get("initial_screen_case_ids") or ()),
        "screening_policy": {
            "initial_level": 2,
            "initial_calls": 4,
            "maximum_calls_before_new_authorization": 4,
            "success_band": [0.30, 0.70],
            "zero_successes": "move_easier",
            "four_successes": "move_harder",
            "mixed_successes": "collect_four_confirmation_cases_only_after_new_authorization",
            "outcome_source": "canonical_model_circulation_reconstruction_only",
            "caller_success_booleans_accepted": False,
        },
        "calls_executed": 0,
        "live_model_selected": False,
        "calibration_established": False,
        "semantic_transfer_established": False,
        "next_action": "execute_four_call_live_baseline_screen" if ready else "repair_preflight",
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    return {**material, "preflight_hash": _sha(material)}


def _adapter_identity(adapter: Any) -> dict[str, str]:
    return {
        "provider_family": str(getattr(adapter, "provider_family", "") or ""),
        "model_id": str(getattr(adapter, "model_id", "") or ""),
        "model_version": str(getattr(adapter, "model_version", "") or ""),
        "adapter_id": str(getattr(adapter, "adapter_id", "") or ""),
        "adapter_version": str(getattr(adapter, "adapter_version", "") or ""),
    }


def freeze_live_calibration_screen(
    store: Any,
    repo: str,
    *,
    preflight: Mapping[str, Any],
    bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Persist the exact four-call screen before any invocation."""
    if preflight.get("state") != "LIVE_CALIBRATION_SCREEN_READY":
        raise ValueError("semantic calibration preflight is not ready")
    bundle_check = verify_semantic_calibration_bundle(bundle)
    if bundle_check.get("valid") is not True:
        raise ValueError("semantic calibration bundle is invalid")
    manifest = bundle["manifest"]
    if preflight.get("corpus_hash") != manifest.get("corpus_hash"):
        raise ValueError("preflight corpus binding is invalid")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    provenance_check = verify_adapter_provenance(store, repo, provenance)
    if (
        provenance_check.get("valid") is not True
        or provenance.get("evidence_class") != EVIDENCE_LIVE
    ):
        raise ValueError("live host-registered adapter provenance is required")
    identity = _adapter_identity(adapter)
    if not all(identity.values()):
        raise ValueError("complete adapter identity is required")
    cases_by_id = {
        str(row["case_id"]): row for row in manifest.get("cases") or ()
    }
    frozen_cases = [
        cases_by_id[str(case_id)] for case_id in preflight["initial_screen_case_ids"]
    ]
    material = {
        "schema_version": "cortex-live-semantic-calibration-preregistration/1.0",
        "version": __version__,
        "repo": str(repo),
        "repository_id": str(store.repo(repo)["repository_id"]),
        "preflight_hash": str(preflight["preflight_hash"]),
        "corpus_hash": str(manifest["corpus_hash"]),
        "answer_key_commitment": str(manifest["answer_key_commitment"]),
        "cases": frozen_cases,
        "planned_calls": 4,
        "normalization": "strip_ascii_whitespace",
        "model_identity": identity,
        "adapter_provenance": provenance,
        "provider_identity_used_in_scoring": False,
        "model_identity_used_in_scoring": False,
        "caller_success_booleans_accepted": False,
        "status": "frozen_before_execution",
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    preregistration_id = _sha(material)
    session = open_symbiotic_session(
        store, repo, task="freeze live semantic calibration screen", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "kind": "live_semantic_calibration_preregistration",
            "preregistration_id": preregistration_id,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"semantic_calibration_prereg_{preregistration_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def execute_live_calibration_screen(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    bundle: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    """Run exactly four task-only calls and reconstruct their outcomes."""
    if preregistration.get("kind") != "live_semantic_calibration_preregistration":
        raise ValueError("canonical calibration preregistration is required")
    if store.verify_symbiotic_receipt(
        repo, str(preregistration.get("receipt_hash") or "")
    ).get("valid") is not True:
        raise ValueError("calibration preregistration receipt is invalid")
    if _adapter_identity(adapter) != preregistration.get("model_identity"):
        raise ValueError("adapter identity changed after preregistration")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if provenance != preregistration.get("adapter_provenance"):
        raise ValueError("adapter provenance changed after preregistration")
    if verify_semantic_calibration_bundle(bundle).get("valid") is not True:
        raise ValueError("private calibration bundle is invalid")
    if _sha(bundle["answer_key"]) != preregistration.get("answer_key_commitment"):
        raise ValueError("private answer key does not match preregistration")
    answers = bundle["answer_key"]["answers"]
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    case_receipts: list[dict[str, Any]] = []
    for case in preregistration.get("cases") or ():
        case_id = str(case["case_id"])
        expected = str(answers[case_id])
        contract = TaskEvaluationContract(
            contract_id=f"alpha18-{case_id}-exact-option-v1",
            task_type="field_equals",
            target_field="text",
            expected_value=expected,
            evaluator_id="cortex.semantic-calibration.exact-option.v1",
        )
        run = runtime.run(
            f"{case['prompt']}\n\n{case['response_contract']}",
            adapter=adapter,
            grant=grant,
            context_treatment="task_only_control",
        )
        trajectory_hash = str(run["trajectory_receipt_hash"])
        trajectory_check = verify_native_agent_trajectory(store, repo, trajectory_hash)
        if trajectory_check.get("valid") is not True:
            raise ValueError(f"native trajectory invalid for {case_id}")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        observed = str(trajectory.get("final_answer") or "").strip()
        evaluation = evaluate_task_result(contract, {"text": observed})
        case_material = {
            "schema_version": "cortex-live-semantic-calibration-case/1.0",
            "kind": "live_semantic_calibration_case",
            "version": __version__,
            "preregistration_id": preregistration["preregistration_id"],
            "preregistration_receipt_hash": preregistration["receipt_hash"],
            "case_id": case_id,
            "case_hash": _sha(case),
            "trajectory_receipt_hash": trajectory_hash,
            "evaluation_contract": contract.to_dict(),
            "evaluation_contract_hash": contract.contract_hash,
            "evaluation": evaluation,
            "task_success": evaluation.get("success"),
            "normalization": "strip_ascii_whitespace",
            "caller_success_fields_authoritative": False,
            "evidence_class": EVIDENCE_LIVE,
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        }
        session = open_symbiotic_session(
            store, repo, task=f"seal live calibration case {case_id}", persist=True
        )
        case_receipts.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **case_material,
                    "status": "live_baseline_observation",
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"semantic_calibration_case_{_sha(case_material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )
    outcomes: list[bool] = []
    errors: list[str] = []
    for row in case_receipts:
        trajectory = store.symbiotic_receipt(
            str(row["trajectory_receipt_hash"]), repo=repo
        ) or {}
        check = verify_native_agent_trajectory(
            store, repo, str(row["trajectory_receipt_hash"])
        )
        contract = TaskEvaluationContract.from_mapping(row["evaluation_contract"])
        rebuilt = evaluate_task_result(
            contract, {"text": str(trajectory.get("final_answer") or "").strip()}
        )
        if check.get("valid") is not True:
            errors.append(f"trajectory_invalid:{row['case_id']}")
        if rebuilt != row.get("evaluation"):
            errors.append(f"evaluation_reconstruction_invalid:{row['case_id']}")
        outcomes.append(rebuilt.get("success") is True)
    sequential = assess_sequential_level(outcomes)
    material = {
        "schema_version": "cortex-live-semantic-calibration-result/1.0",
        "version": __version__,
        "kind": "live_semantic_calibration_result",
        "preregistration_id": preregistration["preregistration_id"],
        "preregistration_receipt_hash": preregistration["receipt_hash"],
        "case_receipt_hashes": [row["receipt_hash"] for row in case_receipts],
        "model_identity": preregistration["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": sequential,
        "errors": errors,
        "calibration_established": sequential["state"] == "calibrated" and not errors,
        "semantic_transfer_established": False,
        "calls_executed": len(case_receipts),
        "status": "LIVE_BASELINE_SCREEN_RECONSTRUCTED" if not errors else "LIVE_BASELINE_SCREEN_HELD",
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(
        store, repo, task="seal live semantic calibration result", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"semantic_calibration_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "CLAIM_BOUNDARY", "CORPUS_SCHEMA", "PRIVATE_KEY_SCHEMA", "SCHEMA",
    "build_semantic_calibration_bundle", "build_semantic_calibration_preflight",
    "execute_live_calibration_screen", "freeze_live_calibration_screen",
    "verify_semantic_calibration_bundle",
]
