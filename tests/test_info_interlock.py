"""v8.2 informational interlock falsification tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.math_net.info_interlock import (
    bridge_deconcentration_report,
    graph_sampling_audit,
    interlock_report,
    stamp_hits_with_interlock_shadow,
    synergy_proxy_bits,
    triad_alignment_score,
)
from cortex.store import Store


class _GraphStore:
    def __init__(self, edges: list[tuple[str, str]]) -> None:
        self.edges = edges

    def neural_synapses(self, repo: str):
        return [
            {
                "synapse_id": f"s{i}",
                "source_id": a,
                "target_id": b,
                "relation": "test",
                "weight": 0.5,
            }
            for i, (a, b) in enumerate(self.edges)
        ]


class InformationMathTests(unittest.TestCase):
    def test_xor_has_joint_synergy(self) -> None:
        e: list[int] = []
        learned: list[int] = []
        outcome: list[int] = []
        for _ in range(32):
            for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
                e.append(a)
                learned.append(b)
                outcome.append(a ^ b)
        report = synergy_proxy_bits(e, learned, outcome)
        self.assertLess(report["i_evidence_outcome_bits"], 0.001)
        self.assertLess(report["i_learned_outcome_bits"], 0.001)
        self.assertGreater(report["synergy_proxy_bits"], 0.85)

    def test_redundant_copy_has_no_synergy(self) -> None:
        e = [0, 1] * 64
        report = synergy_proxy_bits(e, e, e)
        self.assertLess(report["synergy_proxy_bits"], 1e-8)
        self.assertGreater(report["redundancy_proxy_bits"], 0.9)

    def test_constitutional_gate_is_hard_zero(self) -> None:
        report = triad_alignment_score(
            typed_closure=1.0,
            normalized_synergy=1.0,
            outcome_validity=1.0,
            redundancy_penalty=0.0,
            constitutional_gate=False,
        )
        self.assertEqual(report["alignment"], 0.0)

    def test_top_degree_projection_bias_is_exposed(self) -> None:
        core = [("a", "b"), ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"), ("c", "d")]
        tails = [("a", f"tail-{i}") for i in range(20)]
        report = graph_sampling_audit(_GraphStore(core + tails), "R", cap=4)
        self.assertLess(report["node_coverage"], 0.2)
        self.assertGreater(report["global_closure_delta"], 0.1)
        self.assertFalse(report["sampling_agreement"])

    def test_bridge_field_finds_cross_domain_connectors(self) -> None:
        edges = [
            ("core1/a.py", "core1/b.py"),
            ("core1/a.py", "bridge/c.py"),
            ("core1/b.py", "bridge/c.py"),
            ("core2/e.py", "core2/f.py"),
            ("core2/e.py", "bridge/d.py"),
            ("core2/f.py", "bridge/d.py"),
            ("bridge/c.py", "bridge/d.py"),
        ]
        report = bridge_deconcentration_report(_GraphStore(edges), "R")
        top = {item["path"] for item in report["candidates"][:2]}
        self.assertEqual(top, {"bridge/c.py", "bridge/d.py"})
        self.assertTrue(all(item["shadow_only"] for item in report["candidates"]))
        self.assertFalse(report["policy_effect"])


class InformationLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "cortex.db")
        self.store.attach("R", "rid", root)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_readiness_report_names_measurement_deficits(self) -> None:
        report = interlock_report(self.store, "R")
        readiness = report["readiness"]
        self.assertFalse(readiness["ready_for_shadow_analysis"])
        self.assertEqual(readiness["current"]["valid_outcomes"], 0)
        self.assertEqual(readiness["remaining"]["valid_samples_in_cohort"], 32)
        self.assertEqual(readiness["remaining"]["same_epoch_frames"], 16)
        self.assertIn("collect_same_epoch_frames", readiness["next_actions"])
        self.assertIn("collect_verified_outcome_variation", readiness["next_actions"])
        self.assertFalse(readiness["policy_effect"])

    def _activation(self, activation_id: str) -> None:
        self.store.record_neural_activation(
            "R",
            "session",
            {
                "activation_id": activation_id,
                "task_hash": "task",
                "state_hash": activation_id,
                "records": [],
                "traversed_synapses": [],
            },
        )

    def test_observation_resolves_only_after_witnessed_outcome(self) -> None:
        self._activation("act")
        observed = self.store.record_interlock_observation(
            "R",
            activation_id="act",
            session_id="session",
            body_epoch_id="epoch",
            task_family="code_change",
            evidence_paths=["e.py"],
            learned_paths=["l.py"],
            constitutional_valid=True,
        )
        before = self.store.interlock_observations("R")[0]
        self.assertIsNone(before["outcome_id"])
        self.store.record_outcome(
            "R",
            outcome_id="out",
            activation_id="act",
            status="verified",
            reward=1.0,
            verification_type="test",
            verification_payload={},
            credits=[],
            updates=[],
            apply_updates=False,
        )
        resolved = self.store.resolve_interlock_outcome(
            "R",
            activation_id="act",
            outcome_id="out",
            status="verified",
            reward=1.0,
            verification_type="test",
        )
        after = self.store.interlock_observations("R")[0]
        self.assertTrue(observed["receipt_hash"])
        self.assertTrue(resolved["witness_valid"])
        self.assertEqual(after["outcome_id"], "out")

    def test_route_stamp_cannot_change_score_or_order(self) -> None:
        hits = [
            {"path": "a.py", "score": 0.9, "metadata": {}},
            {"path": "b.py", "score": 0.8, "metadata": {}},
        ]
        self.store.set_setting(
            "interlock_shadow_latest:R",
            {
                "data_ready": True,
                "path_scores": {
                    "b.py": {"alignment": 0.75, "shadow_only": True}
                }
            },
        )
        self.store.set_setting(
            "bridge_shadow_latest:R",
            {
                "path_scores": {
                    "b.py": {"bridge_potential": 0.81, "shadow_only": True}
                }
            },
        )
        before = [(h["path"], h["score"]) for h in hits]
        stamped = stamp_hits_with_interlock_shadow(self.store, "R", hits)
        self.assertEqual(stamped, 1)
        self.assertEqual(before, [(h["path"], h["score"]) for h in hits])
        self.assertTrue(hits[1]["metadata"]["information_interlock_shadow"]["shadow_only"])
        self.assertEqual(
            hits[1]["metadata"]["geometric_bridge_shadow"]["bridge_potential"],
            0.81,
        )

    def test_self_report_does_not_satisfy_witness_gate(self) -> None:
        self._activation("weak-act")
        self.store.record_interlock_observation(
            "R",
            activation_id="weak-act",
            session_id="session",
            body_epoch_id="epoch",
            task_family="analysis",
            evidence_paths=["e.py"],
            learned_paths=["l.py"],
            constitutional_valid=True,
        )
        self.store.record_outcome(
            "R",
            outcome_id="weak-out",
            activation_id="weak-act",
            status="helpful",
            reward=0.4,
            verification_type="self_report",
            verification_payload={},
            credits=[],
            updates=[],
            apply_updates=False,
        )
        resolution = self.store.resolve_interlock_outcome(
            "R",
            activation_id="weak-act",
            outcome_id="weak-out",
            status="helpful",
            reward=0.4,
            verification_type="self_report",
        )
        self.assertFalse(resolution["witness_valid"])

    def test_report_spans_compatible_epochs_and_excludes_old_cohort(self) -> None:
        patterns = ((0, 0), (0, 1), (1, 0), (1, 1))
        self._activation("old-act")
        self.store.record_interlock_observation(
            "R",
            activation_id="old-act",
            session_id="session",
            body_epoch_id="epoch-old",
            task_family="code_change",
            evidence_paths=["e.py"],
            learned_paths=["l.py"],
            constitutional_valid=True,
            metadata={"measurement_cohort_id": "cohort-old"},
        )
        for i in range(128):
            a, b = patterns[i % 4]
            activation_id = f"act{i:03d}"
            outcome_id = f"out{i:03d}"
            self._activation(activation_id)
            self.store.record_interlock_observation(
                "R",
                activation_id=activation_id,
                session_id="session",
                body_epoch_id=f"epoch-new-{i % 2}",
                task_family="code_change",
                evidence_paths=["e.py"] if a else [],
                learned_paths=["l.py"] if b else [],
                constitutional_valid=True,
                metadata={"measurement_cohort_id": "cohort-stable"},
            )
            reward = 1.0 if a ^ b else -1.0
            self.store.record_outcome(
                "R",
                outcome_id=outcome_id,
                activation_id=activation_id,
                status="verified" if reward > 0 else "failed",
                reward=reward,
                verification_type="test",
                verification_payload={},
                credits=[],
                updates=[],
                apply_updates=False,
            )
            self.store.resolve_interlock_outcome(
                "R",
                activation_id=activation_id,
                outcome_id=outcome_id,
                status="verified" if reward > 0 else "failed",
                reward=reward,
                verification_type="test",
            )
        report = interlock_report(self.store, "R")
        self.assertTrue(report["data_ready"])
        self.assertEqual(report["measurement_cohort_id"], "cohort-stable")
        self.assertEqual(len(report["body_epochs_in_cohort"]), 2)
        self.assertEqual(report["counts"]["compatible_cross_epoch"], 64)
        self.assertEqual(report["counts"]["excluded_cross_cohort"], 1)
        self.assertGreater(report["top_interlocks"][0]["synergy_proxy_bits"], 0.85)
        self.assertGreater(report["top_interlocks"][0]["alignment"], 0.0)
        self.assertFalse(report["promotion_gates"]["eligible"])
        readiness = report["readiness"]
        self.assertTrue(readiness["ready_for_shadow_analysis"])
        self.assertEqual(readiness["remaining"]["valid_samples_in_cohort"], 0)
        self.assertEqual(readiness["current"]["outcome_classes"], ["non_positive", "positive"])
        self.assertIn("measure_recall_latency_holdout", readiness["next_actions"])
        self.assertIn("not consciousness", report["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
