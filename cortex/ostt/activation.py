"""Typed capture adapter for Cortex's existing activation observation."""

from __future__ import annotations

from typing import Any, Mapping

from .residuals import ResidualReceipt


def activation_observation_receipt(activation: Mapping[str, Any]) -> dict[str, Any]:
    """Capture measured activation output without inventing a known operator.

    The measured event field is an observed output of the existing activation
    transaction.  A future phase may declare the corresponding operator output
    and turn this receipt into a measured residual; this adapter intentionally
    leaves that gate closed.
    """
    measured = activation.get("measured_event_field") or {}
    body_epoch = activation.get("body_epoch") or {}
    interlock = activation.get("information_interlock") or {}
    normalized = measured.get("normalized_delta") or {}
    if not normalized:
        receipt = ResidualReceipt.unmeasured(
            operator_id="activation_observation",
            input_type="TaskRequest",
            output_type="ActivationReceipt",
            reason="measured_event_output_missing",
        )
    else:
        receipt = ResidualReceipt.observed(
            operator_id="activation_observation",
            input_type="TaskRequest",
            output_type="ActivationReceipt",
            observed_output=normalized,
            validation={
                "typed_output_schema": measured.get("schema_version"),
                "event_id": measured.get("event_id"),
                "event_kind": measured.get("event_kind"),
                "measurement_basis": measured.get("measurement_basis"),
                "observed_receipt_hash": measured.get("receipt_hash"),
                "host_immutable": True,
                "known_output_declared": False,
            },
            epoch_id=str(body_epoch.get("epoch_id") or "") or None,
            cohort_id=str(interlock.get("measurement_cohort_id") or "") or None,
            reason="known_operator_output_not_declared",
        )
    payload = receipt.to_dict()
    payload["source"] = {
        "measured_event_schema": measured.get("schema_version"),
        "event_id": measured.get("event_id"),
        "body_epoch_id": body_epoch.get("epoch_id"),
        "measurement_cohort_id": interlock.get("measurement_cohort_id"),
    }
    payload["claim_boundary"] = (
        "This is a typed observed activation output. It is not a measured "
        "operator residual, learning signal, authority, or consciousness claim."
    )
    return payload


__all__ = ["activation_observation_receipt"]
