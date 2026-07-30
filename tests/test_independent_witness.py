from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.store import Store
from cortex.witness import assert_not_in_learning_surfaces, case_commitment, commit_manifest, run_witness


class WitnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# witness overview\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "WHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_commit_and_run(self) -> None:
        cases = [
            {
                "id": "wit_readme",
                "query": "README project overview",
                "expected_substrings": ["README"],
            }
        ]
        m = commit_manifest(cases)
        self.assertIn("case_commitment_hash", m)
        self.assertEqual(case_commitment(cases[0]), m["case_commitments"][0]["commitment"])
        r = run_witness(self.store, "WHost", cases=cases, controller="evidence_baseline")
        self.assertIn("result_hash", r)
        self.assertEqual(r.get("suite_kind"), "sealed_witness")
        # isolation: case ids not in empty surfaces
        iso = assert_not_in_learning_surfaces(["wit_secret_xyz"], {"routes": []})
        self.assertTrue(iso["ok"])


if __name__ == "__main__":
    unittest.main()
