"""v7.5 Self-Sensing Field — observer only, no false healthy when unbound."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from cortex.config import ensure_home
from cortex.epoch import seal_epoch_transition
from cortex.self_sensing import (
    SelfSenseClass,
    classify_self_sense,
    geometric_mean,
    observe_self_sensing,
    residual_mahalanobis,
    update_baseline,
    verify_observation_replay,
)
from cortex.store import Store


class SelfSensingMathTests(unittest.TestCase):
    def test_geometric_mean(self) -> None:
        g = geometric_mean([1.0, 1.0, 1.0])
        self.assertAlmostEqual(g or 0, 1.0, places=5)
        g2 = geometric_mean([0.25, 1.0])
        self.assertAlmostEqual(g2 or 0, 0.5, places=5)

    def test_residual_zero_at_mean(self) -> None:
        z = [0.5] * 13
        mu = [0.5] * 13
        var = [0.1] * 13
        r = residual_mahalanobis(z, mu, var)
        self.assertAlmostEqual(r, 0.0, places=6)

    def test_residual_can_exclude_unknown_axes(self) -> None:
        z = [1.0] * 13
        mu = [0.0] * 13
        var = [0.01] * 13
        full = residual_mahalanobis(z, mu, var)
        partial = residual_mahalanobis(z, mu, var, valid_indices=[0, 1])
        self.assertIsNotNone(partial)
        self.assertLess(partial or 0.0, full or 0.0)

    def test_baseline_ema(self) -> None:
        st: dict = {}
        st = update_baseline(st, [1.0] * 13, alpha=0.5)
        # first sample seeds μ = z
        self.assertAlmostEqual(st["mu"][0], 1.0, places=5)
        st = update_baseline(st, [0.0] * 13, alpha=0.5)
        self.assertEqual(st["n_updates"], 2)
        # μ ← 0.5*1 + 0.5*0 = 0.5
        self.assertAlmostEqual(st["mu"][0], 0.5, places=5)


class SelfSensingClassTests(unittest.TestCase):
    def test_unbound_never_nominal(self) -> None:
        c, reasons = classify_self_sense(
            gates={
                "baseline_warm": True,
                "epoch_current": False,
                "phase_bound": False,
            },
            residual=0.1,
            f_t=0.9,
            missing=[],
            baseline_n=20,
        )
        self.assertEqual(c, SelfSenseClass.UNBOUND.value)
        self.assertTrue(any("unbound" in r for r in reasons))

    def test_cold_when_baseline_short(self) -> None:
        c, _ = classify_self_sense(
            gates={
                "baseline_warm": False,
                "epoch_current": True,
                "phase_bound": True,
            },
            residual=0.1,
            f_t=0.9,
            missing=[],
            baseline_n=3,
        )
        self.assertEqual(c, SelfSenseClass.COLD.value)

    def test_nominal_when_warm_and_stable(self) -> None:
        c, _ = classify_self_sense(
            gates={
                "baseline_warm": True,
                "epoch_current": True,
                "phase_bound": True,
            },
            residual=0.5,
            f_t=0.7,
            missing=[],
            baseline_n=16,
        )
        self.assertEqual(c, SelfSenseClass.NOMINAL.value)


class SelfSensingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        self.host = Path(self.temp.name) / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# sense\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "SenseHost"
        self.store.attach(self.repo, "rid-sense", self.host)
        try:
            from cortex.bootstrap import bootstrap_repository

            bootstrap_repository(
                self.home, self.store, self.host, self.repo, external=True
            )
        except Exception:
            pass

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_observe_advisory_only(self) -> None:
        r = observe_self_sensing(self.store, self.repo, home=self.home, update=True)
        self.assertTrue(r["advisory_only"])
        self.assertIn(r["classification"], {e.value for e in SelfSenseClass})
        self.assertIn("residual_r", r)
        self.assertIn("z_vector", r)
        self.assertEqual(len(r["z_vector"]), 13)

    def test_sqlite_row_bootstrap_status_warms_observer(self) -> None:
        from cortex.epoch import ensure_current_epoch
        from cortex.phases import transition_phase

        ensure_current_epoch(self.store, self.repo, reason="sense_row_test")
        transition_phase(self.store, self.repo, "QUIESCENT", reason="sense_row_test")
        r = observe_self_sensing(self.store, self.repo, home=self.home, update=True)
        self.assertTrue((r.get("gates") or {}).get("evidence_valid"), r)
        self.assertTrue(r.get("baseline_updated"), r)
        self.assertEqual(r.get("baseline_n_updates"), 1, r)

    def test_no_host_writes(self) -> None:
        before = list(self.host.rglob("*"))
        observe_self_sensing(self.store, self.repo, home=self.home)
        after = list(self.host.rglob("*"))
        self.assertEqual(len(before), len(after))

    def test_replay_stable(self) -> None:
        # seal if possible so gates more stable
        try:
            seal_epoch_transition(self.store, self.repo, reason="sense_test")
        except Exception:
            pass
        v = verify_observation_replay(self.store, self.repo, home=self.home)
        self.assertTrue(v.get("stable_across_replay"), v)

    def test_unbound_forced_if_not_verified(self) -> None:
        # without seal, often UNBOUND or COLD — never NOMINAL falsely if unbound logic holds
        r = observe_self_sensing(
            self.store, self.repo, home=self.home, update=False, persist=False
        )
        if not (r.get("gates") or {}).get("epoch_current"):
            self.assertNotEqual(r["classification"], SelfSenseClass.NOMINAL.value)

    def test_anomaly_is_classified_before_and_excluded_from_baseline(self) -> None:
        self.store.set_setting(
            f"self_sense_state:{self.repo}",
            {"mu": [0.0] * 13, "var": [0.01] * 13, "n_updates": 16},
        )
        sample = {
            "z": {k: 1.0 for k in ("C", "N", "I", "L", "D", "H", "G", "Q", "eta_E", "eta_M", "T", "delta_E", "U")},
            "z_vector": [1.0] * 13,
            "missing_components": [],
            "F_t": 0.8,
            "F_spec_literal": 0.8,
            "gates": {"baseline_warm": True, "epoch_current": True, "phase_bound": True, "evidence_valid": True},
            "frame_classification": "QUIESCENT",
            "frame_baseline_eligible": True,
            "frame_policy_eligible": True,
            "frame_measurement_basis": "direct_snapshot",
            "sampled_at": 1.0,
        }
        with patch("cortex.self_sensing.sample_observer_state", return_value=sample):
            report = observe_self_sensing(
                self.store, self.repo, update=True, persist=False
            )
        self.assertEqual(report["classification"], SelfSenseClass.STRESSED.value)
        self.assertFalse(report["baseline_updated"])
        self.assertEqual(report["baseline_reference_n"], 16)
        self.assertTrue(report["classified_before_update"])

    def test_modeled_frame_never_updates_baseline(self) -> None:
        sample = {
            "z": {k: 0.5 for k in ("C", "N", "I", "L", "D", "H", "G", "Q", "eta_E", "eta_M", "T", "delta_E", "U")},
            "z_vector": [0.5] * 13,
            "missing_components": [], "F_t": 0.8, "F_spec_literal": 0.8,
            "gates": {"baseline_warm": False, "epoch_current": True, "phase_bound": True, "evidence_valid": True},
            "frame_classification": "INDETERMINATE",
            "frame_baseline_eligible": False,
            "frame_policy_eligible": False,
            "frame_measurement_basis": "modeled_salience",
            "sampled_at": 1.0,
        }
        with patch("cortex.self_sensing.sample_observer_state", return_value=sample):
            report = observe_self_sensing(
                self.store, self.repo, update=True, persist=False
            )
        self.assertFalse(report["baseline_updated"])
        self.assertIn(
            "measurement_not_baseline_eligible",
            report["baseline_update_decision"]["reasons"],
        )


if __name__ == "__main__":
    unittest.main()
