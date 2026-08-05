"""Observer cold-start must accumulate under warm field + INDETERMINATE frames."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.self_sensing import observe_self_sensing
from cortex.store import Store
from cortex.will import (
    get_default_will_policy,
    issue_will,
    register_will_principal,
    set_default_will_policy,
    verify_will,
)
from cortex.witness import ensure_witness_tables


class SelfSensingColdStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# sense host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "SenseHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_cold_start_updates_under_indeterminate_when_field_ready(self) -> None:
        sample = {
            "z": {k: 0.5 for k in (
                "C", "N", "I", "L", "D", "H", "G", "Q",
                "eta_E", "eta_M", "T", "delta_E", "U",
            )},
            "z_vector": [0.5] * 13,
            "z_keys": list(range(13)),
            "missing_components": [],
            "F_t": 0.5,
            "F_spec_literal": 0.5,
            "gates": {
                "baseline_warm": True,
                "epoch_current": True,
                "phase_bound": True,
                "evidence_valid": True,
                "witness_available": True,
                "field_frames_ready": True,
            },
            "coherence_score": 0.5,
            "frame_id": "f1",
            "frame_classification": "INDETERMINATE",
            "frame_measurement_basis": "direct_snapshot",
            "frame_policy_eligible": True,
            "frame_baseline_eligible": True,
            "field_warmup": {
                "baseline_frames_seen": 16,
                "baseline_ready": True,
            },
            "spectral_mass": None,
            "temporal_field_panel": {},
            "sampled_at": 1.0,
            "claim_boundary": "test",
        }
        with mock.patch(
            "cortex.self_sensing.sample_observer_state", return_value=sample
        ):
            first = observe_self_sensing(
                self.store, self.repo, update=True, persist=True
            )
            self.assertTrue(first["baseline_updated"], first.get("baseline_update_decision"))
            self.assertEqual(first["baseline_n_updates"], 1)
            second = observe_self_sensing(
                self.store, self.repo, update=True, persist=True
            )
            self.assertEqual(second["baseline_n_updates"], 2)
            # Canonical interconnect surface name
            surface = self.store.get_setting(f"self_sensing_latest:{self.repo}")
            self.assertIsInstance(surface, dict)
            self.assertEqual(surface.get("baseline_n_updates"), 2)


class DurableWillPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# will policy host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "WillPolicyHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_default_policy_used_on_issue(self) -> None:
        register_will_principal(
            self.store, self.repo, "op", "Op", secret="s-policy-1"
        )
        set_default_will_policy(
            self.store,
            self.repo,
            principal_id="op",
            admit_types=["successful_procedure", "verified_fact"],
            forbid_types=["unresolved_ambiguity"],
            max_retain=3,
            min_support="medium",
            intent_summary="durable heal policy",
        )
        policy = get_default_will_policy(self.store, self.repo)
        self.assertIsNotNone(policy)
        will = issue_will(
            self.store,
            self.repo,
            principal_id="op",
            secret="s-policy-1",
            clauses=None,
            intent_summary="",
        )
        self.assertTrue(will.get("issued"))
        self.assertTrue(will.get("from_default_policy"))
        kinds = {c["kind"] for c in will.get("clauses") or ()}
        self.assertIn("admit_type", kinds)
        self.assertIn("cap_retain", kinds)
        ok = verify_will(
            self.store, self.repo, will, secret="s-policy-1"
        )
        self.assertTrue(ok["verified"], ok.get("errors"))


if __name__ == "__main__":
    unittest.main()
