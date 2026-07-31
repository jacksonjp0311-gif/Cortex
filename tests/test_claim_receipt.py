"""v7.1.2 claim receipts for promote decisions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.capabilities import issue_for_controller
from cortex.claim_receipt import (
    claim_report,
    issue_promote_claim_receipt,
    latest_claim_receipt,
    verify_claim_receipt,
)
from cortex.config import ensure_home
from cortex.epoch import ensure_current_epoch
from cortex.phases import transition_phase
from cortex.promote_gate import evaluate_promotion
from cortex.store import Store
from cortex.witness import commit_manifest


class ClaimReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# claim\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "ClaimHost")
        ensure_current_epoch(self.store, "ClaimHost", reason="setup")
        transition_phase(self.store, "ClaimHost", "QUIESCENT", reason="setup")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_denied_claim_stamped(self) -> None:
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {"baseline_is_winner": True},
                "ablations": {"baseline": {"recall_at_k": 0.9}},
                "repo": "ClaimHost",
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            store=self.store,
            repo="ClaimHost",
            require_witness=True,
        )
        self.assertFalse(r.get("allow_promote"))
        cr = r.get("claim_receipt") or {}
        self.assertEqual(cr.get("status"), "denied")
        self.assertTrue(cr.get("receipt_hash"))
        self.assertTrue(cr.get("claim_id", "").startswith("claim_"))
        latest = latest_claim_receipt(self.store, "ClaimHost")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.get("receipt_hash"), cr.get("receipt_hash"))

    def test_allowed_claim_verifies(self) -> None:
        cap = issue_for_controller(
            "ClaimHost", "advanced", store=self.store, reason="claim_test"
        )
        commit_manifest(
            [
                {
                    "id": "cw1",
                    "query": "README",
                    "expected_substrings": ["README"],
                }
            ],
            store=self.store,
            evaluator_identity="claim_test",
        )
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {"baseline_is_winner": True},
                "ablations": {"baseline": {"recall_at_k": 0.95}},
                "repo": "ClaimHost",
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            store=self.store,
            repo="ClaimHost",
            capability=cap,
            require_witness=True,
            witness_report={"recall_at_k": 0.9, "ok": True, "suite_kind": "sealed_witness"},
        )
        self.assertTrue(r.get("allow_promote"), r)
        cr = r.get("claim_receipt") or {}
        self.assertEqual(cr.get("status"), "allowed")
        full = r.get("claim_receipt_full") or latest_claim_receipt(self.store, "ClaimHost")
        self.assertTrue(full.get("gate_bits"))
        self.assertIn("axis_truth", full)
        ver = verify_claim_receipt(self.store, "ClaimHost", full)
        self.assertTrue(ver.get("hash_ok"), ver)
        self.assertTrue(ver.get("epoch_ok"), ver)
        self.assertTrue(ver.get("ok"), ver)
        rep = claim_report(self.store, "ClaimHost")
        self.assertEqual(rep["latest"]["claim_id"], full["claim_id"])

    def test_issue_without_allow_is_denied_status(self) -> None:
        rec = issue_promote_claim_receipt(
            self.store,
            "ClaimHost",
            promotion={
                "allow_promote": False,
                "reasons_if_denied": ["test"],
                "holdout_freeze_id": "x",
                "holdout_recall": 0.1,
                "emergent_coupling": False,
            },
            geometry={"gate_bits": [1, 0, 1, 0], "coordinate": [1, 0, 1, 0]},
        )
        self.assertEqual(rec["status"], "denied")
        self.assertTrue(rec["receipt_hash"])


if __name__ == "__main__":
    unittest.main()
