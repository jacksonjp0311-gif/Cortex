"""M0–M10 math/network spine tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.math_net import phase_status, run_math_network_pass
from cortex.math_net.info_account import info_account
from cortex.math_net.ranking import expected_calibration_error, log_loss, score_primary
from cortex.math_net.regimes import m0_status
from cortex.math_net.uncertainty import compute_uncertainty
from cortex.neuron import compile_interlink
from cortex.store import Store


class MathNetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "mn_host"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# MathNet\n\n## Graph\n\nx\n", encoding="utf-8")
        (self.repo_path / "a.py").write_text("def f():\n    return g()\n\ndef g():\n    return 1\n", encoding="utf-8")
        (self.repo_path / "b.py").write_text("from a import f\n\ndef h():\n    return f()\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "MathHost")
        try:
            compile_interlink(self.store, "MathHost")
        except Exception:
            pass
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_m0_regimes_not_spectral(self) -> None:
        m0 = m0_status()
        self.assertTrue(m0["ok"])
        self.assertIn("prior", m0["profile"]["claim_boundary"].lower() + m0["claim_boundary"].lower())
        self.assertEqual(m0["profile"]["terminology"]["preferred"], "retention_regime")

    def test_m1_uncertainty(self) -> None:
        u = compute_uncertainty(retrieval_confidence=0.8, certificate_status="verified")
        self.assertIn("u", u)
        self.assertAlmostEqual(u["confidence"] + u["u"], 1.0, places=5)
        gov = self.gov.evaluate("MathHost", retrieval_confidence=0.7)
        self.assertIn("uncertainty", gov)
        self.assertIn("u", gov)

    def test_m6_ranker_primary_ece(self) -> None:
        sc = score_primary([0.4, 0.2], 0.0, [1.0, 0.5], heuristic_prior=0.1)
        self.assertTrue(sc["primary"])
        self.assertGreaterEqual(sc["probability"], 0.0)
        ece = expected_calibration_error([1.0, 0.0, 1.0], [0.9, 0.1, 0.6])
        self.assertIn("ece", ece)
        self.assertGreaterEqual(log_loss([1.0], [0.8]), 0.0)

    def test_m7_info_account(self) -> None:
        acc = info_account(u_before=0.6, u_after=0.3, budget_tokens=400, evidence_fidelity=0.8)
        self.assertAlmostEqual(acc["delta_u"], 0.3, places=5)
        self.assertIn("promotion_gate_open", acc)

    def test_full_pass_m0_m10(self) -> None:
        report = run_math_network_pass(
            self.store,
            "MathHost",
            retrieval_confidence=0.6,
            budget=300,
        )
        self.assertGreaterEqual(report["phases_ok"], 8)
        for key in ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"):
            self.assertIn(key, report["results"])
        self.assertEqual(len(phase_status()["phases"]), 11)


if __name__ == "__main__":
    unittest.main()
