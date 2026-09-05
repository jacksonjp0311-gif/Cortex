"""Public inventory classification must not turn screening into calibration."""

from copy import deepcopy

from benchmarks.result_manifest import audited_screen_metadata
from cortex.information_calibration import assess_sequential_level


def report(successes):
    screen = assess_sequential_level([True] * successes + [False] * (4 - successes))
    return {
        "state": "AUDITED_SCREEN_RECONSTRUCTED", "planned_calls": 4,
        "calls_executed": 4, "source_commit": "source",
        "preregistration_receipt_hash": "prereg", "result_receipt_hash": "result",
        "model_identity": {"model_id": "runtime-selected"},
        "evidence_class": "live_empirical", "screen": screen,
        "cases": [{"case_id": str(i), "task_success": i < successes} for i in range(4)],
        "canonical_reconstruction": {
            "valid": True, "screen": screen, "result_receipt_hash": "result",
            "preregistration_receipt_hash": "prereg",
        },
        **{field: False for field in (
            "baseline_calibrated", "semantic_transfer_established",
            "general_improvement_established", "private_bundle_persisted_in_artifact",
            "host_mutate_authorized", "execution_authorized",
            "memory_admission_authorized", "policy_effect",
        )},
    }


def test_screen_dispositions_never_claim_calibration():
    for successes in range(5):
        expected = "floor" if successes == 0 else "ceiling" if successes == 4 else "candidate"
        assert audited_screen_metadata(report(successes)) == "development_live_audited_screening_" + expected


def test_frozen_is_not_executed():
    item = report(4)
    item.update(state="FROZEN_NOT_EXECUTED", calls_executed=0, control_audit_hash="audit")
    assert audited_screen_metadata(item) == "zero_call_audited_screen_frozen"
    item["calls_executed"] = 4
    assert audited_screen_metadata(item).endswith("invalid")


def test_forged_claims_and_inconsistent_outcomes_rejected():
    original = report(3)
    for key, value in (
        ("baseline_calibrated", True), ("evidence_class", "synthetic"),
        ("policy_effect", True), ("calls_executed", 3),
    ):
        item = deepcopy(original)
        item[key] = value
        assert audited_screen_metadata(item).endswith("invalid")
    item = deepcopy(original)
    item["cases"][3]["task_success"] = True
    assert audited_screen_metadata(item).endswith("invalid")
    item = deepcopy(original)
    item["canonical_reconstruction"]["result_receipt_hash"] = "unrelated"
    assert audited_screen_metadata(item).endswith("invalid")
