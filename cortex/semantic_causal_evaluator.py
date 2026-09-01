"""Versioned deterministic semantic evaluator for open causal responses.

The evaluator accepts bounded surface variation only through a host-controlled
lexicon.  It does not call a model, infer truth from fluency, or alter v1
receipts.  Semantic atoms remain noncompensatory and exact evidence ordering is
still required.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from . import __version__
from .adapter_provenance import (
    EVIDENCE_LIVE,
    resolve_adapter_provenance,
    verify_adapter_provenance,
)
from .information_calibration import assess_sequential_level
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .open_response_calibration import verify_open_response_latent_bundle
from .symbiosis import open_symbiotic_session

EVALUATOR_SCHEMA = "cortex-semantic-causal-evaluation/2.0"
PRIVATE_SCHEMA = "cortex-semantic-causal-key/2.0"
PUBLIC_SCHEMA = "cortex-semantic-causal-manifest/2.0"
EVALUATOR_ID = "cortex.semantic-causal-response.v2"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def _adapter_identity(adapter: Any) -> dict[str, str]:
    return {
        "provider_family": str(getattr(adapter, "provider_family", "") or ""),
        "model_id": str(getattr(adapter, "model_id", "") or ""),
        "model_version": str(getattr(adapter, "model_version", "") or ""),
        "adapter_id": str(getattr(adapter, "adapter_id", "") or ""),
        "adapter_version": str(getattr(adapter, "adapter_version", "") or ""),
    }


# These patterns define the entire accepted paraphrase surface.  Provider and
# model identifiers never participate in atom extraction.
ATOM_PATTERNS: dict[str, tuple[str, ...]] = {
    "cache": (r"\bcache\b",),
    "stale_value": (
        r"\bstale\b",
        r"\bold (?:database )?value\b",
        r"\b(?:prior|previous) (?:profile|value)\b",
        r"\bversion 7\b",
        r"\bgeneration 41\b",
    ),
    "committed_mutation": (r"\bcommit(?:s|ted)?\b", r"\bmutation\b", r"\bupdate\b"),
    "invalidate": (r"\binvalidat\w*\b", r"\bevict\w*\b", r"\bclear\w*\b.{0,24}\bcache\b"),
    "post_commit": (
        r"\bafter (?:a |the )?(?:successful )?(?:database )?(?:transaction )?commit\w*\b",
        r"\bonce (?:the )?(?:database )?(?:transaction )?(?:commit\w*|succeeds)\b",
        r"\bfollowing (?:the )?commit\w*\b",
        r"\bpost commit\b",
        r"\bmutation boundary\b",
    ),
    "pre_commit": (
        r"\bbefore (?:the )?(?:database )?(?:transaction )?commit\w*\b",
        r"\bprior to (?:the )?(?:database )?(?:transaction )?commit\w*\b",
        r"\bpre commit\b",
    ),
    "concurrent_reader": (
        r"\bconcurrent reader\b",
        r"\bparallel read(?:er)?\b",
        r"\breader\b",
    ),
    "cache_write": (r"\brepopulat\w*\b", r"\bre cach\w*\b", r"\brecach\w*\b"),
    "versioning": (r"\bgeneration\b", r"\bversion(?:ing|ed)?\b"),
    "l2": (r"\bl2\b", r"\blower layer\b"),
    "all_layers": (r"\bboth layers\b", r"\ball layers\b", r"\bl1 and l2\b"),
    "snapshot": (r"\bsnapshot(?: cache)?\b",),
    "rebuild": (r"\bindex rebuild\b", r"\bderived index\b", r"\brebuild\w*\b"),
    "before_rebuild": (
        r"\bbefore (?:the )?(?:index )?rebuild\w*\b",
        r"\bprior to (?:the )?(?:index )?rebuild\w*\b",
        r"\bdependency order\b",
        r"\bsource (?:snapshot )?cache\b",
    ),
}

PHRASE_ATOMS: dict[str, str] = {
    "cache": "cache",
    "stale": "stale_value",
    "prior": "stale_value",
    "old value": "stale_value",
    "version 7": "stale_value",
    "generation 41": "stale_value",
    "mutation": "committed_mutation",
    "commit": "committed_mutation",
    "update": "committed_mutation",
    "invalidate": "invalidate",
    "evict": "invalidate",
    "clear": "invalidate",
    "after commit": "post_commit",
    "post commit": "post_commit",
    "mutation boundary": "post_commit",
    "before commit": "pre_commit",
    "pre commit": "pre_commit",
    "concurrent reader": "concurrent_reader",
    "reader": "concurrent_reader",
    "repopulate": "cache_write",
    "generation": "versioning",
    "version": "versioning",
    "l2": "l2",
    "lower layer": "l2",
    "both layers": "all_layers",
    "l1 and l2": "all_layers",
    "all layers": "all_layers",
    "snapshot cache": "snapshot",
    "snapshot": "snapshot",
    "index rebuild": "rebuild",
    "derived index": "rebuild",
    "before rebuild": "before_rebuild",
    "dependency order": "before_rebuild",
    "source cache": "before_rebuild",
}


def _lexicon_hash() -> str:
    return _sha({"patterns": ATOM_PATTERNS, "phrase_atoms": PHRASE_ATOMS})


def _atoms(text: str) -> tuple[set[str], set[str]]:
    value = _normalized(text)
    observed: set[str] = set()
    negated: set[str] = set()
    for atom, patterns in ATOM_PATTERNS.items():
        positive_hit = False
        negated_hit = False
        for pattern in patterns:
            for match in re.finditer(pattern, value):
                observed.add(atom)
                prefix = value[: match.start()].split()[-4:]
                if any(token in {"not", "never", "without", "no"} for token in prefix):
                    negated_hit = True
                else:
                    positive_hit = True
        # A later negative statement must not erase an independently stated
        # positive causal atom (for example, "old value ... does not clear the
        # stale entry").  Only exclusively negated occurrences close the gate.
        if negated_hit and not positive_hit:
            negated.add(atom)
    return observed, negated


def compile_semantic_contract(source: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a v1 private contract into a versioned semantic-atom contract."""

    def compile_groups(groups: Any) -> list[list[str]]:
        compiled: list[list[str]] = []
        for group in groups or ():
            atoms = sorted({PHRASE_ATOMS.get(_normalized(str(item)), "") for item in group} - {""})
            if not atoms:
                raise ValueError(f"semantic atom unavailable for clause: {group}")
            compiled.append(atoms)
        return compiled

    material = {
        "schema_version": EVALUATOR_SCHEMA,
        "case_id": str(source.get("case_id") or ""),
        "source_contract_hash": str(source.get("contract_hash") or ""),
        "cause_atom_groups": compile_groups(source.get("required_cause_clauses")),
        "repair_atom_groups": compile_groups(source.get("required_repair_clauses")),
        "required_evidence_ids": list(source.get("required_evidence_ids") or ()),
        "forbidden_terms": list(source.get("forbidden_terms") or ()),
        "allowed_response_keys": list(source.get("allowed_response_keys") or ()),
        "lexicon_hash": _lexicon_hash(),
        "evaluator_id": EVALUATOR_ID,
        "caller_success_authoritative": False,
        "model_identity_used_in_scoring": False,
    }
    return {**material, "contract_hash": _sha(material)}


