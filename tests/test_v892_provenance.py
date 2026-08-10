"""Adversarial v8.9.2 canonical provenance and read-purity checks."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex.admitted_memory import (
    commit_admitted_memories,
    deep_verify_admitted_memory,
    list_admitted_memories,
)
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.distillation_candidates import extract_distillation_candidates
from cortex.epoch import ensure_current_epoch
from cortex.interconnect_frame import (
    build_interconnect_transition,
    capture_atomic_interconnect_frame,
)
from cortex.membrane import apply_will_bound_membrane
from cortex.memory_projection import evaluate_memory_eligibility, project_memories
from cortex.store import Store
from cortex.will import issue_will, register_will_principal
from cortex.witness import commit_manifest


class V892ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# provenance host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "ProvenanceHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(self.store, self.repo, "operator", "Operator", secret="v892-secret")
        self.epoch = ensure_current_epoch(self.store, self.repo, reason="v8.9.2-test")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def _canonical_memory(self) -> tuple[dict, dict, dict]:
        session_id = "v892-session"
        epoch_id = self.epoch.epoch_id
        self.store.record_neural_activation(
            self.repo,
            session_id,
            {"activation_id": "v892-activation", "task_hash": "task", "state_hash": "state"},
        )
        self.store.record_outcome(
            self.repo,
            outcome_id="v892-outcome",
            activation_id="v892-activation",
            status="success",
            reward=1.0,
            verification_type="independent",
            verification_payload={},
            credits=[],
            updates=[],
            apply_updates=False,
        )
        outcome = {
            "outcome_id": "v892-outcome",
            "receipt_hash": "o" * 64,
            "verified": True,
            "repo": self.repo,
            "session_id": session_id,
            "turn_id": 1,
        }
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            session_id=session_id,
            body_epoch_id=epoch_id,
            clauses=[
                {"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]},
                {"kind": "prefer_support_min", "min_support": "none"},
            ],
        )
        prior = capture_atomic_interconnect_frame(
            self.store, self.repo, session_id=session_id, turn_id=1,
            body_epoch_id=epoch_id, repository_id=will["repository_id"],
        )
        self.store.append_interconnect_frame(self.repo, prior)
        nxt = capture_atomic_interconnect_frame(
            self.store, self.repo, session_id=session_id, turn_id=2,
            body_epoch_id=epoch_id, repository_id=will["repository_id"],
            prior_frame_hash=prior["receipt_hash"],
        )
        self.store.append_interconnect_frame(self.repo, nxt)
        transition = build_interconnect_transition(
            prior_frame=prior, next_frame=nxt, outcome=outcome
        )
        self.store.append_interconnect_transition(self.repo, transition)
        batch = extract_distillation_candidates(
            prior_frame=prior, next_frame=nxt, transition=transition, outcome=outcome
        )
        self.store.append_distillation_candidate_batch(self.repo, batch)
        witness = commit_manifest(
            [{"id": "v892-case", "query": "test", "expected_substrings": ["test"]}],
            store=self.store,
        )
        gate_evidence = {
            "constitutional_receipt_hash": "c" * 64,
            "constitutional_verified": True,
            "stability_receipt_hash": "s" * 64,
            "stability_verified": True,
        }
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            batches=[batch],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            witness={"witness_id": witness["witness_id"], "passed": True},
            outcome=outcome,
            gate_evidence=gate_evidence,
            session_id=session_id,
            body_epoch_id=epoch_id,
            turn_id=2,
        )
        self.assertEqual(admission["gates"]["overall"], "pass", admission)
        self.assertEqual(admission["admitted_count"], 1, admission)
        committed = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={
                "session_id": session_id,
                "body_epoch_id": epoch_id,
                "repository_id": will["repository_id"],
            },
        )
        self.assertEqual(committed["committed_count"], 1, committed)
        memory = list_admitted_memories(self.store, self.repo)[0]
        return memory, will, admission

    def test_caller_true_cannot_open_naked_candidate(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        receipt = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            candidates=[{
                "candidate_id": "naked",
                "candidate_type": "unresolved_ambiguity",
                "summary": "caller assertion",
                "support_level": "none",
            }],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertNotEqual(receipt["gates"]["overall"], "pass")
        self.assertEqual(receipt["admitted_count"], 0)
        self.assertFalse(receipt["durable_write_authorized"])

    def test_unknown_gate_and_structural_inspection_cannot_promote(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        unknown = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            candidates=[],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertEqual(unknown["gates"]["overall"], "unknown")
        self.assertFalse(unknown["durable_write_authorized"])
        memory, will, _ = self._canonical_memory()
        shallow = dict(memory)
        shallow["membrane_receipt_hash"] = "x" * 64
        # A structural report may be requested, but cannot become guidance.
        projection = project_memories(
            self.store,
            self.repo,
            task="stable route",
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
            structural_inspection=True,
        )
        self.assertNotIn(shallow.get("memory_id"), projection["selected_memory_ids"])

    def test_canonical_append_failure_does_not_advance_latest(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        original = self.store.append_membrane_admission

        def fail_append(repo: str, receipt: dict) -> dict:
            raise RuntimeError("forced canonical failure")

        self.store.append_membrane_admission = fail_append  # type: ignore[method-assign]
        try:
            receipt = apply_will_bound_membrane(
                self.store,
                self.repo,
                will=will,
                will_secret="v892-secret",
                candidates=[],
                persist=True,
            )
        finally:
            self.store.append_membrane_admission = original  # type: ignore[method-assign]
        self.assertEqual(receipt["canonical_persistence"], "failed")
        self.assertIsNone(self.store.get_setting(f"membrane_latest:{self.repo}", None))
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_read_projection_and_epoch_mismatch_do_not_append_state(self) -> None:
        memory, will, _ = self._canonical_memory()
        before = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        projection = project_memories(
            self.store,
            self.repo,
            task="stable route",
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
        )
        after = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        self.assertEqual(before, after)
        self.assertEqual(projection["durable_state_before"], projection["durable_state_after"])
        self.assertFalse(projection["persisted"])
        stale = evaluate_memory_eligibility(
            self.store,
            self.repo,
            memory,
            live_epoch_id="prior-or-future-epoch",
            current_will=will,
            will_secret="v892-secret",
        )
        self.assertFalse(stale["eligible"])
        self.assertIn("epoch_mismatch", stale["exclusions"])
        self.assertEqual(before, self.store.list_memory_state_receipts(self.repo, memory["memory_id"]))

    def test_deep_verification_rejects_tamper_and_shallow_lineage(self) -> None:
        memory, _, _ = self._canonical_memory()
        tampered = dict(memory)
        tampered["summary"] = "rewritten"
        report = deep_verify_admitted_memory(self.store, self.repo, tampered)
        self.assertFalse(report["structural_validity"])
        self.assertFalse(report["valid"])
        shallow = dict(memory)
        shallow["membrane_receipt_hash"] = "f" * 64
        shallow_report = deep_verify_admitted_memory(self.store, self.repo, shallow)
        self.assertFalse(shallow_report["lineage_validity"])
        self.assertFalse(shallow_report["valid"])

    def test_projection_persist_is_receipt_only(self) -> None:
        memory, will, _ = self._canonical_memory()
        before = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        receipt = project_memories(
            self.store,
            self.repo,
            task="stable route",
            session_id="projection-session",
            turn_id=1,
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
            persist=True,
        )
        after = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        self.assertEqual(before, after)
        self.assertIn(receipt["canonical_persistence"], {"committed", "duplicate"})
        self.assertFalse(receipt["policy_effect"])
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_expired_will_is_not_current_authority(self) -> None:
        memory, will, _ = self._canonical_memory()
        expired = dict(will)
        expired["not_after"] = time.time() - 1
        eligibility = evaluate_memory_eligibility(
            self.store,
            self.repo,
            memory,
            current_will=expired,
            will_secret="v892-secret",
            live_epoch_id=self.epoch.epoch_id,
        )
        self.assertFalse(eligibility["gates"]["will"])
        self.assertFalse(eligibility["eligible"])
        self.assertFalse(eligibility["host_mutate_authorized"])
        self.assertFalse(eligibility["execution_authorized"])

    def test_duplicate_admission_is_exactly_once(self) -> None:
        memory, will, admission = self._canonical_memory()
        replay = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={"session_id": "v892-session", "body_epoch_id": self.epoch.epoch_id},
        )
        self.assertEqual(replay["committed_count"], 0)
        self.assertEqual(replay["canonical_persistence"], "duplicate")
        self.assertEqual(len(list_admitted_memories(self.store, self.repo)), 1)
        self.assertFalse(memory["host_mutate_authorized"])
        self.assertFalse(memory["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
