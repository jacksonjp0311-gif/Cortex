"""v9.5.1 runtime convergence and observational-purity tests."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.interconnect import mesh_status
from cortex.integration import BASH_WRAPPER, POWERSHELL_WRAPPER
from cortex.ranker.model import MODEL_ID, ranker_status
from cortex.store import Store


class RuntimeConvergenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# runtime convergence\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "RuntimeConvergenceHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_unknown_repository_interconnect_fails_closed_without_writes(self) -> None:
        before_changes = self.store.db.total_changes
        before_repositories = self.store.db.execute(
            "SELECT COUNT(*) AS n FROM repositories"
        ).fetchone()["n"]
        before_rankers = self.store.db.execute(
            "SELECT COUNT(*) AS n FROM ranker_models"
        ).fetchone()["n"]

        report = mesh_status(self.store, "does-not-exist", home=self.home)

        self.assertEqual(report["status"], "unknown_repository")
        self.assertFalse(report["mesh_green"])
        self.assertFalse(report["overall_ready"])
        self.assertEqual(report["bottlenecks"], ["unknown_repository"])
        self.assertFalse(report["policy_effect"])
        self.assertFalse(report["update_authorized"])
        self.assertFalse(report["host_mutate_authorized"])
        self.assertFalse(report["execution_authorized"])
        self.assertEqual(self.store.db.total_changes, before_changes)
        self.assertEqual(
            self.store.db.execute("SELECT COUNT(*) AS n FROM repositories").fetchone()["n"],
            before_repositories,
        )
        self.assertEqual(
            self.store.db.execute("SELECT COUNT(*) AS n FROM ranker_models").fetchone()["n"],
            before_rankers,
        )

    def test_ranker_status_does_not_initialize_missing_model(self) -> None:
        self.store.db.execute(
            "DELETE FROM ranker_models WHERE repo=? AND model_id=?",
            (self.repo, MODEL_ID),
        )
        self.store.db.commit()
        before_changes = self.store.db.total_changes

        report = ranker_status(self.store, self.repo)

        self.assertFalse(report["available"])
        self.assertEqual(report["train_count"], 0)
        self.assertFalse(report["policy_effect"])
        self.assertFalse(report["update_authorized"])
        self.assertEqual(self.store.db.total_changes, before_changes)
        row = self.store.db.execute(
            "SELECT 1 FROM ranker_models WHERE repo=? AND model_id=?",
            (self.repo, MODEL_ID),
        ).fetchone()
        self.assertIsNone(row)

    def test_known_repository_interconnect_does_not_initialize_ranker(self) -> None:
        self.store.db.execute(
            "DELETE FROM ranker_models WHERE repo=? AND model_id=?",
            (self.repo, MODEL_ID),
        )
        self.store.db.commit()
        before_changes = self.store.db.total_changes

        report = mesh_status(self.store, self.repo, home=self.home)

        self.assertEqual(report["repo"], self.repo)
        self.assertFalse(report["policy_effect"])
        self.assertFalse(report["update_authorized"])
        self.assertFalse(report["host_mutate_authorized"])
        self.assertFalse(report["execution_authorized"])
        self.assertEqual(self.store.db.total_changes, before_changes)
        row = self.store.db.execute(
            "SELECT 1 FROM ranker_models WHERE repo=? AND model_id=?",
            (self.repo, MODEL_ID),
        ).fetchone()
        self.assertIsNone(row)

    def test_cli_help_survives_legacy_windows_encoding(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp1252:strict"
        result = subprocess.run(
            [sys.executable, "-m", "cortex", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        output = result.stdout.decode("utf-8")
        self.assertIn("Hermetic attach", output)
        self.assertIn("◈", output)

    def test_generated_wrappers_expose_required_emergence_log(self) -> None:
        self.assertIn('"emergence-log"', POWERSHELL_WRAPPER)
        self.assertIn('$Command -eq "emergence-log"', POWERSHELL_WRAPPER)
        self.assertIn("|emergence-log)", BASH_WRAPPER)


if __name__ == "__main__":
    unittest.main()
