"""v8.4.0 AI–Cortex symbiotic runtime tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.store import Store
from cortex.symbiosis import (
    complementarity_surplus,
    consolidate_session,
    evaluate_proposal,
    open_symbiotic_session,
    record_joint_action,
    record_proposal,
    reconstruct_next_session_brief,
    symbiotic_status,
)
from cortex.witness import ensure_witness_tables


class SymbiosisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# symbiosis host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "SymbiosisHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_open_session_emits_instantiation_and_context(self) -> None:
        session = open_symbiotic_session(
            self.store,
            self.repo,
            task="inspect architecture",
            provider="xai",
            model_id="grok-test",
        )
        self.assertEqual(session["schema_version"], "cortex-symbiosis/1.6")
        self.assertIn("agent_instantiation", session["receipts"])
        self.assertIn("cortex_context", session["receipts"])
        self.assertFalse(session["policy_effect"])
        self.assertFalse(session["update_authorized"])
        self.assertFalse(
            session["receipts"]["agent_instantiation"]["persistent_self"]
        )
        self.assertEqual(len(session["chain"]), 2)
        status = symbiotic_status(self.store, self.repo)
        self.assertEqual(status["session_id"], session["session_id"])
        self.assertEqual(status["status"], "open")

    def test_proposal_fail_closed_without_citations_or_epoch(self) -> None:
        session = open_symbiotic_session(
            self.store, self.repo, task="propose change"
        )
        updated = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="improve docs",
            proposed_action="edit README",
            evidence_citations=[],
            declared_uncertainty=0.2,
        )
        evaluation = updated["receipts"]["cortex_evaluation"]
        # Live path uses observed epoch currency. Unverified epochs hold first;
        # missing citations alone ask when currency is present.
        self.assertIn(evaluation["decision"], {"hold", "ask"})
        self.assertFalse(evaluation["execution_authorized"])
        self.assertFalse(evaluation["learning_authorized"])

        no_citations = evaluate_proposal(
            proposal={
                "receipt_hash": "p1",
                "interpreted_objective": "improve docs",
                "proposed_action": "edit README",
                "declared_uncertainty_scalar": 0.2,
                "evidence_citations": [],
                "requested_permissions": [],
                "session_id": "s",
                "body_epoch_id": "e",
            },
            context={"session_id": "s", "body_epoch_id": "e"},
            gate_states={
                "epoch_current": "pass",
                "host_immutable": "pass",
                "invariants_ok": "pass",
                "authority_scope_ok": "pass",
                "outcome_history_ready": "pass",
                "operator_contract_ready": "pass",
                "measurement_complete": "pass",
                "context_bound": "pass",
            },
        )
        self.assertEqual(no_citations["decision"], "ask")

    def test_forbidden_permission_holds(self) -> None:
        session = open_symbiotic_session(
            self.store, self.repo, task="dangerous"
        )
        updated = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="mutate host",
            proposed_action="rewrite source",
            evidence_citations=["docs/ARCHITECTURE.md"],
            declared_uncertainty=0.1,
            requested_permissions=["host_source_mutation"],
        )
        self.assertEqual(
            updated["receipts"]["cortex_evaluation"]["decision"], "hold"
        )

    def test_consolidation_stays_closed_without_gates(self) -> None:
        session = open_symbiotic_session(
            self.store, self.repo, task="learn something"
        )
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="note a fact",
            proposed_action="remember fluent claim",
            evidence_citations=["path/a.py"],
            declared_uncertainty=0.2,
        )
        session = record_joint_action(
            self.store,
            self.repo,
            session,
            tool_action={"executed": False},
            measured_result={"ok": False},
        )
        closed = consolidate_session(
            self.store,
            self.repo,
            session,
            candidates=[
                {
                    "kind": "verified_fact",
                    "summary": "fluent model claim",
                    "retain": True,
                }
            ],
            constitutional_gate=False,
            witness_present=False,
            outcome_closed=False,
            stable_regime=False,
        )
        consolidation = closed["receipts"]["symbiotic_consolidation"]
        self.assertEqual(consolidation["retained_count"], 0)
        self.assertEqual(consolidation["rejected_count"], 1)
        self.assertFalse(consolidation["adaptation_authorized"])
        self.assertFalse(consolidation["durable_write_authorized"])
        self.assertEqual(consolidation["gates"]["product"], 0)

    def test_evaluate_proposal_allow_path_is_review_only(self) -> None:
        proposal = {
            "receipt_hash": "abc",
            "interpreted_objective": "fix tests",
            "proposed_action": "run pytest",
            "declared_uncertainty_scalar": 0.2,
            "evidence_citations": ["tests/test_symbiosis.py"],
            "requested_permissions": [],
            "session_id": "s",
            "body_epoch_id": "e",
        }
        panel = evaluate_proposal(
            proposal=proposal,
            context={"session_id": "s", "body_epoch_id": "e"},
            gate_states={
                "epoch_current": "pass",
                "host_immutable": "pass",
                "invariants_ok": "pass",
                "authority_scope_ok": "pass",
                "outcome_history_ready": "pass",
                "operator_contract_ready": "pass",
                "measurement_complete": "pass",
                "context_bound": "pass",
            },
            blast_radius="bounded",
        )
        self.assertEqual(panel["decision"], "allow")
        self.assertTrue(panel["review_eligible"])
        self.assertFalse(panel["execution_authorized"])
        self.assertFalse(panel["learning_authorized"])

    def test_unknown_gate_never_allows(self) -> None:
        panel = evaluate_proposal(
            proposal={
                "receipt_hash": "abc",
                "interpreted_objective": "x",
                "proposed_action": "y",
                "declared_uncertainty_scalar": 0.1,
                "evidence_citations": ["a"],
                "requested_permissions": [],
                "session_id": "s",
                "body_epoch_id": "e",
            },
            context={"session_id": "s", "body_epoch_id": "e"},
            gate_states={
                "epoch_current": "pass",
                "host_immutable": "unknown",
                "invariants_ok": "pass",
                "authority_scope_ok": "pass",
                "outcome_history_ready": "pass",
                "operator_contract_ready": "pass",
                "measurement_complete": "pass",
                "context_bound": "pass",
            },
        )
        self.assertEqual(panel["decision"], "hold")
        self.assertIn("host_immutability_unknown", panel["reason"])

    def test_complementarity_unmeasured_without_estimators(self) -> None:
        report = complementarity_surplus()
        self.assertEqual(report["status"], "unmeasured")
        self.assertIsNone(report["S_AC"])
        measured = complementarity_surplus(i_joint=1.0, i_agent=0.0, i_cortex=0.0)
        self.assertEqual(measured["S_AC"], 1.0)
        self.assertTrue(measured["complementary"])

    def test_next_session_brief_is_reconstructed(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="continue work")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="brief",
            proposed_action="inspect",
            evidence_citations=["a.md"],
            assumptions=["A1"],
            declared_uncertainty=0.2,
        )
        brief = reconstruct_next_session_brief(self.store, self.repo)
        self.assertIn("what_is_currently_believed", brief)
        self.assertIn("forbidden_actions", brief)
        self.assertIn("assumptions", brief)
        self.assertIn("assumptions_blocked", brief["assumptions"])
        # Held/ask path should classify A1 as blocked or unverified, not empty.
        classified = sum(len(v) for v in brief["assumptions"].values())
        self.assertEqual(classified, 1)
        self.assertFalse(brief["policy_effect"])
        self.assertFalse(brief["update_authorized"])

    def test_turn_regenerates_context_and_frame(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="frame pulse")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t1",
            proposed_action="a1",
            evidence_citations=["x"],
            declared_uncertainty=0.2,
        )
        frame = session["receipts"]["interconnect_frame"]
        context = session["receipts"]["cortex_context"]
        proposal = session["receipts"]["agent_proposal"]
        self.assertEqual(int(frame["turn_id"]), 1)
        self.assertEqual(int(context["turn_id"]), 1)
        self.assertEqual(
            proposal.get("interconnect_frame_hash"), frame.get("receipt_hash")
        )
        self.assertEqual(
            proposal.get("context_receipt_hash"), context.get("receipt_hash")
        )
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="t2",
            proposed_action="a2",
            evidence_citations=["y"],
            declared_uncertainty=0.2,
        )
        self.assertEqual(int(session["receipts"]["interconnect_frame"]["turn_id"]), 2)
        self.assertNotEqual(
            session["receipts"]["cortex_context"]["receipt_hash"],
            context["receipt_hash"],
        )

    def test_recurrent_turns_are_independently_ledgered(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="multi-turn")
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="first turn",
            proposed_action="inspect a",
            evidence_citations=["a.md"],
            assumptions=["A1"],
            declared_uncertainty=0.2,
        )
        session = record_joint_action(
            self.store,
            self.repo,
            session,
            tool_action={"executed": False},
        )
        session = record_proposal(
            self.store,
            self.repo,
            session,
            interpreted_objective="second turn",
            proposed_action="inspect b",
            evidence_citations=["b.md"],
            assumptions=["A2"],
            declared_uncertainty=0.2,
        )
        self.assertGreaterEqual(int(session["turn_count"]), 2)
        self.assertEqual(int(session["current_turn_id"]), 2)
        rows = self.store.symbiotic_session_receipts(
            self.repo, session["session_id"]
        )
        proposal_turns = {
            int(row["turn_id"])
            for row in rows
            if row.get("kind") == "agent_proposal"
        }
        self.assertEqual(proposal_turns, {1, 2})
        chain = self.store.verify_symbiotic_session(
            self.repo, session["session_id"]
        )
        self.assertTrue(chain["valid"])


if __name__ == "__main__":
    unittest.main()
