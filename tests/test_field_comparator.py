"""v7.3 evidence-memory comparator."""

from __future__ import annotations

import unittest

from cortex.field_channels import FieldSample
from cortex.field_comparator import compare_evidence_memory


def _s(fam: str, truth: str, path: str, act: float = 0.8, **meta) -> FieldSample:
    return FieldSample(
        repo="R",
        body_epoch_id="e",
        tick=0,
        timestamp=0.0,
        channel_id=fam,
        channel_family=fam,
        activity=act,
        reliability=1.0,
        truth_source=truth,
        paths=(path,),
        metadata=meta,
    )


class ComparatorTests(unittest.TestCase):
    def test_unknown_not_agreement(self) -> None:
        # only memory side
        r = compare_evidence_memory([_s("M_CONSOLIDATED", "INFERRED", "a.py")])
        self.assertFalse(r["comparator_available"])
        self.assertIsNone(r["agreement"])
        self.assertIsNone(r["quality"])

    def test_simulated_not_verified_evidence(self) -> None:
        samples = [
            _s("E_HOST", "SIMULATED", "a.py"),
            _s("M_CONSOLIDATED", "INFERRED", "a.py"),
        ]
        r = compare_evidence_memory(samples)
        self.assertFalse(r["comparator_available"])

    def test_agreement_on_shared_paths(self) -> None:
        samples = [
            _s("E_HOST", "MEASURED", "a.py"),
            _s("E_RUNTIME", "RECEIPT_VERIFIED", "a.py"),
            _s("M_CONSOLIDATED", "INFERRED", "a.py"),
            _s("M_LEARNED", "INFERRED", "a.py"),
        ]
        r = compare_evidence_memory(samples)
        self.assertTrue(r["comparator_available"])
        self.assertIsNotNone(r["agreement"])
        self.assertGreater(r["agreement"] or 0, 0.5)
        self.assertIsNotNone(r["quality"])

    def test_explicit_contradiction_only(self) -> None:
        samples = [
            _s("E_HOST", "MEASURED", "a.py"),
            _s("M_CONSOLIDATED", "INFERRED", "a.py", explicit_contradiction=True),
        ]
        r = compare_evidence_memory(samples)
        self.assertTrue(r["comparator_available"])
        self.assertGreater(float(r["contradiction_mass"]), 0.0)
        # quality reduced by contradiction (0.0 is a valid quality)
        self.assertIsNotNone(r["quality"])
        self.assertLess(float(r["quality"]), float(r["agreement"]))


if __name__ == "__main__":
    unittest.main()
