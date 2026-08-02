"""v7.7 Binding Field — names live interconnect structure without authority."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.binding_field import (
    BindingClass,
    classify_binding_field,
    commit_live_buffer,
    observe_binding_field,
)
from cortex.config import ensure_home
from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels
from cortex.resonant_frame import append_field_samples
from cortex.store import Store


class BindingClassifyTests(unittest.TestCase):
    def test_binding_gap_first(self) -> None:
        c, r = classify_binding_field(
            needs_realign=True,
            epoch_current=False,
            phase_bound=False,
            buffer_ticks=11,
            frames_seen=0,
            field_ready=False,
            sense_class="UNBOUND",
            immune_block=True,
        )
        self.assertEqual(c, BindingClass.BINDING_GAP.value)

    def test_buffer_pending(self) -> None:
        c, r = classify_binding_field(
            needs_realign=False,
            epoch_current=True,
            phase_bound=True,
            buffer_ticks=11,
            frames_seen=0,
            field_ready=False,
            sense_class="COLD",
            immune_block=True,
            w_min=8,
        )
        self.assertEqual(c, BindingClass.BUFFER_PENDING.value)

    def test_cold_field(self) -> None:
        c, _ = classify_binding_field(
            needs_realign=False,
            epoch_current=True,
            phase_bound=True,
            buffer_ticks=0,
            frames_seen=3,
            field_ready=False,
            sense_class="COLD",
            immune_block=False,
        )
        self.assertEqual(c, BindingClass.COLD_FIELD.value)

    def test_verified(self) -> None:
        c, _ = classify_binding_field(
            needs_realign=False,
            epoch_current=True,
            phase_bound=True,
            buffer_ticks=0,
            frames_seen=16,
            field_ready=True,
            sense_class="NOMINAL",
            latest_frame_class="QUIESCENT",
            immune_block=True,
        )
        self.assertEqual(c, BindingClass.VERIFIED_REGIME.value)

    def test_transition_is_not_verified(self) -> None:
        c, _ = classify_binding_field(
            needs_realign=False, epoch_current=True, phase_bound=True,
            buffer_ticks=0, frames_seen=16, field_ready=True,
            sense_class="NOMINAL", latest_frame_class="TRANSITION",
            immune_block=False,
        )
        self.assertEqual(c, BindingClass.TRANSITION_REGIME.value)

    def test_drift_and_stress_are_not_verified(self) -> None:
        for sense_class in ("DRIFT", "STRESSED"):
            c, _ = classify_binding_field(
                needs_realign=False, epoch_current=True, phase_bound=True,
                buffer_ticks=0, frames_seen=16, field_ready=True,
                sense_class=sense_class,
                latest_frame_class="COHERENT_DIFFERENTIATED",
                immune_block=False,
            )
            self.assertEqual(c, BindingClass.DRIFT_REGIME.value)


class BindingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        self.host = Path(self.temp.name) / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# bind\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "BindHost"
        self.store.attach(self.repo, "rid-bind", self.host)
        try:
            from cortex.bootstrap import bootstrap_repository
            from cortex.epoch import seal_epoch_transition

            bootstrap_repository(
                self.home, self.store, self.host, self.repo, external=True
            )
            seal_epoch_transition(self.store, self.repo, reason="bind_test")
        except Exception:
            pass

    def tearDown(self) -> None:
        try:
            self.store.close()
        except Exception:
            pass
        self.temp.cleanup()

    def test_observe_advisory(self) -> None:
        r = observe_binding_field(self.store, self.repo, home=self.home)
        self.assertTrue(r["advisory_only"])
        self.assertIn(r["classification"], {e.value for e in BindingClass})
        self.assertIn("field_vector", r)

    def test_commit_closes_buffer(self) -> None:
        for t in range(10):
            samples = sample_tick_channels(
                repo=self.repo,
                body_epoch_id="e",
                tick=t,
                activities={f: 0.4 for f in CHANNEL_FAMILIES},
            )
            append_field_samples(self.store, self.repo, samples)
        out = commit_live_buffer(self.store, self.repo)
        self.assertTrue(out.get("ok"))
        # after commit, empty buffer or closed
        self.assertIn("binding_after", out)
        self.assertFalse(out.get("claim_boundary") is None)

    def test_no_host_write(self) -> None:
        n0 = len(list(self.host.rglob("*")))
        observe_binding_field(self.store, self.repo, home=self.home)
        commit_live_buffer(self.store, self.repo)
        n1 = len(list(self.host.rglob("*")))
        self.assertEqual(n0, n1)


if __name__ == "__main__":
    unittest.main()
