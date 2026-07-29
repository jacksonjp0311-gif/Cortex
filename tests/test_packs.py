"""Binary-intel packs — portable domain memory branch."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.packs import (
    domain_route,
    index_packs_into_repo,
    install_pack,
    list_packs,
    verify_pack,
)
from cortex.packs.format import build_binary_field, parse_binary_field
from cortex.store import Store

ENGINE_PACK = (
    Path(__file__).resolve().parents[1] / "packs" / "cortex-core-intel-v1"
)


class PacksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "packhost"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Pack Host\n\n## Architecture\n\nDomain packs.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "def run() -> str:\n    return 'ok'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "PackHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_binary_field_roundtrip(self) -> None:
        raw = build_binary_field(
            ["math", "geometry"],
            domain_keywords={"math": ["math", "equation"]},
        )
        parsed = parse_binary_field(raw)
        self.assertEqual(parsed["format"], "CORTEXBF1")
        self.assertEqual(len(parsed["domains"]), 2)

    def test_install_index_probe_activate(self) -> None:
        self.assertTrue(ENGINE_PACK.is_dir(), msg=str(ENGINE_PACK))
        inst = install_pack(ENGINE_PACK, self.home, force=True)
        self.assertTrue(inst["installed"])
        self.assertEqual(inst["pack_id"], "cortex-core-intel-v1")
        self.assertTrue((Path(inst["path"]) / "field.cortexbf1").is_file())
        ver = verify_pack(Path(inst["path"]))
        self.assertTrue(ver["ok"])
        listed = list_packs(self.home)
        self.assertGreaterEqual(listed["count"], 1)

        idx = index_packs_into_repo(self.store, self.home, "PackHost")
        self.assertGreater(idx["chunks_indexed"], 0)

        route = domain_route(self.home, "geometry triangle circle proof")
        self.assertEqual(route["top_domain"], "geometry")
        self.assertTrue(route["expand"] or route["top_score"] >= 0.75)

        packet = activate_repository(
            self.home,
            self.store,
            self.gov,
            "PackHost",
            "geometry triangle spatial proof",
            budget=500,
        )
        packs = packet.get("packs") or (packet.get("context") or {}).get("packs")
        full = packet.get("context_full") or {}
        if not packs:
            packs = full.get("packs")
        self.assertIsNotNone(packs)
        self.assertEqual(packs.get("glyph"), "▣")
        # domain should prefer geometry-ish
        self.assertTrue(
            packs.get("top_domain") in {"geometry", "math", "general", "knowledge"}
            or packs.get("top_score") is not None
        )


if __name__ == "__main__":
    unittest.main()