def build_semantic_evaluator_bundle(
    corpus_manifest: Mapping[str, Any], source_private_key: Mapping[str, Any]
) -> dict[str, Any]:
    source_bundle = {"manifest": dict(corpus_manifest), "private_key": dict(source_private_key)}
    if verify_open_response_latent_bundle(source_bundle).get("valid") is not True:
        raise ValueError("canonical v1 corpus/private contract pair is required")
    contracts = {
        str(case_id): compile_semantic_contract(contract)
        for case_id, contract in (source_private_key.get("contracts") or {}).items()
    }
    private_key = {
        "schema_version": PRIVATE_SCHEMA,
        "source_corpus_hash": corpus_manifest["corpus_hash"],
        "source_private_key_commitment": corpus_manifest["private_key_commitment"],
        "lexicon_hash": _lexicon_hash(),
        "contracts": contracts,
    }
    material = {
        "schema_version": PUBLIC_SCHEMA,
        "version": __version__,
        "evaluator_id": EVALUATOR_ID,
        "source_corpus_hash": corpus_manifest["corpus_hash"],
        "source_private_key_commitment": corpus_manifest["private_key_commitment"],
        "lexicon_hash": _lexicon_hash(),
        "private_key_commitment": _sha(private_key),
        "case_ids": sorted(contracts),
        "private_contracts_present": False,
        "development_only": True,
        "confirmatory_eligible": False,
        "model_identity_in_scoring": False,
    }
    manifest = {**material, "evaluator_hash": _sha(material)}
    return {"manifest": manifest, "private_key": private_key}


