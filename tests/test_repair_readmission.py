from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.immunity import open_wound, plan_repair, readmit, verify_repair
from cortex.lineage import record_artifact
from cortex.store import Store
from cortex.unlearning import apply_unlearning


class RepairReadmitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# rr\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "RRHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_verify_and_readmit(self) -> None:
        record_artifact(
            self.store,
            "RRHost",
            artifact_id="syn_z",
            artifact_type="invented_synapse",
            origin_memory_ids=["2"],
            parent_ids=["mem:2"],
        )
        w = open_wound(
            self.store,
            "RRHost",
            kind="test",
            origin_ids=["syn_z"],
            summary="t",
        )
        plan = plan_repair(self.store, "RRHost", w["wound_id"])
        rep = apply_unlearning(
            self.store,
            "RRHost",
            plan["plan_id"],
            authorize=True,
            governance_mode="normal",
        )
        v = verify_repair(self.store, "RRHost", rep["repair_id"])
        self.assertIn("readmit_allowed", v)
        ra = readmit(
            self.store, "RRHost", rep["repair_id"], authorize=True, verify_result=v
        )
        self.assertIn("readmitted", ra)


if __name__ == "__main__":
    unittest.main()
