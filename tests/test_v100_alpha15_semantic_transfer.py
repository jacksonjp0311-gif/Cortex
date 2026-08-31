"""Alpha.15 zero-call semantic-transfer readiness tests."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from cortex.semantic_transfer import assess_semantic_transfer_readiness


class _Store:
    def __init__(self, memories):
        self.memories = list(memories)
        self.settings = {}

    def list_admitted_memories(self, repo, *, session_id=None, limit=100):
        return copy.deepcopy(self.memories[:limit])

    def get_setting(self, key, default=None):
        return copy.deepcopy(self.settings.get(key, default))

    def set_setting(self, key, value):
        self.settings[key] = copy.deepcopy(value)


def _memory(index: int, *, modern: bool = True) -> dict:
    summary = f"Verified lesson {index}: invalidate cached state before rereading."
    row = {
        "memory_id": f"mem-{index}",
        "candidate_id": f"cand-{index}",
        "candidate_type": "successful_procedure",
        "summary": summary,
        "support_level": "high",
        "receipt_hash": str(index) * 64,
        "evidence": {"outcome": "success", "index": index},
    }
    if modern:
        row["candidate_material"] = {
            "candidate_id": row["candidate_id"],
            "candidate_type": row["candidate_type"],
            "summary": summary,
            "support_level": "high",
        }
    return row


def _deep():
    return {
        "structural_validity": True,
        "lineage_validity": True,
        "evidence_validity": True,
        "errors": [],
    }


def _eligible():
    return {"eligible": True, "exclusions": [], "current_state": "active"}


class Alpha15SemanticTransferTests(unittest.TestCase):
    def assess(self, store, **kwargs):
        with (
            patch("cortex.semantic_transfer.deep_verify_admitted_memory", return_value=_deep()),
            patch("cortex.semantic_transfer.evaluate_memory_eligibility", return_value=_eligible()),
        ):
            return assess_semantic_transfer_readiness(
                store, "Cortex", body_epoch_id="epoch", **kwargs
            )

    def test_legacy_memory_holds_trial_without_spending_calls(self) -> None:
        report = self.assess(_Store([_memory(1, modern=False)]))
        self.assertEqual(report["state"], "SEMANTIC_TRANSFER_HELD")
        self.assertEqual(report["counts"]["legacy_partial"], 1)
        self.assertEqual(report["calls_executed"], 0)
        self.assertEqual(report["next_run_policy"]["maximum_live_calls"], 0)
        self.assertEqual(
            report["next_run_policy"]["action"],
            "generate_modern_verified_source_experience",
        )

    def test_two_distinct_lessons_do_not_let_caller_named_corpus_open_readiness(self) -> None:
        report = self.assess(
            _Store([_memory(1), _memory(2)]),
            task_families=["stale_state_repair"],
            maximum_next_run_calls=6,
        )
        self.assertEqual(report["state"], "SEMANTIC_TRANSFER_HELD")
        self.assertEqual(report["next_run_policy"]["maximum_live_calls"], 0)
        self.assertEqual(
            report["next_run_policy"]["action"],
            "calibrate_non_ceiling_target_corpus",
        )
        self.assertEqual(report["gates"]["task_families_declared"], "pass")
        self.assertEqual(report["gates"]["non_ceiling_target_corpus"], "unknown")
        self.assertEqual(report["calls_executed"], 0)
        self.assertFalse(report["empirical_transfer_established"])
        self.assertFalse(report["host_mutate_authorized"])
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["memory_admission_authorized"])

    def test_one_lesson_cannot_impersonate_relevant_and_sham_pair(self) -> None:
        report = self.assess(
            _Store([_memory(1)]), task_families=["stale_state_repair"]
        )
        self.assertEqual(report["state"], "SEMANTIC_TRANSFER_HELD")
        self.assertIn("relevant_and_sham_pair_missing", report["blockers"])
        self.assertEqual(report["next_run_policy"]["maximum_live_calls"], 0)

    def test_result_persists_only_as_non_authorizing_advisory_tip(self) -> None:
        store = _Store([_memory(1, modern=False)])
        report = self.assess(store, persist=True)
        saved = store.settings["semantic_transfer_readiness_latest:Cortex"]
        self.assertEqual(report["persistence"], "advisory_tip_only")
        self.assertFalse(saved["policy_effect"])
        self.assertFalse(saved["empirical_transfer_established"])
        self.assertEqual(saved["calls_executed"], 0)


if __name__ == "__main__":
    unittest.main()