def verify_semantic_evaluator_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else None
    private_key = bundle.get("private_key") if isinstance(bundle, Mapping) else None
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(private_key, Mapping):
        return {"valid": False, "errors": ["bundle_shape_invalid"]}
    material = {key: value for key, value in manifest.items() if key != "evaluator_hash"}
    if manifest.get("schema_version") != PUBLIC_SCHEMA:
        errors.append("manifest_schema_invalid")
    if manifest.get("evaluator_hash") != _sha(material):
        errors.append("evaluator_hash_invalid")
    if manifest.get("private_key_commitment") != _sha(private_key):
        errors.append("private_key_commitment_invalid")
    if manifest.get("lexicon_hash") != _lexicon_hash() or private_key.get("lexicon_hash") != _lexicon_hash():
        errors.append("lexicon_hash_invalid")
    contracts = private_key.get("contracts") or {}
    if sorted(contracts) != list(manifest.get("case_ids") or ()):
        errors.append("case_identity_mismatch")
    for case_id, contract in contracts.items():
        contract_material = {key: value for key, value in contract.items() if key != "contract_hash"}
        if contract.get("case_id") != case_id or contract.get("contract_hash") != _sha(contract_material):
            errors.append(f"contract_integrity_invalid:{case_id}")
    if manifest.get("private_contracts_present") is not False:
        errors.append("private_boundary_invalid")
    return {"valid": not errors, "errors": errors}


def evaluate_semantic_causal_response(contract: Mapping[str, Any], public_text: str) -> dict[str, Any]:
    """Evaluate explicit semantic atoms; no score or metadata comes from the caller."""
    contract_material = {key: value for key, value in contract.items() if key != "contract_hash"}
    if (
        contract.get("schema_version") != EVALUATOR_SCHEMA
        or contract.get("contract_hash") != _sha(contract_material)
        or contract.get("lexicon_hash") != _lexicon_hash()
    ):
        return {"state": "unknown", "success": None, "errors": ["contract_invalid"]}
    try:
        response = json.loads(str(public_text))
    except json.JSONDecodeError:
        response = None
    if not isinstance(response, Mapping):
        return {"state": "unknown", "success": None, "errors": ["response_json_object_required"]}
    errors: list[str] = []
    if set(response) != set(contract.get("allowed_response_keys") or ()):
        errors.append("response_keys_invalid")
    cause_atoms, cause_negated = _atoms(str(response.get("cause") or ""))
    repair_atoms, repair_negated = _atoms(str(response.get("repair") or ""))

    def missing(groups: Any, observed: set[str], negated: set[str]) -> list[int]:
        return [
            index
            for index, alternatives in enumerate(groups or ())
            if not any(atom in observed and atom not in negated for atom in alternatives or ())
        ]

    missing_cause = missing(contract.get("cause_atom_groups"), cause_atoms, cause_negated)
    missing_repair = missing(contract.get("repair_atom_groups"), repair_atoms, repair_negated)
    if missing_cause:
        errors.append("required_cause_semantics_missing")
    if missing_repair:
        errors.append("required_repair_semantics_missing")
    combined = _normalized(f"{response.get('cause', '')} {response.get('repair', '')}")
    forbidden = [
        term for term in contract.get("forbidden_terms") or () if _normalized(str(term)) in combined
    ]
    if forbidden:
        errors.append("forbidden_unsupported_claim")
    evidence = response.get("evidence_ids")
    if not isinstance(evidence, list) or [str(item) for item in evidence] != list(
        contract.get("required_evidence_ids") or ()
    ):
        errors.append("causal_evidence_binding_invalid")
    if str(response.get("uncertainty") or "") not in {"low", "medium", "high", "unknown"}:
        errors.append("uncertainty_state_invalid")
    return {
        "state": "pass" if not errors else "fail",
        "success": not errors,
        "errors": errors,
        "missing_cause_group_indices": missing_cause,
        "missing_repair_group_indices": missing_repair,
        "cause_atoms": sorted(cause_atoms),
        "repair_atoms": sorted(repair_atoms),
        "negated_atoms": sorted(cause_negated | repair_negated),
        "forbidden_terms_observed": forbidden,
        "contract_hash": contract.get("contract_hash"),
        "response_hash": _sha(response),
        "evaluator_id": EVALUATOR_ID,
        "independent": True,
        "caller_success_authoritative": False,
    }


