"""v8.3.3 activation measurement-conformance receipts.

The producer is the normal activation path.  This module only captures and
independently verifies that one persisted state transition was represented
correctly.  It does not establish task utility, prediction accuracy, cognition,
consciousness, agency, or authority.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Mapping

from ..cognitive.measured import (
    capture_measured_state,
    coordinate_schema_payload,
    measured_delta,
)
from ..epoch import observe_current_epoch
from ..math_net.info_interlock import measurement_cohort_identity
from .contracts import ActivationObservationInput, MeasuredActivationTransition
from .independent_verifier import (
    CONFORMANCE_TOLERANCE,
    VERIFIER_DIGEST,
    VERIFIER_IMPLEMENTATION_VERSION,
    independently_recompute_transition,
    measurement_subject_hash,
    residual_panel,
    validate_conformance_payload,
)
SCHEMA = "cortex-activation-conformance/1.0"
INPUT_TYPE = "ActivationObservationInput"
OUTPUT_TYPE = "MeasuredActivationTransition"
OPERATOR_ID = "activation_observation"
CLAIM_BOUNDARY = (
    "v8.3.3 verifies activation-measurement conformance. It does not establish "
    "that Cortex improves task performance, reasoning quality, cognition, "
    "consciousness, agency, or authority."
)
def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _invariant(
    invariant_id: str,
    passed: bool,
    *,
    evidence_ids: list[str],
    expected: Any,
    observed: Any,
    reason: str,
) -> dict[str, Any]:
    return {
        "invariant_id": invariant_id,
        "passed": bool(passed),
        "evidence_ids": list(evidence_ids),
        "expected": expected,
        "observed": observed,
        "reason": reason,
    }


def _event_id(
    *,
    repository_id: str,
    task_hash: str,
    controller: str,
    capability_id: str,
    before_hash: str,
    after_hash: str,
) -> str:
    material = {
        "repository_id": repository_id,
        "task_hash": task_hash,
        "controller": controller,
        "capability_id": capability_id,
        "before_hash": before_hash,
        "after_hash": after_hash,
    }
    return "mevent_" + _sha(material)[:20]


def _current_cohort(
    repo: str,
    body_epoch: Mapping[str, Any],
    coordinate_schema_digest: str,
) -> str:
    return measurement_cohort_identity(
        repo=repo,
        repository_id=str(body_epoch.get("repository_id") or ""),
        evidence_root_hash=str(body_epoch.get("evidence_root_hash") or ""),
        schema_hash=str(body_epoch.get("schema_hash") or ""),
        constitutional_config_hash=str(
            body_epoch.get("constitutional_config_hash") or ""
        ),
        coordinate_schema_digest=coordinate_schema_digest,
        prefix="aco",
    )


def build_activation_conformance_receipt(
    store: Any,
    repo: str,
    *,
    task: str,
    controller: str,
    realized_action: str,
    capability_id: str,
    pre_epoch_id: str,
    body_epoch: Mapping[str, Any],
    measured_transition: Mapping[str, Any],
    host_manifest_before: str,
    host_manifest_after: str,
    measurement_cohort_id: str | None = None,
) -> dict[str, Any]:
    """Build a pre-ledger receipt from production-path measurement material."""
    repository = store.repo(repo)
    repository_id = str(repository["repository_id"] or "") if repository else ""
    task_hash = hashlib.sha256(task.encode("utf-8")).hexdigest()
    coordinate_metadata = coordinate_schema_payload()
    coordinate_digest = str(coordinate_metadata["coordinate_schema_digest"])
    before = dict(measured_transition.get("before_state") or {})
    after = dict(measured_transition.get("after_state") or {})
    persisted = measured_transition.get("normalized_delta") or {}
    event_id = str(measured_transition.get("event_id") or "")
    if not event_id:
        event_id = _event_id(
            repository_id=repository_id,
            task_hash=task_hash,
            controller=controller,
            capability_id=capability_id,
            before_hash=str(before.get("state_hash") or ""),
            after_hash=str(after.get("state_hash") or ""),
        )
    observation_input = ActivationObservationInput(
        task_hash=task_hash,
        controller=controller,
        capability_id=capability_id,
        repository_id=repository_id,
        pre_epoch_id=pre_epoch_id,
        coordinate_schema_digest=coordinate_digest,
    )
    transition = MeasuredActivationTransition(
        before_state=before,
        after_state=after,
        raw_delta=dict(
            measured_transition.get("raw_delta")
            or measured_transition.get("delta")
            or {}
        ),
        normalized_delta=dict(persisted) if isinstance(persisted, Mapping) else {},
        coordinate_validity=dict(
            measured_transition.get("coordinate_validity") or {}
        ),
        signed_channel_mass=dict(
            measured_transition.get("signed_channel_mass") or {}
        ),
        event_id=event_id,
    )
    recomputed = independently_recompute_transition(before, after)
    panel = residual_panel(
        persisted,
        recomputed["normalized_delta"],
        recomputed["coordinate_validity"],
    )
    epoch_observation = observe_current_epoch(store, repo)
    claimed_epoch_id = str(body_epoch.get("epoch_id") or "")
    epoch_current = bool(
        epoch_observation.get("present")
        and epoch_observation.get("verified")
        and claimed_epoch_id
        and claimed_epoch_id == epoch_observation.get("epoch_id")
        and claimed_epoch_id == epoch_observation.get("live_epoch_id")
        and repository_id == str(body_epoch.get("repository_id") or "")
    )
    try:
        expected_cohort = _current_cohort(repo, body_epoch, coordinate_digest)
    except Exception:
        expected_cohort = ""
    claimed_cohort = str(measurement_cohort_id or expected_cohort)
    cohort_current = bool(
        epoch_current and expected_cohort and claimed_cohort == expected_cohort
    )
    schema_match = bool(
        measured_transition.get("coordinate_schema_digest") == coordinate_digest
        and before.get("coordinate_schema_digest") == coordinate_digest
        and after.get("coordinate_schema_digest") == coordinate_digest
        and recomputed.get("coordinate_schema_match")
        and measured_transition.get("scale_digest")
        == coordinate_metadata["scale_digest"]
    )
    host_immutable = bool(
        host_manifest_before
        and host_manifest_after
        and host_manifest_before == host_manifest_after
    )
    measurement_complete = bool(
        recomputed.get("measurement_complete")
        and float(recomputed.get("valid_fraction") or 0.0) == 1.0
    )
    delta_recomputed = bool(panel.get("conforms"))

    subject = {
        "schema_version": SCHEMA,
        "operator_id": OPERATOR_ID,
        "input_type": INPUT_TYPE,
        "output_type": OUTPUT_TYPE,
        "input": observation_input.to_dict(),
        "measured_transition": transition.to_dict(),
        "observed_output": transition.to_dict()["normalized_delta"],
        "reference_output": recomputed["normalized_delta"],
        "residual_panel": panel,
        "B_rms": panel["B_rms"],
        "B_max": panel["B_max"],
        "B_invalid": panel["B_invalid"],
        "channel_burdens": panel["channel_burdens"],
        "verifier_implementation_version": VERIFIER_IMPLEMENTATION_VERSION,
        "verifier_digest": VERIFIER_DIGEST,
        "repository_id": repository_id,
        "repo": repo,
        "event_id": event_id,
        "case_id": "case_" + task_hash[:24],
        "comparison_arm": controller,
        "controller": controller,
        "realized_action": realized_action,
        "task_hash": task_hash,
        "body_epoch_id": claimed_epoch_id,
        "measurement_cohort_id": claimed_cohort,
        "coordinate_schema_version": coordinate_metadata[
            "coordinate_schema_version"
        ],
        "coordinate_schema_digest": coordinate_digest,
        "ordered_coordinate_names": list(
            coordinate_metadata["ordered_coordinate_names"]
        ),
        "ordered_shape_signature": list(
            coordinate_metadata["ordered_shape_signature"]
        ),
        "scale_digest": coordinate_metadata["scale_digest"],
        "valid_fraction": recomputed["valid_fraction"],
    }
    subject_receipt_hash = measurement_subject_hash(subject)
    witness_material = {
        "witness_kind": "MEASUREMENT",
        "verifier": "cortex.ostt.independent_verifier",
        "subject_receipt_hash": subject_receipt_hash,
        "evidence_hashes": [
            str(before.get("state_hash") or ""),
            str(after.get("state_hash") or ""),
            VERIFIER_DIGEST,
            coordinate_digest,
        ],
        "passed": bool(
            measurement_complete
            and delta_recomputed
            and recomputed.get("before_hash_valid")
            and recomputed.get("after_hash_valid")
        ),
    }
    measurement_witness = {
        "witness_id": "mw_" + _sha(witness_material)[:24],
        **witness_material,
        "issued_at": float(
            measured_transition.get("measured_at")
            or after.get("captured_at")
            or before.get("captured_at")
            or 0.0
        ),
    }
    invariant_results = [
        _invariant(
            "host_immutable",
            host_immutable,
            evidence_ids=[host_manifest_before, host_manifest_after],
            expected=host_manifest_before,
            observed=host_manifest_after,
            reason="pre/post host-source manifests compared",
        ),
        _invariant(
            "epoch_current",
            epoch_current,
            evidence_ids=[claimed_epoch_id, str(epoch_observation.get("live_epoch_id") or "")],
            expected=claimed_epoch_id,
            observed=epoch_observation.get("live_epoch_id"),
            reason="sealed epoch compared with live repository roots",
        ),
        _invariant(
            "cohort_current",
            cohort_current,
            evidence_ids=[claimed_cohort, expected_cohort],
            expected=expected_cohort,
            observed=claimed_cohort,
            reason="cohort recomputed from current identity roots and coordinate schema",
        ),
        _invariant(
            "coordinate_schema_match",
            schema_match,
            evidence_ids=[coordinate_digest],
            expected=coordinate_digest,
            observed=measured_transition.get("coordinate_schema_digest"),
            reason="ordered coordinate and scale schema checked",
        ),
        _invariant(
            "measurement_complete",
            measurement_complete,
            evidence_ids=[str(before.get("state_hash") or ""), str(after.get("state_hash") or "")],
            expected=1.0,
            observed=recomputed.get("valid_fraction"),
            reason="every required coordinate must be valid before and after",
        ),
        _invariant(
            "before_hash_valid",
            bool(recomputed.get("before_hash_valid")),
            evidence_ids=[str(before.get("state_hash") or "")],
            expected=True,
            observed=bool(recomputed.get("before_hash_valid")),
            reason="before snapshot hash independently recomputed",
        ),
        _invariant(
            "after_hash_valid",
            bool(recomputed.get("after_hash_valid")),
            evidence_ids=[str(after.get("state_hash") or "")],
            expected=True,
            observed=bool(recomputed.get("after_hash_valid")),
            reason="after snapshot hash independently recomputed",
        ),
        _invariant(
            "delta_recomputed",
            delta_recomputed,
            evidence_ids=[VERIFIER_DIGEST, subject_receipt_hash],
            expected={"B_rms_max": CONFORMANCE_TOLERANCE, "B_max_max": CONFORMANCE_TOLERANCE},
            observed={"B_rms": panel["B_rms"], "B_max": panel["B_max"]},
            reason="persisted normalized vector compared with independent raw-snapshot recomputation",
        ),
        _invariant(
            "exactly_once_event",
            False,
            evidence_ids=[event_id],
            expected="one canonical row per repository/operator/event",
            observed="pending_ledger_append",
            reason="proved only by the transactional canonical append",
        ),
        _invariant(
            "receipt_hash_valid",
            False,
            evidence_ids=[subject_receipt_hash],
            expected="canonical SHA-256 envelope",
            observed="pending_ledger_append",
            reason="proved only after the canonical ledger envelope is stored",
        ),
    ]
    scientific_candidate = bool(
        observation_input.to_dict()["valid"]
        and transition.to_dict()["valid"]
        and all(
            result["passed"]
            for result in invariant_results
            if result["invariant_id"]
            not in {"exactly_once_event", "receipt_hash_valid"}
        )
        and measurement_witness["passed"]
    )
    return {
        **subject,
        "measurement_subject_hash": subject_receipt_hash,
        "measurement_witness": measurement_witness,
        "outcome_receipt": {"status": "pending", "required_for_conformance": False},
        "invariant_results": invariant_results,
        "status": (
            "conformance_candidate"
            if scientific_candidate
            else "observed_incomplete"
        ),
        "gate_state": "OBSERVED",
        "candidate_ready": scientific_candidate,
        "evidence_ready": False,
        "conformance_ready": False,
        "cohort_calibrated": False,
        "cohort_minimum": 16,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "created_at": time.time(),
    }


def capture_activation_transition(
    store: Any,
    repo: str,
    before_state: Mapping[str, Any],
    *,
    event_id: str,
) -> dict[str, Any]:
    """Controller-neutral producer used by the shared finalizer."""
    after_state = capture_measured_state(store, repo)
    return measured_delta(
        dict(before_state),
        after_state,
        event_id=event_id,
        event_kind="activation_transaction",
    )


def open_activation_observation(
    store: Any,
    repo: str,
    *,
    pre_epoch_id: str,
    host_manifest: str,
) -> dict[str, Any]:
    """Capture the metrology opening after activation identity is bound.

    This opening is deliberately independent of the predictive cognitive-cycle
    opening.  The latter may begin before evidence refresh and epoch rebinding;
    reusing it would make the conformance receipt describe a wider, stale
    transition than the activation identity named by the receipt.
    """
    return {
        "schema_version": "cortex-activation-observation-opening/1.0",
        "pre_epoch_id": str(pre_epoch_id or ""),
        "before_state": capture_measured_state(store, repo),
        "host_manifest_before": str(host_manifest or ""),
        "opened_at": time.time(),
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
    }


def finalize_activation_observation(
    store: Any,
    repo: str,
    activation: dict[str, Any],
    *,
    task: str,
    controller: str,
    realized_action: str,
    capability_id: str,
    pre_epoch_id: str,
    before_state: Mapping[str, Any],
    host_manifest_before: str,
    host_manifest_after: str,
) -> dict[str, Any]:
    """Finalize either controller through one observation-only code path."""
    # Always reconstruct the conformance transition from the explicit
    # post-binding opening.  ``activation["measured_event_field"]`` may be a
    # predictive cognitive-cycle transition opened before refresh/epoch
    # rebinding and is therefore not admissible as this receipt's pre-state.
    repository = store.repo(repo)
    repository_id = str(repository["repository_id"] or "") if repository else ""
    provisional_event = _event_id(
        repository_id=repository_id,
        task_hash=hashlib.sha256(task.encode("utf-8")).hexdigest(),
        controller=controller,
        capability_id=capability_id,
        before_hash=str(before_state.get("state_hash") or ""),
        after_hash="pending",
    )
    measured = capture_activation_transition(
        store,
        repo,
        before_state,
        event_id=provisional_event,
    )
    final_event = _event_id(
        repository_id=repository_id,
        task_hash=hashlib.sha256(task.encode("utf-8")).hexdigest(),
        controller=controller,
        capability_id=capability_id,
        before_hash=str(before_state.get("state_hash") or ""),
        after_hash=str((measured.get("after_state") or {}).get("state_hash") or ""),
    )
    measured = measured_delta(
        dict(before_state),
        dict(measured.get("after_state") or {}),
        event_id=final_event,
        event_kind="activation_transaction",
    )
    activation["measured_event_field"] = measured
    store.set_setting(f"measured_event_latest:{repo}", measured)
    body_epoch = dict(activation.get("body_epoch") or {})
    receipt = build_activation_conformance_receipt(
        store,
        repo,
        task=task,
        controller=controller,
        realized_action=realized_action,
        capability_id=capability_id,
        pre_epoch_id=pre_epoch_id,
        body_epoch=body_epoch,
        measured_transition=dict(measured),
        host_manifest_before=host_manifest_before,
        host_manifest_after=host_manifest_after,
    )
    appended = store.append_activation_conformance_receipt(repo, receipt)
    canonical = dict(appended.get("receipt") or appended)
    canonical["inserted"] = bool(appended.get("inserted"))
    canonical["duplicate"] = bool(appended.get("duplicate"))
    canonical["chain_sequence"] = appended.get(
        "chain_sequence", canonical.get("chain_sequence")
    )
    canonical["previous_receipt_hash"] = appended.get(
        "previous_receipt_hash", canonical.get("previous_receipt_hash")
    )
    chain = store.verify_activation_conformance_chain(
        repo,
        str(canonical.get("operator_id") or ""),
        str(canonical.get("body_epoch_id") or ""),
        str(canonical.get("measurement_cohort_id") or ""),
        str(canonical.get("coordinate_schema_digest") or ""),
    )
    canonical["chain_valid"] = bool(chain.get("valid"))
    cohort_rows = store.activation_conformance_receipts(
        repo,
        operator_id=OPERATOR_ID,
        body_epoch_id=canonical.get("body_epoch_id"),
        measurement_cohort_id=canonical.get("measurement_cohort_id"),
        coordinate_schema_digest=canonical.get("coordinate_schema_digest"),
        limit=128,
    )
    cohort_count = len(cohort_rows)
    cohort_rows_valid = True
    for row in cohort_rows:
        try:
            row_valid = bool(
                row.get("status") == "conformance_measured"
                and float(row.get("valid_fraction") or 0.0) == 1.0
                and validate_conformance_payload(row).get("valid") is True
            )
        except Exception:
            row_valid = False
        if not row_valid:
            cohort_rows_valid = False
            break
    canonical["cohort_count"] = cohort_count
    canonical["cohort_calibrated"] = bool(
        cohort_count >= 16
        and chain.get("valid") is True
        and cohort_rows_valid
    )
    canonical["gate_c_state"] = (
        "COHORT_CALIBRATED" if canonical["cohort_calibrated"] else "COLD"
    )
    store.set_setting(f"ostt_residual_latest:{repo}", canonical)
    history = store.activation_conformance_receipts(repo, limit=128)
    store.set_setting(f"ostt_residual_history:{repo}", history)
    return canonical


def activation_receipt_report(store: Any, repo: str) -> dict[str, Any]:
    receipt = store.latest_activation_conformance_receipt(repo)
    if not receipt:
        return {
            "status": "unmeasured",
            "repo": repo,
            "policy_effect": False,
            "update_authorized": False,
            "advisory_only": True,
        }
    verification = verify_activation_receipt(
        store, repo, str(receipt.get("receipt_hash") or "")
    )
    return {**receipt, **verification}


def activation_cohort_report(store: Any, repo: str) -> dict[str, Any]:
    latest = store.latest_activation_conformance_receipt(repo)
    if not latest:
        return {
            "status": "cold",
            "receipt_count": 0,
            "remaining": 16,
            "policy_effect": False,
            "update_authorized": False,
            "advisory_only": True,
        }
    rows = store.activation_conformance_receipts(
        repo,
        operator_id=OPERATOR_ID,
        body_epoch_id=latest.get("body_epoch_id"),
        measurement_cohort_id=latest.get("measurement_cohort_id"),
        coordinate_schema_digest=latest.get("coordinate_schema_digest"),
        limit=4096,
    )
    # Cohort counting uses the independent scientific validator, not the
    # ledger-bound ResidualReceipt.evidence_ready surface.  A stored row is
    # compatible when Gate-B status and independent recomputation still hold.
    compatible = []
    for row in rows:
        if row.get("status") != "conformance_measured":
            continue
        try:
            scientific = validate_conformance_payload(row)
        except Exception:
            continue
        if scientific.get("valid") is True:
            compatible.append(row)
    coordinate_errors: dict[str, list[float]] = {}
    channel_burdens: dict[str, list[float]] = {}
    for row in compatible:
        panel = row.get("residual_panel") or {}
        for name, value in (panel.get("per_coordinate_absolute_error") or {}).items():
            if value is not None:
                coordinate_errors.setdefault(name, []).append(float(value))
        for name, value in (panel.get("channel_burdens") or {}).items():
            channel_burdens.setdefault(name, []).append(float(value))
    count = len(compatible)
    chain = store.verify_activation_conformance_chain(
        repo,
        OPERATOR_ID,
        str(latest.get("body_epoch_id") or ""),
        str(latest.get("measurement_cohort_id") or ""),
        str(latest.get("coordinate_schema_digest") or ""),
    )
    calibrated = bool(
        count >= 16
        and len(compatible) == len(rows)
        and chain.get("valid") is True
        and all(float(row.get("valid_fraction") or 0.0) == 1.0 for row in rows)
    )
    return {
        "status": "cohort_calibrated" if calibrated else "cold",
        "repo": repo,
        "body_epoch_id": latest.get("body_epoch_id"),
        "measurement_cohort_id": latest.get("measurement_cohort_id"),
        "coordinate_schema_digest": latest.get("coordinate_schema_digest"),
        "receipt_count": count,
        "required_count": 16,
        "remaining": max(0, 16 - count),
        "per_coordinate_distributions": {
            name: {
                "n": len(values),
                "mean_absolute_error": sum(values) / len(values),
                "max_absolute_error": max(values),
            }
            for name, values in coordinate_errors.items()
        },
        "per_channel_distributions": {
            name: {
                "n": len(values),
                "mean_burden": sum(values) / len(values),
                "max_burden": max(values),
            }
            for name, values in channel_burdens.items()
        },
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_activation_receipt(
    store: Any, repo: str, receipt_hash: str
) -> dict[str, Any]:
    receipt = store.activation_conformance_receipt(receipt_hash)
    if not receipt or receipt.get("repo") != repo:
        return {
            "status": "not_found",
            "receipt_hash": receipt_hash,
            "receipt_hash_valid": False,
            "chain_valid": False,
            "policy_effect": False,
            "update_authorized": False,
            "advisory_only": True,
        }
    chain = store.verify_activation_conformance_chain(
        repo,
        str(receipt.get("operator_id") or ""),
        str(receipt.get("body_epoch_id") or ""),
        str(receipt.get("measurement_cohort_id") or ""),
        str(receipt.get("coordinate_schema_digest") or ""),
    )
    row_valid = bool(chain.get("valid")) and receipt_hash not in set(
        chain.get("invalid_receipt_hashes") or []
    )
    try:
        scientific = validate_conformance_payload(receipt)
        panel = scientific.get("residual_panel") or {"conforms": False}
        transition_checks = scientific.get("transition_checks") or {}
        witness_checks = scientific.get("witness_checks") or {}
        reference_matches = bool(transition_checks.get("reference_output"))
        witness_valid = bool(witness_checks) and all(witness_checks.values())
        measurement_subject_hash_valid = bool(
            receipt.get("measurement_subject_hash")
            and receipt.get("measurement_subject_hash")
            == scientific.get("measurement_subject_hash")
        )
        host_projection_valid = (
            "invariant_evidence_mismatch:host_immutable"
            not in set(scientific.get("errors") or ())
        )
        invariant_panel_valid = not any(
            str(error).startswith("invariant_")
            for error in scientific.get("errors") or ()
        )
        epoch_observation = observe_current_epoch(store, repo)
        claimed_epoch_id = str(receipt.get("body_epoch_id") or "")
        repository = store.repo(repo)
        repository_binding_valid = bool(
            repository
            and str(repository["repository_id"] or "")
            == str(receipt.get("repository_id") or "")
        )
        epoch_current = bool(
            repository_binding_valid
            and epoch_observation.get("present")
            and epoch_observation.get("verified")
            and claimed_epoch_id == epoch_observation.get("epoch_id")
            and claimed_epoch_id == epoch_observation.get("live_epoch_id")
        )
        epoch_row = store.db.execute(
            "SELECT * FROM body_epochs WHERE repo=? AND epoch_id=?",
            (repo, claimed_epoch_id),
        ).fetchone()
        coordinate_metadata = coordinate_schema_payload()
        expected_cohort = (
            _current_cohort(
                repo,
                dict(epoch_row),
                str(coordinate_metadata["coordinate_schema_digest"]),
            )
            if epoch_row is not None
            else ""
        )
        cohort_current = bool(
            epoch_current
            and expected_cohort
            and receipt.get("measurement_cohort_id") == expected_cohort
            and receipt.get("coordinate_schema_digest")
            == coordinate_metadata["coordinate_schema_digest"]
        )
        event_count = store.db.execute(
            """SELECT COUNT(*) AS n FROM activation_conformance_receipts
               WHERE repository_id=? AND repo=? AND operator_id=? AND event_id=?""",
            (
                str(receipt.get("repository_id") or ""),
                repo,
                str(receipt.get("operator_id") or ""),
                str(receipt.get("event_id") or ""),
            ),
        ).fetchone()["n"]
        exactly_once_event = int(event_count) == 1
        measurement_valid = bool(
            scientific.get("valid")
            and repository_binding_valid
            and epoch_current
            and cohort_current
            and exactly_once_event
        )
    except Exception as exc:
        scientific = {"valid": False, "errors": [f"{type(exc).__name__}:{exc}"]}
        panel = {"conforms": False}
        reference_matches = False
        witness_valid = False
        measurement_subject_hash_valid = False
        host_projection_valid = False
        invariant_panel_valid = False
        repository_binding_valid = False
        epoch_current = False
        cohort_current = False
        exactly_once_event = False
        measurement_valid = False
    verified = bool(row_valid and measurement_valid)
    return {
        "verification_status": "verified" if verified else "failed",
        "receipt_hash": receipt_hash,
        "receipt_hash_valid": row_valid,
        "chain_valid": bool(chain.get("valid")),
        "measurement_conformance_valid": measurement_valid,
        "scientific_payload_valid": bool(scientific.get("valid")),
        "scientific_errors": list(scientific.get("errors") or ()),
        "independent_recomputation_matches": bool(panel.get("conforms")),
        "reference_output_matches": reference_matches,
        "measurement_witness_valid": witness_valid,
        "measurement_subject_hash_valid": measurement_subject_hash_valid,
        "host_projection_valid": host_projection_valid,
        "invariant_panel_valid": invariant_panel_valid,
        "repository_binding_valid": repository_binding_valid,
        "epoch_current": epoch_current,
        "cohort_current": cohort_current,
        "exactly_once_event": exactly_once_event,
        "B_rms": panel.get("B_rms"),
        "B_max": panel.get("B_max"),
        "B_invalid": panel.get("B_invalid"),
        "channel_burdens": panel.get("channel_burdens") or {},
        "chain": chain,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "ActivationObservationInput",
    "CLAIM_BOUNDARY",
    "INPUT_TYPE",
    "MeasuredActivationTransition",
    "OPERATOR_ID",
    "OUTPUT_TYPE",
    "SCHEMA",
    "activation_cohort_report",
    "activation_receipt_report",
    "build_activation_conformance_receipt",
    "capture_activation_transition",
    "finalize_activation_observation",
    "open_activation_observation",
    "verify_activation_receipt",
]
