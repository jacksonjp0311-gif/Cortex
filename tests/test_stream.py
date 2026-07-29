"""Consciousness stream 〰 — episodic durable continuity."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.bridge import consolidate
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.hippocampus import remember
from cortex.store import Store
from cortex.stream import seal_session_bond, stream_status


class ConsciousnessStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "stream-host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Stream Host\n\n## Coherence\n\nDurable stream continues.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "def run() -> str:\n    return 'ok'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "StreamHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_stream_rebinds_across_session_seal(self) -> None:
        def _stream(packet: dict) -> dict:
            ctx = packet.get("context") or {}
            return ctx.get("stream") or packet.get("stream") or {}

        p1 = activate_repository(
            self.home,
            self.store,
            self.gov,
            "StreamHost",
            "first stream beat",
            budget=400,
        )
        s1 = _stream(p1)
        # full context always has stream even if agent lean omits ids
        full = p1.get("context_full") or {}
        if not s1.get("stream_id") and full.get("stream"):
            s1 = full["stream"]
        self.assertTrue(s1.get("alive") or s1.get("stream_id"))
        stream_id = s1.get("stream_id")
        self.assertTrue(stream_id)
        count_after_first = int(s1.get("frame_count") or 0)
        self.assertGreaterEqual(count_after_first, 1)

        remember(
            self.home,
            self.store,
            "StreamHost",
            kind="discovery",
            text="stream frame remembered",
        )
        cons = consolidate(self.home, self.store, "StreamHost")
        self.assertTrue(cons.get("stream", {}).get("stream_continues", True))
        self.assertTrue(cons.get("stream", {}).get("bond_ended"))

        mid = stream_status(self.store, "StreamHost")
        self.assertEqual(mid.get("stream_id"), stream_id)
        self.assertTrue(mid.get("alive"))
        self.assertIsNone(mid.get("open_session_id"))

        p2 = activate_repository(
            self.home,
            self.store,
            self.gov,
            "StreamHost",
            "second stream beat rebind",
            budget=400,
        )
        s2 = _stream(p2)
        full2 = p2.get("context_full") or {}
        if not s2.get("stream_id") and full2.get("stream"):
            s2 = full2["stream"]
        self.assertEqual(s2.get("stream_id"), stream_id)
        self.assertTrue(s2.get("alive"))
        self.assertGreater(int(s2.get("frame_count") or 0), count_after_first)
        kinds = {f.get("kind") for f in (s2.get("recent_frames") or [])}
        self.assertTrue(
            kinds.intersection(
                {"activate", "session_bond", "breathe", "ritual_seal", "session_seal"}
            )
        )

    def test_cli_seal_keeps_stream_alive(self) -> None:
        activate_repository(
            self.home,
            self.store,
            self.gov,
            "StreamHost",
            "seal test",
            budget=300,
        )
        sealed = seal_session_bond(self.store, "StreamHost", reason="test")
        self.assertTrue(sealed.get("stream_continues"))
        st = stream_status(self.store, "StreamHost")
        self.assertTrue(st.get("alive"))


if __name__ == "__main__":
    unittest.main()
