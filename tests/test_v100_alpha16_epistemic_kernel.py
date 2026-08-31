from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.epistemic_kernel import (
    append_epistemic_event,
    compile_action_sufficient_context,
    list_epistemic_events,
    project_epistemic_state,
    update_continuation_debt,
    verify_epistemic_history,
)
from cortex.source_experience import forge_structural_source_experience
from cortex.store import Store


class Alpha16EpistemicKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("alpha16\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha16Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _event(self, polarity: str, root: str) -> dict:
        return append_epistemic_event(
            self.store,
            self.repo,
            claim_id="claim.cache",
            claim_text="cache invalidation precedes reread",
            polarity=polarity,
            evidence_receipt_hash="a" * 64,
            source_lineage_hash=root * 64,
            valid_from=time.time() - 1,
        )

    def test_history_is_immutable_chained_and_state_is_derived(self) -> None:
        first = self._event("support", "b")
        self._event("oppose", "c")
        check = verify_epistemic_history(self.store, self.repo)
        self.assertTrue(check["valid"], check["errors"])
        projection = project_epistemic_state(list_epistemic_events(self.store, self.repo))
        self.assertEqual(projection["claims"][0]["truth_state"], "BOTH")
        self.assertEqual(projection["claims"][0]["support_bits"], [1, 1])
        with self.assertRaises(Exception):
            self.store.db.execute(
                "UPDATE epistemic_events SET polarity='support' WHERE event_hash=?",
                (first["event_hash"],),
            )

    def test_bitemporal_retraction_changes_projection_not_history(self) -> None:
        support = self._event("support", "b")
        append_epistemic_event(
            self.store,
            self.repo,
            claim_id="claim.cache",
            claim_text="cache invalidation precedes reread",
            polarity="retract",
            evidence_receipt_hash="d" * 64,
            source_lineage_hash="e" * 64,
            valid_from=time.time() - 1,
            retracts_event_hash=support["event_hash"],
        )
        projection = project_epistemic_state(list_epistemic_events(self.store, self.repo))
        self.assertEqual(projection["claims"], [])
        self.assertEqual(len(list_epistemic_events(self.store, self.repo)), 2)

    def test_context_compiler_preserves_conflict_and_never_authorizes(self) -> None:
        self._event("support", "b")
        self._event("oppose", "c")
        context = compile_action_sufficient_context(
            list_epistemic_events(self.store, self.repo),
            required_claim_ids=["claim.cache"],
        )
        self.assertEqual(context["state_preservation"], "PASS")
        self.assertEqual(len(context["evidence"]), 2)
        self.assertEqual(context["claims"][0]["truth_state"], "BOTH")
        self.assertFalse(context["action_authorized"])
        self.assertEqual(context["authority_state"], "SEPARATE_CANONICAL_GATE_REQUIRED")

    def test_missing_policy_yields_unknown_and_explicit_policy_controls_debt(self) -> None:
        unknown = update_continuation_debt(
            0.1, uncertainty=1, conflict=0, drift=0, staleness=0,
            verification=0, policy={},
        )
        self.assertEqual(unknown["state"], "UNKNOWN")
        result = update_continuation_debt(
            0.1, uncertainty=0.5, conflict=0.5, drift=0, staleness=0,
            verification=0, policy={
                "rho": 1, "alpha": 0.2, "beta": 0.4, "gamma": 0.1,
                "eta": 0.1, "delta": 0.5, "reanchor": 0.2, "quarantine": 0.8,
            },
        )
        self.assertEqual(result["regime"], "REANCHOR")
        self.assertFalse(result["action_authorized"])

    def test_modern_source_experience_is_structural_not_empirical(self) -> None:
        result = forge_structural_source_experience(self.store, self.repo)
        self.assertEqual(result["state"], "STRUCTURAL_SOURCE_EXPERIENCE_PASS")
        self.assertEqual(result["evidence_class"], "synthetic")
        self.assertFalse(result["empirical"])
        self.assertFalse(result["production_transfer_eligible"])
        self.assertEqual(result["paid_calls_executed"], 0)
        self.assertEqual(result["checks"]["semantic_support"]["state"], "pass")


if __name__ == "__main__":
    unittest.main()
