"""v7.3 nonmutation — field layer never seals epoch, mutates host, or grants axes."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

import cortex.resonant_frame as rf
from cortex.config import ensure_home
from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels
from cortex.resonant_frame import append_field_samples, cleanup_field_data, field_close
from cortex.store import Store


class NonmutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.host = Path(self.temp.name) / "hostproj"
        self.host.mkdir()
        (self.host / "README.md").write_text("hi\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "HostProj"
        self.store.attach(self.repo, "rid", self.host)

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_source_no_ensure_current_epoch(self) -> None:
        src = inspect.getsource(rf)
        # observation only in field path
        self.assertNotIn("ensure_current_epoch(", src)
        self.assertIn("observe_current_epoch", src)

    def test_no_host_mutation(self) -> None:
        before = list(self.host.rglob("*"))
        for t in range(8):
            samples = sample_tick_channels(
                repo=self.repo,
                body_epoch_id="e",
                tick=t,
                activities={f: 0.5 for f in CHANNEL_FAMILIES},
            )
            append_field_samples(self.store, self.repo, samples)
        field_close(self.store, self.repo)
        after = list(self.host.rglob("*"))
        self.assertEqual(len(before), len(after))
        self.assertFalse((self.host / ".cortex").exists())

    def test_cleanup_dry_run_safe(self) -> None:
        r = cleanup_field_data(self.store, self.repo, dry_run=True)
        self.assertTrue(r["dry_run"])
        self.assertEqual(r["removed"], [])
        # host reg intact
        self.assertIsNotNone(self.store.repo(self.repo))

    def test_policy_never_authority(self) -> None:
        from cortex.field_policy import policy_for_classification

        p = policy_for_classification("COHERENT_DIFFERENTIATED")
        self.assertTrue(p.advisory_only)
        from cortex.field_receipt import issue_frame_receipt
        from cortex.resonant_frame import close_resonant_frame

        samples = []
        for t in range(8):
            samples.extend(
                sample_tick_channels(
                    repo=self.repo,
                    body_epoch_id="e",
                    tick=t,
                    activities={f: 0.4 for f in CHANNEL_FAMILIES},
                )
            )
        fr = close_resonant_frame(samples, repo=self.repo, body_epoch_id="e")
        rec = issue_frame_receipt(fr)
        self.assertFalse(rec["authority_satisfying"])
        self.assertFalse(rec["evidence_satisfying"])
        self.assertFalse(rec["epoch_satisfying"])
        self.assertFalse(rec["witness_satisfying"])


if __name__ == "__main__":
    unittest.main()
