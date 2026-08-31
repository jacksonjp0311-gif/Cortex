from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.semantic_calibration import (
    build_semantic_calibration_bundle,
    build_semantic_calibration_preflight,
    verify_semantic_calibration_bundle,
)
from cortex.source_experience import forge_structural_source_experience_pair
from cortex.store import Store


class Alpha17SemanticCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("alpha17\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha17Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_relevant_and_sham_lessons_are_distinct_and_independently_witnessed(self) -> None:
        pair = forge_structural_source_experience_pair(self.store, self.repo)
        self.assertEqual(pair["state"], "STRUCTURAL_LESSON_PAIR_PASS")
        self.assertEqual(pair["semantic_distinctness"], "pass")
        self.assertEqual(pair["witness_distinctness"], "pass")
        self.assertNotEqual(pair["relevant"]["competence_id"], pair["sham"]["competence_id"])
        self.assertEqual(pair["relevant"]["checks"]["semantic_support"]["state"], "pass")
        self.assertEqual(pair["sham"]["checks"]["semantic_support"]["state"], "pass")
        self.assertEqual(pair["evidence_class"], "synthetic")
        self.assertFalse(pair["empirical_transfer_established"])

    def test_public_calibration_manifest_is_answer_free_and_hash_bound(self) -> None:
        bundle = build_semantic_calibration_bundle(secret_seed="alpha17-test-seed")
        check = verify_semantic_calibration_bundle(bundle)
        self.assertTrue(check["valid"], check["errors"])
        self.assertEqual(bundle["manifest"]["case_count"], 12)
        self.assertEqual(len(bundle["manifest"]["initial_screen_case_ids"]), 4)
        self.assertTrue(all("answer" not in row for row in bundle["manifest"]["cases"]))
        self.assertTrue(all("expected" not in row for row in bundle["manifest"]["cases"]))

    def test_public_or_private_tampering_fails(self) -> None:
        bundle = build_semantic_calibration_bundle(secret_seed="alpha17-test-seed")
        public_tamper = copy.deepcopy(bundle)
        public_tamper["manifest"]["cases"][0]["prompt"] = "tampered"
        self.assertFalse(verify_semantic_calibration_bundle(public_tamper)["valid"])
        key_tamper = copy.deepcopy(bundle)
        first = next(iter(key_tamper["answer_key"]["answers"]))
        key_tamper["answer_key"]["answers"][first] = "D"
        self.assertFalse(verify_semantic_calibration_bundle(key_tamper)["valid"])

    def test_preflight_unlocks_only_four_call_baseline_screen(self) -> None:
        pair = forge_structural_source_experience_pair(self.store, self.repo)
        bundle = build_semantic_calibration_bundle(secret_seed="alpha17-test-seed")
        preflight = build_semantic_calibration_preflight(pair, bundle)
        self.assertEqual(preflight["state"], "LIVE_CALIBRATION_SCREEN_READY")
        self.assertEqual(preflight["screening_policy"]["initial_calls"], 4)
        self.assertEqual(
            preflight["screening_policy"]["maximum_calls_before_new_authorization"], 4
        )
        self.assertFalse(preflight["screening_policy"]["caller_success_booleans_accepted"])
        self.assertEqual(preflight["calls_executed"], 0)
        self.assertFalse(preflight["calibration_established"])
        self.assertFalse(preflight["semantic_transfer_established"])
        self.assertFalse(preflight["execution_authorized"])

    def test_renamed_or_empirical_claiming_fixture_pair_cannot_open_preflight(self) -> None:
        pair = forge_structural_source_experience_pair(self.store, self.repo)
        pair["evidence_class"] = "live_empirical"
        bundle = build_semantic_calibration_bundle(secret_seed="alpha17-test-seed")
        preflight = build_semantic_calibration_preflight(pair, bundle)
        self.assertEqual(preflight["state"], "CALIBRATION_PREFLIGHT_HELD")
        self.assertEqual(preflight["calls_executed"], 0)


if __name__ == "__main__":
    unittest.main()
