"""v8.4.5 distillation candidate extraction tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.distillation_candidates import (
    CANDIDATE_TYPES,
    SUPPORT_HIGH,
    SUPPORT_MEDIUM,
    SUPPORT_NONE,
    candidates_authorize_nothing,
    extract_distillation_candidates,
    flatten_candidates,
)
from cortex.interconnect_frame import (
    build_interconnect_transition,
    capture_atomic_interconnect_frame,
)
from cortex.store import Store
from cortex.symbiosis import (
    consolidate_session,
    open_symbiotic_session,
    record_joint_action,
    record_outcome,
    record_proposal,
    reconstruct_next_session_brief,
)
from cortex.witness import ensure_witness_tables


class DistillationCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# distill host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "DistillHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _two_frames(self, session_id: str = "s1"):
        a = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id=session_id,
            turn_id=1,
            body_epoch_id="e1",
            repository_id="r1",
        )
        b = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id=session_id,
            turn_id=2,
            body_epoch_id="e1",
            repository_id="r1",
            prior_frame_hash=a["receipt_hash"],
        )
        return a, b

    def test_blocked_on_hash_mismatch(self) -> None:
        a, b = self._two_frames()
        t = build_interconnect_transition(prior_frame=a, next_frame=b)
        t = {**t, "prior_frame_hash": "0" * 64}
        batch = extract_distillation_candidates(
            prior_frame=a, next_frame=b, transition=t
        )
        self.assertEqual(batch["extraction_status"], "blocked")
        self.assertFalse(batch["trajectory_verified"])
        self.assertEqual(batch["candidate_count"], 0)
        self.assertTrue(candidates_authorize_nothing(batch))

    def test_regime_warning_without_outcome(self) -> None:
        a, b = self._two_frames()
        # Force regression class via validity overall states
        a = {
            **a,
            "validity": {**(a.get("validity") or {}), "overall_state": "pass"},
        }
        b = {
            **b,
            "validity": {
                **(b.get("validity") or {}),
                "overall_state": "fail",
                "freshness_state": "fail",
            },
        }
        t = build_interconnect_transition(prior_frame=a, next_frame=b)
        batch = extract_distillation_candidates(
            prior_frame=a, next_frame=b, transition=t
        )
        self.assertEqual(batch["extraction_status"], "extracted")
        types = {c["candidate_type"] for c in batch["candidates"]}
        self.assertTrue(types & {"regime_warning", "unresolved_ambiguity"})
        for c in batch["candidates"]:
            self.assertFalse(c["retain"])
            self.assertFalse(c["memory_write_authorized"])
            self.assertIn(c["candidate_type"], CANDIDATE_TYPES)
        self.assertTrue(candidates_authorize_nothing(batch))

    def test_outcome_linked_success_requires_identity_bound_outcome(self) -> None:
        a, b = self._two_frames(session_id="sess-ok")
        proposal = {
            "receipt_hash": "p" * 64,
            "session_id": "sess-ok",
            "repo": self.repo,
            "turn_id": 1,
            "proposed_action": "run tests",
            "interpreted_objective": "verify build",
        }
        outcome = {
            "receipt_hash": "o" * 64,
            "session_id": "sess-ok",
            "repo": self.repo,
            "turn_id": 1,
            "success": True,
            "status": "closed",
            "witnessed": True,
        }
        t = build_interconnect_transition(
            prior_frame=a,
            next_frame=b,
            proposal=proposal,
            outcome=outcome,
        )
        self.assertIn(t["causal_status"], {"outcome_bound", "comparison_supported"})
        batch = extract_distillation_candidates(
            prior_frame=a,
            next_frame=b,
            transition=t,
            proposal=proposal,
            outcome=outcome,
        )
        types = {c["candidate_type"] for c in batch["candidates"]}
        self.assertIn("successful_procedure", types)
        self.assertIn(batch["support_ceiling"], {SUPPORT_HIGH, SUPPORT_MEDIUM})
        for c in batch["candidates"]:
            self.assertFalse(c["retain"])

    def test_unrelated_outcome_does_not_credit_procedure(self) -> None:
        a, b = self._two_frames(session_id="sess-a")
        foreign = {
            "receipt_hash": "f" * 64,
            "session_id": "other",
            "repo": self.repo,
            "turn_id": 1,
            "success": True,
            "witnessed": True,
        }
        t = build_interconnect_transition(
            prior_frame=a, next_frame=b, outcome=foreign
        )
        batch = extract_distillation_candidates(
            prior_frame=a,
            next_frame=b,
            transition=t,
            outcome=foreign,
        )
        types = {c["candidate_type"] for c in batch["candidates"]}
        self.assertNotIn("successful_procedure", types)
        self.assertNotIn("verified_fact", types)

    def test_failed_hypothesis_and_counterevidence(self) -> None:
        a, b = self._two_frames(session_id="sess-fail")
        # Simulate a changed digest so counterevidence can fire
        b = {**b, "measured_state_digest": "changed-digest-xyz"}
        proposal = {
            "receipt_hash": "p" * 64,
            "session_id": "sess-fail",
            "repo": self.repo,
            "turn_id": 1,
            "proposed_action": "refactor X",
            "interpreted_objective": "X improves latency",
        }
        outcome = {
            "receipt_hash": "o" * 64,
            "session_id": "sess-fail",
            "repo": self.repo,
            "turn_id": 1,
            "success": False,
            "status": "closed",
            "witnessed": True,
        }
        t = build_interconnect_transition(
            prior_frame=a,
            next_frame=b,
            proposal=proposal,
            outcome=outcome,
        )
        batch = extract_distillation_candidates(
            prior_frame=a,
            next_frame=b,
            transition=t,
            proposal=proposal,
            outcome=outcome,
        )
        types = {c["candidate_type"] for c in batch["candidates"]}
        self.assertIn("failed_hypothesis", types)
        self.assertIn("counterevidence", types)

    def test_symbiosis_multi_turn_persists_candidates(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="distill")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t1",
            proposed_action="a1",
            evidence_citations=["e"],
            declared_uncertainty=0.2,
        )
        session = record_joint_action(
            self.store,
            self.repo,
            session,
            tool_action={"name": "noop"},
            measured_result={"ok": True},
        )
        session = record_outcome(
            self.store,
            self.repo,
            session,
            success=True,
            metrics={"score": 1},
        )
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t2",
            proposed_action="a2",
            evidence_citations=["e2"],
            declared_uncertainty=0.2,
        )
        batch = (session.get("receipts") or {}).get("distillation_candidates")
        self.assertIsInstance(batch, dict)
        self.assertIn(batch.get("extraction_status"), {"extracted", "empty", "blocked"})
        self.assertTrue(candidates_authorize_nothing(batch))
        stored = self.store.distillation_session_candidates(
            self.repo, session["session_id"]
        )
        self.assertGreaterEqual(len(stored), 1)
        again = self.store.append_distillation_candidate_batch(
            self.repo, dict(batch)
        )
        self.assertTrue(again["duplicate"])

        brief = reconstruct_next_session_brief(self.store, self.repo)
        self.assertIn("distillation_candidates", brief["what_is_currently_believed"])

        sealed = consolidate_session(self.store, self.repo, session)
        # Gates closed → all candidates rejected, none retained as memory
        consolidation = sealed["receipts"]["symbiotic_consolidation"]
        self.assertEqual(consolidation["retained_count"], 0)
        self.assertFalse(sealed["durable_write_authorized"])
        self.assertFalse(sealed["adaptation_authorized"])

    def test_flatten_and_no_authority(self) -> None:
        a, b = self._two_frames()
        t = build_interconnect_transition(prior_frame=a, next_frame=b)
        batch = extract_distillation_candidates(
            prior_frame=a, next_frame=b, transition=t
        )
        flat = flatten_candidates([batch])
        self.assertEqual(len(flat), batch["candidate_count"])
        self.assertTrue(candidates_authorize_nothing(batch))
        self.assertNotEqual(batch.get("support_ceiling"), None)
        # unmeasured transitions never claim high support for facts alone
        if batch["causal_status"] == "unmeasured":
            self.assertEqual(batch["support_ceiling"], SUPPORT_NONE)


if __name__ == "__main__":
    unittest.main()
