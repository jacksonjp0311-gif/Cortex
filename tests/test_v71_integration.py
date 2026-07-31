"""v7.1 boundary integration — promote, repair_readmit, federate (geometry seal)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.capabilities import issue_for_controller
from cortex.config import ensure_home
from cortex.constitutional_path import assess_operation_at_boundary
from cortex.epoch import ensure_current_epoch
from cortex.federation import federated_query
from cortex.immunity import open_wound, plan_repair, readmit, verify_repair
from cortex.lineage import record_artifact
from cortex.phases import transition_phase
from cortex.promote_gate import evaluate_promotion
from cortex.store import Store
from cortex.unlearning import apply_unlearning
from cortex.witness import commit_manifest


class V71IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# v71\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "V71Host")
        ensure_current_epoch(self.store, "V71Host", reason="setup")
        transition_phase(
            self.store, "V71Host", "QUIESCENT", reason="setup_bind"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_promotion_boundary_uses_geometry(self) -> None:
        # Operator-asserted authority must not open promote
        g_bad = assess_operation_at_boundary(
            self.store,
            "V71Host",
            "promote",
            authority_ok=True,
            witness_ok=True,
            require_witness=True,
        )
        self.assertFalse(g_bad["allowed"], g_bad)
        self.assertTrue(
            g_bad.get("truth_ineligible_axes")
            or any("truth" in r for r in (g_bad.get("reasons") or []))
            or g_bad.get("missing_axes"),
            g_bad,
        )

        # Without capability / witness receipts — deny
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {"baseline_is_winner": True},
                "ablations": {"baseline": {"recall_at_k": 0.9}},
                "repo": "V71Host",
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            store=self.store,
            repo="V71Host",
            require_witness=True,
            witness_report=None,
        )
        self.assertFalse(r.get("allow_promote"))
        self.assertIn("geometry", r)

        # Real capability + witness commitment (RECEIPT_VERIFIED)
        cap = issue_for_controller(
            "V71Host", "advanced", store=self.store, reason="promote_test"
        )
        commit_manifest(
            [
                {
                    "id": "prom_w1",
                    "query": "README",
                    "expected_substrings": ["README"],
                }
            ],
            store=self.store,
            evaluator_identity="promote_test",
        )
        g = assess_operation_at_boundary(
            self.store,
            "V71Host",
            "promote",
            capability=cap,
            require_witness=True,
        )
        self.assertTrue(g["allowed"], g)
        r2 = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {"baseline_is_winner": True},
                "ablations": {"baseline": {"recall_at_k": 0.9}},
                "repo": "V71Host",
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            store=self.store,
            repo="V71Host",
            capability=cap,
            witness_report={"recall_at_k": 0.9},
            require_witness=True,
        )
        self.assertTrue(r2.get("allow_promote"), r2)

    def test_repair_readmission_uses_geometry(self) -> None:
        record_artifact(
            self.store,
            "V71Host",
            artifact_id="syn_v71",
            artifact_type="invented_synapse",
            origin_memory_ids=["2"],
            parent_ids=["mem:2"],
        )
        w = open_wound(
            self.store, "V71Host", kind="test", origin_ids=["syn_v71"], summary="t"
        )
        plan = plan_repair(self.store, "V71Host", w["wound_id"])
        rep = apply_unlearning(
            self.store,
            "V71Host",
            plan["plan_id"],
            authorize=True,
            governance_mode="normal",
        )
        v = verify_repair(self.store, "V71Host", rep["repair_id"])
        ra = readmit(
            self.store, "V71Host", rep["repair_id"], authorize=True, verify_result=v
        )
        if not ra.get("readmitted"):
            self.assertIn(
                ra.get("error"),
                {
                    "constitutional_geometry_denied",
                    "verify_failed",
                },
            )
            if ra.get("error") == "constitutional_geometry_denied":
                self.assertIn("required_legal_path", ra)
                self.assertIn("coordinate", ra)
        else:
            self.assertTrue(ra.get("readmitted") or ra.get("ok"))

    def test_federation_admission_uses_geometry(self) -> None:
        out = federated_query(self.store, "readme", repositories=["V71Host"])
        self.assertIn(
            out.get("protocol"), {"cortex-federation/1.0", "cortex-federation/1.1"}
        )
        self.assertIn("geometry", out)
        if out.get("error") == "constitutional_geometry_denied":
            self.assertTrue(out.get("admission_denied"))
            self.assertTrue(out.get("geometry"))
        else:
            self.assertIn("hits", out)
            g = out["geometry"]["V71Host"]
            self.assertTrue(g.get("allowed"), g)


if __name__ == "__main__":
    unittest.main()
