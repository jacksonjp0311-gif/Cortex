"""v8.0 measured self-model, workspace, autobiography, and lesions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cortex.cognitive.autobiography import append_episode, verify_autobiography
from cortex.cognitive.counterfactual import simulate_counterfactuals
from cortex.cognitive.lesion import run_lesion_benchmarks
from cortex.cognitive.measured import (
    METRICS,
    capture_measured_state,
    delta_field_samples,
    measured_delta,
)
from cortex.cognitive.model import calibration_report, predict_next_delta, score_and_update
from cortex.cognitive.workspace import CAPACITY, compete_and_broadcast
from cortex.connect_pass import DECAY_EVERY, persist_connect_pass
from cortex.config import ensure_home
from cortex.store import Store


class CognitiveV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "CognitiveHost"
        host = Path(self.temp.name) / "host"
        host.mkdir()
        self.store.attach(self.repo, "rid-cognitive", host)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _delta(self, value: float = 0.1, event: str = "e1") -> dict:
        before = {"state_hash": "before", "values": {name: 0.0 for name in METRICS}}
        after = {
            "state_hash": "after",
            "values": {
                name: value * METRICS[name][2] for name in METRICS
            },
        }
        return measured_delta(before, after, event_id=event)

    def test_measured_delta_and_field_provenance(self) -> None:
        before = capture_measured_state(self.store, self.repo)
        self.store.db.execute(
            "INSERT INTO sessions(session_id, repo, task, started_at, status) VALUES(?,?,?,?,?)",
            ("s1", self.repo, "t", 1.0, "active"),
        )
        self.store.db.commit()
        after = capture_measured_state(self.store, self.repo)
        report = measured_delta(before, after, event_id="event-1")
        self.assertEqual(report["delta"]["sessions"], 1.0)
        samples = delta_field_samples(
            report, repo=self.repo, body_epoch_id="ep", tick=1
        )
        self.assertEqual(len(samples), 11)
        self.assertTrue(all(s.metadata["measurement_basis"] == "measured_delta" for s in samples))
        self.assertTrue(all(s.metadata["baseline_eligible"] for s in samples))

    def test_prediction_is_scored_before_learning(self) -> None:
        forecast = predict_next_delta(self.store, self.repo, action="activation")
        score = score_and_update(self.store, self.repo, forecast, self._delta())
        self.assertEqual(forecast["model_n"], 0)
        self.assertEqual(score["model_n_after"], 1)
        next_forecast = predict_next_delta(self.store, self.repo, action="activation")
        self.assertAlmostEqual(
            next_forecast["predicted_normalized_delta"]["sessions"], 0.1
        )

    def test_calibration_requires_samples_and_empirical_fit(self) -> None:
        well_fit = [
            {"confidence": 1.0, "accurate": True}
            for _ in range(16)
        ]
        badly_fit = [
            {"confidence": 1.0, "accurate": False}
            for _ in range(16)
        ]
        self.assertTrue(calibration_report(well_fit)["calibrated"])
        bad = calibration_report(badly_fit)
        self.assertTrue(bad["data_ready"])
        self.assertFalse(bad["calibrated"])

    def test_counterfactuals_do_not_mutate(self) -> None:
        forecast = predict_next_delta(self.store, self.repo, action="activation")
        before = capture_measured_state(self.store, self.repo)["state_hash"]
        report = simulate_counterfactuals(forecast)
        after = capture_measured_state(self.store, self.repo)["state_hash"]
        self.assertEqual(before, after)
        self.assertEqual(len(report["simulations"]), 3)
        self.assertTrue(all(s["simulated_not_observed"] for s in report["simulations"]))

    def test_workspace_is_capacity_bounded(self) -> None:
        workspace = compete_and_broadcast(
            self.store,
            self.repo,
            measured=self._delta(),
            prediction_score={"normalized_mae": 0.4},
            self_sensing={"classification": "DRIFT", "residual_r": 3.0},
            frame={"classification": "TRANSITION", "measurement_basis": "measured_delta"},
            epoch_delta={"material_change": True, "changed_roots": ["adaptive_root_hash"]},
        )
        self.assertEqual(len(workspace["selected"]), CAPACITY)
        self.assertEqual(len(workspace["suppressed"]), 1)

    def test_autobiography_hash_chain_detects_tamper(self) -> None:
        workspace = {"broadcast_hash": "b", "selected": [{"signal_id": "x"}]}
        for index in range(2):
            append_episode(
                self.store,
                self.repo,
                task=f"task-{index}",
                body_epoch_id="ep",
                measured=self._delta(event=f"e{index}"),
                prediction_score={"forecast_id": f"f{index}", "normalized_mae": 0.1},
                workspace=workspace,
                self_sensing={"classification": "NOMINAL"},
            )
        self.assertTrue(verify_autobiography(self.store, self.repo)["chain_valid"])
        episodes = self.store.get_setting(f"operational_autobiography:{self.repo}", [])
        episodes[0]["changed_metrics"] = ["tampered"]
        self.store.set_setting(f"operational_autobiography:{self.repo}", episodes)
        self.assertFalse(verify_autobiography(self.store, self.repo)["chain_valid"])

    def test_lesion_benchmark_detects_predictive_dependence(self) -> None:
        for index in range(9):
            forecast = predict_next_delta(self.store, self.repo, action="activation")
            score_and_update(self.store, self.repo, forecast, self._delta(event=f"m{index}"))
        compete_and_broadcast(
            self.store,
            self.repo,
            measured=self._delta(),
            prediction_score={"normalized_mae": 0.01},
            self_sensing={"classification": "NOMINAL", "residual_r": 0.1},
            frame={"classification": "QUIESCENT", "measurement_basis": "measured_delta"},
            epoch_delta={"material_change": False},
        )
        report = run_lesion_benchmarks(self.store, self.repo)
        self.assertTrue(report["tests"]["predictive_self_model"]["data_ready"])
        self.assertTrue(report["tests"]["predictive_self_model"]["functional_dependence_observed"])

    def test_maintenance_cadence_leaves_a_reachable_field_window(self) -> None:
        metrics = {
            "repo": self.repo,
            "pass_id": "p",
            "session_id": None,
            "surface": "breathe",
            "immune": {},
            "surprise": {},
            "neural": {},
            "aria": {},
            "evidence": {},
            "thalamus": {},
        }
        with patch("cortex.prune.decay_unused_weights") as decay:
            for index in range(1, DECAY_EVERY + 1):
                metrics["pass_id"] = f"p{index}"
                persist_connect_pass(
                    self.store,
                    self.repo,
                    metrics,
                    auto_distill=False,
                    causal_every=0,
                )
                if index < DECAY_EVERY:
                    decay.assert_not_called()
            decay.assert_called_once_with(self.store, self.repo, factor=0.98)
        self.assertGreaterEqual(DECAY_EVERY - 1, 8)


if __name__ == "__main__":
    unittest.main()
