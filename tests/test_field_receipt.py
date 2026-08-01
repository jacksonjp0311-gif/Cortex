"""v7.3 frame receipts — integrity independent of classification."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.config import ensure_home
from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels
from cortex.field_receipt import issue_frame_receipt, verify_frame_receipt
from cortex.resonant_frame import close_resonant_frame, persist_closed_frame
from cortex.store import Store


class FieldReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "R"
        self.store.attach(self.repo, "rid", Path(self.temp.name) / "host")

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def _frame(self, classification_force: str | None = None):
        samples = []
        for t in range(10):
            samples.extend(
                sample_tick_channels(
                    repo=self.repo,
                    body_epoch_id="e1",
                    tick=t,
                    activities={f: 0.05 for f in CHANNEL_FAMILIES},
                )
            )
        fr = close_resonant_frame(samples, repo=self.repo, body_epoch_id="e1")
        return fr

    def test_hash_covers_panel_metrics_policy(self) -> None:
        fr = self._frame()
        rec = issue_frame_receipt(fr)
        self.assertIn("receipt_hash", rec)
        self.assertEqual(rec["schema_version"], "cortex-field-receipt/1.0")
        self.assertIn("channel_truth_panel", rec)
        self.assertIn("metrics", rec)
        self.assertIn("policy", rec)
        self.assertFalse(rec["authority_satisfying"])
        self.assertFalse(rec["witness_satisfying"])
        # tamper
        bad = dict(rec)
        bad["classification"] = "COHERENT_DIFFERENTIATED"
        material = {k: v for k, v in bad.items() if k != "receipt_hash"}
        import hashlib
        import json

        h = hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertNotEqual(h, rec["receipt_hash"])

    def test_stale_echo_still_integrity_ok(self) -> None:
        fr = self._frame()
        # force classification in receipt path via object mutate is hard (frozen fields)
        rec = issue_frame_receipt(fr)
        rec2 = dict(rec)
        rec2["classification"] = "STALE_ECHO"
        # re-hash properly for a valid STALE receipt
        material = {k: v for k, v in rec2.items() if k != "receipt_hash"}
        import hashlib
        import json

        rec2["receipt_hash"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        self.store.set_setting(f"field_frame_latest:{self.repo}", rec2)
        v = verify_frame_receipt(self.store, self.repo, rec2)
        self.assertTrue(v["integrity_ok"])

    def test_persist_and_verify(self) -> None:
        fr = self._frame()
        persist_closed_frame(self.store, self.repo, fr)
        v = verify_frame_receipt(self.store, self.repo)
        self.assertTrue(v["integrity_ok"])


if __name__ == "__main__":
    unittest.main()
