"""v8.4.1 verified symbiotic circulation ledger tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.store import Store
from cortex.symbiosis import (
    consolidate_session,
    measure_evaluation_gates,
    open_symbiotic_session,
    record_joint_action,
    record_outcome,
    record_proposal,
    symbiotic_status,
    verify_session_circulation,
)
from cortex.witness import ensure_witness_tables


class SymbiosisLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# ledger host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "LedgerHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_open_appends_exactly_once_chain(self) -> None:
        session = open_symbiotic_session(
            self.store, self.repo, task="ledger open", provider="xai", model_id="g"
        )
        session_id = session["session_id"]
        first = self.store.symbiotic_session_receipts(self.repo, session_id)
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0]["kind"], "agent_instantiation")
        self.assertEqual(first[1]["kind"], "cortex_context")
        self.assertEqual(int(first[0]["chain_sequence"]), 1)
        self.assertEqual(int(first[1]["chain_sequence"]), 2)

        # Replay open path kinds is not done; duplicate append of same body is ok.
        again = self.store.append_symbiotic_receipt(
            self.repo, dict(session["receipts"]["agent_instantiation"])
        )
        self.assertTrue(again["duplicate"])
        self.assertEqual(len(self.store.symbiotic_session_receipts(self.repo, session_id)), 2)

        chain = self.store.verify_symbiotic_session(self.repo, session_id)
        self.assertTrue(chain["valid"])
        self.assertEqual(chain["receipt_count"], 2)

    def test_proposal_evaluation_uses_measured_gates(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="measure gates")
        gates = measure_evaluation_gates(
            self.store,
            self.repo,
            proposal={
                "receipt_hash": "x",
                "interpreted_objective": "o",
                "proposed_action": "a",
                "session_id": session["session_id"],
                "body_epoch_id": session["body_epoch_id"],
            },
            context=session["receipts"]["cortex_context"],
        )
        self.assertIn("measurement_sources", gates)
        self.assertIn("epoch", gates["measurement_sources"])
        self.assertIn("outcome_count", gates["measurement_sources"])

        updated = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="inspect",
            proposed_action="read file",
            evidence_citations=["README.md"],
            declared_uncertainty=0.2,
        )
        evaluation = updated["receipts"]["cortex_evaluation"]
        self.assertIn(evaluation["decision"], {"hold", "ask", "constrain", "allow"})
        self.assertIsInstance(evaluation.get("measurement_sources"), dict)
        self.assertFalse(evaluation["execution_authorized"])

        rows = self.store.symbiotic_session_receipts(
            self.repo, updated["session_id"]
        )
        kinds = [row["kind"] for row in rows]
        self.assertIn("agent_proposal", kinds)
        self.assertIn("cortex_evaluation", kinds)
        self.assertTrue(
            verify_session_circulation(
                self.store, self.repo, updated["session_id"]
            )["valid"]
        )

    def test_outcome_requires_independent_witness(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="outcome path")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="run check",
            proposed_action="pytest",
            evidence_citations=["tests/"],
            declared_uncertainty=0.1,
        )
        session = record_joint_action(
            self.store,
            self.repo,
            session,
            tool_action={"executed": False},
            measured_result={},
        )
        unwitnessed = record_outcome(
            self.store,
            self.repo,
            session,
            success=True,
            metrics={"tests_passed": 1},
            witness=None,
        )
        self.assertFalse(unwitnessed["receipts"]["outcome"]["witnessed"])
        self.assertEqual(unwitnessed["receipts"]["outcome"]["status"], "unwitnessed")

        from cortex.symbiosis import _sha

        joint = unwitnessed["receipts"]["joint_action"]
        subject = {
            "outcome_kind": "task_result",
            "success": True,
            "metrics": {"tests_passed": 1},
            "external_reference": None,
            "joint_action_receipt_hash": joint.get("receipt_hash") or "",
            "session_id": unwitnessed["session_id"],
            "body_epoch_id": unwitnessed["body_epoch_id"],
            "repository_id": unwitnessed["repository_id"],
            "repo": self.repo,
        }
        subject_hash = _sha(subject)
        witness = {
            "witness_kind": "OUTCOME",
            "verifier": "unit_test",
            "subject_receipt_hash": subject_hash,
            "evidence_hashes": [subject_hash],
            "passed": True,
            "issued_at": 1.0,
        }
        witness["witness_id"] = "ow_" + _sha(witness)[:24]
        # Kind already used: cannot replace outcome. Open a fresh session for witnessed path.
        session2 = open_symbiotic_session(self.store, self.repo, task="outcome witnessed")
        session2 = record_proposal(
            self.store,
            self.repo,
            session2,
            interpreted_objective="run check",
            proposed_action="pytest",
            evidence_citations=["tests/"],
            declared_uncertainty=0.1,
        )
        session2 = record_joint_action(
            self.store,
            self.repo,
            session2,
            tool_action={"executed": False},
            measured_result={},
        )
        joint2 = session2["receipts"]["joint_action"]
        subject2 = {
            "outcome_kind": "task_result",
            "success": True,
            "metrics": {"tests_passed": 1},
            "external_reference": None,
            "joint_action_receipt_hash": joint2.get("receipt_hash") or "",
            "session_id": session2["session_id"],
            "turn_id": int(joint2.get("turn_id") or 1),
            "body_epoch_id": session2["body_epoch_id"],
            "repository_id": session2["repository_id"],
            "repo": self.repo,
        }
        subject_hash2 = _sha(subject2)
        witness2 = {
            "witness_kind": "OUTCOME",
            "verifier": "unit_test",
            "subject_receipt_hash": subject_hash2,
            "evidence_hashes": [subject_hash2],
            "passed": True,
            "issued_at": 1.0,
        }
        witness2["witness_id"] = "ow_" + _sha(witness2)[:24]
        witnessed = record_outcome(
            self.store,
            self.repo,
            session2,
            success=True,
            metrics={"tests_passed": 1},
            witness=witness2,
        )
        self.assertTrue(witnessed["receipts"]["outcome"]["witnessed"])
        closed = consolidate_session(
            self.store,
            self.repo,
            witnessed,
            candidates=[{"kind": "verified_fact", "summary": "x", "retain": True}],
            constitutional_gate=True,
        )
        # Even with constitutional_gate true, stability/epoch may still close retention.
        consolidation = closed["receipts"]["symbiotic_consolidation"]
        self.assertFalse(consolidation["adaptation_authorized"])
        self.assertIn("product", consolidation["gates"])
        status = symbiotic_status(self.store, self.repo)
        self.assertTrue(status["ledger"]["valid"])

    def test_tamper_fails_chain_verification(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="tamper")
        session_id = session["session_id"]
        row = self.store.db.execute(
            """SELECT receipt_hash, receipt_json FROM symbiotic_circulation_receipts
               WHERE session_id=? ORDER BY chain_sequence LIMIT 1""",
            (session_id,),
        ).fetchone()
        self.store.db.execute("DROP TRIGGER symbiotic_circulation_receipts_no_update")
        self.store.db.execute(
            """UPDATE symbiotic_circulation_receipts
               SET receipt_json=? WHERE receipt_hash=?""",
            (row["receipt_json"].replace(self.repo, "Tampered"), row["receipt_hash"]),
        )
        self.store.db.commit()
        chain = self.store.verify_symbiotic_session(self.repo, session_id)
        self.assertFalse(chain["valid"])
        self.assertTrue(chain["errors"])


if __name__ == "__main__":
    unittest.main()
