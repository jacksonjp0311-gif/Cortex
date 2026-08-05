"""v8.8 cross-instantiation memory trial tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.admitted_memory import commit_admitted_memories, list_admitted_memories
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.membrane import apply_will_bound_membrane
from cortex.memory_conflict import supersede_memory
from cortex.memory_state import issue_memory_state
from cortex.memory_trials import (
    ARMS,
    build_arm_context,
    memory_trial_status,
    run_cross_instantiation_trial,
    score_arm_package,
)
from cortex.store import Store
from cortex.will import issue_will, register_will_principal, set_default_will_policy


class MemoryTrialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# trial host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "TrialHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store, self.repo, "op", "Op", secret="trial-secret-88"
        )
        set_default_will_policy(
            self.store,
            self.repo,
            principal_id="op",
            admit_types=[
                "successful_procedure",
                "persistent_constraint",
                "verified_fact",
            ],
            forbid_types=["unresolved_ambiguity"],
            max_retain=8,
            min_support="medium",
        )
        self.will = issue_will(
            self.store,
            self.repo,
            principal_id="op",
            secret="trial-secret-88",
            session_id="sess-trial",
            body_epoch_id="epoch-trial",
        )
        # Seed useful + stale memories
        self.active = self._admit(
            "cand_proc_ok",
            "successful_procedure",
            "run tests then commit procedure",
        )
        self.constraint = self._admit(
            "cand_const_host",
            "persistent_constraint",
            "host source mutation forbidden and unwitnessed memory write blocked",
        )
        self.stale = self._admit(
            "cand_proc_stale",
            "successful_procedure",
            "obsolete procedure from prior epoch should not be fact",
        )
        issue_memory_state(
            self.store,
            self.repo,
            memory_id=self.stale["memory_id"],
            state="epoch_stale",
            reason="trial_seed",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _admit(self, cid: str, ctype: str, summary: str) -> dict:
        candidates = [
            {
                "candidate_id": cid,
                "candidate_type": ctype,
                "kind": ctype,
                "summary": summary,
                "support_level": "medium",
                "source": {
                    "transition_hash": "t" * 64,
                    "outcome_hash": "o" * 64,
                    "prior_frame_hash": "a" * 64,
                    "next_frame_hash": "b" * 64,
                },
                "evidence": {},
            }
        ]
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=self.will,
            will_secret="trial-secret-88",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            session_id="sess-trial",
            body_epoch_id="epoch-trial",
        )
        commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=self.will,
            session={
                "session_id": "sess-trial",
                "body_epoch_id": "epoch-trial",
                "repository_id": self.will.get("repository_id"),
            },
        )
        for row in list_admitted_memories(self.store, self.repo):
            if row.get("candidate_id") == cid:
                return row
        self.fail(f"missing {cid}")

    def test_arms_and_gains(self) -> None:
        trial = run_cross_instantiation_trial(
            self.store,
            self.repo,
            task="run tests then commit procedure under host immutability",
            body_epoch_id="epoch-trial",
            current_will=self.will,
            will_secret="trial-secret-88",
        )
        self.assertEqual(set(trial["U"]), set(ARMS))
        self.assertIn("G_rehydration", trial)
        self.assertIn("G_credit", trial)
        # Governed D should beat raw A when relevant memories exist
        self.assertGreaterEqual(trial["U"]["D"], trial["U"]["A"])
        # Rehydration gain defined and reported
        self.assertEqual(
            trial["G_rehydration"],
            round(trial["U"]["D"] - trial["U"]["A"], 6),
        )
        self.assertEqual(
            trial["G_credit"],
            round(trial["U"]["E"] - trial["U"]["D"], 6),
        )
        # Unfiltered C incurs inappropriate-use cost when stale rows exist
        self.assertGreater(
            trial["arm_scores"]["C"]["metrics"]["inappropriate_memory_use"],
            0.0,
        )
        self.assertFalse(trial["host_mutate_authorized"])
        self.assertFalse(trial["execution_authorized"])
        self.assertTrue(trial["G_rehydration"] >= 0)

        status = memory_trial_status(self.store, self.repo)
        self.assertEqual(status["latest_receipt_hash"], trial["receipt_hash"])

    def test_deterministic_same_inputs(self) -> None:
        t1 = run_cross_instantiation_trial(
            self.store,
            self.repo,
            task="run tests then commit procedure",
            body_epoch_id="epoch-trial",
            current_will=self.will,
            will_secret="trial-secret-88",
            simulate_e_feedback=False,
            persist=False,
        )
        t2 = run_cross_instantiation_trial(
            self.store,
            self.repo,
            task="run tests then commit procedure",
            body_epoch_id="epoch-trial",
            current_will=self.will,
            will_secret="trial-secret-88",
            simulate_e_feedback=False,
            persist=False,
        )
        self.assertEqual(t1["U"], t2["U"])
        self.assertEqual(t1["G_rehydration"], t2["G_rehydration"])

    def test_arm_c_includes_stale_text_penalized(self) -> None:
        c_pkg = build_arm_context(
            self.store,
            self.repo,
            "C",
            task="run tests",
            body_epoch_id="epoch-trial",
        )
        d_pkg = build_arm_context(
            self.store,
            self.repo,
            "D",
            task="run tests then commit procedure under host mutation forbidden",
            body_epoch_id="epoch-trial",
            current_will=self.will,
            will_secret="trial-secret-88",
        )
        # C is unfiltered — more or equal ids than D
        self.assertGreaterEqual(len(c_pkg["memory_ids"]), len(d_pkg["memory_ids"]))
        self.assertTrue(d_pkg["filtered"])
        self.assertFalse(c_pkg["filtered"])

    def test_no_authority_bits(self) -> None:
        pkg = build_arm_context(self.store, self.repo, "A", task="x")
        score = score_arm_package(pkg)
        self.assertIn("U", score)
        trial = run_cross_instantiation_trial(
            self.store, self.repo, task="x", persist=False, simulate_e_feedback=False
        )
        self.assertFalse(trial.get("learning_authorized"))


if __name__ == "__main__":
    unittest.main()
