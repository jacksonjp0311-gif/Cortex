"""Counterexamples for the bounded epistemic mathematics; no model calls."""

import itertools
import json
from unittest.mock import patch

import pytest

from cortex.epistemic_kernel import (
    compile_action_sufficient_context,
    project_epistemic_state,
    update_continuation_debt,
)
from cortex.information_calibration import assess_sequential_level, eligible_success_counts


def event(polarity="support", *, text="cache invalidation precedes reread", key="a", start=0):
    return {
        "claim_id": "cache", "claim_text": text, "polarity": polarity,
        "event_hash": key * 64, "evidence_receipt_hash": "e" * 64,
        "source_lineage_hash": "f" * 64, "system_time": 0,
        "valid_time": {"from": start, "to": None},
    }


def compile_context(events, budget=4000):
    return compile_action_sufficient_context(
        events, required_claim_ids=["cache"], valid_at=10, known_at=10,
        character_budget=budget,
    )


def test_zero_is_a_real_time_coordinate():
    with patch("cortex.epistemic_kernel.time.time", return_value=100):
        assert project_epistemic_state([event(start=1)], valid_at=0, known_at=0)["claims"] == []


def test_retraction_respects_its_valid_time_and_claim():
    support = event()
    retract = {**event("retract", key="b", start=20), "retracts_event_hash": support["event_hash"]}
    assert project_epistemic_state([support, retract], valid_at=10, known_at=10)["claims"]
    assert project_epistemic_state([support, retract], valid_at=20, known_at=20)["claims"] == []
    retract["claim_id"] = "unrelated"
    assert project_epistemic_state([support, retract], valid_at=20, known_at=20)["claims"]


def test_insufficient_budget_cannot_emit_half_a_conflict():
    support, oppose = event(), event("oppose", key="b")
    one_side = compile_context([support])
    conflict = compile_context([support, oppose], one_side["characters_used"])
    assert conflict["state_preservation"] == "UNKNOWN"
    assert conflict["evidence"] == []
    assert conflict["claims"] == []


def test_minimum_representative_is_order_independent_and_payload_is_bounded():
    rows = [event(key="z"), event(key="b"), event("oppose", key="c")]
    projections = [compile_context(order, 1600) for order in itertools.permutations(rows)]
    for result in projections:
        assert result["state_preservation"] == "PASS"
        assert result["claims"][0]["support_bits"] == [1, 1]
        assert {item["event_hash"] for item in result["evidence"]} == {"b" * 64, "c" * 64}
        payload = json.dumps(
            {"claims": result["claims"], "evidence": result["evidence"]},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        assert result["characters_used"] == len(payload) <= 1600


def test_reusing_a_claim_id_does_not_hide_different_claim_text():
    result = compile_context([event(), event(text="cache never needs invalidation", key="b")])
    assert result["state_preservation"] == "UNKNOWN"
    assert result["evidence"] == []


POLICY = dict(rho=1, alpha=1, beta=1, gamma=1, eta=1, delta=1, reanchor=1, quarantine=2)


@pytest.mark.parametrize("field,value", [
    ("rho", -1), ("rho", 2), ("alpha", -1), ("beta", float("nan")),
    ("gamma", float("inf")), ("reanchor", 3), ("quarantine", -1),
])
def test_invalid_debt_policy_cannot_recommend_continuation(field, value):
    result = update_continuation_debt(
        1, uncertainty=1, conflict=0, drift=0, staleness=0, verification=0,
        policy={**POLICY, field: value},
    )
    assert result["state"] == "UNKNOWN"
    assert "regime" not in result


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True])
def test_invalid_measurement_cannot_recommend_continuation(value):
    result = update_continuation_debt(
        1, uncertainty=value, conflict=0, drift=0, staleness=0, verification=0,
        policy=POLICY,
    )
    assert result["state"] == "UNKNOWN"
    assert "regime" not in result


def test_small_screen_policy_has_discrete_resolution_not_statistical_certainty():
    # Under independent Bernoulli(1/2), these sixteen outcomes are equiprobable.
    accepted = eligible_success_counts(4)
    assert accepted == [2]
    assert sum(sum(bits) in accepted for bits in itertools.product((0, 1), repeat=4)) == 6
    assert assess_sequential_level([1, 1, 1, 0])["state"] == "screening_candidate"


def test_valid_debt_recurrence_and_monotonicity():
    debts = []
    for uncertainty in (0, 0.25, 0.5, 1):
        result = update_continuation_debt(
            0.5, uncertainty=uncertainty, conflict=0, drift=0, staleness=0,
            verification=0, policy=POLICY,
        )
        assert result["state"] == "PASS"
        assert result["continuation_debt"] == 0.5 + uncertainty
        assert result["action_authorized"] is False
        debts.append(result["continuation_debt"])
    assert debts == sorted(debts)
