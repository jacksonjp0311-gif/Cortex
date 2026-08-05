"""v8.5 authenticated will + unified distillation membrane tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.distillation_candidates import extract_distillation_candidates
from cortex.interconnect_frame import (
    build_interconnect_transition,
    capture_atomic_interconnect_frame,
)
from cortex.membrane import apply_will_bound_membrane
from cortex.store import Store
from cortex.symbiosis import consolidate_session, open_symbiotic_session
from cortex.will import issue_will, register_will_principal, verify_will
from cortex.witness import ensure_witness_tables


class WillMembraneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# will host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "WillHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_witness_tables(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _register(self) -> dict:
        return register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Operator",
            secret="test-secret-will-8.5",
        )

    def _issue(self, **kwargs) -> dict:
        self._register()
        clauses = kwargs.pop(
            "clauses",
            [
                {
                    "kind": "admit_type",
                    "candidate_types": [
                        "successful_procedure",
                        "verified_fact",
                        "regime_warning",
                        "persistent_constraint",
                    ],
                },
                {
                    "kind": "prioritize_type",
                    "candidate_types": ["successful_procedure"],
                },
                {"kind": "prefer_support_min", "min_support": "low"},
            ],
        )
        return issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="test-secret-will-8.5",
            clauses=clauses,
            **kwargs,
        )

    def test_will_register_issue_verify(self) -> None:
        reg = self._register()
        self.assertTrue(reg["registered"])
        self.assertFalse(reg["execution_authorized"])
        self.assertFalse(reg["host_mutate_authorized"])
        will = self._issue(intent_summary="prefer procedures")
        self.assertTrue(will.get("issued"))
        self.assertEqual(will["kind"], "will_root")
        self.assertFalse(will["invents_facts"])
        self.assertFalse(will["alters_evidence"])
        ok = verify_will(
            self.store,
            self.repo,
            will,
            secret="test-secret-will-8.5",
        )
        self.assertTrue(ok["verified"], ok.get("errors"))
        bad = verify_will(
            self.store,
            self.repo,
            will,
            secret="wrong-secret",
        )
        self.assertFalse(bad["verified"])

    def test_will_rejects_forbidden_scope(self) -> None:
        self._register()
        with self.assertRaises(ValueError):
            issue_will(
                self.store,
                self.repo,
                principal_id="operator",
                secret="test-secret-will-8.5",
                scopes=["host.mutate"],
            )

    def test_membrane_never_invents_and_defers_without_gates(self) -> None:
        will = self._issue()
        a = capture_atomic_interconnect_frame(
            self.store,
            self.repo,
            session_id="s",
            turn_id=1,
            body_epoch_id="e",
            repository_id="r",
        )
        b = {
            **capture_atomic_interconnect_frame(
                self.store,
                self.repo,
                session_id="s",
                turn_id=2,
                body_epoch_id="e",
                repository_id="r",
                prior_frame_hash=a["receipt_hash"],
            ),
            "validity": {
                "overall_state": "fail",
                "freshness_state": "fail",
                "epoch_state": "unknown",
            },
        }
        # Force regression-ish prior
        a = {
            **a,
            "validity": {**(a.get("validity") or {}), "overall_state": "pass"},
        }
        t = build_interconnect_transition(prior_frame=a, next_frame=b)
        batch = extract_distillation_candidates(
            prior_frame=a, next_frame=b, transition=t
        )
        # Gates closed → directed candidates deferred, not admitted
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="test-secret-will-8.5",
            batches=[batch],
            constitutional_gate=False,
            epoch_compatible=False,
            witness_present=False,
            outcome_closed=False,
            stable_regime=False,
            session_id="s",
            body_epoch_id="e",
        )
        self.assertEqual(admission["invented_count"], 0)
        self.assertTrue(admission["sources_only_from_candidates"])
        self.assertFalse(admission["host_mutate_authorized"])
        self.assertFalse(admission["execution_authorized"])
        self.assertFalse(admission["durable_write_authorized"])
        # Some regime warnings may be directed → deferred when gates closed
        self.assertGreaterEqual(
            admission["deferred_count"] + admission["rejected_count"], 1
        )
        self.assertEqual(admission["admitted_count"], 0)

    def test_membrane_admits_under_will_and_open_gates(self) -> None:
        will = self._issue()
        # Medium-support successful procedure candidate (synthetic but typed)
        candidates = [
            {
                "candidate_id": "cand_proc_1",
                "candidate_type": "successful_procedure",
                "kind": "successful_procedure",
                "summary": "run tests succeeded",
                "support_level": "medium",
                "retain": False,
            },
            {
                "candidate_id": "cand_amb_1",
                "candidate_type": "unresolved_ambiguity",
                "kind": "unresolved_ambiguity",
                "summary": "noise",
                "support_level": "low",
                "retain": False,
            },
        ]
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="test-secret-will-8.5",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertTrue(admission["will_verified"])
        self.assertTrue(admission["gates"]["open"])
        self.assertEqual(admission["invented_count"], 0)
        types = {c["candidate_type"] for c in admission["admitted"]}
        self.assertIn("successful_procedure", types)
        self.assertNotIn("unresolved_ambiguity", types)  # not directed
        self.assertTrue(admission["durable_write_authorized"])
        for c in admission["admitted"]:
            self.assertTrue(c["retain"])
            self.assertTrue(c["memory_write_authorized"])

    def test_membrane_rejects_unverified_will(self) -> None:
        will = self._issue()
        candidates = [
            {
                "candidate_id": "c1",
                "candidate_type": "successful_procedure",
                "kind": "successful_procedure",
                "summary": "x",
                "support_level": "high",
            }
        ]
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="bad-secret",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertFalse(admission["will_verified"])
        self.assertEqual(admission["admitted_count"], 0)
        self.assertFalse(admission["durable_write_authorized"])

    def test_forbid_type_blocks_admission(self) -> None:
        will = self._issue(
            clauses=[
                {
                    "kind": "forbid_type",
                    "candidate_types": ["successful_procedure"],
                },
                {
                    "kind": "admit_type",
                    "candidate_types": ["successful_procedure"],
                },
            ]
        )
        candidates = [
            {
                "candidate_id": "c1",
                "candidate_type": "successful_procedure",
                "kind": "successful_procedure",
                "summary": "x",
                "support_level": "high",
            }
        ]
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="test-secret-will-8.5",
            candidates=candidates,
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertEqual(admission["admitted_count"], 0)
        self.assertTrue(
            any(r.get("rejection_reason") == "will_forbid_type" for r in admission["rejected"])
        )

    def test_consolidate_with_will_sets_durable_only_when_admitted(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="will-consol")
        will = self._issue(
            session_id=session["session_id"],
            body_epoch_id=session.get("body_epoch_id") or "",
        )
        # Without open gates → no durable write even with will
        sealed = consolidate_session(
            self.store,
            self.repo,
            session,
            candidates=[
                {
                    "candidate_id": "c1",
                    "candidate_type": "successful_procedure",
                    "kind": "successful_procedure",
                    "summary": "x",
                    "support_level": "high",
                    "retain": False,
                }
            ],
            constitutional_gate=False,
            will=will,
            will_secret="test-secret-will-8.5",
        )
        self.assertFalse(sealed["durable_write_authorized"])
        self.assertFalse(sealed["host_mutate_authorized"])
        self.assertIn("distillation_membrane_admission", sealed["receipts"])

        sealed_open = consolidate_session(
            self.store,
            self.repo,
            session,
            candidates=[
                {
                    "candidate_id": "c2",
                    "candidate_type": "successful_procedure",
                    "kind": "successful_procedure",
                    "summary": "y",
                    "support_level": "high",
                    "retain": False,
                }
            ],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            will=will,
            will_secret="test-secret-will-8.5",
        )
        membrane = sealed_open["receipts"]["distillation_membrane_admission"]
        self.assertTrue(membrane["will_verified"])
        # durable only if something was admitted
        if membrane["admitted_count"] > 0:
            self.assertTrue(sealed_open["durable_write_authorized"])
            self.assertGreater(
                sealed_open["receipts"]["symbiotic_consolidation"]["retained_count"], 0
            )
        self.assertFalse(sealed_open["execution_authorized"])
        self.assertEqual(membrane["invented_count"], 0)

    def test_will_does_not_alter_evidence_claim(self) -> None:
        will = self._issue()
        self.assertFalse(will["alters_evidence"])
        self.assertFalse(will["invents_facts"])
        self.assertFalse(will["memory_write_authorized"])
        self.assertFalse(will["durable_write_authorized"])


if __name__ == "__main__":
    unittest.main()
