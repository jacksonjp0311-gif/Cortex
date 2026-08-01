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
            activation={"bootstrap_status": "verified"},
            task="epoch-atomic boundary",
            governor_mode="normal",
            force_close=True,
            reason="constitutional_transition",
        )
        self.assertTrue(result.get("closed"), result)
        latest = latest_frame(self.store, self.repo)
        self.assertEqual((latest or {}).get("body_epoch_id"), epoch.epoch_id, latest)
        self.assertTrue(((latest or {}).get("metrics") or {}).get("epoch_current"), latest)


if __name__ == "__main__":
    unittest.main()