def semantic_evaluator_self_test(
    bundle: Mapping[str, Any], source_private_key: Mapping[str, Any]
) -> dict[str, Any]:
    """Run deterministic positive, paraphrase, and adversarial evaluator checks."""
    contracts = bundle["private_key"]["contracts"]
    source_contracts = source_private_key.get("contracts") or {}
    checks: list[dict[str, Any]] = []
    for case_id, contract in contracts.items():
        reference = source_contracts[case_id]["reference_response"]
        result = evaluate_semantic_causal_response(contract, json.dumps(reference))
        checks.append({"id": f"reference:{case_id}", "expected": True, "observed": result["success"]})
        for mutation, expected_error in (
            ("reversed_evidence", "causal_evidence_binding_invalid"),
            ("caller_success", "response_keys_invalid"),
            ("forbidden_retry", "forbidden_unsupported_claim"),
        ):
            altered = dict(reference)
            if mutation == "reversed_evidence":
                altered["evidence_ids"] = list(reversed(altered["evidence_ids"]))
            elif mutation == "caller_success":
                altered["success"] = True
            else:
                altered["repair"] += " then retry"
            verdict = evaluate_semantic_causal_response(contract, json.dumps(altered))
            checks.append(
                {
                    "id": f"{mutation}:{case_id}",
                    "expected": False,
                    "observed": verdict["success"],
                    "expected_error_present": expected_error in verdict["errors"],
                }
            )
    level_three = next(
        contract
        for contract in contracts.values()
        if len(contract.get("required_evidence_ids") or ()) == 5
        and any("pre_commit" in group for group in contract.get("cause_atom_groups") or ())
    )
    paraphrase = {
        "cause": "cache invalidation occurs before the database transaction commits, so a parallel reader can recache the old value",
        "repair": "clear the cache only once the transaction succeeds",
        "evidence_ids": list(level_three["required_evidence_ids"]),
        "uncertainty": "low",
    }
    checks.append(
        {
            "id": "held_out_surface_paraphrase",
            "expected": True,
            "observed": evaluate_semantic_causal_response(level_three, json.dumps(paraphrase))["success"],
        }
    )
    wrong_order = dict(paraphrase)
    wrong_order["cause"] = "cache invalidation occurs after commit and a reader sees the old value"
    wrong_order["repair"] = "clear the cache before commit"
    checks.append(
        {
            "id": "wrong_temporal_relation",
            "expected": False,
            "observed": evaluate_semantic_causal_response(level_three, json.dumps(wrong_order))["success"],
        }
    )
    negated = dict(paraphrase)
    negated["cause"] = "the cache is not invalidated before commit; a concurrent reader never recaches the old value"
    checks.append(
        {
            "id": "negated_required_semantics",
            "expected": False,
            "observed": evaluate_semantic_causal_response(level_three, json.dumps(negated))["success"],
        }
    )
    passed = all(row["observed"] is row["expected"] for row in checks) and all(
        row.get("expected_error_present", True) for row in checks
    )
    return {"passed": passed, "check_count": len(checks), "checks": checks}


