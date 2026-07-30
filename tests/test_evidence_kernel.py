"""Evidence Kernel purity — no advanced adaptive imports invoked."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.evidence_kernel import KERNEL_ID, evidence_kernel_context, evidence_kernel_query
from cortex.store import Store


class EvidenceKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "ek"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# EK authority boundary\n", encoding="utf-8")
        (self.repo_path / "core.py").write_text("def authority():\n    return 1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "EKHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_query_returns_receipt(self) -> None:
        r = evidence_kernel_query(self.store, "EKHost", "authority boundary", limit=8)
        self.assertTrue(r.get("ok"))
        self.assertEqual(r.get("kernel_id"), KERNEL_ID)
        self.assertIn("receipt", r)
        self.assertIn("receipt_hash", r["receipt"])

    def test_no_ranker_or_spectral_called(self) -> None:
        with mock.patch("cortex.ranker.model.rerank_hits", side_effect=AssertionError("ranker")):
            with mock.patch(
                "cortex.math_net.spectral_memory.enrich_hits_with_diffusion",
                side_effect=AssertionError("spectral"),
            ):
                with mock.patch(
                    "cortex.retrieval.query",
                    side_effect=AssertionError("advanced_query"),
                ):
                    r = evidence_kernel_query(self.store, "EKHost", "authority", limit=5)
                    self.assertTrue(r.get("ok"))

    def test_context_flat_budget(self) -> None:
        c = evidence_kernel_context(self.store, "EKHost", "authority", budget=400)
        self.assertEqual((c.get("budget_partition") or {}).get("scheme"), "flat")
        self.assertEqual(c.get("controller"), "evidence_baseline")


if __name__ == "__main__":
    unittest.main()
