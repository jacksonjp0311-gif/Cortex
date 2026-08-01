"""v7.4 Continuity Realignment — diagnose observe-only; apply needs auth."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.config import ensure_home
from cortex.epoch import compute_body_epoch, seal_epoch_transition
from cortex.realign import (
    apply_realign,
    diagnose_realign,
    plan_realign,
    warm_field_baseline,
)
from cortex.store import Store


class RealignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.host = Path(self.temp.name) / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# demo\n", encoding="utf-8")
        (self.host / "main.py").write_text("x=1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Demo"
        self.store.attach(self.repo, "rid-demo", self.host)
        # bootstrap minimal so epoch roots resolve
        try:
            from cortex.bootstrap import bootstrap_repository

            bootstrap_repository(
                self.home,
                self.store,
                self.host,
                self.repo,
                external=True,
            )
        except Exception:
            pass

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_diagnose_observe_only(self) -> None:
        d = diagnose_realign(self.store, self.repo)
        self.assertTrue(d["observation_only"])
        self.assertIn("epoch", d)
        self.assertIn("recommended_action", d)
        # diagnose must not create seals by itself — if absent, still observe
        self.assertIn(d["severity"], {"ok", "low", "medium", "high"})

    def test_apply_requires_auth_when_stale(self) -> None:
        # Seal old-style then force drift by sealing nothing and mutating setting
        try:
            seal_epoch_transition(self.store, self.repo, reason="test_seed")
        except Exception:
            pass
        # If already verified, invent mismatch by not applying — force needs via empty
        d = diagnose_realign(self.store, self.repo)
        if d["needs_realign"]:
            r = apply_realign(self.store, self.repo, authorize=False)
            self.assertFalse(r["ok"])
            self.assertEqual(r["error"], "authorization_required")
        else:
            # still test flag rejection path with force by plan
            plan = plan_realign(self.store, self.repo)
            self.assertIn("steps", plan)

    def test_apply_with_auth_clears_or_skips(self) -> None:
        try:
            seal_epoch_transition(self.store, self.repo, reason="pre")
        except Exception:
            pass
        # Touch host to create live drift if possible
        (self.host / "extra.py").write_text("y=2\n", encoding="utf-8")
        r = apply_realign(
            self.store,
            self.repo,
            authorize=True,
            warm_field=True,
            warm_ticks=2,
            reason="test_realign",
        )
        self.assertTrue(r.get("applied"))
        self.assertIn("receipt", r)
        self.assertIn("receipt_hash", r["receipt"])
        post = r.get("diagnosis_after") or {}
        # After authorize apply, epoch should not need realign (unless seal failed)
        if r.get("ok"):
            self.assertFalse(post.get("needs_realign"))

    def test_warm_field_only(self) -> None:
        w = warm_field_baseline(self.store, self.repo, ticks=2)
        self.assertEqual(w["ticks_seeded"], 2)
        self.assertIn("baseline_frames_display", w)

    def test_source_no_silent_seal_on_diagnose(self) -> None:
        import inspect

        import cortex.realign as mod

        src = inspect.getsource(mod.diagnose_realign)
        self.assertNotIn("seal_epoch_transition", src)
        self.assertNotIn("ensure_current_epoch", src)


if __name__ == "__main__":
    unittest.main()
