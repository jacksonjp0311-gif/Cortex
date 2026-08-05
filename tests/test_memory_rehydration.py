"""v8.7 governed memory rehydration, state, conflict, credit tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.admitted_memory import (
    commit_admitted_memories,
    list_admitted_memories,
    verify_admitted_memories,
)
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.membrane import apply_will_bound_membrane
from cortex.memory_conflict import challenge_memory, supersede_memory
from cortex.memory_credit import issue_memory_credit, record_memory_use
from cortex.memory_projection import evaluate_memory_eligibility, project_memories
from cortex.memory_state import current_memory_state, issue_memory_state
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import issue_will, register_will_principal, set_default_will_policy


class MemoryRehydrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# mem rehydrate\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "RehydrateHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store, self.repo, "op", "Op", secret="rehy-secret-87"
        )
        set_default_will_policy(
            self.store,
            self.repo,
            principal_id="op",
            admit_types=[
                "successful_procedure",
                "verified_fact",
                "persistent_constraint",
                "regime_warning",
            ],
            forbid_types=["unresolved_ambiguity"],
            max_retain=8,
            min_support="medium",
        )
        self.will = issue_will(
            self.store,
            self.repo,
            principal_id="op",
            secret="rehy-secret-87",
            session_id="sess-a",
            body_epoch_id="epoch-a",
        )
        self.mem = self._admit(
            candidate_id="cand_proc_rehy",
            ctype="successful_procedure",
            summary="run tests then commit procedure",
            session_id="sess-a",
            epoch="epoch-a",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _admit(
        self,
        *,
        candidate_id: str,
        ctype: str,
        summary: str,
        session_id: str,
        epoch: str,
    ) -> dict:
        candidates = [
            {
                "candidate_id": candidate_id,
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
                "evidence": {"transition_class": "distillation_ready"},
            }
        ]
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=self.will,
            will_secret="rehy-secret-87",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            session_id=session_id,
            body_epoch_id=epoch,
        )
        batch = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=self.will,
            session={
                "session_id": session_id,
                "body_epoch_id": epoch,
                "repository_id": self.will.get("repository_id"),
            },
        )
        self.assertGreaterEqual(batch["committed_count"], 1, batch)
        rows = list_admitted_memories(self.store, self.repo)
        for row in rows:
            if row.get("candidate_id") == candidate_id:
                return row
        self.fail("memory not found after commit")

    def test_cross_session_projection_after_restart(self) -> None:
        # Process restart simulation
        path = self.home / "cortex.db"
        self.store.close()
        reopened = Store(path)
        try:
            proj = project_memories(
                reopened,
                self.repo,
                task="run tests then commit",
                session_id="sess-b",
                turn_id=1,
                body_epoch_id="epoch-a",
                current_will=self.will,
                will_secret="rehy-secret-87",
            )
            self.assertIn(self.mem["memory_id"], proj["selected_memory_ids"])
            # deterministic
            proj2 = project_memories(
                reopened,
                self.repo,
                task="run tests then commit",
                session_id="sess-b",
                turn_id=2,
                body_epoch_id="epoch-a",
                current_will=self.will,
                will_secret="rehy-secret-87",
            )
            self.assertEqual(
                proj["selected_memory_ids"], proj2["selected_memory_ids"]
            )
        finally:
            reopened.close()
            self.store = Store(path)

    def test_stale_epoch_excluded_but_preserved(self) -> None:
        elig = evaluate_memory_eligibility(
            self.store,
            self.repo,
            self.mem,
            live_epoch_id="epoch-LIVE",
            current_will=self.will,
            will_secret="rehy-secret-87",
            task="run tests",
        )
        self.assertFalse(elig["eligible"])
        self.assertIn("epoch_mismatch", elig["exclusions"])
        # still in ledger
        self.assertEqual(len(list_admitted_memories(self.store, self.repo)), 1)
        tip = current_memory_state(self.store, self.repo, self.mem["memory_id"])
        self.assertEqual(tip["state"], "epoch_stale")

    def test_superseded_not_projected(self) -> None:
        other = self._admit(
            candidate_id="cand_proc_new",
            ctype="successful_procedure",
            summary="run tests then commit improved",
            session_id="sess-a",
            epoch="epoch-a",
        )
        supersede_memory(
            self.store,
            self.repo,
            superseded_memory_id=self.mem["memory_id"],
            replacement_memory_id=other["memory_id"],
            authorized=True,
        )
        proj = project_memories(
            self.store,
            self.repo,
            task="run tests then commit",
            body_epoch_id="epoch-a",
            current_will=self.will,
            will_secret="rehy-secret-87",
        )
        self.assertNotIn(self.mem["memory_id"], proj["selected_memory_ids"])
        # still auditable
        self.assertEqual(
            current_memory_state(self.store, self.repo, self.mem["memory_id"])[
                "state"
            ],
            "superseded",
        )

    def test_contested_surfaced_not_as_fact(self) -> None:
        challenge_memory(
            self.store,
            self.repo,
            challenged_memory_id=self.mem["memory_id"],
            challenger_candidate_id="cand_counter",
            contradiction_kind="direct_disconfirmation",
        )
        proj = project_memories(
            self.store,
            self.repo,
            task="run tests then commit",
            body_epoch_id="epoch-a",
            current_will=self.will,
            will_secret="rehy-secret-87",
        )
        self.assertNotIn(self.mem["memory_id"], proj["selected_memory_ids"])
        contested_ids = [c.get("memory_id") for c in proj.get("contested") or ()]
        self.assertIn(self.mem["memory_id"], contested_ids)

    def test_deep_verify_rejects_forged_and_checks_membrane(self) -> None:
        report = verify_admitted_memories(self.store, self.repo, deep=True)
        self.assertTrue(report["valid"], report.get("errors"))
        # forge row into store is hard; test deep_verify on mutated mapping
        from cortex.admitted_memory import deep_verify_admitted_memory

        forged = dict(self.mem)
        forged["receipt_hash"] = "0" * 64
        forged["membrane_receipt_hash"] = "f" * 64
        deep = deep_verify_admitted_memory(self.store, self.repo, forged)
        self.assertFalse(deep["lineage_validity"])

    def test_memory_use_unmeasured_without_outcome(self) -> None:
        proj = project_memories(
            self.store,
            self.repo,
            task="run tests",
            body_epoch_id="epoch-a",
            current_will=self.will,
            will_secret="rehy-secret-87",
        )
        use = record_memory_use(
            self.store,
            self.repo,
            projection=proj,
            proposal={"evidence_citations": [self.mem["memory_id"]]},
            outcome={},  # no witness
        )
        credit = issue_memory_credit(
            self.store,
            self.repo,
            memory_id=self.mem["memory_id"],
            use_receipt=use,
        )
        self.assertEqual(credit["credit_status"], "unmeasured")

    def test_open_session_projects_historical_memory(self) -> None:
        # new session should rehydrate prior admitted memory
        session = open_symbiotic_session(
            self.store, self.repo, task="run tests then commit carefully"
        )
        proj = (session.get("receipts") or {}).get("memory_projection") or {}
        self.assertTrue(proj.get("receipt_hash"), session.get("receipts", {}).keys())
        ctx = (session.get("receipts") or {}).get("cortex_context") or {}
        preds = ctx.get("predictions") or {}
        # Either embedded in predictions or present as sibling receipt.
        self.assertTrue(
            "memory_projection_hash" in preds or proj.get("receipt_hash"),
            preds,
        )

    def test_projection_no_authority(self) -> None:
        proj = project_memories(
            self.store,
            self.repo,
            task="anything",
            body_epoch_id="epoch-a",
        )
        self.assertFalse(proj["host_mutate_authorized"])
        self.assertFalse(proj["execution_authorized"])
        self.assertFalse(proj["learning_authorized"])
        self.assertTrue(proj["advisory_only"])


if __name__ == "__main__":
    unittest.main()