def freeze_semantic_evaluator_v2(
    store: Any,
    repo: str,
    *,
    audit_receipt_hash: str,
    source_result_receipt_hash: str,
    bundle: Mapping[str, Any],
    source_private_key: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal v2 after canonical alpha.21 evidence and zero-call self-tests."""
    audit_hash = str(audit_receipt_hash or "")
    result_hash = str(source_result_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, audit_hash).get("valid") is not True:
        raise ValueError("canonical alpha.21 evaluator audit is required")
    if store.verify_symbiotic_receipt(repo, result_hash).get("valid") is not True:
        raise ValueError("canonical alpha.21 live result is required")
    audit = store.symbiotic_receipt(audit_hash, repo=repo) or {}
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    if (
        audit.get("kind") != "live_open_response_evaluator_audit"
        or audit.get("result_receipt_hash") != result_hash
        or audit.get("raw_scores_rewritten") is not False
        or audit.get("baseline_difficulty_established") is not False
        or result.get("kind") != "live_open_response_result"
    ):
        raise ValueError("alpha.21 evidence does not open evaluator replacement")
    if verify_semantic_evaluator_bundle(bundle).get("valid") is not True:
        raise ValueError("semantic evaluator bundle is invalid")
    self_test = semantic_evaluator_self_test(bundle, source_private_key)
    if self_test.get("passed") is not True:
        raise ValueError("semantic evaluator adversarial self-test failed")
    contracts = bundle["private_key"]["contracts"]
    shadow: list[dict[str, Any]] = []
    for case_hash in result.get("case_receipt_hashes") or ():
        case = store.symbiotic_receipt(str(case_hash), repo=repo) or {}
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError("historical trajectory reconstruction failed")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        verdict = evaluate_semantic_causal_response(
            contracts[str(case.get("case_id") or "")], str(trajectory.get("final_answer") or "")
        )
        shadow.append({"case_id": case["case_id"], "trajectory_receipt_hash": trajectory_hash, "verdict": verdict})
    material = {
        "schema_version": "cortex-semantic-causal-evaluator-preflight/2.0",
        "version": __version__,
        "kind": "semantic_causal_evaluator_preflight",
        "source_result_receipt_hash": result_hash,
        "source_audit_receipt_hash": audit_hash,
        "evaluator_manifest": bundle["manifest"],
        "self_test": self_test,
        "historical_shadow": shadow,
        "historical_scores_rewritten": False,
        "historical_shadow_is_post_hoc": True,
        "planned_live_calls": 0,
        "baseline_difficulty_established": False,
        "calibration_established": False,
        "semantic_transfer_established": False,
        "state": "SEMANTIC_CAUSAL_EVALUATOR_V2_READY",
        "next_action": "separately_authorize_new_four_call_task_only_screen",
        "claim_boundary": (
            "V2 is a deterministic development evaluator. Post-hoc shadow results cannot "
            "rescore alpha.21 or establish task difficulty, transfer, or model improvement."
        ),
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze semantic causal evaluator v2", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"semantic_evaluator_v2_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def freeze_live_semantic_screen_v2(
    store: Any,
    repo: str,
    *,
    evaluator_preflight_receipt_hash: str,
    corpus_manifest: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Freeze four fresh task-only calls against the already sealed v2 evaluator."""
    preflight_hash = str(evaluator_preflight_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, preflight_hash).get("valid") is not True:
        raise ValueError("canonical semantic evaluator preflight is required")
    preflight = store.symbiotic_receipt(preflight_hash, repo=repo) or {}
    if (
        preflight.get("kind") != "semantic_causal_evaluator_preflight"
        or preflight.get("state") != "SEMANTIC_CAUSAL_EVALUATOR_V2_READY"
        or int(preflight.get("planned_live_calls", -1)) != 0
    ):
        raise ValueError("semantic evaluator preflight cannot open a live screen")
    if verify_semantic_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("semantic evaluator bundle is invalid")
    evaluator_manifest = evaluator_bundle["manifest"]
    if (
        preflight.get("evaluator_manifest") != evaluator_manifest
        or evaluator_manifest.get("source_corpus_hash") != corpus_manifest.get("corpus_hash")
        or evaluator_manifest.get("source_private_key_commitment")
        != corpus_manifest.get("private_key_commitment")
    ):
        raise ValueError("semantic evaluator/corpus binding is invalid")
    cases = [
        row
        for row in corpus_manifest.get("cases") or ()
        if int(row.get("difficulty_level") or 0) == 3
    ]
    if len(cases) != 4:
        raise ValueError("live semantic causal screen requires four level-three cases")
    identity = _adapter_identity(adapter)
    if not all(identity.values()):
        raise ValueError("complete adapter identity is required")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if (
        verify_adapter_provenance(store, repo, provenance).get("valid") is not True
        or provenance.get("evidence_class") != EVIDENCE_LIVE
    ):
        raise ValueError("live host-registered adapter provenance is required")
    material = {
        "schema_version": "cortex-live-semantic-causal-preregistration/2.0",
        "version": __version__,
        "kind": "live_semantic_causal_preregistration",
        "evaluator_preflight_receipt_hash": preflight_hash,
        "corpus_hash": corpus_manifest["corpus_hash"],
        "evaluator_hash": evaluator_manifest["evaluator_hash"],
        "private_key_commitment": evaluator_manifest["private_key_commitment"],
        "cases": cases,
        "planned_calls": 4,
        "context_treatment": "task_only_control",
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "evaluator_id": EVALUATOR_ID,
        "status": "frozen_before_execution",
        "development_only": True,
        "confirmatory_eligible": False,
        "caller_success_booleans_accepted": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze live semantic causal screen", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"live_semantic_causal_prereg_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def execute_live_semantic_screen_v2(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    corpus_manifest: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    """Execute and independently reconstruct the frozen four-call v2 screen."""
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical live semantic preregistration is required")
    if preregistration.get("kind") != "live_semantic_causal_preregistration":
        raise ValueError("live semantic preregistration kind is invalid")
    if verify_semantic_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("semantic evaluator bundle is invalid")
    manifest = evaluator_bundle["manifest"]
    contracts = evaluator_bundle["private_key"]["contracts"]
    if (
        preregistration.get("corpus_hash") != corpus_manifest.get("corpus_hash")
        or preregistration.get("evaluator_hash") != manifest.get("evaluator_hash")
        or preregistration.get("private_key_commitment")
        != manifest.get("private_key_commitment")
    ):
        raise ValueError("live semantic evaluator binding is invalid")
    if _adapter_identity(adapter) != preregistration.get("model_identity"):
        raise ValueError("adapter identity changed after preregistration")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if provenance != preregistration.get("adapter_provenance"):
        raise ValueError("adapter provenance changed after preregistration")
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    cases: list[dict[str, Any]] = []
    for case in preregistration.get("cases") or ():
        case_id = str(case.get("case_id") or "")
        contract = contracts.get(case_id)
        if not isinstance(contract, Mapping):
            raise ValueError(f"private semantic contract missing for {case_id}")
        task = (
            f"{case['prompt']}\n\nEVENT_RECORD\n"
            + "\n".join(str(item) for item in case.get("events") or ())
            + "\n\nRESPONSE_CONTRACT\n"
            + _canonical(case["response_contract"])
        )
        run = runtime.run(
            task,
            adapter=adapter,
            grant=grant,
            context_treatment="task_only_control",
        )
        trajectory_hash = str(run["trajectory_receipt_hash"])
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError(f"native trajectory invalid for {case_id}")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        evaluation = evaluate_semantic_causal_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        material = {
            "schema_version": "cortex-live-semantic-causal-case/2.0",
            "version": __version__,
            "kind": "live_semantic_causal_case",
            "preregistration_receipt_hash": prereg_hash,
            "case_id": case_id,
            "case_hash": _sha(case),
            "semantic_contract_hash": contract["contract_hash"],
            "evaluator_hash": manifest["evaluator_hash"],
            "private_contract_persisted": False,
            "trajectory_receipt_hash": trajectory_hash,
            "evaluation": evaluation,
            "task_success": evaluation.get("success"),
            "caller_success_authoritative": False,
            "evidence_class": EVIDENCE_LIVE,
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        }
        session = open_symbiotic_session(store, repo, task=f"seal v2 case {case_id}", persist=True)
        cases.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **material,
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"live_semantic_causal_case_{_sha(material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )
    outcomes: list[bool] = []
    unknown_count = 0
    errors: list[str] = []
    for case in cases:
        trajectory_hash = str(case["trajectory_receipt_hash"])
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        rebuilt = evaluate_semantic_causal_response(
            contracts[str(case["case_id"])], str(trajectory.get("final_answer") or "")
        )
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"trajectory_invalid:{case['case_id']}")
        if rebuilt != case.get("evaluation"):
            errors.append(f"evaluation_reconstruction_invalid:{case['case_id']}")
        if rebuilt.get("success") is None:
            unknown_count += 1
        else:
            outcomes.append(rebuilt.get("success") is True)
    if unknown_count:
        screen = {
            "state": "screening_held_unknown",
            "recommended_action": "repair_response_contract_or_transport",
            "case_count": len(cases),
            "known_outcome_count": len(outcomes),
            "unknown_count": unknown_count,
            "success_count": sum(outcomes),
            "success_rate": None,
            "development_only": True,
            "confirmatory_eligible": False,
        }
    else:
        screen = {**assess_sequential_level(outcomes), "unknown_count": 0}
    material = {
        "schema_version": "cortex-live-semantic-causal-result/2.0",
        "version": __version__,
        "kind": "live_semantic_causal_result",
        "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in cases],
        "evaluator_hash": manifest["evaluator_hash"],
        "model_identity": preregistration["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": screen,
        "errors": errors,
        "calls_executed": len(cases),
        "calibration_established": screen["state"] == "calibrated" and not errors,
        "semantic_transfer_established": False,
        "status": "LIVE_SEMANTIC_CAUSAL_SCREEN_RECONSTRUCTED" if not errors else "LIVE_SEMANTIC_CAUSAL_SCREEN_HELD",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="seal live semantic causal result", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"live_semantic_causal_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def verify_live_semantic_screen_v2(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    evaluator_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconstruct a live screen from canonical receipts and model trajectories."""
    result_hash = str(result_receipt_hash or "")
    errors: list[str] = []
    if verify_semantic_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        return {"valid": False, "errors": ["evaluator_bundle_invalid"]}
    if store.verify_symbiotic_receipt(repo, result_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        return {"valid": False, "errors": ["preregistration_receipt_invalid"]}
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    manifest = evaluator_bundle["manifest"]
    contracts = evaluator_bundle["private_key"]["contracts"]
    if result.get("kind") != "live_semantic_causal_result":
        errors.append("result_kind_invalid")
    if prereg.get("kind") != "live_semantic_causal_preregistration":
        errors.append("preregistration_kind_invalid")
    if (
        result.get("evaluator_hash") != manifest.get("evaluator_hash")
        or prereg.get("evaluator_hash") != manifest.get("evaluator_hash")
        or prereg.get("private_key_commitment") != manifest.get("private_key_commitment")
    ):
        errors.append("evaluator_binding_invalid")
    if result.get("model_identity") != prereg.get("model_identity"):
        errors.append("model_identity_binding_invalid")

    outcomes: list[bool] = []
    unknown_count = 0
    case_hashes = list(result.get("case_receipt_hashes") or ())
    for case_hash in case_hashes:
        if store.verify_symbiotic_receipt(repo, str(case_hash)).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{case_hash}")
            continue
        case = store.symbiotic_receipt(str(case_hash), repo=repo) or {}
        case_id = str(case.get("case_id") or "")
        contract = contracts.get(case_id)
        if not isinstance(contract, Mapping):
            errors.append(f"semantic_contract_missing:{case_id}")
            continue
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"trajectory_invalid:{case_id}")
            continue
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        rebuilt = evaluate_semantic_causal_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        if (
            case.get("kind") != "live_semantic_causal_case"
            or case.get("preregistration_receipt_hash") != prereg_hash
            or case.get("semantic_contract_hash") != contract.get("contract_hash")
            or case.get("evaluator_hash") != manifest.get("evaluator_hash")
            or case.get("evaluation") != rebuilt
            or case.get("task_success") != rebuilt.get("success")
        ):
            errors.append(f"case_binding_invalid:{case_id}")
        if rebuilt.get("success") is None:
            unknown_count += 1
        else:
            outcomes.append(rebuilt.get("success") is True)

    if unknown_count:
        rebuilt_screen = {
            "state": "screening_held_unknown",
            "recommended_action": "repair_response_contract_or_transport",
            "case_count": len(case_hashes),
            "known_outcome_count": len(outcomes),
            "unknown_count": unknown_count,
            "success_count": sum(outcomes),
            "success_rate": None,
            "development_only": True,
            "confirmatory_eligible": False,
        }
    else:
        rebuilt_screen = {**assess_sequential_level(outcomes), "unknown_count": 0}
    if result.get("screen") != rebuilt_screen:
        errors.append("screen_reconstruction_invalid")
    if (
        len(case_hashes) != int(prereg.get("planned_calls") or -1)
        or len(case_hashes) != int(result.get("calls_executed") or -1)
    ):
        errors.append("call_count_binding_invalid")
    if result.get("errors") not in ([], ()):
        errors.append("result_contains_execution_errors")
    if result.get("status") != "LIVE_SEMANTIC_CAUSAL_SCREEN_RECONSTRUCTED":
        errors.append("result_status_invalid")
    if result.get("semantic_transfer_established") is not False:
        errors.append("semantic_transfer_claim_invalid")
    for field in (
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    ):
        if result.get(field) is not False or prereg.get(field) is not False:
            errors.append(f"authority_open:{field}")
    return {
        "valid": not errors,
        "errors": errors,
        "result_receipt_hash": result_hash,
        "preregistration_receipt_hash": prereg_hash,
        "difficulty_levels": sorted(
            {
                int(case.get("difficulty_level") or 0)
                for case in prereg.get("cases") or ()
            }
        ),
        "screen": rebuilt_screen,
        "model_identity": prereg.get("model_identity"),
        "adapter_provenance": prereg.get("adapter_provenance"),
        "corpus_hash": prereg.get("corpus_hash"),
        "evaluator_hash": prereg.get("evaluator_hash"),
    }


def freeze_harder_live_semantic_screen_v2(
    store: Any,
    repo: str,
    *,
    prior_result_receipt_hash: str,
    corpus_manifest: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Freeze level four only when canonical level-three evidence proves a ceiling."""
    audit = verify_live_semantic_screen_v2(
        store,
        repo,
        result_receipt_hash=prior_result_receipt_hash,
        evaluator_bundle=evaluator_bundle,
    )
    if (
        audit.get("valid") is not True
        or audit.get("difficulty_levels") != [3]
        or (audit.get("screen") or {}).get("state") != "screening_ceiling"
        or int((audit.get("screen") or {}).get("success_count") or 0) != 4
        or int((audit.get("screen") or {}).get("unknown_count") or 0) != 0
    ):
        raise ValueError("canonical level-three ceiling is required")
    manifest = evaluator_bundle["manifest"]
    if (
        audit.get("corpus_hash") != corpus_manifest.get("corpus_hash")
        or audit.get("evaluator_hash") != manifest.get("evaluator_hash")
    ):
        raise ValueError("prior screen does not bind this corpus and evaluator")
    identity = _adapter_identity(adapter)
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if identity != audit.get("model_identity") or provenance != audit.get("adapter_provenance"):
        raise ValueError("harder screen requires the same registered model boundary")
    cases = [
        row
        for row in corpus_manifest.get("cases") or ()
        if int(row.get("difficulty_level") or 0) == 4
    ]
    if len(cases) != 4:
        raise ValueError("harder semantic screen requires four level-four cases")
    material = {
        "schema_version": "cortex-live-semantic-causal-preregistration/2.1",
        "version": __version__,
        "kind": "live_semantic_causal_preregistration",
        "prior_result_receipt_hash": str(prior_result_receipt_hash),
        "prior_screen_audit": audit,
        "corpus_hash": corpus_manifest["corpus_hash"],
        "evaluator_hash": manifest["evaluator_hash"],
        "private_key_commitment": manifest["private_key_commitment"],
        "cases": cases,
        "difficulty_level": 4,
        "planned_calls": 4,
        "context_treatment": "task_only_control",
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "evaluator_id": EVALUATOR_ID,
        "status": "frozen_before_execution",
        "development_only": True,
        "confirmatory_eligible": False,
        "caller_success_booleans_accepted": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze harder live semantic screen", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"harder_live_semantic_prereg_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def audit_harder_live_semantic_screen_v2(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    evaluator_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Diagnose a level-four floor without rewriting any canonical score."""
    audit = verify_live_semantic_screen_v2(
        store,
        repo,
        result_receipt_hash=result_receipt_hash,
        evaluator_bundle=evaluator_bundle,
    )
    screen = audit.get("screen") or {}
    if (
        audit.get("valid") is not True
        or audit.get("difficulty_levels") != [4]
        or screen.get("state") != "screening_floor"
        or int(screen.get("success_count", -1)) != 0
        or int(screen.get("unknown_count", -1)) != 0
    ):
        raise ValueError("canonical level-four zero-success floor is required")
    result = store.symbiotic_receipt(str(result_receipt_hash), repo=repo) or {}
    contracts = evaluator_bundle["private_key"]["contracts"]
    diagnostics: list[dict[str, Any]] = []
    evidence_rejections = 0
    semantic_rejections = 0
    for case_hash in result.get("case_receipt_hashes") or ():
        case = store.symbiotic_receipt(str(case_hash), repo=repo) or {}
        case_id = str(case.get("case_id") or "")
        contract = contracts[case_id]
        trajectory = store.symbiotic_receipt(
            str(case.get("trajectory_receipt_hash") or ""), repo=repo
        ) or {}
        try:
            response = json.loads(str(trajectory.get("final_answer") or ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            response = {}
        reported = [str(item) for item in response.get("evidence_ids") or ()]
        required = [str(item) for item in contract.get("required_evidence_ids") or ()]
        evaluation = dict(case.get("evaluation") or {})
        errors = [str(item) for item in evaluation.get("errors") or ()]
        evidence_rejected = "causal_evidence_binding_invalid" in errors
        semantic_rejected = any(
            item in errors
            for item in (
                "required_cause_semantics_missing",
                "required_repair_semantics_missing",
            )
        )
        evidence_rejections += int(evidence_rejected)
        semantic_rejections += int(semantic_rejected)
        diagnostics.append(
            {
                "case_id": case_id,
                "case_receipt_hash": str(case_hash),
                "trajectory_receipt_hash": str(case.get("trajectory_receipt_hash") or ""),
                "response_hash": evaluation.get("response_hash"),
                "evaluation_errors": errors,
                "reported_evidence_ids": reported,
                "required_evidence_ids": required,
                "missing_evidence_ids": [item for item in required if item not in reported],
                "extra_evidence_ids": [item for item in reported if item not in required],
                "missing_cause_group_indices": list(
                    evaluation.get("missing_cause_group_indices") or ()
                ),
                "missing_repair_group_indices": list(
                    evaluation.get("missing_repair_group_indices") or ()
                ),
                "canonical_score_rewritten": False,
            }
        )
    confounded = evidence_rejections > 0 or semantic_rejections > 0
    material = {
        "schema_version": "cortex-semantic-screen-instrument-audit/1.0",
        "version": __version__,
        "kind": "semantic_screen_instrument_audit",
        "result_receipt_hash": str(result_receipt_hash),
        "result_audit": audit,
        "case_diagnostics": diagnostics,
        "case_count": len(diagnostics),
        "evidence_binding_rejection_count": evidence_rejections,
        "semantic_clause_rejection_count": semantic_rejections,
        "instrument_task_confound_present": confounded,
        "historical_scores_rewritten": False,
        "additional_model_calls": 0,
        "difficulty_interpolation_ready": not confounded,
        "baseline_difficulty_established": False,
        "semantic_transfer_established": False,
        "state": (
            "DIFFICULTY_INTERPOLATION_HELD"
            if confounded
            else "DIFFICULTY_INTERPOLATION_READY"
        ),
        "next_action": (
            "freeze_evidence_minimality_and_semantic_repair_policy"
            if confounded
            else "forge_intermediate_difficulty_zero_call"
        ),
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="audit harder semantic instrument", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"semantic_instrument_audit_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "EVALUATOR_ID",
    "audit_harder_live_semantic_screen_v2",
    "build_semantic_evaluator_bundle",
    "compile_semantic_contract",
    "evaluate_semantic_causal_response",
    "execute_live_semantic_screen_v2",
    "freeze_harder_live_semantic_screen_v2",
    "freeze_semantic_evaluator_v2",
    "freeze_live_semantic_screen_v2",
    "semantic_evaluator_self_test",
    "verify_live_semantic_screen_v2",
    "verify_semantic_evaluator_bundle",
]
