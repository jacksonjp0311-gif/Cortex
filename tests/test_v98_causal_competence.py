"""v9.8 semantic-distillation and preregistered causal evidence tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.causal_trial import (
    CausalTrialError,
    create_causal_preregistration,
    evaluate_preregistered_causal_trial,
    exact_matched_binary,
    holm_adjust,
    matched_binary_power_plan,
    paired_bootstrap_interval,
)
from cortex.competence import derive_competence_candidate
from cortex.competence_transfer import run_cross_model_transfer_trial
from cortex.config import ensure_home
from cortex.distillation_witness import (
    create_distillation_witness,
    resolve_distillation_support,
    verify_distillation_witness,
)
from cortex.discriminability import assess_task_panel
from cortex.discriminative_forge import TASK_FAMILIES, build_difficulty_ladder_corpus, build_held_out_bundle
from cortex.information_calibration import calibrate_difficulty_ladders
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class V98CausalCompetenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        host = base / "host"
        host.mkdir()
        (host / "README.md").write_text("v9.8 fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V98Host"
        bootstrap_repository(self.home, self.store, host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v98-exact-token-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="TARGET",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _origin(self, model: str = "fixture-origin") -> str:
        session = open_symbiotic_session(self.store, self.repo, task="v9.8 origin")
        run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=FixtureAdapter(model_id=model, text="TARGET"),
            task_contract=self.contract,
            observed_result={"text": "TARGET"},
        )
        return str(session["session_id"])

    def _candidate(self, *, procedure: str = "TARGET", description: str = "first"):
        return derive_competence_candidate(
            self.store,
            self.repo,
            session_id=self._origin(f"origin-{procedure}-{description}"),
            turn_id=1,
            capability={"id": "cap.v98", "procedure": procedure, "description": description},
            intended_outcome={"id": "out.v98", "criterion": "TARGET"},
        )

    def test_semantic_id_binds_operational_siblings_but_not_harmless_prose(self) -> None:
        first = self._candidate(procedure="TARGET", description="first wording")
        prose = self._candidate(procedure="TARGET", description="different wording")
        changed = self._candidate(procedure="DIFFERENT", description="first wording")
        self.assertEqual(first["competence_id"], prose["competence_id"])
        self.assertTrue(prose["duplicate"])
        self.assertNotEqual(first["competence_id"], changed["competence_id"])

    def test_semantic_witness_reconstructs_exact_public_support(self) -> None:
        candidate = self._candidate()
        self.assertEqual(candidate["semantic_support_state"], "pass")
        self.assertTrue(candidate["distillation_witness_id"])
        witness = create_distillation_witness(self.store, self.repo, candidate["competence_id"])
        self.assertEqual(witness["status"], "SUPPORTED", witness)
        self.assertEqual(witness["unknown_count"], 0)
        checked = verify_distillation_witness(self.store, self.repo, witness["witness_id"])
        self.assertTrue(checked["valid"], checked["errors"])
        self.assertEqual(checked["state"], "pass")
        self.assertEqual(witness["counterevidence_completeness"], "UNKNOWN")

    def test_identifier_only_abstraction_cannot_self_support(self) -> None:
        candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=self._origin("identifier-only-origin"),
            turn_id=1,
            capability={"id": "cap.label.only"},
            intended_outcome={"id": "out.label.only"},
        )
        support = resolve_distillation_support(
            self.store, self.repo, candidate["competence_id"]
        )
        self.assertEqual(support["state"], "unknown", support)
        witness = create_distillation_witness(
            self.store, self.repo, candidate["competence_id"]
        )
        self.assertEqual(witness["meaningful_operational_claim_count"], 0)
        self.assertEqual(
            witness["required_operational_surfaces"],
            {"capability": False, "intended_outcome": False},
        )
        self.assertFalse(witness["distribution_authorized"])
        self.assertFalse(witness["execution_authorized"])

    def test_structural_trial_binds_semantic_support_without_promoting_it(self) -> None:
        candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=self._origin("structural-origin"),
            turn_id=1,
            capability={"id": "cap.structural.only"},
            intended_outcome={"id": "out.structural.only"},
        )
        trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: FixtureAdapter(
                model_id=f"structural-{arm}", text="TARGET"
            ),
            task="structural semantic-seal trial",
            trial_nonce="v987-semantic-unknown",
        )
        self.assertEqual(trial["distillation_support"]["state"], "unknown")
        self.assertFalse(trial["empirical_transfer_established"])
        self.assertFalse(trial["distribution_authorized"])
        self.assertFalse(trial["execution_authorized"])

    def test_unsupported_generalization_remains_unknown(self) -> None:
        candidate = self._candidate(procedure="generalizes to every repository")
        witness = create_distillation_witness(self.store, self.repo, candidate["competence_id"])
        self.assertEqual(witness["status"], "UNKNOWN")
        self.assertGreater(witness["unknown_count"], 0)
        self.assertFalse(witness["generalization_authorized"])

    def test_exact_matched_binary_and_n1_uncertainty_are_honest(self) -> None:
        panel = exact_matched_binary([0, 0, 0, 1], [1, 1, 1, 1])
        self.assertEqual(panel["benefit_pairs"], 3)
        self.assertEqual(panel["paired_risk_difference"], 0.75)
        self.assertEqual(panel["exact_two_sided_p"], 0.25)
        singleton = exact_matched_binary([1], [1])
        self.assertEqual(singleton["variance_state"], "not_estimable")
        self.assertIsNone(singleton["confidence_interval"])
        adjusted = holm_adjust({"a": 0.01, "b": 0.03, "c": 0.20})
        self.assertEqual(adjusted, {"a": 0.03, "b": 0.06, "c": 0.2})

    def test_paired_interval_and_power_plan_are_frozen_and_reproducible(self) -> None:
        first = paired_bootstrap_interval(
            [0, 0, 0, 1], [1, 1, 1, 1], seed_material="v98-test"
        )
        second = paired_bootstrap_interval(
            [0, 0, 0, 1], [1, 1, 1, 1], seed_material="v98-test"
        )
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "estimated")
        self.assertEqual(first["interval"], [0.25, 1.0])
        plan = matched_binary_power_plan(
            minimum_effect=0.20,
            expected_discordance=0.40,
            alpha=0.05 / 3,
            target_power=0.80,
        )
        self.assertEqual(plan["state"], "complete")
        self.assertGreaterEqual(plan["required_cases"], 2)
        self.assertGreaterEqual(plan["achieved_power"], 0.80)

    def test_preregistration_rejects_model_residual_paths(self) -> None:
        candidate = self._candidate()
        witness = create_distillation_witness(self.store, self.repo, candidate["competence_id"])
        with self.assertRaises(CausalTrialError):
            create_causal_preregistration(
                self.store,
                self.repo,
                competence_id=candidate["competence_id"],
                distillation_witness_id=witness["witness_id"],
                task_corpus_hash="corpus",
                task_contract_hashes=[self.contract.contract_hash],
                planned_cases=2,
                randomization_seed_commitment="seed",
                minimum_effects={"continuity": 0.1, "distillation": 0.1, "governance": 0.1},
                negative_transfer_threshold=0.1,
                alpha=0.05,
                stopping_rule={"model_id": "forbidden"},
                exclusion_rules=[],
            )

    def test_synthetic_post_preregistered_trial_remains_held(self) -> None:
        candidate = self._candidate()
        witness = create_distillation_witness(self.store, self.repo, candidate["competence_id"])
        prereg = create_causal_preregistration(
            self.store,
            self.repo,
            competence_id=candidate["competence_id"],
            distillation_witness_id=witness["witness_id"],
            task_corpus_hash="corpus-v98",
            task_contract_hashes=[self.contract.contract_hash],
            planned_cases=2,
            randomization_seed_commitment="seed-commitment",
            minimum_effects={"continuity": 0.1, "distillation": 0.1, "governance": 0.1},
            negative_transfer_threshold=0.1,
            alpha=0.05,
            stopping_rule={"kind": "fixed_sample", "planned_cases": 2},
            exclusion_rules=["canonical trial invalid"],
            arms=list("ABCDE"),
            task_family_strata=["fixture_family"],
            calibration_receipt=assess_task_panel({"fixture_family": [0, 1, 0, 1]}),
        )
        trials = []
        for index in range(2):
            trial = run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=candidate["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: FixtureAdapter(text="TARGET" if arm in {"D", "E"} else "MISS"),
                task=f"preregistered case {index}",
                measurement_cohort_id="v98-cohort",
                trial_nonce=f"v98-{index}",
            )
            trials.append(str(trial["trial_id"]))
        result = evaluate_preregistered_causal_trial(
            self.store,
            self.repo,
            preregistration_id=prereg["preregistration_id"],
            trial_ids=trials,
        )
        self.assertEqual(result["status"], "CAUSAL_TRIAL_HELD")
        self.assertFalse(result["promotion_eligible"])
        self.assertIn("live_empirical_evidence", result["failed_gates"])
        self.assertTrue(result["gates"]["development_calibration_bound"])
        self.assertFalse(result["model_identity_used_in_scoring"])
        self.assertFalse(result["host_mutate_authorized"])
        self.assertFalse(result["execution_authorized"])

    def test_v982_preregistration_binds_public_heldout_seal_without_answers(self) -> None:
        candidate = self._candidate()
        witness = create_distillation_witness(self.store, self.repo, candidate["competence_id"])
        development = build_difficulty_ladder_corpus(seed="v982-dev", maximum_level=3, variants_per_level=2)
        calibration = calibrate_difficulty_ladders({
            family: {"1": [1, 1, 1, 1], "2": [1, 0, 1, 0], "3": [0, 0, 0, 0]}
            for family in TASK_FAMILIES
        })
        bundle = build_held_out_bundle(
            calibration, development, secret_seed="host-secret-test-seed", cases_per_family=2
        )
        manifest = bundle["manifest"]
        prereg = create_causal_preregistration(
            self.store,
            self.repo,
            competence_id=candidate["competence_id"],
            distillation_witness_id=witness["witness_id"],
            task_corpus_hash=manifest["corpus_hash"],
            task_contract_hashes=[self.contract.contract_hash],
            planned_cases=2,
            randomization_seed_commitment="confirmatory-seed-commitment",
            minimum_effects={"continuity": 0.1, "distillation": 0.1, "governance": 0.1},
            negative_transfer_threshold=0.1,
            alpha=0.05,
            stopping_rule={"kind": "fixed_sample", "planned_cases": 2},
            exclusion_rules=["canonical trial invalid"],
            task_family_strata=list(TASK_FAMILIES),
            difficulty_calibration_receipt=calibration,
            heldout_corpus_manifest=manifest,
        )
        self.assertEqual(prereg["discriminability_calibration"]["state"], "pass")
        self.assertEqual(prereg["heldout_corpus_seal"]["state"], "pass")
        self.assertFalse(prereg["heldout_corpus_seal"]["answers_present"])
        self.assertNotIn("host-secret-test-seed", str(prereg))
        self.assertNotIn("answer_key", prereg)


if __name__ == "__main__":
    unittest.main()
