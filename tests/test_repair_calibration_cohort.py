"""Cohort state-machine tests; lower-level runtime has separate integration tests."""
import copy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cortex.epistemic_instrumentation import AUTHORITY
from cortex.repair_calibration_cohort import (
    POLICY, SCHEMA, _screens, freeze_repair_cohort, inspect_repair_cohort,
    execute_repair_cohort_stage,
)


class Store:
    def __init__(self): self.rows = {}
    def verify_symbiotic_receipt(self, repo, identity): return {"valid": identity in self.rows}
    def symbiotic_receipt(self, identity, *, repo): return copy.deepcopy(self.rows[identity])
    def symbiotic_receipts_by_kind(self, repo, kind, limit=10000):
        return [copy.deepcopy(r) for r in self.rows.values() if r["kind"] == kind][:limit]
    def append_symbiotic_receipt(self, repo, row):
        identity = "cohort"
        self.rows[identity] = {**row, "receipt_hash": identity, "created_at": 100}
        return self.rows[identity]


@pytest.fixture
def store():
    s = Store()
    for i in range(2):
        s.rows[f"instrument{i}"] = {"kind": "instrument_assurance", "source_commit": "a" * 40}
        s.rows[f"screen{i}"] = {
            "kind": "structured_repair_preregistration", "schema_version": "cortex-structured-repair-preregistration/1.3",
            "context_treatment": "task_only_control", "tools": [], "planned_calls": 4,
            "cases": [{"case_id": str(i*4+j), "files": {"source.py": str(i*4+j)}} for j in range(4)],
            "model_identity": {"model_id": "selected"}, "adapter_provenance": {"id": "host"},
            "screening_policy": {}, "governed_prerequisite": {"budget": "same"},
            "response_contract": {"schema": "one", "allowed_paths": ["source.py"]},
            "frontier_binding": {"stratum": "L3", "instrument_receipt_hash": f"instrument{i}"}, **AUTHORITY,
        }
    with patch("cortex.repair_calibration_cohort._repeat_binding_errors", return_value=[]):
        with patch("cortex.repair_calibration_cohort.open_symbiotic_session", return_value={"session_id": "s", "body_epoch_id": "e"}):
            freeze_repair_cohort(s, "test", screen_receipt_hashes=["screen0", "screen1"], source_commit="a"*40)
        yield s


def add_result(s, stage, successes, claim_time=110):
    s.rows[f"claim{stage}"] = {"kind": "structured_repair_execution_claim", "created_at": claim_time,
                                "preregistration_receipt_hash": f"screen{stage}"}
    for j in range(4):
        s.rows[f"case{stage}{j}"] = {"kind": "structured_repair_case", "task_success": j < successes}
    s.rows[f"result{stage}"] = {"kind": "structured_repair_result", "receipt_hash": f"result{stage}",
        "preregistration_receipt_hash": f"screen{stage}", "execution_claim_receipt_hash": f"claim{stage}",
        "created_at": claim_time+10, "screen": {"success_count": successes},
        "case_receipt_hashes": [f"case{stage}{j}" for j in range(4)]}


@pytest.mark.parametrize("successes,allowed", [(0, False), (1, True), (2, True), (3, True), (4, False)])
def test_four_cases_are_never_confirmation(store, successes, allowed):
    add_result(store, 0, successes)
    with patch("cortex.repair_calibration_cohort.verify_structured_repair_screen", return_value={"valid": True}):
        result = inspect_repair_cohort(store, "test", "cohort")
    assert result["valid"] and result["confirmation_permitted"] is allowed
    assert not result["development_region_selected"] and not result["population_calibration_established"]


def test_eight_fresh_mixed_cases_only_select_development_region(store):
    add_result(store, 0, 2)
    add_result(store, 1, 2, claim_time=130)
    with patch("cortex.repair_calibration_cohort.verify_structured_repair_screen", return_value={"valid": True}):
        result = inspect_repair_cohort(store, "test", "cohort")
    assert result["valid"] and result["development_region_selected"]
    assert result["completed_calls"] == 8 and not result["semantic_transfer_established"]
    assert all(result[k] is False for k in AUTHORITY)


@pytest.mark.parametrize("mutation", ["repeat", "model", "stratum", "treatment", "budget"])
def test_frozen_boundaries_cannot_shift(store, mutation):
    second = store.rows["screen1"]
    if mutation == "repeat":
        second["cases"][0]["files"] = store.rows["screen0"]["cases"][0]["files"]
    if mutation == "model":
        second["model_identity"] = {"model_id": "changed"}
    if mutation == "stratum":
        second["frontier_binding"]["stratum"] = "L2"
    if mutation == "treatment":
        second["context_treatment"] = "lesson"
    if mutation == "budget":
        second["governed_prerequisite"] = {"budget": "larger"}
    with pytest.raises(ValueError):
        _screens(store, "test", ["screen0", "screen1"])


@pytest.mark.parametrize("first_success,second_time", [(4, 130), (0, 130), (2, 105), (2, 90)])
def test_posthoc_or_out_of_order_confirmation_rejected(store, first_success, second_time):
    add_result(store, 0, first_success)
    add_result(store, 1, 2, claim_time=second_time)
    with patch("cortex.repair_calibration_cohort.verify_structured_repair_screen", return_value={"valid": True}):
        assert not inspect_repair_cohort(store, "test", "cohort")["valid"]


def test_confirmation_and_source_drift_stop_before_runtime(store):
    with patch("cortex.coding_workspace.repository_head", return_value="a"*40), patch("cortex.repair_calibration_cohort.execute_structured_repair_screen") as run:
        with pytest.raises(ValueError, match="stopping rule"):
            execute_repair_cohort_stage(store, "test", cohort_receipt_hash="cohort", stage=1, private_bundle={}, adapter=None, tools=None, grant=SimpleNamespace(workspace_root="host"))
        run.assert_not_called()
    with patch("cortex.coding_workspace.repository_head", return_value="b"*40):
        with pytest.raises(ValueError, match="source drift"):
            execute_repair_cohort_stage(store, "test", cohort_receipt_hash="cohort", stage=0, private_bundle={}, adapter=None, tools=None, grant=SimpleNamespace(workspace_root="host"))


def test_budget_and_source_identity_tampering_rejected(store):
    assert store.rows["cohort"]["schema_version"] == SCHEMA
    assert store.rows["cohort"]["policy"] == POLICY
    store.rows["cohort"]["policy"] = {**POLICY, "maximum_total_calls": 99}
    assert not inspect_repair_cohort(store, "test", "cohort")["valid"]
    store.rows["cohort"]["policy"] = dict(POLICY)
    store.rows["cohort"]["source_commit"] = "b" * 40
    assert not inspect_repair_cohort(store, "test", "cohort")["valid"]
