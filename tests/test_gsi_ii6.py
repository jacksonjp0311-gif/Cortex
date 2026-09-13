"""Runtime evidence must be present, including for empty candidate sets."""
import pytest

from cortex.causal_treatment import candidate_runtime_matches, valid_execution_usage
from cortex.self_improvement import _sealed
from test_gsi_ii import freeze, payload
from test_gsi_ii3 import proof_host  # noqa: F401
from test_gsi_ii4 import build_empirical_bundle, readiness_components, runtime


@pytest.mark.parametrize("candidates,expected", [
    ([], "runtime"),
    ([{}], "runtime"),
    ([{"model_runtime_hash": None}], "runtime"),
    ([{"model_runtime_hash": "other"}], "runtime"),
    ([{"model_runtime_hash": "runtime"}, {}], "runtime"),
    ([{}], None),
])
def test_missing_or_mismatched_runtime_cannot_pass(candidates, expected):
    assert not candidate_runtime_matches(candidates, expected)


def test_explicit_matching_runtime_passes():
    assert candidate_runtime_matches([{"model_runtime_hash": "runtime"}], "runtime")


@pytest.mark.parametrize("field,value", [
    ("token_cost", -1), ("token_cost", 1.5), ("token_cost", True),
    ("duration_ms", -1), ("duration_ms", float("nan")),
    ("duration_ms", float("inf")), ("duration_ms", True),
    ("provider_calls", -1), ("candidate_evaluations", 0),
    ("candidate_attempts", -1), ("transport_retries", -1),
])
def test_invalid_usage_cannot_satisfy_budget(field, value):
    usage = dict(candidate_evaluations=1, provider_calls=0, transport_retries=0,
                 candidate_attempts=1, token_cost=0, duration_ms=0)
    usage[field] = value
    assert not valid_execution_usage(**usage)


def test_zero_cost_deterministic_execution_is_valid():
    assert valid_execution_usage(candidate_evaluations=1, provider_calls=0,
                                 transport_retries=0, candidate_attempts=1,
                                 token_cost=0, duration_ms=0)


def test_empirical_path_rejects_canonical_candidate_missing_runtime(proof_host, monkeypatch):  # noqa: F811
    experiment = freeze(proof_host, holdout_id="ii6-runtime")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"], model_runtime=runtime(), task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={"candidate_budget": 1, "provider_call_budget": 1,
                 "token_budget": 1000, "wall_clock_budget_seconds": 60},
        sham_tolerances={"count": 0, "bytes": 100, "token_estimate": 25,
                         "positive": 0, "constraints": 0},
    )
    bundle = build_empirical_bundle(proof_host, experiment, treatment, execution)
    original = proof_host._record

    def record(kind, obj, **kwargs):
        if kind == "gsi_generated_candidate":
            body = dict(obj)
            schema = body.pop("schema_version")
            body.pop("object_hash", None)
            body.pop("model_runtime_hash", None)
            obj = _sealed(schema, **body)
        return original(kind, obj, **kwargs)

    monkeypatch.setattr(proof_host, "_record", record)
    with pytest.raises(ValueError, match="HOLD_EPISODE"):
        proof_host.run_empirical(*bundle, payload)


def dispatch_bundle(host):
    experiment = freeze(host, holdout_id="ii6-dispatch")
    treatment = host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = host.freeze_execution_contract(
        experiment["receipt_hash"], model_runtime=runtime(), task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={"candidate_budget": 1, "provider_call_budget": 1,
                 "token_budget": 1000, "wall_clock_budget_seconds": 60},
        sham_tolerances={"count": 0, "bytes": 100, "token_estimate": 25,
                         "positive": 0, "constraints": 0},
    )
    return build_empirical_bundle(host, experiment, treatment, execution), execution


def reserved_dispatch(host):
    bundle, execution = dispatch_bundle(host)
    receipt = host._record("gsi_dispatch_reservation", _sealed(
        "cortex-gsi-dispatch-reservation/1.0", candidate_units=1,
        execution_contract_receipt=execution["receipt_hash"], assignment_receipt=bundle[3],
        execution_lock_receipt=bundle[2], experiment_receipt=bundle[0]))
    return receipt, execution


@pytest.mark.parametrize("usage,expected", [(12, "PASS"), (None, "HELD"), (101, "HELD")])
def test_call_usage_reconstructed_from_receipts(proof_host, usage, expected):  # noqa: F811
    parent, execution = reserved_dispatch(proof_host)
    call = proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="one", reserved_tokens=100)
    assert proof_host.reconstruct_call_usage(execution["receipt_hash"])["disposition"] == "HELD"
    proof_host.record_call_outcome(call["receipt_hash"], status="COMPLETED", token_usage=usage, duration_ms=2)
    result = proof_host.reconstruct_call_usage(execution["receipt_hash"])
    assert result["disposition"] == expected
    assert result["token_usage"] == usage
    assert result["reserved_calls"] == 1
    with pytest.raises(ValueError, match="budget exhausted"):
        proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="two", reserved_tokens=100)


