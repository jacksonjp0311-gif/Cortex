"""Answer-sealed open-response latent-cause calibration geometry.

The model produces public causal language and exact evidence identifiers. A
host-frozen atomic contract scores the response; neither the model nor caller
supplies success. Private contracts belong in the OS credential vault.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import zlib
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
from .symbiosis import open_symbiotic_session

PUBLIC_SCHEMA = "cortex-open-response-latent-cause-corpus/1.0"
PRIVATE_SCHEMA = "cortex-open-response-latent-cause-key/1.0"
CONTRACT_SCHEMA = "cortex-atomic-causal-evaluation/1.0"
PREFLIGHT_SCHEMA = "cortex-open-response-latent-cause-preflight/1.0"
VAULT_SERVICE = "Cortex.CalibrationContracts"
CLAIM_BOUNDARY = (
    "This development forge verifies task and evaluator structure only. It does "
    "not establish calibration, semantic transfer, model improvement, or authority."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


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


class HostCalibrationContractVault:
    """OS-vault storage for private development evaluator contracts."""

    def _keyring(self):
        import keyring  # type: ignore[import-not-found]

        return keyring

    def set(self, corpus_hash: str, private_key: Mapping[str, Any]) -> None:
        keyring = self._keyring()
        identity = str(corpus_hash)
        raw = _canonical(private_key).encode("utf-8")
        encoded = base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")
        # Windows Generic Credentials cap the UTF-16 credential blob. Keep the
        # ASCII payload below half that byte ceiling rather than counting code
        # points as bytes.
        chunk_size = 900
        chunks = [
            encoded[index:index + chunk_size]
            for index in range(0, len(encoded), chunk_size)
        ]
        written: list[str] = []
        try:
            for index, chunk in enumerate(chunks):
                username = f"{identity}:{index:04d}"
                keyring.set_password(VAULT_SERVICE, username, chunk)
                written.append(username)
            manifest = {
                "schema_version": "cortex-calibration-vault/1.0",
                "chunk_count": len(chunks),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "compression": "zlib9+base64",
            }
            keyring.set_password(VAULT_SERVICE, identity, _canonical(manifest))
        except Exception:
            for username in written:
                try:
                    keyring.delete_password(VAULT_SERVICE, username)
                except Exception:
                    pass
            raise

    def get(self, corpus_hash: str) -> dict[str, Any] | None:
        keyring = self._keyring()
        identity = str(corpus_hash)
        value = keyring.get_password(VAULT_SERVICE, identity)
        if not value:
            return None
        manifest = json.loads(value)
        if (
            not isinstance(manifest, Mapping)
            or manifest.get("schema_version") != "cortex-calibration-vault/1.0"
        ):
            return None
        chunks = []
        for index in range(int(manifest.get("chunk_count") or 0)):
            chunk = keyring.get_password(VAULT_SERVICE, f"{identity}:{index:04d}")
            if not chunk:
                return None
            chunks.append(str(chunk))
        try:
            raw = zlib.decompress(base64.b64decode("".join(chunks))).decode("utf-8")
        except (ValueError, zlib.error, UnicodeDecodeError):
            return None
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != str(
            manifest.get("raw_sha256") or ""
        ):
            return None
        parsed = json.loads(raw)
        return dict(parsed) if isinstance(parsed, Mapping) else None

    def delete(self, corpus_hash: str) -> None:
        keyring = self._keyring()
        identity = str(corpus_hash)
        try:
            value = keyring.get_password(VAULT_SERVICE, identity)
            manifest = json.loads(value) if value else {}
            for index in range(int((manifest or {}).get("chunk_count") or 0)):
                try:
                    keyring.delete_password(VAULT_SERVICE, f"{identity}:{index:04d}")
                except Exception:
                    pass
            keyring.delete_password(VAULT_SERVICE, identity)
        except Exception:
            return


def _contract(
    case_id: str,
    *,
    cause_clauses: list[list[str]],
    repair_clauses: list[list[str]],
    evidence_ids: list[str],
    forbidden_terms: list[str],
    reference_response: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "schema_version": CONTRACT_SCHEMA,
        "case_id": case_id,
        "required_cause_clauses": cause_clauses,
        "required_repair_clauses": repair_clauses,
        "required_evidence_ids": evidence_ids,
        "forbidden_terms": forbidden_terms,
        "allowed_response_keys": ["cause", "repair", "evidence_ids", "uncertainty"],
        "reference_response": dict(reference_response),
        "evaluator_id": "cortex.atomic-causal-response.v1",
        "caller_success_authoritative": False,
        "model_identity_used_in_scoring": False,
    }
    return {**material, "contract_hash": _sha(material)}


def build_open_response_latent_bundle(*, secret_seed: str) -> dict[str, Any]:
    """Build four levels of causal diagnosis without answer choices."""
    if not str(secret_seed).strip():
        raise ValueError("secret_seed is required")
    scenarios = {
        1: {
            "events": [
                "E1: store commits a new profile value",
                "E2: the process cache still contains the prior profile",
                "E3: read_profile returns the cached prior value",
                "D1: an unrelated metrics export completes",
            ],
            "cause": [["cache"], ["stale", "prior"], ["mutation", "commit", "update"]],
            "repair": [["invalidate", "evict", "clear"], ["after commit", "mutation boundary"]],
            "evidence": ["E1", "E2", "E3"],
            "reference": {
                "cause": "the process cache remains stale after the committed mutation",
                "repair": "invalidate the cache after commit at the mutation boundary",
                "evidence_ids": ["E1", "E2", "E3"],
                "uncertainty": "low",
            },
        },
        2: {
            "events": [
                "E1: commit writes object version 8",
                "E2: L1 is invalidated",
                "E3: the next L1 miss loads version 7 from L2",
                "E4: L1 is repopulated with version 7",
                "D1: request tracing records a normal span",
            ],
            "cause": [["l2", "lower layer"], ["stale", "version 7"], ["repopulate"]],
            "repair": [["invalidate", "evict", "version"], ["both layers", "l1 and l2", "all layers"]],
            "evidence": ["E1", "E2", "E3", "E4"],
            "reference": {
                "cause": "stale L2 repopulates L1 with version 7 after the L1 invalidation",
                "repair": "invalidate or version both layers at commit",
                "evidence_ids": ["E1", "E2", "E3", "E4"],
                "uncertainty": "low",
            },
        },
        3: {
            "events": [
                "E1: transaction callback invalidates the cache before commit",
                "E2: a concurrent reader observes the old database value",
                "E3: that reader repopulates the cache with the old value",
                "E4: the transaction commits the new value",
                "E5: the stale cache entry survives after commit",
                "D1: connection pooling remains healthy",
            ],
            "cause": [["before commit", "pre commit"], ["concurrent reader", "reader"], ["repopulate"], ["stale", "old value"]],
            "repair": [["after commit", "post commit", "generation"], ["invalidate", "evict", "version"]],
            "evidence": ["E1", "E2", "E3", "E4", "E5"],
            "reference": {
                "cause": "pre commit invalidation lets a concurrent reader repopulate the stale old value before commit",
                "repair": "invalidate after commit or use generation versioning",
                "evidence_ids": ["E1", "E2", "E3", "E4", "E5"],
                "uncertainty": "low",
            },
        },
        4: {
            "events": [
                "E1: source graph mutation commits generation 42",
                "E2: snapshot cache remains at generation 41",
                "E3: index rebuild reads the snapshot cache rather than the committed source",
                "E4: derived index is sealed as generation 42 while containing generation 41 edges",
                "E5: direct source reads return generation 42",
                "D1: index serialization checksum is internally consistent",
                "D2: worker memory pressure is nominal",
            ],
            "cause": [["snapshot cache", "snapshot"], ["generation 41", "stale"], ["index rebuild", "derived index"]],
            "repair": [["invalidate", "evict", "version"], ["before rebuild", "dependency order", "source cache"]],
            "evidence": ["E1", "E2", "E3", "E4", "E5"],
            "reference": {
                "cause": "the index rebuild consumes the stale generation 41 snapshot cache after source generation 42 commits",
                "repair": "invalidate or version the source snapshot cache before rebuilding the derived index",
                "evidence_ids": ["E1", "E2", "E3", "E4", "E5"],
                "uncertainty": "low",
            },
        },
    }
    public_cases: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    for level, scenario in scenarios.items():
        for variant in range(1, 5):
            identity = {
                "family": "open_response_cache_causality",
                "difficulty_level": level,
                "variant": variant,
                "events": scenario["events"],
            }
            case_id = f"olc_{_sha(identity)[:20]}"
            contract = _contract(
                case_id,
                cause_clauses=scenario["cause"],
                repair_clauses=scenario["repair"],
                evidence_ids=scenario["evidence"],
                forbidden_terms=["retry", "increase timeout", "ignore", "suppress"],
                reference_response=scenario["reference"],
            )
            contracts[case_id] = contract
            public_cases.append(
                {
                    **identity,
                    "case_id": case_id,
                    "prompt": (
                        "Infer the latent causal mechanism and smallest causal repair from the "
                        "event record. Distractor events begin with D. Return one JSON object."
                    ),
                    "response_contract": {
                        "keys": ["cause", "repair", "evidence_ids", "uncertainty"],
                        "cause": "brief public causal explanation",
                        "repair": "brief public repair principle",
                        "evidence_ids": "exact ordered IDs necessary to prove the causal chain",
                        "uncertainty": ["low", "medium", "high", "unknown"],
                        "extra_keys_forbidden": True,
                    },
                    "contract_commitment": _sha(
                        {
                            "case_id": case_id,
                            "contract": contract,
                            "secret_seed": str(secret_seed),
                        }
                    ),
                    "development_only": True,
                }
            )
    private_key = {
        "schema_version": PRIVATE_SCHEMA,
        "secret_seed": str(secret_seed),
        "contracts": contracts,
    }
    public_material = {
        "schema_version": PUBLIC_SCHEMA,
        "version": __version__,
        "family": "open_response_cache_causality",
        "levels": [1, 2, 3, 4],
        "variants_per_level": 4,
        "case_count": len(public_cases),
        "initial_screen_level": 3,
        "cases": public_cases,
        "private_key_commitment": _sha(private_key),
        "secret_seed_commitment": _sha(str(secret_seed)),
        "answers_present": False,
        "development_only": True,
        "confirmatory_eligible": False,
        "model_identity_in_ontology": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    manifest = {**public_material, "corpus_hash": _sha(public_material)}
    return {"manifest": manifest, "private_key": private_key}


def verify_open_response_latent_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else None
    private_key = bundle.get("private_key") if isinstance(bundle, Mapping) else None
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(private_key, Mapping):
        return {"valid": False, "state": "fail", "errors": ["bundle_shape_invalid"]}
    material = {key: value for key, value in manifest.items() if key != "corpus_hash"}
    if manifest.get("schema_version") != PUBLIC_SCHEMA:
        errors.append("public_schema_invalid")
    if manifest.get("corpus_hash") != _sha(material):
        errors.append("corpus_hash_invalid")
    if manifest.get("private_key_commitment") != _sha(private_key):
        errors.append("private_key_commitment_invalid")
    seed = str(private_key.get("secret_seed") or "")
    if manifest.get("secret_seed_commitment") != _sha(seed):
        errors.append("secret_seed_commitment_invalid")
    contracts = private_key.get("contracts") or {}
    cases = manifest.get("cases") or ()
    if {str(row.get("case_id") or "") for row in cases} != set(contracts):
        errors.append("case_contract_identity_mismatch")
    for row in cases:
        case_id = str(row.get("case_id") or "")
        contract = contracts.get(case_id) or {}
        contract_material = {key: value for key, value in contract.items() if key != "contract_hash"}
        if contract.get("contract_hash") != _sha(contract_material):
            errors.append(f"contract_hash_invalid:{case_id}")
        if row.get("contract_commitment") != _sha(
            {"case_id": case_id, "contract": contract, "secret_seed": seed}
        ):
            errors.append(f"contract_commitment_invalid:{case_id}")
        if any(key in row for key in ("required_cause_clauses", "reference_response")):
            errors.append(f"private_contract_leaked:{case_id}")
    if manifest.get("development_only") is not True or manifest.get("confirmatory_eligible") is not False:
        errors.append("development_boundary_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


def evaluate_atomic_causal_response(
    contract: Mapping[str, Any], public_text: str
) -> dict[str, Any]:
    """Score only the frozen public response; caller verdicts are irrelevant."""
    errors: list[str] = []
    try:
        response = json.loads(str(public_text))
    except json.JSONDecodeError:
        response = None
    if not isinstance(response, Mapping):
        return {
            "state": "unknown",
            "success": None,
            "errors": ["response_json_object_required"],
            "contract_hash": contract.get("contract_hash"),
            "independent": True,
        }
    allowed = set(contract.get("allowed_response_keys") or ())
    if set(response) != allowed:
        errors.append("response_keys_invalid")
    cause = _normalized(str(response.get("cause") or ""))
    repair = _normalized(str(response.get("repair") or ""))
    combined = f"{cause} {repair}".strip()

    def clause_passes(clause: Any, text: str) -> bool:
        return any(_normalized(str(option)) in text for option in (clause or ()))

    missing_cause = [
        index
        for index, clause in enumerate(contract.get("required_cause_clauses") or ())
        if not clause_passes(clause, cause)
    ]
    missing_repair = [
        index
        for index, clause in enumerate(contract.get("required_repair_clauses") or ())
        if not clause_passes(clause, repair)
    ]
    if missing_cause:
        errors.append("required_cause_atoms_missing")
    if missing_repair:
        errors.append("required_repair_atoms_missing")
    forbidden = [
        term
        for term in contract.get("forbidden_terms") or ()
        if _normalized(str(term)) in combined
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
        "missing_cause_clause_indices": missing_cause,
        "missing_repair_clause_indices": missing_repair,
        "forbidden_terms_observed": forbidden,
        "contract_hash": contract.get("contract_hash"),
        "response_hash": _sha(response),
        "independent": True,
        "caller_success_authoritative": False,
    }


def audit_atomic_evaluator_response(
    contract: Mapping[str, Any], public_text: str
) -> dict[str, Any]:
    """Diagnose lexical near-misses without changing the frozen v1 verdict."""
    original = evaluate_atomic_causal_response(contract, public_text)
    try:
        response = json.loads(str(public_text))
    except json.JSONDecodeError:
        response = None
    if not isinstance(response, Mapping):
        return {
            "state": "audit_unavailable",
            "original_state": original["state"],
            "brittleness_signal": False,
            "reason": "public_json_unavailable",
        }

    def recalls(clauses: Any, text: str) -> list[float]:
        observed = set(_normalized(text).split())
        result = []
        for clause in clauses or ():
            options = []
            for alternative in clause or ():
                required = set(_normalized(str(alternative)).split())
                options.append(len(required & observed) / len(required) if required else 0.0)
            result.append(round(max(options, default=0.0), 9))
        return result

    cause_recalls = recalls(contract.get("required_cause_clauses"), str(response.get("cause") or ""))
    repair_recalls = recalls(contract.get("required_repair_clauses"), str(response.get("repair") or ""))
    combined = cause_recalls + repair_recalls
    mean_recall = round(sum(combined) / len(combined), 9) if combined else 0.0
    errors = set(original.get("errors") or ())
    structural_gates_pass = not errors.intersection(
        {
            "response_keys_invalid",
            "forbidden_unsupported_claim",
            "causal_evidence_binding_invalid",
            "uncertainty_state_invalid",
        }
    )
    lexical_only_failure = bool(errors) and errors.issubset(
        {"required_cause_atoms_missing", "required_repair_atoms_missing"}
    )
    brittleness_signal = bool(
        original.get("success") is False
        and structural_gates_pass
        and lexical_only_failure
        and mean_recall >= 0.75
    )
    return {
        "state": "evaluator_brittleness_signal" if brittleness_signal else "no_brittleness_signal",
        "original_state": original["state"],
        "original_success": original["success"],
        "original_errors": list(original.get("errors") or ()),
        "cause_clause_token_recall": cause_recalls,
        "repair_clause_token_recall": repair_recalls,
        "mean_clause_token_recall": mean_recall,
        "structural_gates_pass": structural_gates_pass,
        "lexical_only_failure": lexical_only_failure,
        "brittleness_signal": brittleness_signal,
        "changes_original_verdict": False,
        "semantic_correctness_established": False,
    }


def freeze_open_response_forge(
    store: Any,
    repo: str,
    *,
    prior_result_receipt_hash: str,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Open the new zero-call forge only from the canonical exhausted ladder."""
    prior_hash = str(prior_result_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, prior_hash).get("valid") is not True:
        raise ValueError("canonical prior calibration result is required")
    prior = store.symbiotic_receipt(prior_hash, repo=repo) or {}
    prereg_hash = str(prior.get("preregistration_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("prior calibration preregistration is invalid")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    levels = {
        int(row.get("difficulty_level") or 0)
        for row in prereg.get("cases") or ()
        if isinstance(row, Mapping)
    }
    screen = prior.get("screen") or {}
    if not (
        prior.get("kind") == "live_semantic_calibration_result"
        and prior.get("status") == "LIVE_BASELINE_SCREEN_RECONSTRUCTED"
        and levels == {3}
        and int(screen.get("success_count") or 0) == 4
        and int(screen.get("case_count") or 0) == 4
        and screen.get("state") == "screening_ceiling"
        and prior.get("semantic_transfer_established") is False
    ):
        raise ValueError("prior evidence does not prove exhausted choice geometry")
    check = verify_open_response_latent_bundle(bundle)
    if check.get("valid") is not True:
        raise ValueError("open-response latent bundle is invalid")
    manifest = bundle["manifest"]
    material = {
        "schema_version": PREFLIGHT_SCHEMA,
        "version": __version__,
        "kind": "open_response_latent_cause_preflight",
        "repo": repo,
        "repository_id": str(store.repo(repo)["repository_id"]),
        "prior_result_receipt_hash": prior_hash,
        "prior_preregistration_receipt_hash": prereg_hash,
        "choice_geometry_evidence": {"level": 3, "successes": 4, "cases": 4},
        "corpus_hash": manifest["corpus_hash"],
        "private_key_commitment": manifest["private_key_commitment"],
        "initial_screen_level": manifest["initial_screen_level"],
        "initial_screen_case_ids": [
            row["case_id"]
            for row in manifest["cases"]
            if row["difficulty_level"] == manifest["initial_screen_level"]
        ],
        "state": "OPEN_RESPONSE_LATENT_FORGE_READY",
        "planned_live_calls": 0,
        "calibration_established": False,
        "semantic_transfer_established": False,
        "next_action": "run_four_call_task_only_open_response_screen_after_separate_authorization",
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    preflight_id = _sha(material)
    session = open_symbiotic_session(
        store, repo, task="freeze open-response latent-cause forge", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "preflight_id": preflight_id,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"open_response_forge_{preflight_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def freeze_live_open_response_screen(
    store: Any,
    repo: str,
    *,
    preflight_receipt_hash: str,
    manifest: Mapping[str, Any],
    private_key: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Freeze the exact four-call open-response screen before invocation."""
    preflight_hash = str(preflight_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, preflight_hash).get("valid") is not True:
        raise ValueError("canonical open-response preflight is required")
    preflight = store.symbiotic_receipt(preflight_hash, repo=repo) or {}
    if (
        preflight.get("kind") != "open_response_latent_cause_preflight"
        or preflight.get("state") != "OPEN_RESPONSE_LATENT_FORGE_READY"
        or int(preflight.get("planned_live_calls", -1)) != 0
    ):
        raise ValueError("open-response preflight cannot open a live screen")
    bundle = {"manifest": dict(manifest), "private_key": dict(private_key)}
    if verify_open_response_latent_bundle(bundle).get("valid") is not True:
        raise ValueError("open-response private evaluator does not match public corpus")
    if (
        preflight.get("corpus_hash") != manifest.get("corpus_hash")
        or preflight.get("private_key_commitment")
        != manifest.get("private_key_commitment")
    ):
        raise ValueError("open-response corpus is not bound to the preflight")
    case_ids = list(preflight.get("initial_screen_case_ids") or ())
    cases_by_id = {str(row.get("case_id") or ""): row for row in manifest.get("cases") or ()}
    cases = [cases_by_id.get(str(case_id)) for case_id in case_ids]
    if len(cases) != 4 or any(not isinstance(row, Mapping) for row in cases):
        raise ValueError("live open-response screen requires four bound cases")
    identity = _adapter_identity(adapter)
    if not all(identity.values()):
        raise ValueError("complete adapter identity is required")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    provenance_check = verify_adapter_provenance(store, repo, provenance)
    if (
        provenance_check.get("valid") is not True
        or provenance.get("evidence_class") != EVIDENCE_LIVE
    ):
        raise ValueError("live host-registered adapter provenance is required")
    material = {
        "schema_version": "cortex-live-open-response-preregistration/1.0",
        "version": __version__,
        "kind": "live_open_response_preregistration",
        "repo": repo,
        "repository_id": str(store.repo(repo)["repository_id"]),
        "forge_preflight_receipt_hash": preflight_hash,
        "corpus_hash": manifest["corpus_hash"],
        "private_key_commitment": manifest["private_key_commitment"],
        "screen_level": int(preflight["initial_screen_level"]),
        "cases": cases,
        "planned_calls": 4,
        "context_treatment": "task_only_control",
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "evaluator_id": "cortex.atomic-causal-response.v1",
        "private_contract_persisted": False,
        "caller_success_booleans_accepted": False,
        "status": "frozen_before_execution",
        "development_only": True,
        "confirmatory_eligible": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    preregistration_id = _sha(material)
    session = open_symbiotic_session(
        store, repo, task="freeze live open-response baseline", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "preregistration_id": preregistration_id,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"live_open_response_prereg_{preregistration_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def execute_live_open_response_screen(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    manifest: Mapping[str, Any],
    private_key: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    """Execute four calls and rebuild every score from canonical trajectories."""
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical live open-response preregistration is required")
    if preregistration.get("kind") != "live_open_response_preregistration":
        raise ValueError("live open-response preregistration kind is invalid")
    bundle = {"manifest": dict(manifest), "private_key": dict(private_key)}
    if verify_open_response_latent_bundle(bundle).get("valid") is not True:
        raise ValueError("private evaluator no longer matches public corpus")
    if (
        manifest.get("corpus_hash") != preregistration.get("corpus_hash")
        or manifest.get("private_key_commitment")
        != preregistration.get("private_key_commitment")
    ):
        raise ValueError("live screen corpus binding is invalid")
    if _adapter_identity(adapter) != preregistration.get("model_identity"):
        raise ValueError("adapter identity changed after preregistration")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if provenance != preregistration.get("adapter_provenance"):
        raise ValueError("adapter provenance changed after preregistration")
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    contracts = private_key.get("contracts") or {}
    case_receipts: list[dict[str, Any]] = []
    for case in preregistration.get("cases") or ():
        case_id = str(case["case_id"])
        contract = contracts.get(case_id)
        if not isinstance(contract, Mapping):
            raise ValueError(f"private evaluator missing for {case_id}")
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
        evaluation = evaluate_atomic_causal_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        material = {
            "schema_version": "cortex-live-open-response-case/1.0",
            "version": __version__,
            "kind": "live_open_response_case",
            "preregistration_receipt_hash": prereg_hash,
            "case_id": case_id,
            "case_hash": _sha(case),
            "private_contract_hash": contract["contract_hash"],
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
        session = open_symbiotic_session(
            store, repo, task=f"seal live open-response case {case_id}", persist=True
        )
        case_receipts.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **material,
                    "status": "live_baseline_observation",
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"live_open_response_case_{_sha(material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )
    outcomes: list[bool] = []
    unknown_count = 0
    errors: list[str] = []
    for row in case_receipts:
        trajectory_hash = str(row["trajectory_receipt_hash"])
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        contract = contracts.get(str(row["case_id"])) or {}
        rebuilt = evaluate_atomic_causal_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"trajectory_invalid:{row['case_id']}")
        if rebuilt != row.get("evaluation"):
            errors.append(f"evaluation_reconstruction_invalid:{row['case_id']}")
        if rebuilt.get("success") is None:
            unknown_count += 1
        else:
            outcomes.append(rebuilt.get("success") is True)
    if unknown_count:
        screen = {
            "state": "screening_held_unknown",
            "recommended_action": "repair_response_contract_or_transport",
            "case_count": len(case_receipts),
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
        "schema_version": "cortex-live-open-response-result/1.0",
        "version": __version__,
        "kind": "live_open_response_result",
        "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [row["receipt_hash"] for row in case_receipts],
        "model_identity": preregistration["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": screen,
        "errors": errors,
        "calls_executed": len(case_receipts),
        "calibration_established": screen["state"] == "calibrated" and not errors,
        "semantic_transfer_established": False,
        "status": "LIVE_OPEN_RESPONSE_SCREEN_RECONSTRUCTED" if not errors else "LIVE_OPEN_RESPONSE_SCREEN_HELD",
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(
        store, repo, task="seal live open-response baseline result", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"live_open_response_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def audit_live_open_response_result(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    private_key: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal a non-authorizing diagnostic over immutable live case receipts."""
    result_hash = str(result_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, result_hash).get("valid") is not True:
        raise ValueError("canonical live open-response result is required")
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    if result.get("kind") != "live_open_response_result":
        raise ValueError("live open-response result kind is invalid")
    contracts = private_key.get("contracts") or {}
    diagnostics = []
    errors = []
    for case_hash in result.get("case_receipt_hashes") or ():
        if store.verify_symbiotic_receipt(repo, str(case_hash)).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{case_hash}")
            continue
        case = store.symbiotic_receipt(str(case_hash), repo=repo) or {}
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"trajectory_invalid:{case.get('case_id')}")
            continue
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        contract = contracts.get(str(case.get("case_id") or ""))
        if not isinstance(contract, Mapping):
            errors.append(f"private_contract_missing:{case.get('case_id')}")
            continue
        diagnostic = audit_atomic_evaluator_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        diagnostics.append(
            {
                "case_id": case["case_id"],
                "case_receipt_hash": case_hash,
                "trajectory_receipt_hash": trajectory_hash,
                "private_contract_hash": contract["contract_hash"],
                "diagnostic": diagnostic,
            }
        )
    all_signal = bool(diagnostics) and all(
        row["diagnostic"].get("brittleness_signal") is True for row in diagnostics
    )
    material = {
        "schema_version": "cortex-live-open-response-evaluator-audit/1.0",
        "version": __version__,
        "kind": "live_open_response_evaluator_audit",
        "result_receipt_hash": result_hash,
        "diagnostics": diagnostics,
        "errors": errors,
        "state": "EVALUATOR_BRITTLENESS_DETECTED" if all_signal and not errors else "EVALUATOR_AUDIT_HELD",
        "raw_screen_state_preserved": (result.get("screen") or {}).get("state"),
        "raw_scores_rewritten": False,
        "baseline_difficulty_established": False,
        "calibration_established": False,
        "semantic_transfer_established": False,
        "next_action": "freeze_paraphrase_robust_v2_evaluator_before_new_calls",
        "claim_boundary": (
            "Lexical near-miss diagnostics do not establish semantic correctness or "
            "rewrite the frozen v1 evaluation. They may only hold calibration."
        ),
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(
        store, repo, task="audit live open-response evaluator brittleness", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"live_open_response_audit_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "CONTRACT_SCHEMA",
    "HostCalibrationContractVault",
    "PREFLIGHT_SCHEMA",
    "PRIVATE_SCHEMA",
    "PUBLIC_SCHEMA",
    "build_open_response_latent_bundle",
    "audit_atomic_evaluator_response",
    "audit_live_open_response_result",
    "evaluate_atomic_causal_response",
    "execute_live_open_response_screen",
    "freeze_open_response_forge",
    "freeze_live_open_response_screen",
    "verify_open_response_latent_bundle",
]
