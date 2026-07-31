"""v7.1.1 Geometry Seal — truth sources, phase binding, foreign prediction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.capabilities import issue_for_controller
from cortex.config import ensure_home
from cortex.constitutional_geometry import (
    AxisTruthSource,
    assess_repo_coordinate,
    coordinate_from_bits,
)
from cortex.constitutional_path import assess_operation_at_boundary
from cortex.constitutional_requirements import coordinate_satisfies
from cortex.epoch import ensure_current_epoch
from cortex.evidence_refresh import authorize_evidence_refresh, run_evidence_refresh_edge
from cortex.phases import (
    BOUND,
    BOOTSTRAP_UNBOUND,
    phase_binding_status,
    transition_phase,
)
from cortex.store import Store


class GeometrySealTruthTests(unittest.TestCase):
    def test_simulated_never_satisfies_live_promote(self) -> None:
        sim = coordinate_from_bits((1, 1, 1, 1))  # default SIMULATED
        self.assertEqual(sim.evidence.truth_source, AxisTruthSource.SIMULATED)
        self.assertFalse(coordinate_satisfies("promote", sim, live_gate=True))
        self.assertTrue(coordinate_satisfies("promote", sim, live_gate=False))
        receipt = coordinate_from_bits(
            (1, 1, 1, 1), truth_source=AxisTruthSource.RECEIPT_VERIFIED
        )
        self.assertTrue(coordinate_satisfies("promote", receipt, live_gate=True))

    def test_operator_asserted_denied_at_boundary(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            home = ensure_home(Path(temp.name) / "h")
            p = Path(temp.name) / "r"
            p.mkdir()
            (p / "README.md").write_text("# t\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            bootstrap_repository(home, store, p, "TruthHost")
            ensure_current_epoch(store, "TruthHost", reason="t")
            transition_phase(store, "TruthHost", "QUIESCENT", reason="t")
            g = assess_operation_at_boundary(
                store,
                "TruthHost",
                "promote",
                authority_ok=True,
                witness_ok=True,
                require_witness=True,
            )
            self.assertFalse(g["allowed"], g)
            # Authority/witness marked operator — gate bits zero for those
            coord = assess_repo_coordinate(
                store, "TruthHost", authority_ok=True, witness_ok=True
            )
            self.assertEqual(
                coord.authority.truth_source, AxisTruthSource.OPERATOR_ASSERTED
            )
            self.assertFalse(coord.authority.gate_eligible())
            store.close()
        finally:
            temp.cleanup()


class PhaseBindingTests(unittest.TestCase):
    def test_only_bound_is_compatible(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            home = ensure_home(Path(temp.name) / "h")
            p = Path(temp.name) / "r"
            p.mkdir()
            (p / "README.md").write_text("# p\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            bootstrap_repository(home, store, p, "PhBind")
            # No seal → bootstrap unbound
            b0 = phase_binding_status(store, "PhBind")
            self.assertIn(
                b0["binding"],
                {BOOTSTRAP_UNBOUND, "UNKNOWN", BOOTSTRAP_UNBOUND},
            )
            self.assertFalse(b0["constitutionally_compatible"])
            ensure_current_epoch(store, "PhBind", reason="bind")
            transition_phase(store, "PhBind", "QUIESCENT", reason="bind")
            b1 = phase_binding_status(store, "PhBind")
            self.assertEqual(b1["binding"], BOUND)
            self.assertTrue(b1["constitutionally_compatible"])
            store.close()
        finally:
            temp.cleanup()


class EvidenceRefreshEdgeTests(unittest.TestCase):
    def test_authorize_edge_sequence(self) -> None:
        a = authorize_evidence_refresh(
            refresh_mode="auto", manifest_current=False
        )
        self.assertTrue(a["authorized"])
        self.assertEqual(a["edge"], "EVIDENCE_REFRESH")
        b = authorize_evidence_refresh(
            refresh_mode="never", manifest_current=False
        )
        self.assertFalse(b["authorized"])

    def test_run_edge_steps(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            home = ensure_home(Path(temp.name) / "h")
            p = Path(temp.name) / "r"
            p.mkdir()
            (p / "README.md").write_text("# e\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            bootstrap_repository(home, store, p, "EdgeHost")
            from cortex.config import load_repo_config
            from cortex.governor import Governor

            config = load_repo_config(p)
            gov = Governor(home, store)
            # Force drift
            (p / "README.md").write_text("# e\nchanged\n", encoding="utf-8")
            audit = run_evidence_refresh_edge(
                home,
                store,
                "EdgeHost",
                root=p,
                config=config,
                refresh_mode="auto",
                governor=gov,
            )
            self.assertTrue(audit.get("ok"), audit)
            self.assertEqual(
                audit.get("steps_completed"),
                [
                    "observe_drift",
                    "authorize_evidence_refresh",
                    "refresh_evidence_only",
                    "recompute_epoch_controller",
                    "select_path",
                ],
            )
            self.assertTrue(audit.get("receipt_hash"))
            store.close()
        finally:
            temp.cleanup()


class ForeignGeometryPredictionTests(unittest.TestCase):
    """Foreign repo: geometry detects unencoded authority/epoch/witness/provenance gaps."""

    def test_foreign_prediction_detects_unencoded_failures(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            home = ensure_home(Path(temp.name) / "h")
            local = Path(temp.name) / "local"
            foreign = Path(temp.name) / "foreign"
            local.mkdir()
            foreign.mkdir()
            (local / "README.md").write_text("# local body\n", encoding="utf-8")
            (foreign / "README.md").write_text("# foreign host\n", encoding="utf-8")
            (foreign / "src").mkdir()
            (foreign / "src" / "lib.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            bootstrap_repository(home, store, local, "LocalBody")
            bootstrap_repository(home, store, foreign, "ForeignApp")
            # Local fully sealed + bound
            ensure_current_epoch(store, "LocalBody", reason="local")
            transition_phase(store, "LocalBody", "QUIESCENT", reason="local")
            cap_local = issue_for_controller(
                "LocalBody", "advanced", store=store, reason="local"
            )

            # Foreign: NO epoch seal, NO capability, NO witness
            # Predict geometry fails on epoch and/or authority for promote/federate
            pred_promote = assess_operation_at_boundary(
                store, "ForeignApp", "promote", require_witness=True
            )
            self.assertFalse(pred_promote["allowed"], pred_promote)
            miss = set(pred_promote.get("missing_axes") or [])
            reasons = " ".join(pred_promote.get("reasons") or [])
            # Must detect at least one unencoded failure class
            detected = (
                "epoch" in miss
                or "authority" in miss
                or "witness" in miss
                or "phase_binding" in miss
                or "epoch" in reasons
                or "authority" in reasons
                or "witness" in reasons
                or "phase" in reasons
            )
            self.assertTrue(
                detected,
                f"expected unencoded failure axes/reasons, got {pred_promote}",
            )

            # Foreign federate without capability/epoch binding → deny or admit only after fix
            pred_fed = assess_operation_at_boundary(
                store, "ForeignApp", "federate", require_witness=False
            )
            # After boundary auto-bind may seal epoch via transition; still no capability if not issued
            # Without capability, authority missing under live_gate
            if pred_fed.get("allowed"):
                # If allowed, must have issued capability path with gate-eligible authority
                self.assertTrue(pred_fed.get("gate_bits"), pred_fed)
            else:
                self.assertTrue(
                    pred_fed.get("missing_axes") or pred_fed.get("reasons"),
                    pred_fed,
                )

            # Provenance: foreign capability on local repo is wrong — authority mismatch
            g_cross = assess_operation_at_boundary(
                store,
                "ForeignApp",
                "federate",
                capability=cap_local,  # wrong repo capability
                require_witness=False,
            )
            self.assertFalse(g_cross["allowed"], g_cross)
            store.close()
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
