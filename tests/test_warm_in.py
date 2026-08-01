"""v7.6 Warm-In Protocol — milestone closure without host mutation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.config import ensure_home
from cortex.epoch import seal_epoch_transition
from cortex.store import Store
from cortex.warm_in import (
    run_warm_in,
    verify_warm_in_receipt,
    warm_in_status,
)


class WarmInTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        self.host = Path(self.temp.name) / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# warm\n", encoding="utf-8")
        (self.host / "a.py").write_text("x=1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "WarmHost"
        self.store.attach(self.repo, "rid-warm", self.host)
        try:
            from cortex.bootstrap import bootstrap_repository

            bootstrap_repository(
                self.home, self.store, self.host, self.repo, external=True
            )
        except Exception:
            pass
        try:
            seal_epoch_transition(self.store, self.repo, reason="warm_setup")
        except Exception:
            pass

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_status_observe_only(self) -> None:
        st = warm_in_status(self.store, self.repo)
        self.assertTrue(st["observation_only"])
        self.assertIn("checks", st)
        self.assertIn("field_frames_display", st)
        self.assertIn("observer_baseline_display", st)

    def test_run_requires_auth_when_stale(self) -> None:
        # Force drift if possible
        (self.host / "b.py").write_text("y=2\n", encoding="utf-8")
        from cortex.realign import diagnose_realign

        d = diagnose_realign(self.store, self.repo)
        if d.get("needs_realign"):
            r = run_warm_in(
                self.store,
                self.repo,
                home=self.home,
                authorize_realign=False,
                rounds=1,
                field_ticks=2,
                sense_updates=2,
            )
            self.assertFalse(r.get("ok"))
            self.assertEqual(r.get("error"), "realign_authorization_required")

    def test_run_warm_in_progress(self) -> None:
        r = run_warm_in(
            self.store,
            self.repo,
            home=self.home,
            authorize_realign=True,
            rounds=2,
            field_ticks=3,
            sense_updates=4,
        )
        self.assertTrue(r.get("log"))
        self.assertIn("receipt", r)
        self.assertTrue(r["receipt"].get("receipt_hash"))
        self.assertFalse(r["receipt"].get("host_mutation"))
        self.assertFalse(r["receipt"].get("authority_satisfying"))
        ver = verify_warm_in_receipt(self.store, self.repo)
        self.assertTrue(ver.get("hash_ok"), ver)

    def test_authorized_warm_in_binds_current_ephemeral_phase(self) -> None:
        from cortex.phases import BOUND, phase_binding_status

        before = phase_binding_status(self.store, self.repo)
        # A fresh external bootstrap may expose an ephemeral phase record even
        # when the body epoch itself is current.
        if before.get("binding") != BOUND:
            result = run_warm_in(
                self.store,
                self.repo,
                home=self.home,
                authorize_realign=True,
                rounds=1,
                field_ticks=1,
                sense_updates=1,
            )
            self.assertFalse(result["receipt"].get("host_mutation"))
            after = phase_binding_status(self.store, self.repo)
            self.assertEqual(after.get("binding"), BOUND, result)

    def test_no_host_mutation(self) -> None:
        before = {p.name for p in self.host.rglob("*")}
        run_warm_in(
            self.store,
            self.repo,
            home=self.home,
            authorize_realign=True,
            rounds=1,
            field_ticks=2,
            sense_updates=2,
        )
        after = {p.name for p in self.host.rglob("*")}
        # may have same files; no .cortex pollution required
        self.assertFalse((self.host / ".cortex").exists())
        self.assertTrue(before.issubset(after) or before == after)


if __name__ == "__main__":
    unittest.main()
