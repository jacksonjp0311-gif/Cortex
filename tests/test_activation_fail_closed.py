"""v6.25.1 activation fail-closed + sterile baseline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cortex.activation import activate_repository, resolve_activation_controller
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.store import Store


class ActivationFailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "afc"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# AFC\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "AFCHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_force_evidence_baseline_sterile(self) -> None:
        called = {"index": False, "connect": False, "invent": False}

        def boom_index(*a, **k):
            called["index"] = True
            raise AssertionError("index_repository must not run on baseline")

        def boom_connect(*a, **k):
            called["connect"] = True
            raise AssertionError("connect_pass must not run on baseline")

        with mock.patch("cortex.activation.index_repository", side_effect=boom_index):
            with mock.patch(
                "cortex.connect_pass.record_connect_pass", side_effect=boom_connect
            ):
                r = activate_repository(
                    self.home,
                    self.store,
                    self.gov,
                    "AFCHost",
                    "readme",
                    budget=400,
                    refresh="never",
                    force_evidence_baseline=True,
                )
        self.assertTrue(r.get("sterile_baseline"))
        ce = r.get("controller_execution") or {}
        self.assertEqual(ce.get("resolved"), "evidence_baseline")
        self.assertFalse(called["index"])
        self.assertFalse(called["connect"])
        # only audit channel may grow
        n = self.store.db.execute(
            "SELECT COUNT(1) AS c FROM controller_audit_events WHERE repo=?",
            ("AFCHost",),
        ).fetchone()
        self.assertGreater(int(n["c"]), 0)

    def test_governor_throw_fail_closed(self) -> None:
        with mock.patch.object(
            self.gov, "evaluate", side_effect=RuntimeError("gov_down")
        ):
            r = activate_repository(
                self.home,
                self.store,
                self.gov,
                "AFCHost",
                "readme",
                budget=300,
                refresh="never",
            )
        self.assertTrue(r.get("sterile_baseline") or (r.get("controller_execution") or {}).get("resolved") == "evidence_baseline")

    def test_unknown_controller_via_resolve(self) -> None:
        res = resolve_activation_controller(
            self.gov, "AFCHost", memory_controller="not_a_real_controller"
        )
        # unknown maps through simplex to advanced or baseline — issuer normalizes
        self.assertIn(res["controller"], {"advanced", "evidence_baseline"})
        # v7.0: capability is issued after epoch bind in activate_repository, not resolve
        self.assertNotIn("capability", res)

    def test_activate_issues_epoch_capability(self) -> None:
        r = activate_repository(
            self.home,
            self.store,
            self.gov,
            "AFCHost",
            "readme",
            budget=300,
            refresh="never",
            force_evidence_baseline=True,
        )
        self.assertIn("capability", r)
        cap = r["capability"]
        self.assertTrue(cap.get("capability_id") or cap.get("body_epoch_id"))
        self.assertIn("body_epoch", r)
        self.assertTrue((r.get("body_epoch") or {}).get("epoch_id"))

    def test_activation_leaves_phase_bound_to_final_epoch(self) -> None:
        from cortex.phases import BOUND, phase_binding_status

        r = activate_repository(
            self.home,
            self.store,
            self.gov,
            "AFCHost",
            "exercise advanced activation phase continuity",
            budget=400,
            refresh="never",
            memory_controller="advanced",
        )
        binding = phase_binding_status(self.store, "AFCHost")
        self.assertEqual(binding.get("binding"), BOUND, r)
        self.assertEqual(
            binding.get("phase_epoch_id"),
            (r.get("body_epoch") or {}).get("epoch_id"),
            r,
        )


if __name__ == "__main__":
    unittest.main()
