"""Adversarial tests for the alpha.12 governed autonomy differential."""

from __future__ import annotations

import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from cortex.autonomy_differential import (
    AutonomyDifferentialError,
    create_autonomy_differential_preregistration,
    evaluate_autonomy_differential,
    randomization_seed_commitment,
    run_autonomy_differential_case,
    verify_autonomy_differential_preregistration,
)
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter, ToolRegistry
from cortex.store import Store


class RenamedFixtureAdapter(ScriptedAgentAdapter):
    provider_family = "frontier-looking-provider"
    adapter_id = "external-looking-adapter"


class V100Alpha12AutonomyDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("alpha12\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(
            ["git", "config", "user.email", "alpha12@example.invalid"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Alpha 12 Fixture"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        self.home = ensure_home(self.base / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha12Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.seed = "alpha12-randomization-seed"
        self.tools = ToolRegistry()
        self.grant = CapabilityGrant(
            workspace_root=str(self.host),
            allowed_tools=(),
            max_tool_calls=0,
            issued_at=time.time() - 1,
            expires_at=time.time() + 300,
        )
        self.cases = [
            {
                "case_id": f"case-{index}",
                "task": f"Solve frozen case {index}",
                "task_family": "text_fixture",
                "evaluation_contract": {
                    "contract_id": f"eval-{index}",
                    "task_type": "text_contains",
                    "target_field": "text",
                    "expected_value": "PASS",
                },
            }
            for index in range(1, 5)
        ]

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    @staticmethod
    def adapter(text: str, *, renamed: bool = False, model_id: str = "same-model"):
        cls = RenamedFixtureAdapter if renamed else ScriptedAgentAdapter
        return cls(
            [
                {
                    "public_output": text,
                    "finish_reason": "stop",
                    "success": True,
                    "verified": True,
                    "token_usage": {
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "total_tokens": 12,
                    },
                    "cost": {"total": 0.001},
                }
            ],
            model_id=model_id,
        )

    def preregister(self, *, renamed: bool = False):
        return create_autonomy_differential_preregistration(
            self.store,
            self.repo,
            self.host,
            adapter=self.adapter("template", renamed=renamed),
            tools=self.tools,
            grant=self.grant,
            cases=self.cases,
            randomization_seed_commitment=randomization_seed_commitment(self.seed),
            minimum_effect=0.10,
            maximum_regression_rate=0.25,
            alpha=0.05,
            maximum_total_tokens=100,
            maximum_latency_ms=60_000,
            maximum_cost=1.0,
        )

    def run_case(self, prereg, case_id, control, cortex, *, renamed=False):
        return run_autonomy_differential_case(
            self.store,
            self.repo,
            self.host,
            preregistration_id=prereg["preregistration_id"],
            case_id=case_id,
            randomization_seed=self.seed,
            control_adapter=self.adapter(control, renamed=renamed),
            cortex_adapter=self.adapter(cortex, renamed=renamed),
            tools=self.tools,
            grant=self.grant,
        )

    def test_preregistration_freezes_model_tools_grant_source_and_evaluator(self) -> None:
        prereg = self.preregister()
        check = verify_autonomy_differential_preregistration(
            self.store, self.repo, prereg["preregistration_id"]
        )
        self.assertTrue(check["valid"])
        self.assertEqual(prereg["status"], "frozen_before_execution")
        self.assertEqual(prereg["planned_cases"], 4)
        self.assertEqual(prereg["power_analysis"]["state"], "unresolved")
        self.assertEqual(prereg["power_analysis"]["max_cases"], 4)
        self.assertFalse(prereg["model_identity_used_in_scoring"])
        self.assertFalse(prereg["host_mutate_authorized"])
        self.assertFalse(prereg["execution_authorized"])

    def test_control_receives_no_cortex_evidence_and_success_is_independent(self) -> None:
        prereg = self.preregister()
        case = self.run_case(prereg, "case-1", "model says success but fails", "PASS")
        control_hash = case["arms"]["task_only_control"]["trajectory_receipt_hash"]
        control = self.store.symbiotic_receipt(control_hash, repo=self.repo)
        request_context = control["requests"][0]["context_projection"]
        self.assertEqual(request_context["experimental_arm"], "task_only_control")
        self.assertEqual(request_context["evidence_digests"], [])
        self.assertEqual(request_context["memory_episode_digests"], [])
        self.assertFalse(case["arms"]["task_only_control"]["task_success"])
        self.assertTrue(case["arms"]["cortex_governed"]["task_success"])
        self.assertFalse(case["caller_success_fields_authoritative"])

    def test_fixture_renaming_cannot_create_empirical_advantage(self) -> None:
        prereg = self.preregister(renamed=True)
        outcomes = {
            "case-1": ("FAIL", "PASS"),
            "case-2": ("PASS", "PASS"),
            "case-3": ("PASS", "FAIL"),
            "case-4": ("FAIL", "PASS"),
        }
        for case_id, (control, cortex) in outcomes.items():
            row = self.run_case(
                prereg, case_id, control, cortex, renamed=True
            )
            self.assertEqual(row["evidence_class"], "synthetic")
        result = evaluate_autonomy_differential(
            self.store,
            self.repo,
            preregistration_id=prereg["preregistration_id"],
        )
        self.assertEqual(result["status"], "STRUCTURAL_DIFFERENTIAL_MEASURED")
        self.assertEqual(
            result["exact_matched_binary"]["paired_risk_difference"], 0.25
        )
        self.assertFalse(result["gates"]["live_empirical_evidence"])
        self.assertFalse(result["empirical_advantage_established"])
        self.assertFalse(result["host_mutate_authorized"])
        self.assertFalse(result["execution_authorized"])

    def test_wrong_model_grant_seed_and_source_fail_closed(self) -> None:
        prereg = self.preregister()
        with self.assertRaisesRegex(AutonomyDifferentialError, "seed"):
            run_autonomy_differential_case(
                self.store,
                self.repo,
                self.host,
                preregistration_id=prereg["preregistration_id"],
                case_id="case-1",
                randomization_seed="wrong",
                control_adapter=self.adapter("PASS"),
                cortex_adapter=self.adapter("PASS"),
                tools=self.tools,
                grant=self.grant,
            )
        with self.assertRaisesRegex(AutonomyDifferentialError, "model identity"):
            run_autonomy_differential_case(
                self.store,
                self.repo,
                self.host,
                preregistration_id=prereg["preregistration_id"],
                case_id="case-1",
                randomization_seed=self.seed,
                control_adapter=self.adapter("PASS", model_id="other"),
                cortex_adapter=self.adapter("PASS"),
                tools=self.tools,
                grant=self.grant,
            )
        changed_grant = CapabilityGrant(
            workspace_root=str(self.host),
            max_tool_calls=1,
            issued_at=time.time() - 1,
            expires_at=time.time() + 300,
        )
        with self.assertRaisesRegex(AutonomyDifferentialError, "capability profile"):
            run_autonomy_differential_case(
                self.store,
                self.repo,
                self.host,
                preregistration_id=prereg["preregistration_id"],
                case_id="case-1",
                randomization_seed=self.seed,
                control_adapter=self.adapter("PASS"),
                cortex_adapter=self.adapter("PASS"),
                tools=self.tools,
                grant=changed_grant,
            )
        (self.host / "drift.txt").write_text("drift\n", encoding="utf-8")
        subprocess.run(["git", "add", "drift.txt"], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "drift"], cwd=self.host, check=True)
        with self.assertRaisesRegex(AutonomyDifferentialError, "source snapshot"):
            self.run_case(prereg, "case-1", "PASS", "PASS")

    def test_incomplete_panel_is_held_and_case_replay_is_exactly_once(self) -> None:
        prereg = self.preregister()
        first = self.run_case(prereg, "case-1", "FAIL", "PASS")
        replay = self.run_case(prereg, "case-1", "PASS", "FAIL")
        self.assertTrue(replay["duplicate"])
        self.assertEqual(replay["receipt_hash"], first["receipt_hash"])
        result = evaluate_autonomy_differential(
            self.store,
            self.repo,
            preregistration_id=prereg["preregistration_id"],
            persist=False,
        )
        self.assertEqual(result["status"], "STRUCTURAL_DIFFERENTIAL_MEASURED")
        self.assertFalse(result["gates"]["planned_sample_complete"])
        self.assertFalse(result["empirical_advantage_established"])


if __name__ == "__main__":
    unittest.main()
