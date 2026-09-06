"""Bounded measurement assurance, never model/caller legitimacy."""
import copy
import sqlite3

import pytest

from cortex.contract_aligned_repair import _sha
from cortex.epistemic_instrumentation import (
    AUTHORITY, assurance_boundary, audit_instrument, instrument_state,
    verify_instrument, inspect_measurement_claim, governed_state_view,
)
from cortex.store import Store
from cortex.structured_repair_screen import fresh_task_fingerprints
from test_evaluator_control_panel import fixture
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home


def panel(outcomes=(True, True, False)):
    rows = [{"case_id": "c", "control_id": str(i), "patch_hash": str(i),
             "expected_pass": i < 2, "observed_pass": value,
             "expectation_met": value == (i < 2), "evaluation_hash": str(i)}
            for i, value in enumerate(outcomes)]
    body = {"schema_version": "cortex-evaluator-control-audit/1.0",
            "state": "CONTROL_PANEL_PASS" if all(r["expectation_met"] for r in rows) else "EVALUATOR_CHALLENGED",
            "corpus_hash": "corpus", "evaluator_commitments": {"c": "evaluator"},
            "observations": rows, "additional_model_calls": 0,
            "evidence_class": "local_instrument_audit", "expected_labels": "host_reviewed_not_semantically_proven",
            "universal_implementation_equivalence": False,
            "semantic_transfer_established": False, "general_improvement_established": False, **AUTHORITY}
    return {**body, "result_hash": _sha(body)}


def assess(report, **kw):
    return instrument_state(report, corpus_hash="corpus", commitments={"c": "evaluator"}, **kw)


@pytest.mark.parametrize("outcomes,state", [
    ((True, True, False), "READY"), ((True, False, False), "OVERCONSTRAINED"),
    ((True, True, True), "UNDERCONSTRAINED"), ((True, False, True), "CONFLICTED"),
])
def test_both_support_dimensions_preserved(outcomes, state):
    result = assess(panel(outcomes))
    assert result["state"] == state
    p = result["panels"]["c"]
    assert p["allowed_rejection_count"] == sum(not v for v in outcomes[:2])
    assert p["invalid_acceptance_count"] == int(outcomes[2])
    assert result["universal_semantic_validity"] == "UNKNOWN"
    assert all(result[k] is False for k in AUTHORITY)


@pytest.mark.parametrize("field,value", [("corpus_hash", "wrong"), ("evaluator_commitments", {"c": "wrong"}),
                                         ("execution_authorized", True)])
def test_rehashed_wrong_binding_is_not_evidence(field, value):
    report = panel()
    report[field] = value
    report["result_hash"] = _sha({k: v for k, v in report.items() if k != "result_hash"})
    assert assess(report)["binding_state"] == "FAIL"


def test_incomplete_and_excess_depth_hold():
    report = panel()
    report["observations"] = report["observations"][:2]
    report["result_hash"] = _sha({k: v for k, v in report.items() if k != "result_hash"})
    assert assess(report)["state"] == "UNRESOLVED"
    assert assess(panel(), max_depth=2)["state"] == "UNRESOLVED"
    for depth in (4, True, -1):
        assert assurance_boundary(max_depth=depth)["state"] == "UNKNOWN"


def test_renaming_same_source_is_not_fresh():
    case = {"case_id": "one", "task": "first", "files": {"a.py": "x=1"}}
    alias = {**case, "case_id": "two", "task": "rewritten prose"}
    with pytest.raises(ValueError, match="not a fresh"):
        fresh_task_fingerprints([case, alias])
    previous = tuple(fresh_task_fingerprints([case]))
    with pytest.raises(ValueError, match="not a fresh"):
        fresh_task_fingerprints([alias], previous)


def test_host_audit_reconstruction_claims_challenges_and_immutability(tmp_path):
    home = ensure_home(tmp_path / "home")
    host = tmp_path / "host"
    host.mkdir()
    (host / "README.md").write_text("audit fixture", encoding="utf-8")
    store = Store(home / "cortex.db")
    try:
        bootstrap_repository(home, store, host, "test")
        public, private, controls = fixture()
        receipt = audit_instrument(store, "test", public=public, private=private, controls=controls,
                                   root=tmp_path / "controls", source_commit="a" * 40)
        identity = receipt["receipt_hash"]
        persisted = store.symbiotic_receipt(identity, repo="test")
        assert verify_instrument(store, "test", identity)["state"] == "READY"
        assert inspect_measurement_claim(store, "test", identity, "bounded_instrument_controls")["claim_eligible"]
        for claim in ("competence", "semantic_transfer", "calibrated", "general_improvement"):
            assert not inspect_measurement_claim(store, "test", identity, claim)["claim_eligible"]
        view = governed_state_view(store, "test", identity)
        assert view["object_type"] == "instrument_assurance" and view["applicability"] == "UNKNOWN"
        rewrite = copy.deepcopy(receipt)
        rewrite["instrument"]["state"] = "UNDERCONSTRAINED"
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            store.append_symbiotic_receipt("test", rewrite)
        assert store.symbiotic_receipt(identity, repo="test") == persisted
        store.append_symbiotic_receipt("test", {
            "kind": "repair_evaluator_challenge", "session_id": receipt["session_id"], "turn_id": 1,
            "body_epoch_id": receipt["body_epoch_id"],
            "event_id": "challenge-instrument",
            "evaluator_commitment": next(iter(receipt["instrument"]["evaluator_commitments"].values())),
            **AUTHORITY,
        })
        assert verify_instrument(store, "test", identity)["valid"]
        assert not inspect_measurement_claim(store, "test", identity, "bounded_instrument_controls")["claim_eligible"]
    finally:
        store.close()
