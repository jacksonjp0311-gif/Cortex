"""Witness commit-before-reveal chronology."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.store import Store
from cortex.witness import (
    case_commitment,
    commit_manifest,
    run_witness,
    verify_reveal,
)


class WitnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# witness overview\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "WHost")
        self.cases = [
            {
                "id": "wit_readme",
                "query": "README project overview",
                "expected_substrings": ["README"],
            }
        ]

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_legacy_run_without_commitment_denied(self) -> None:
        r = run_witness(self.store, "WHost", cases=self.cases)
        self.assertFalse(r.get("ok"))
        self.assertEqual(r.get("error"), "commitment_required_before_reveal")

    def test_commit_then_reveal_run(self) -> None:
        commitment = commit_manifest(
            self.cases,
            store=self.store,
            cortex_commit_hash="test-commit",
            repository_snapshot_hash="snap1",
        )
        self.assertIn("case_commitment_hash", commitment)
        self.assertIsNone(commitment.get("revealed_at"))
        # mismatch reveal rejected
        bad = [{**self.cases[0], "query": "tampered"}]
        v = verify_reveal(commitment, bad)
        self.assertFalse(v.get("ok"))
        # correct reveal
        r = run_witness(
            self.store,
            "WHost",
            commitment=commitment,
            revealed_cases=self.cases,
            controller="evidence_baseline",
            cortex_commit_hash="test-commit",
            repository_snapshot_hash="snap1",
        )
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(r.get("chronology_ok"))
        self.assertLessEqual(r["created_at"], r["revealed_at"])
        # changed commit rejected
        r2 = run_witness(
            self.store,
            "WHost",
            commitment=commitment,
            revealed_cases=self.cases,
            cortex_commit_hash="other-commit",
            repository_snapshot_hash="snap1",
        )
        self.assertFalse(r2.get("ok"))


if __name__ == "__main__":
    unittest.main()
