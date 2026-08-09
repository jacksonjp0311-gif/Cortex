"""v7.1 diagnostics must not create or seal epochs."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.continuity import continuity_report, snapshot_continuity
from cortex.epoch import ensure_current_epoch, observe_current_epoch
from cortex.interconnect import mesh_status
from cortex.phases import current_phase
from cortex.store import Store


def _epoch_fingerprint(store: Store, repo: str) -> dict:
    rows = store.db.execute(
        "SELECT epoch_id, receipt_hash FROM body_epochs WHERE repo=? ORDER BY epoch_id",
        (repo,),
    ).fetchall()
    phase = store.db.execute(
        "SELECT phase, epoch_id, receipt_hash FROM runtime_phase_state WHERE repo=?",
        (repo,),
    ).fetchone()
    material = {
        "epochs": [dict(r) for r in rows],
        "phase": dict(phase) if phase else None,
        "count": len(rows),
    }
    h = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {"hash": h, "count": len(rows), "ids": [r["epoch_id"] for r in rows], "phase": material["phase"]}


class ObservationNonmutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# obs\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "ObsHost")
        # One explicit seal (mutation path)
        ensure_current_epoch(self.store, "ObsHost", reason="setup")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_diagnostics_do_not_create_epochs(self) -> None:
        before = _epoch_fingerprint(self.store, "ObsHost")
        binding_before = self.store.get_setting("binding_field_latest:ObsHost", None)
        for _ in range(3):
            observe_current_epoch(self.store, "ObsHost")
            continuity_report(self.store, "ObsHost")
            snapshot_continuity(self.store, "ObsHost")
            mesh_status(self.store, "ObsHost")
            current_phase(self.store, "ObsHost")  # observe-only default
        after = _epoch_fingerprint(self.store, "ObsHost")
        self.assertEqual(before["count"], after["count"])
        self.assertEqual(before["ids"], after["ids"])
        self.assertEqual(before["hash"], after["hash"])
        self.assertEqual(before["phase"], after["phase"])
        self.assertEqual(
            self.store.get_setting("binding_field_latest:ObsHost", None),
            binding_before,
        )


if __name__ == "__main__":
    unittest.main()
