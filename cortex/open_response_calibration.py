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
        chunks = [encoded[index:index + 1800] for index in range(0, len(encoded), 1800)]
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


__all__ = [
    "CONTRACT_SCHEMA",
    "HostCalibrationContractVault",
    "PREFLIGHT_SCHEMA",
    "PRIVATE_SCHEMA",
    "PUBLIC_SCHEMA",
    "build_open_response_latent_bundle",
    "evaluate_atomic_causal_response",
    "freeze_open_response_forge",
    "verify_open_response_latent_bundle",
]
