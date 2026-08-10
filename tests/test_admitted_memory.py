"""v8.6 will-bound admitted memory ledger tests."""

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
from cortex.store import Store
from cortex.will import issue_will, register_will_principal, set_default_will_policy


class AdmittedMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# admitted host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "AdmittedHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store, self.repo, "op", "Op", secret="adm-secret-86"
        )
        set_default_will_policy(
            self.store,
            self.repo,
            principal_id="op",
            admit_types=["successful_procedure", "verified_fact", "persistent_constraint"],
            forbid_types=["unresolved_ambiguity"],
            max_retain=8,
            min_support="medium",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _will(self) -> dict:
        return issue_will(
            self.store,
            self.repo,
            principal_id="op",
            secret="adm-secret-86",
            session_id="sess-adm",
            body_epoch_id="epoch-adm",
            clauses=None,
        )

    def test_commit_writes_immutable_rows(self) -> None:
        will = self._will()
        candidates = [
            {
                "candidate_id": "cand_proc_adm",
                "candidate_type": "successful_procedure",
                "kind": "successful_procedure",
                "summary": "procedure worked",
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
            will=will,
            will_secret="adm-secret-86",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            session_id="sess-adm",
            body_epoch_id="epoch-adm",
        )
        # Naked candidates and caller-supplied gate booleans are intentionally
        # blocked until a canonical trajectory batch is persisted.
        self.assertFalse(admission["durable_write_authorized"])
        batch = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={
                "session_id": "sess-adm",
                "body_epoch_id": "epoch-adm",
                "repository_id": will.get("repository_id"),
            },
        )
        self.assertIn(
            batch["status"],
            {
                "blocked_gates_or_will",
                "empty_or_duplicate",
                "blocked_unresolved_or_noncanonical_candidates",
            },
        )
        self.assertEqual(batch["committed_count"], 0)
        self.assertFalse(batch["host_mutate_authorized"])
        self.assertFalse(batch["execution_authorized"])
        rows = list_admitted_memories(self.store, self.repo)
        self.assertEqual(rows, [])
        # A replay of a blocked admission cannot create a row.
        again = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={"session_id": "sess-adm", "body_epoch_id": "epoch-adm"},
        )
        self.assertEqual(again["committed_count"], 0)
        self.assertEqual(len(list_admitted_memories(self.store, self.repo)), 0)
        report = verify_admitted_memories(self.store, self.repo)
        self.assertTrue(report["valid"], report.get("errors"))

    def test_blocks_without_durable_or_with_invention(self) -> None:
        will = self._will()
        admission = {
            "durable_write_authorized": False,
            "will_verified": True,
            "invented_count": 0,
            "admitted": [
                {
                    "candidate_id": "x",
                    "retain": True,
                    "candidate_type": "successful_procedure",
                    "support_level": "high",
                }
            ],
            "receipt_hash": "m" * 64,
        }
        batch = commit_admitted_memories(
            self.store, self.repo, admission=admission, will=will
        )
        # Fabricated mapping with hash not in ledger is independently fail-closed.
        self.assertIn(
            batch["status"],
            {
                "blocked_gates_or_will",
                "blocked_membrane_not_in_ledger",
                "blocked_unresolved_or_noncanonical_candidates",
            },
        )
        self.assertEqual(batch["committed_count"], 0)

        # No receipt_hash → flag-based path still blocks invention.
        admission2 = {
            "durable_write_authorized": True,
            "will_verified": True,
            "invented_count": 1,
            "admitted": admission["admitted"],
        }
        batch2 = commit_admitted_memories(
            self.store, self.repo, admission=admission2, will=will
        )
        self.assertEqual(batch2["status"], "blocked_unresolved_or_noncanonical_candidates")


if __name__ == "__main__":
    unittest.main()
