from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.lineage import record_artifact
from cortex.store import Store
from cortex.unlearning import apply_unlearning, plan_unlearning, rollback_repair


class UnlearningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# u\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "UHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_plan_and_apply_authorize(self) -> None:
        record_artifact(
            self.store,
            "UHost",
            artifact_id="syn_x",
            artifact_type="invented_synapse",
            parent_ids=["mem:1"],
            origin_memory_ids=["1"],
        )
        plan = plan_unlearning(
            self.store, "UHost", wound_id="mw_test", origin_ids=["syn_x"]
        )
        self.assertIn("plan_id", plan)
        denied = apply_unlearning(self.store, "UHost", plan["plan_id"], authorize=False)
        self.assertFalse(denied.get("ok"))
        ok = apply_unlearning(
            self.store, "UHost", plan["plan_id"], authorize=True, governance_mode="normal"
        )
        self.assertTrue(ok.get("ok"))
        self.assertIn("snapshot_id", ok)
        rb = rollback_repair(self.store, "UHost", ok["snapshot_id"])
        self.assertTrue(rb.get("ok"))


if __name__ == "__main__":
    unittest.main()
