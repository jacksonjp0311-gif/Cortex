"""v8.4.4 atomic interconnect trajectory tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.interconnect_frame import (
    GATE_FAIL,
    GATE_PASS,
    GATE_UNKNOWN,
    build_context_delta,
    build_interconnect_transition,
    capture_atomic_interconnect_frame,
    readiness_panel,
    verify_trajectory,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session, record_proposal
from cortex.witness import ensure_witness_tables


class InterconnectTrajectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# trajectory host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "TrajectoryHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_atomic_frame_has_snapshot_and_tri_state_validity(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="frame")
        frame = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id=session["session_id"],
            turn_id=1,
            body_epoch_id=session["body_epoch_id"],
            repository_id=session["repository_id"],
        )
        self.assertIn("snapshot_transaction_id", frame)
        self.assertIn("validity", frame)
        for key in (
            "structural_state",
            "epoch_state",
            "schema_state",
            "cohort_state",
            "freshness_state",
            "measurement_state",
            "chain_state",
            "overall_state",
        ):
            self.assertIn(key, frame["validity"])
            self.assertIn(
                frame["validity"][key],
                {GATE_PASS, GATE_FAIL, GATE_UNKNOWN},
            )
        # compatible remains structural-only; complete measurement is separate
        self.assertTrue(frame["structurally_valid"])
        self.assertIsInstance(frame["measurement_complete"], bool)
        self.assertIn("surfaces", frame)
        self.store.append_interconnect_frame(self.repo, frame)
        again = self.store.append_interconnect_frame(self.repo, frame)
        self.assertTrue(again["duplicate"])

    def test_two_frames_bound_by_transition_and_survive_restart(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="traj")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t1",
            proposed_action="a1",
            evidence_citations=["a"],
            declared_uncertainty=0.2,
        )
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t2",
            proposed_action="a2",
            evidence_citations=["b"],
            declared_uncertainty=0.2,
        )
        frames = self.store.interconnect_session_frames(
            self.repo, session["session_id"]
        )
        transitions = self.store.interconnect_session_transitions(
            self.repo, session["session_id"]
        )
        self.assertGreaterEqual(len(frames), 2)
        self.assertGreaterEqual(len(transitions), 1)
        report = verify_trajectory(frames, transitions)
        self.assertTrue(report["valid"], report.get("errors"))

        # Process restart simulation: new Store handle
        db_path = self.home / "cortex.db"
        self.store.close()
        reopened = Store(db_path)
        try:
            frames2 = reopened.interconnect_session_frames(
                self.repo, session["session_id"]
            )
            transitions2 = reopened.interconnect_session_transitions(
                self.repo, session["session_id"]
            )
            self.assertEqual(len(frames2), len(frames))
            self.assertTrue(verify_trajectory(frames2, transitions2)["valid"])
        finally:
            reopened.close()
            # restore for tearDown
            self.store = Store(db_path)

    def test_mismatched_epoch_fails_epoch_state(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="epoch")
        frame = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id=session["session_id"],
            turn_id=1,
            body_epoch_id="stale-epoch-not-live",
            repository_id=session["repository_id"],
        )
        self.assertEqual(frame["validity"]["epoch_state"], GATE_FAIL)
        self.assertFalse(frame["temporally_coherent"])

    def test_readiness_uses_tri_state(self) -> None:
        panel = readiness_panel(
            mesh_green_constitutional=True,
            continuity={"epoch_verified": True},
            symbiosis={"status": "open", "ledger": {"valid": True}},
            self_sensing={},
            binding={},
            resonance={},
            interlock={},
            ostt={},
            frame={},
        )
        self.assertEqual(panel["constitutional_ready"], GATE_PASS)
        self.assertEqual(panel["temporal_ready"], GATE_UNKNOWN)
        self.assertNotEqual(panel["overall_state"], GATE_PASS)

    def test_context_delta_records_changes(self) -> None:
        prior = {
            "receipt_hash": "c0",
            "predictions": {"a": 1},
            "unresolved_contradictions": ["x"],
            "constitutional_restrictions": ["r1"],
        }
        nxt = {
            "receipt_hash": "c1",
            "predictions": {"a": 2},
            "unresolved_contradictions": ["y"],
            "constitutional_restrictions": ["r1"],
            "turn_id": 2,
            "session_id": "s",
            "repo": self.repo,
        }
        prior_f = {"measured_state_digest": "m0", "binding_digest": "b0"}
        next_f = {"measured_state_digest": "m1", "binding_digest": None}
        delta = build_context_delta(
            prior_context=prior,
            next_context=nxt,
            prior_frame=prior_f,
            next_frame=next_f,
        )
        self.assertIn("measured_state_digest", delta["new_information"])
        self.assertIn("binding_digest", delta["invalidated_information"])
        self.assertIn("y", delta["new_failures"])
        self.assertIn("x", delta["resolved_questions"])

    def test_transition_does_not_authorize(self) -> None:
        a = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id="s",
            turn_id=1,
            body_epoch_id="e",
            repository_id="r",
        )
        b = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id="s",
            turn_id=2,
            body_epoch_id="e",
            repository_id="r",
            prior_frame_hash=a["receipt_hash"],
        )
        t = build_interconnect_transition(prior_frame=a, next_frame=b)
        self.assertFalse(t["policy_effect"])
        self.assertFalse(t["update_authorized"])
        self.assertIn(t["transition_class"], {
            "stable_continuation",
            "unknown_transition",
            "measurement_loss",
            "evidence_gain",
            "symbiotic_progress",
            "symbiotic_regression",
            "temporal_drift",
            "epoch_transition",
            "schema_transition",
            "constitutional_block",
            "distillation_ready",
            "distillation_blocked",
        })

    def test_stale_surface_present_but_fails_freshness(self) -> None:
        from cortex.interconnect_frame import _surface_payload_meta, FRESHNESS_LIMITS_MS

        stale = {
            "event_id": "old",
            "captured_at": 1.0,  # far in the past
            "schema_version": "x",
        }
        meta = _surface_payload_meta(
            stale,
            now=1_000_000.0,
            limit_ms=FRESHNESS_LIMITS_MS["self_sensing"],
        )
        self.assertTrue(meta["present"])
        self.assertEqual(meta["status"], "present_but_stale")
        self.assertEqual(meta["freshness_state"], GATE_FAIL)

    def test_missing_measurement_is_unknown_not_pass(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="measure")
        frame = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id=session["session_id"],
            turn_id=0,
            body_epoch_id=session["body_epoch_id"] or "claimed",
            repository_id=session["repository_id"],
        )
        self.assertEqual(frame["validity"]["measurement_state"], GATE_UNKNOWN)
        self.assertNotEqual(frame["validity"]["measurement_state"], GATE_PASS)
        self.assertNotEqual(frame["validity"]["overall_state"], GATE_PASS)

    def test_unrelated_outcome_does_not_bind(self) -> None:
        a = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id="sess-a",
            turn_id=1,
            body_epoch_id="e",
            repository_id="r",
        )
        b = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id="sess-a",
            turn_id=2,
            body_epoch_id="e",
            repository_id="r",
            prior_frame_hash=a["receipt_hash"],
        )
        foreign_outcome = {
            "receipt_hash": "foreign-outcome-hash",
            "session_id": "other-session",
            "repo": self.repo,
            "turn_id": 2,
            "witnessed": True,
            "success": True,
        }
        t = build_interconnect_transition(
            prior_frame=a,
            next_frame=b,
            outcome=foreign_outcome,
        )
        self.assertIsNone(t["outcome_hash"])
        self.assertEqual(t["causal_status"], "unmeasured")
        self.assertNotEqual(t["transition_class"], "distillation_ready")

    def test_mesh_green_legacy_is_constitutional_only(self) -> None:
        panel = readiness_panel(
            mesh_green_constitutional=True,
            continuity={},
            symbiosis={"status": "cold"},
            frame={},
        )
        self.assertTrue(panel["mesh_green_legacy"])
        self.assertEqual(panel["constitutional_ready"], GATE_PASS)
        # Constitutional green must not force overall pass without other planes.
        self.assertFalse(panel["overall_ready"])
        self.assertNotEqual(panel["overall_state"], GATE_PASS)
        self.assertTrue(panel["advisory_only"])
        self.assertFalse(panel["policy_effect"])


if __name__ == "__main__":
    unittest.main()
