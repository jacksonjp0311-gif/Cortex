"""v9.7 provider-neutral empirical differentiation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.competence import derive_competence_candidate
from cortex.competence_differentiation import (
    DifferentiationError,
    evaluate_competence_differentiation,
    verify_differentiation_receipt,
)
from cortex.competence_transfer import run_cross_model_transfer_trial
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class CaseAdapter(FixtureAdapter):
    def __init__(
        self,
        arm: str,
        *,
        baseline_success: bool,
        competence_success: bool,
        family: str,
        case: int,
    ) -> None:
        super().__init__(model_id=f"fresh-{family}-{case}-{arm}")
        self.provider_family = family
        self.arm = arm
        self.baseline_success = baseline_success
        self.competence_success = competence_success

    def invoke(self, request):
        included = self.arm in {"D", "E"}
        success = self.competence_success if included else self.baseline_success
        return {
            "public_output": {"text": "TARGET" if success else "MISS"},
            "proposal": {"proposed_action": "return bounded public result"},
            "declared_uncertainty": 0.1,
            "request_hash": request.request_hash,
        }


class V97CompetenceDifferentiationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        host = base / "host"
        host.mkdir()
        (host / "README.md").write_text("v9.7 fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V97Host"
        bootstrap_repository(self.home, self.store, host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v97-differentiation-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="TARGET",
        )
        origin = open_symbiotic_session(self.store, self.repo, task="origin")
        run_model_circulation(
            self.store,
            self.repo,
            origin,
            adapter=FixtureAdapter(model_id="origin-fixture"),
            task_contract=self.contract,
            observed_result={"text": "TARGET"},
        )
        self.candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin["session_id"],
            turn_id=1,
            capability={"id": "cap.v97", "procedure": "emit TARGET when applicable"},
            intended_outcome={"id": "out.v97"},
            counterevidence=[{"kind": "limit", "text": "synthetic test only"}],
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _trial(
        self,
        case: int,
        *,
        baseline_success: bool,
        competence_success: bool = True,
        family: str = "fixture-family",
        cohort: str = "v97-cohort",
    ) -> str:
        trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: CaseAdapter(
                arm,
                baseline_success=baseline_success,
                competence_success=competence_success,
                family=family,
                case=case,
            ),
            task=f"case {case}",
            measurement_cohort_id=cohort,
            trial_nonce=f"case-{family}-{case}",
        )
        return str(trial["trial_id"])

    def _structural_policy(self) -> dict[str, object]:
        return {
            "minimum_cases": 4,
            "minimum_effect": 0.20,
            "maximum_baseline_mean": 0.90,
            "minimum_competence_mean": 0.50,
            "minimum_dynamic_range": 0.50,
            "confidence_z": 1.0,
            "maximum_negative_transfer_rate": 0.0,
            "required_evidence_class": "structural",
            "require_same_epoch": True,
            "require_same_measurement_cohort": True,
        }

    def test_matched_cohort_establishes_structural_differentiation(self) -> None:
        trials = [
            self._trial(index, baseline_success=(index == 0)) for index in range(4)
        ]
        receipt = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=trials,
            policy=self._structural_policy(),
            cohort_nonce="positive",
        )
        self.assertEqual(receipt["status"], "STRUCTURAL_DIFFERENTIATION_PASS")
        self.assertTrue(receipt["promotion_eligible"])
        self.assertEqual(receipt["discriminability"]["baseline_mean"], 0.25)
        self.assertEqual(receipt["paired_effects"]["continuity"]["mean"], 0.75)
        self.assertGreater(
            receipt["paired_effects"]["continuity"]["lower_confidence_bound"],
            0.20,
        )
        checked = verify_differentiation_receipt(
            self.store, self.repo, receipt["cohort_id"]
        )
        self.assertTrue(checked["valid"], checked["errors"])
        self.assertFalse(checked["distribution_authorized"])

    def test_ceiling_effect_is_detected_and_blocks_promotion(self) -> None:
        trials = [self._trial(index, baseline_success=True) for index in range(4)]
        receipt = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=trials,
            policy=self._structural_policy(),
            cohort_nonce="ceiling",
        )
        self.assertTrue(receipt["discriminability"]["ceiling_detected"])
        self.assertIn("ceiling", receipt["failed_gates"])
        self.assertIn("dynamic_range", receipt["failed_gates"])
        self.assertFalse(receipt["promotion_eligible"])

    def test_synthetic_trials_cannot_satisfy_empirical_policy(self) -> None:
        trials = [
            self._trial(index, baseline_success=(index == 0)) for index in range(4)
        ]
        policy = self._structural_policy()
        policy["required_evidence_class"] = "live_empirical"
        receipt = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=trials,
            policy=policy,
            cohort_nonce="empirical-block",
        )
        self.assertEqual(receipt["status"], "DIFFERENTIATION_HELD")
        self.assertIn("evidence_class", receipt["failed_gates"])

    def test_model_provider_and_endpoint_cannot_enter_policy(self) -> None:
        for key in ("model_id", "provider_family", "endpoint", "preferred_model"):
            with self.subTest(key=key), self.assertRaises(DifferentiationError):
                evaluate_competence_differentiation(
                    self.store,
                    self.repo,
                    competence_id=self.candidate["competence_id"],
                    trial_ids=["x" * 64],
                    policy={key: "residual-path"},
                    cohort_nonce="reject",
                    persist=False,
                )

    def test_provider_labels_do_not_change_effect_or_gate_semantics(self) -> None:
        first = [
            self._trial(
                index,
                baseline_success=(index == 0),
                family="provider-shaped-alpha",
                cohort="cohort-alpha",
            )
            for index in range(4)
        ]
        second = [
            self._trial(
                index + 10,
                baseline_success=(index == 0),
                family="provider-shaped-beta",
                cohort="cohort-beta",
            )
            for index in range(4)
        ]
        a = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=first,
            policy=self._structural_policy(),
            cohort_nonce="provider-a",
            persist=False,
        )
        b = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=second,
            policy=self._structural_policy(),
            cohort_nonce="provider-b",
            persist=False,
        )
        self.assertEqual(a["paired_effects"], b["paired_effects"])
        self.assertEqual(a["discriminability"], b["discriminability"])
        self.assertEqual(a["status"], b["status"])
        self.assertFalse(a["model_identity_used_in_scoring"])
        self.assertFalse(a["provider_identity_used_in_scoring"])

    def test_negative_transfer_is_conserved_and_blocks(self) -> None:
        trials = [
            self._trial(
                index,
                baseline_success=True,
                competence_success=(index != 0),
            )
            for index in range(4)
        ]
        policy = self._structural_policy()
        policy["maximum_baseline_mean"] = 1.1
        policy["minimum_effect"] = -1.0
        receipt = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=trials,
            policy=policy,
            cohort_nonce="negative",
        )
        self.assertEqual(receipt["negative_transfer_rate"], 0.25)
        self.assertIn("negative_transfer", receipt["failed_gates"])
        self.assertFalse(receipt["promotion_eligible"])

    def test_authority_flags_remain_false(self) -> None:
        trials = [
            self._trial(index, baseline_success=(index == 0)) for index in range(4)
        ]
        receipt = evaluate_competence_differentiation(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            trial_ids=trials,
            policy=self._structural_policy(),
            cohort_nonce="authority",
        )
        for key in (
            "distribution_authorized",
            "memory_admission_authorized",
            "policy_effect",
            "execution_authorized",
            "host_mutate_authorized",
        ):
            self.assertIs(receipt[key], False)


if __name__ == "__main__":
    unittest.main()
