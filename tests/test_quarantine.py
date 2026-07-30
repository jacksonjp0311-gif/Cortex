from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.quarantine import active_quarantined_ids, quarantine_artifacts, release_quarantine
from cortex.store import Store


class QuarantineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# q\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "QHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_quarantine_release(self) -> None:
        e = quarantine_artifacts(
            self.store, "QHost", ["a1", "a2"], reason="test"
        )
        self.assertIn("a1", active_quarantined_ids(self.store, "QHost"))
        release_quarantine(self.store, "QHost", e["envelope_id"])
        # envelope inactive — ids may still appear if other envelopes; single env
        self.assertNotIn("a1", active_quarantined_ids(self.store, "QHost"))


if __name__ == "__main__":
    unittest.main()
