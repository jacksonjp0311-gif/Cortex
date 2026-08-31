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


__all__ = [
    "CLAIM_BOUNDARY", "CORPUS_SCHEMA", "PRIVATE_KEY_SCHEMA", "SCHEMA",
    "build_semantic_calibration_bundle", "build_semantic_calibration_preflight",
    "verify_semantic_calibration_bundle",
]
