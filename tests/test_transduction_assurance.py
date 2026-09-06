"""Zero-call counterexample inventory; HELD is the expected audit disposition."""
from unittest.mock import patch

import pytest

from benchmarks.transduction_assurance import run_audit
from cortex.epistemic_instrumentation import inspect_repair_observation_path


@pytest.fixture(scope="module")
def audit(tmp_path_factory):
    return run_audit(tmp_path_factory.mktemp("transduction"))


def test_audit_preserves_three_unresolved_counterexamples(audit):
    assert audit["model_calls"] == 0 and audit["state"] == "HELD"
    assert {r["control"] for r in audit["observations"] if not r["expectation_met"]} == {
        "no_terminal_newline", "numeric_edit", "evaluator_changes_candidate"}
    assert audit["expectations_met"] == 13 and audit["control_count"] == 16
    assert audit["adaptation_authorized"] is False


def test_real_whitespace_stale_scope_and_distortion_remain_rejected(audit):
    rows = {r["control"]: r for r in audit["observations"]}
    for name in ("trailing_whitespace", "stale_preimage", "unauthorized_target", "malformed_patch", "distorted_patch"):
        assert rows[name]["expectation_met"]
    assert rows["distorted_patch"]["reason"] == "EVALUATOR_REJECTION"
    assert rows["evaluator_changes_candidate"]["expected_vs_recorded_postimage_mismatch"]


@pytest.mark.parametrize("observed,success", [(False, False), (True, False), (True, True)])
def test_receipt_validity_never_upgrades_legacy_path_to_assured(observed, success):
    class Store:
        def symbiotic_receipt(self, identity, *, repo):
            if identity == "result":
                return {"case_receipt_hashes": ["case"]}
            return {"case_id": "fixture", "task_success": success,
                    "evaluation": {"candidate_error": None if observed else "application failed",
                                   "candidate": {"steps": [{"passed": success}] if observed else []}}}
    with patch("cortex.structured_repair_screen.verify_structured_repair_screen", return_value={"valid": True}):
        view = inspect_repair_observation_path(Store(), "test", "result")
    assert view["state"] == ("UNRESOLVED" if observed else "INCOMPLETE")
    assert not view["complete_path_assured"] and not view["capability_inference_eligible"]
    assert not view["cases"][0]["reasoning_failure_established"]


def test_bad_receipt_cannot_supply_path_observations():
    with patch("cortex.structured_repair_screen.verify_structured_repair_screen", return_value={"valid": False, "errors": ["invalid"]}):
        view = inspect_repair_observation_path(None, "test", "missing")
    assert view["state"] == "INCOMPLETE" and view["cases"] == []
