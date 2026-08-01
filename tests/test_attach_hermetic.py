"""Hermetic attach — external home, no host pollution, quiet ritual path."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from cortex.attach import attach_repository, safe_repo_name
from cortex.config import ensure_home


class AttachHermeticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "cortex_home")
        self.host = self.base / "some_app"
        self.host.mkdir()
        (self.host / "README.md").write_text("# Some App\n\nHello.\n", encoding="utf-8")
        (self.host / "main.py").write_text("print('hi')\n", encoding="utf-8")
        os.environ["CORTEX_ATTACH_RITUAL"] = "0"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_safe_name(self) -> None:
        self.assertEqual(safe_repo_name(self.host), "some_app")

    def test_external_attach_no_host_dot_cortex(self) -> None:
        report = attach_repository(
            self.host,
            name="SomeApp",
            home=self.home,
            force=False,
            ritual=False,
            seal_epoch=True,
            activate=True,
            quiet=True,
            json_mode=True,
        )
        self.assertEqual(report["repo"], "SomeApp")
        self.assertTrue(report["external"])
        self.assertFalse(report["host_files_modified"])
        self.assertFalse((self.host / ".cortex").exists())
        self.assertTrue((self.home / "cortex.db").exists())
        self.assertTrue(report.get("epoch", {}).get("epoch_id") or report.get("bootstrap"))

    def test_engine_tree_not_required_as_host(self) -> None:
        # Host is dummy; engine is importable cortex package only
        report = attach_repository(
            self.host,
            home=self.home,
            ritual=False,
            quiet=True,
            json_mode=True,
            activate=False,
            seal_epoch=True,
        )
        self.assertEqual(report["host_path"], str(self.host.resolve()))
        self.assertNotEqual(
            Path(report["host_path"]).resolve(),
            Path(__file__).resolve().parents[1],
        )

    def test_demo_mode_redacts_paths(self) -> None:
        os.environ["CORTEX_ATTACH_DEMO"] = "1"
        try:
            report = attach_repository(
                self.host,
                home=self.home,
                ritual=False,
                quiet=True,
                json_mode=True,
                activate=False,
                seal_epoch=False,
            )
            self.assertEqual(report["host_path"], "./your-project")
            self.assertEqual(report["home"], "~/.cortex")
            self.assertNotIn("Users", report["host_path"])
            self.assertNotIn(str(self.host), report["host_path"])
        finally:
            os.environ.pop("CORTEX_ATTACH_DEMO", None)

    def test_public_display_paths_symbolic(self) -> None:
        from cortex.hermetic_ritual import public_display_paths

        host, body = public_display_paths(repo_name="flask", demo=False)
        self.assertEqual(host, "./flask")
        self.assertEqual(body, "~/.cortex")
        host_d, body_d = public_display_paths(demo=True)
        self.assertEqual(host_d, "./your-project")
        self.assertEqual(body_d, "~/.cortex")


if __name__ == "__main__":
    unittest.main()