def test_call_token_exhaustion_precedes_reservation(proof_host):  # noqa: F811
    parent, execution = reserved_dispatch(proof_host)
    with pytest.raises(ValueError, match="budget exhausted"):
        proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="one", reserved_tokens=1001)
    assert proof_host.reconstruct_call_usage(execution["receipt_hash"])["reserved_calls"] == 0


def test_call_outcome_cannot_be_rewritten(proof_host):  # noqa: F811
    parent, _ = reserved_dispatch(proof_host)
    call = proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="one", reserved_tokens=100)
    proof_host.record_call_outcome(call["receipt_hash"], status="TIMEOUT", token_usage=None, duration_ms=2)
    with pytest.raises(ValueError, match="different content"):
        proof_host.record_call_outcome(call["receipt_hash"], status="COMPLETED", token_usage=1, duration_ms=2)


def test_call_attempt_replay_is_rejected(proof_host):  # noqa: F811
    parent, _ = reserved_dispatch(proof_host)
    proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="one", reserved_tokens=100)
    with pytest.raises(ValueError, match="already reserved"):
        proof_host.reserve_measured_call(parent["receipt_hash"], attempt_id="one", reserved_tokens=100)


def test_interrupted_dispatch_is_not_refunded(proof_host, monkeypatch):  # noqa: F811
    bundle, _ = dispatch_bundle(proof_host)
    calls = []

    def interrupted(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("interrupted after reservation")

    monkeypatch.setattr(proof_host, "_run", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        proof_host.run_empirical(*bundle, payload)
    with pytest.raises(ValueError, match="already reserved"):
        proof_host.run_empirical(*bundle, payload)
    assert len(calls) == 1
    receipts = proof_host.store.symbiotic_receipts_by_kind(
        proof_host.repo, "gsi_dispatch_reservation")
    assert len(receipts) == 1
    assert proof_host.store.verify_symbiotic_receipt(
        proof_host.repo, receipts[0]["receipt_hash"])["valid"]


@pytest.mark.parametrize("same_assignment", [True, False])
def test_concurrent_dispatch_reservations_share_atomic_limit(proof_host, same_assignment):  # noqa: F811
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from threading import Barrier
    from cortex.store import Store
    from cortex.autonomous_improvement import _session

    bundle, execution = dispatch_bundle(proof_host)
    sessions = [_session(proof_host.store, proof_host.repo, f"reservation-{i}")
                for i in range(2)]
    db_path = Path(proof_host.store.db.execute("PRAGMA database_list").fetchone()[2])
    assignments = [bundle[3], bundle[3]]
    if not same_assignment:
        from cortex.causal_treatment import assignment
        first = proof_host._resolve(bundle[3], "gsi_assignment")["object"]
        assignments[1] = proof_host.record_empirical_component("gsi_assignment", assignment(
            randomization_plan_hash=first["randomization_plan_hash"],
            task_hash=first["task_hash"], arm="B"))["receipt_hash"]
    barrier = Barrier(2)

    def reserve(item):
        session, assignment_hash = item
        store = Store(db_path)
        try:
            obj = _sealed("cortex-gsi-dispatch-reservation/1.0",
                          execution_contract_receipt=execution["receipt_hash"],
                          assignment_receipt=assignment_hash, candidate_units=1)
            barrier.wait(timeout=30)
            try:
                store.append_symbiotic_receipt(proof_host.repo, {
                    "kind": "gsi_dispatch_reservation", "object": obj,
                    "session_id": session["session_id"],
                    "body_epoch_id": session["body_epoch_id"], "turn_id": 0,
                    "event_id": obj["object_hash"],
                })
                return "reserved"
            except ValueError as exc:
                assert ("already reserved" if same_assignment else "budget exhausted") in str(exc)
                return "held"
        finally:
            store.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(reserve, zip(sessions, assignments))) == ["held", "reserved"]
    # A separate connection reconstructs consumption after both workers exit.
    reopened = Store(db_path)
    try:
        receipts = reopened.symbiotic_receipts_by_kind(proof_host.repo, "gsi_dispatch_reservation")
        assert len(receipts) == 1
        assert receipts[0]["object"]["execution_contract_receipt"] == execution["receipt_hash"]
    finally:
        reopened.close()
