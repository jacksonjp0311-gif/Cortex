"""v7.3 integration — buffer, close, CLI surfaces."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.config import ensure_home
from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels
from cortex.resonant_frame import (
    append_field_samples,
    field_close,
    field_report,
    frame_trace,
    latest_frame,
    seed_from_activation,
)
from cortex.store import Store


class ResonantIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "DemoRepo"
        host = Path(self.temp.name) / "host"
        host.mkdir()
        self.store.attach(self.repo, "rid-demo", host)

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_buffer_then_close(self) -> None:
        for t in range(5):
            samples = sample_tick_channels(
                repo=self.repo,
                body_epoch_id="e1",
                tick=t,
                activities={f: 0.4 for f in CHANNEL_FAMILIES},
                truth_sources={"E_HOST": "MEASURED", "E_RUNTIME": "MEASURED"},
                paths_by_channel={"E_HOST": ["a.py"], "M_CONSOLIDATED": ["a.py"]},
            )
            r = append_field_samples(self.store, self.repo, samples)
            self.assertTrue(r["ok"])
        # not yet W_max
        self.assertFalse(r.get("closed"))
        closed = field_close(self.store, self.repo)
        self.assertTrue(closed.get("closed"))
        latest = latest_frame(self.store, self.repo)
        self.assertIsNotNone(latest)
        self.assertIn("receipt_hash", latest or {})
        report = field_report(self.store, self.repo)
        self.assertEqual(report["repo"], self.repo)
        self.assertTrue(report["advisory_only"])
        tr = frame_trace(self.store, self.repo, limit=4)
        self.assertGreaterEqual(len(tr), 1)

    def test_w_max_auto_close(self) -> None:
        last = {}
        for t in range(33):
            samples = sample_tick_channels(
                repo=self.repo,
                body_epoch_id="e1",
                tick=t,
                activities={f: 0.3 + 0.01 * (t % 5) for f in CHANNEL_FAMILIES},
            )
            last = append_field_samples(self.store, self.repo, samples)
        self.assertTrue(last.get("closed") or latest_frame(self.store, self.repo))

    def test_activation_boundary_close_preserves_current_epoch(self) -> None:
        from cortex.epoch import ensure_current_epoch

        epoch = ensure_current_epoch(self.store, self.repo, reason="frame_boundary")
        result = seed_from_activation(
            self.store,
            self.repo,
            activation={
                "bootstrap_status": "verified",
                "packet_hash": "receipt_epoch_atomic_boundary",
            },
            task="epoch-atomic boundary",
            governor_mode="normal",
            force_close=True,
            reason="constitutional_transition",
        )
        self.assertTrue(result.get("closed"), result)
        latest = latest_frame(self.store, self.repo)
        self.assertEqual((latest or {}).get("body_epoch_id"), epoch.epoch_id, latest)
        self.assertTrue(((latest or {}).get("metrics") or {}).get("epoch_current"), latest)

    def test_activation_observations_accrue_exactly_once_to_w_min(self) -> None:
        from cortex.epoch import ensure_current_epoch

        epoch = ensure_current_epoch(self.store, self.repo, reason="temporal_accrual")
        first = seed_from_activation(
            self.store,
            self.repo,
            activation={
                "bootstrap_status": "verified",
                "context": {
                    "stream": {
                        "chain_tip": "frm_0",
                        "recent_frames": [{"frame_id": "frm_0", "at": 100.0}],
                    }
                },
            },
            task="observe runtime event",
            governor_mode="normal",
            reason="activation_observation",
        )
        self.assertEqual(first.get("buffer_ticks"), 1, first)
        duplicate = seed_from_activation(
            self.store,
            self.repo,
            activation={
                "bootstrap_status": "verified",
                "context": {"stream": {"chain_tip": "frm_0"}},
            },
            task="observe runtime event",
            governor_mode="normal",
            reason="activation_observation",
        )
        self.assertTrue(duplicate.get("skipped"), duplicate)
        self.assertEqual(duplicate.get("reason"), "duplicate_observation")
        self.assertEqual(duplicate.get("buffer_ticks"), 1, duplicate)

        result = first
        for tick in range(1, 8):
            result = seed_from_activation(
                self.store,
                self.repo,
                activation={
                    "bootstrap_status": "verified",
                    "context": {
                        "stream": {
                            "chain_tip": f"frm_{tick}",
                            "recent_frames": [
                                {"frame_id": f"frm_{tick}", "at": 100.0 + tick}
                            ],
                        }
                    },
                },
                task="observe runtime event",
                governor_mode="normal",
                reason="activation_observation",
            )
        self.assertTrue(result.get("closed"), result)
        self.assertEqual(result.get("reason"), "temporal_window_ready", result)
        latest = latest_frame(self.store, self.repo)
        self.assertEqual((latest or {}).get("body_epoch_id"), epoch.epoch_id, latest)
        self.assertEqual(((latest or {}).get("metrics") or {}).get("tick_count"), 8, latest)
        state = self.store.get_setting(f"field_state:{self.repo}", {}) or {}
        self.assertEqual(
            set(state.get("activation_observation_ids") or []),
            {f"frm_{tick}" for tick in range(8)},
        )


if __name__ == "__main__":
    unittest.main()
