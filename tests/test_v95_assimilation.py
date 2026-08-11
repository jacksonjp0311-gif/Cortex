"""Focused adversarial coverage for v9.5 evidence assimilation."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.competence import derive_competence_candidate
from cortex.competence_assimilation import (
    DEFAULT_ANALYSIS_POLICY,
    AssimilationError,
    analyze_evidence_cohort,
    derive_dependence,
    derive_diversity,
    derive_scope,
    ensure_assimilation_tables,
    freeze_evidence_cohort,
    resolve_feedback_observation,
    verify_evidence_cohort,
)
from cortex.competence_distribution import (
    _profile_model_family,
    project_competence,
    register_target_profile,
    submit_distribution_feedback,
)
from cortex.competence_transfer import run_cross_model_transfer_trial
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import (
    FixtureAdapter,
    run_model_circulation,
    verify_model_circulation,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class V95AssimilationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        home = ensure_home(base / "home")
        host = base / "host"
        host.mkdir()
        (host / "README.md").write_text("v9.5 assimilation\n", encoding="utf-8")
        self.store = Store(home / "cortex.db")
        ensure_assimilation_tables(self.store)
        self.repo = "V95Host"
        bootstrap_repository(home, self.store, host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v95-assimilation-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="ok",
        )
        origin = open_symbiotic_session(self.store, self.repo, task="origin")
        run_model_circulation(
            self.store,
            self.repo,
            origin,
            adapter=FixtureAdapter(model_id="origin", text="ok"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        self.competence = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin["session_id"],
            turn_id=1,
            capability={"id": "cap.v95"},
            intended_outcome={"id": "out.v95"},
            counterevidence=[{"kind": "fixture_limit"}],
        )
        run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: FixtureAdapter(
                model_id=f"consumer-{arm}", text="ok"
            ),
            task="structural transfer",
            trial_nonce="v95-structural",
        )
        session = open_symbiotic_session(self.store, self.repo, task="consume")
        profile = register_target_profile(
            self.store,
            self.repo,
            {
                "target_id": "target-a",
                "profile_version": "1",
                "identity": {
                    "system": "target-a",
                    "target_class": "worker-class",
                },
                "environment": {"regime": "R1"},
                "role": "operator",
                "task_family": "procedure",
                "model_capability": {"class": "fixture-test"},
                "available_tools": [],
                "authority_scope": {"propose": True, "execute": False},
                "body_epoch_id": session["body_epoch_id"],
                "required_competence_types": ["successful_procedure"],
                "distribution_mode": "sandbox",
                "freshness_ttl_seconds": 86400,
            },
        )
        self.package = project_competence(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            profile_id=profile["profile_id"],
        )
        self.assertEqual(self.package["status"], "active", self.package)
        circulation = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=FixtureAdapter(model_id="consumer", text="ok"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
            competence_package_id=self.package["package_id"],
        )
        checked = verify_model_circulation(
            self.store,
            self.repo,
            circulation["session_id"],
            turn_id=circulation["turn_id"],
        )
        self.assertTrue(checked["valid"], checked)
        self.use_hash = checked["package_use_receipt_hash"]
        self.feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=self.package["package_id"],
            kind="success",
            package_use_receipt_hash=self.use_hash,
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _table_counts(self) -> tuple[int, int]:
        cohort_count = self.store.db.execute(
            "SELECT COUNT(*) FROM competence_assimilation_cohorts"
        ).fetchone()[0]
        analysis_count = self.store.db.execute(
            "SELECT COUNT(*) FROM competence_assimilation_analyses"
        ).fetchone()[0]
        return int(cohort_count), int(analysis_count)

    @staticmethod
    def _empirical_observation(
        observation_id: str, *, target_id: str, success: bool
    ) -> dict[str, object]:
        return {
            "observation_identity": observation_id,
            "empirically_eligible": True,
            "duplicate_observation": False,
            "outcome_success": success,
            "competence_lineage_hash": "lineage",
            "principal_id": "shared-principal",
            "adapter_registration_id": "adapter-registration",
            "model_identity_hash": "model-identity",
            "provider_family": "provider-family",
            "target_id": target_id,
            "target_class": "shared-target-class",
            "environment_hash": "shared-environment",
            "task_contract_hash": "shared-contract",
            "witness_suite": "shared-witness-suite",
            "transfer_trial_root": "shared-transfer-root",
            "model_family": "shared-model-family",
            "profile_id": "shared-profile-class",
            "package_id": f"package-{target_id}",
            "feedback_created_at": 1.0,
        }

    def test_cohort_is_append_only_and_creation_time_is_hash_bound(self) -> None:
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            evidence_cutoff=time.time(),
            persist=True,
        )
        self.assertTrue(verify_evidence_cohort(self.store, self.repo, cohort["cohort_id"])["valid"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute(
                "UPDATE competence_assimilation_cohorts SET created_at=created_at+1 WHERE cohort_id=?",
                (cohort["cohort_id"],),
            )
        self.store.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute(
                "DELETE FROM competence_assimilation_cohorts WHERE cohort_id=?",
                (cohort["cohort_id"],),
            )
        self.store.db.rollback()

    def test_one_package_use_root_counts_as_one_observation(self) -> None:
        second = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=self.package["package_id"],
            kind="global_contradiction",
            context={"caller": "different representation"},
            package_use_receipt_hash=self.use_hash,
        )
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            feedback_ids=[self.feedback["feedback_id"], second["feedback_id"]],
        )
        identities = {
            item["observation_identity"] for item in cohort["observations"]
        }
        self.assertEqual(len(identities), 1)
        self.assertEqual(cohort["counts"]["duplicate_count"], 1)
        self.assertEqual(
            sum(not item["duplicate_observation"] for item in cohort["observations"]),
            1,
        )

    def test_one_feedback_replayed_one_thousand_times_remains_one_root(self) -> None:
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            feedback_ids=[self.feedback["feedback_id"]] * 1000,
        )
        self.assertEqual(cohort["counts"]["requested_feedback_count"], 1000)
        self.assertEqual(cohort["counts"]["unique_feedback_count"], 1)
        self.assertEqual(cohort["counts"]["raw_evidence_count"], 1)
        self.assertEqual(cohort["counts"]["duplicate_count"], 999)
        self.assertFalse(cohort["selection_production_eligible"])

    def test_synthetic_feedback_is_visible_but_empirically_excluded(self) -> None:
        observation = resolve_feedback_observation(
            self.store,
            self.repo,
            self.feedback["feedback_id"],
            competence_id=self.competence["competence_id"],
        )
        self.assertEqual(observation["evidence_class"], "synthetic")
        self.assertEqual(observation["theta_planes"]["empirical_class"], "fail")
        self.assertFalse(observation["empirically_eligible"])
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
        )
        self.assertEqual(cohort["counts"]["excluded_synthetic_count"], 1)
        self.assertEqual(cohort["counts"]["empirically_eligible_count"], 0)

    def test_explicit_feedback_after_cutoff_fails_freshness(self) -> None:
        observation = resolve_feedback_observation(
            self.store,
            self.repo,
            self.feedback["feedback_id"],
            competence_id=self.competence["competence_id"],
            as_of=float(self.feedback["created_at"]) - 1.0,
        )
        self.assertEqual(observation["theta_planes"]["freshness"], "fail")
        self.assertEqual(
            observation["freshness"]["reason"],
            "feedback_created_after_evidence_cutoff",
        )
        self.assertFalse(observation["empirically_eligible"])

    def test_tampered_package_or_profile_cannot_open_as_of_currentness(self) -> None:
        package_row = self.store.db.execute(
            "SELECT package_json FROM competence_distribution_packages WHERE package_id=?",
            (self.package["package_id"],),
        ).fetchone()
        original_package_json = str(package_row["package_json"])
        forged_package = json.loads(original_package_json)
        forged_package["freshness"]["planes"]["competence"]["expires_at"] = (
            time.time() + 10_000_000
        )
        self.store.db.execute(
            "DROP TRIGGER competence_distribution_packages_no_update"
        )
        self.store.db.execute(
            "UPDATE competence_distribution_packages SET package_json=? WHERE package_id=?",
            (json.dumps(forged_package, sort_keys=True), self.package["package_id"]),
        )
        self.store.db.commit()
        package_observation = resolve_feedback_observation(
            self.store,
            self.repo,
            self.feedback["feedback_id"],
            competence_id=self.competence["competence_id"],
        )
        self.assertFalse(package_observation["empirically_eligible"])
        self.assertTrue(
            any("package_hash_invalid" in item for item in package_observation["errors"]),
            package_observation,
        )

        self.store.db.execute(
            "UPDATE competence_distribution_packages SET package_json=? WHERE package_id=?",
            (original_package_json, self.package["package_id"]),
        )
        profile_row = self.store.db.execute(
            "SELECT profile_json FROM competence_target_profiles WHERE profile_id=?",
            (self.package["profile_id"],),
        ).fetchone()
        forged_profile = json.loads(str(profile_row["profile_json"]))
        forged_profile["freshness_policy"]["feedback_max_age_seconds"] = (
            10_000_000.0
        )
        self.store.db.execute("DROP TRIGGER competence_target_profiles_no_update")
        self.store.db.execute(
            "UPDATE competence_target_profiles SET profile_json=? WHERE profile_id=?",
            (json.dumps(forged_profile, sort_keys=True), self.package["profile_id"]),
        )
        self.store.db.commit()
        profile_observation = resolve_feedback_observation(
            self.store,
            self.repo,
            self.feedback["feedback_id"],
            competence_id=self.competence["competence_id"],
        )
        self.assertFalse(profile_observation["empirically_eligible"])
        self.assertTrue(
            any("profile_hash_invalid" in item for item in profile_observation["errors"]),
            profile_observation,
        )

    def test_caller_cannot_select_only_one_empirical_evidence_class(self) -> None:
        with self.assertRaisesRegex(
            AssimilationError, "evidence classes are a canonical boundary"
        ):
            freeze_evidence_cohort(
                self.store,
                self.repo,
                competence_id=self.competence["competence_id"],
                selection_policy={
                    "required_evidence_classes": ["live_empirical"]
                },
            )

    def test_model_family_axis_does_not_alias_capability_or_model_id(self) -> None:
        self.assertEqual(
            _profile_model_family(
                {
                    "model_capability": {
                        "class": "family-looking-class",
                        "model_id": "family-looking-model-id",
                    }
                }
            ),
            "",
        )
        self.assertEqual(
            _profile_model_family(
                {"model_capability": {"model_family": "host-family"}}
            ),
            "host-family",
        )

    def test_correlated_volume_remains_one_dependence_cluster(self) -> None:
        observations = [
            self._empirical_observation(
                f"observation-{index}", target_id=f"target-{index}", success=True
            )
            for index in range(100)
        ]
        dependence = derive_dependence(observations, DEFAULT_ANALYSIS_POLICY)
        self.assertEqual(dependence["raw_eligible_count"], 100)
        self.assertEqual(dependence["effective_evidence_count"], 1)
        self.assertEqual(dependence["complete_cluster_count"], 1)
        self.assertGreater(
            dependence["pair_relation_counts"]["strongly_dependent"], 0
        )

    def test_caller_global_scope_label_has_no_authority(self) -> None:
        observation = self._empirical_observation(
            "support", target_id="target-a", success=True
        )
        observation["caller_scope_claim"] = "global_contradiction"
        dependence = derive_dependence([observation], DEFAULT_ANALYSIS_POLICY)
        diversity = derive_diversity([observation])
        scope = derive_scope(
            [observation], dependence, diversity, DEFAULT_ANALYSIS_POLICY
        )
        self.assertEqual(scope["derived_scope"], "supporting_evidence")
        self.assertTrue(scope["caller_scope_labels_ignored"])
        self.assertFalse(scope["causal_effect_established"])

    def test_unknown_dependence_never_becomes_independence(self) -> None:
        left = self._empirical_observation("left", target_id="a", success=False)
        right = self._empirical_observation("right", target_id="b", success=False)
        left.pop("target_class")
        right.pop("target_class")
        dependence = derive_dependence([left, right], DEFAULT_ANALYSIS_POLICY)
        self.assertEqual(dependence["effective_evidence_count"], 0)
        self.assertEqual(len(dependence["unresolved_dependence"]), 2)
        diversity = derive_diversity([left, right])
        scope = derive_scope(
            [left, right], dependence, diversity, DEFAULT_ANALYSIS_POLICY
        )
        self.assertEqual(scope["global_contradiction_state"], "unknown")
        self.assertNotEqual(scope["derived_scope"], "global_contradiction_candidate")

    def test_partially_dependent_failures_cannot_open_global_revision(self) -> None:
        left = self._empirical_observation("left", target_id="a", success=False)
        right = self._empirical_observation("right", target_id="b", success=False)
        left.update(
            {
                "adapter_registration_id": "adapter-a",
                "model_identity_hash": "model-a",
                "model_family": "family-a",
                "provider_family": "provider-a",
                "target_class": "class-a",
                "environment_hash": "environment-a",
            }
        )
        right.update(
            {
                "adapter_registration_id": "adapter-b",
                "model_identity_hash": "model-b",
                "model_family": "family-b",
                "provider_family": "provider-b",
                "target_class": "class-b",
                "environment_hash": "environment-b",
            }
        )
        policy = {
            **DEFAULT_ANALYSIS_POLICY,
            "global_contradiction": {
                "minimum_complete_clusters": 2,
                "minimum_diversity": {
                    "targets": 2,
                    "model_families": 2,
                    "provider_families": 2,
                    "environments": 2,
                },
            },
        }
        dependence = derive_dependence([left, right], policy)
        self.assertEqual(dependence["complete_cluster_count"], 2)
        self.assertEqual(dependence["policy_separated_component_count"], 1)
        self.assertEqual(dependence["effective_evidence_count"], 1)
        self.assertIsNone(dependence["independent_support_count"])
        self.assertEqual(
            dependence["pair_relation_counts"]["partially_dependent"], 1
        )
        diversity = derive_diversity([left, right])
        scope = derive_scope([left, right], dependence, diversity, policy)
        self.assertEqual(scope["global_contradiction_state"], "unknown")
        self.assertNotEqual(
            scope["derived_scope"], "global_contradiction_candidate"
        )

    def test_one_principal_cannot_masquerade_as_independent_models(self) -> None:
        left = self._empirical_observation("left", target_id="target-a", success=False)
        right = self._empirical_observation("right", target_id="target-b", success=False)
        for suffix, item in (("a", left), ("b", right)):
            item.update(
                {
                    "adapter_registration_id": f"adapter-{suffix}",
                    "model_identity_hash": f"model-{suffix}",
                    "model_family": f"family-{suffix}",
                    "provider_family": f"provider-{suffix}",
                    "target_class": f"class-{suffix}",
                    "environment_hash": f"environment-{suffix}",
                    "task_contract_hash": f"task-{suffix}",
                    "witness_suite": f"witness-{suffix}",
                    "transfer_trial_root": f"trial-{suffix}",
                    # The canonical host registration principal is shared.
                    # Different model/provider strings cannot erase this
                    # common control surface.
                    "principal_id": "one-host-principal",
                }
            )
        dependence = derive_dependence(
            [left, right], DEFAULT_ANALYSIS_POLICY
        )
        self.assertEqual(
            dependence["pair_relation_counts"]["partially_dependent"], 1
        )
        self.assertEqual(dependence["effective_evidence_count"], 1)
        self.assertEqual(
            dependence["pair_relations"][0]["shared_axes"], ["principal_id"]
        )

        right.pop("principal_id")
        unresolved = derive_dependence(
            [left, right], DEFAULT_ANALYSIS_POLICY
        )
        self.assertEqual(unresolved["unresolved_pair_count"], 1)
        self.assertTrue(unresolved["unresolved_dependence"])

    def test_explicit_subset_is_structural_and_not_production_promotable(self) -> None:
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            feedback_ids=[self.feedback["feedback_id"]],
            persist=True,
        )
        checked = verify_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"]
        )
        self.assertTrue(checked["valid"], checked)
        self.assertEqual(
            cohort["selection_integrity"], "structural_explicit_subset"
        )
        self.assertEqual(cohort["selection_integrity_state"], "unknown")
        self.assertFalse(cohort["selection_production_eligible"])
        self.assertFalse(cohort["production_revision_eligible"])

        analysis = analyze_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"], persist=False
        )
        self.assertEqual(
            analysis["selection_integrity"], "structural_explicit_subset"
        )
        self.assertFalse(analysis["production_revision_eligible"])
        self.assertEqual(analysis["scope"]["derived_scope"], "unresolved")
        self.assertEqual(
            analysis["scope"]["scope_reason"],
            "selection_not_canonically_precommitted_for_production",
        )
        self.assertIn("structural_interpretation", analysis["scope"])
        self.assertFalse(
            analysis["proposed_revision"]["production_revision_eligible"]
        )

    def test_retroactive_cutoff_is_structural_not_production_promotable(self) -> None:
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            evidence_cutoff=time.time(),
            persist=True,
        )
        checked = verify_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"]
        )
        self.assertTrue(checked["valid"], checked)
        self.assertEqual(
            cohort["selection_integrity"], "structural_explicit_cutoff"
        )
        self.assertEqual(cohort["selection_integrity_state"], "unknown")
        self.assertFalse(cohort["selection_production_eligible"])
        analysis = analyze_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"], persist=False
        )
        self.assertFalse(analysis["production_revision_eligible"])
        self.assertEqual(analysis["scope"]["derived_scope"], "unresolved")

    def test_caller_cannot_redefine_independence_or_dependence_admission(self) -> None:
        with self.assertRaisesRegex(
            AssimilationError, "constitutional v9.5 evidence boundary"
        ):
            freeze_evidence_cohort(
                self.store,
                self.repo,
                competence_id=self.competence["competence_id"],
                analysis_policy={"independence_axes": ["target_id"]},
            )
        with self.assertRaisesRegex(
            AssimilationError, "cannot be weakened by the caller"
        ):
            freeze_evidence_cohort(
                self.store,
                self.repo,
                competence_id=self.competence["competence_id"],
                analysis_policy={
                    "dependence_admission": {
                        "strongly_dependent": "independent",
                        "partially_dependent": "independent",
                        "unresolved": "independent",
                    }
                },
            )

    def test_mixed_outcomes_in_one_dependence_component_are_unresolved(self) -> None:
        support = self._empirical_observation(
            "support", target_id="target-a", success=True
        )
        contradiction = self._empirical_observation(
            "contradiction", target_id="target-a", success=False
        )
        dependence = derive_dependence(
            [support, contradiction], DEFAULT_ANALYSIS_POLICY
        )
        diversity = derive_diversity([support, contradiction])
        scope = derive_scope(
            [support, contradiction],
            dependence,
            diversity,
            DEFAULT_ANALYSIS_POLICY,
        )
        self.assertEqual(scope["derived_scope"], "unresolved")
        self.assertEqual(scope["proposed_revision_type"], "unresolved")
        self.assertTrue(scope["uncertainty_increased"])
        self.assertTrue(scope["mixed_dependence_component_ids"])
        self.assertEqual(
            scope["scope_reason"],
            "support_and_contradiction_share_dependence_component",
        )

    def test_target_local_exception_becomes_enforceable_narrowing(self) -> None:
        contradiction = self._empirical_observation(
            "target-failure", target_id="target-r2", success=False
        )
        dependence = derive_dependence(
            [contradiction], DEFAULT_ANALYSIS_POLICY
        )
        diversity = derive_diversity([contradiction])
        scope = derive_scope(
            [contradiction], dependence, diversity, DEFAULT_ANALYSIS_POLICY
        )
        self.assertEqual(scope["derived_scope"], "local_exception")
        self.assertEqual(scope["proposed_revision_type"], "narrow_applicability")
        self.assertEqual(
            scope["proposed_applicability_change"],
            {"exclude_target_ids": ["target-r2"]},
        )

    def test_disjoint_environment_resolves_scoped_within_lineage_contrast(self) -> None:
        support = self._empirical_observation(
            "support", target_id="target-a", success=True
        )
        contradiction = self._empirical_observation(
            "contradiction", target_id="target-a", success=False
        )
        support["environment_hash"] = "environment-r1"
        contradiction["environment_hash"] = "environment-r2"
        dependence = derive_dependence(
            [support, contradiction], DEFAULT_ANALYSIS_POLICY
        )
        diversity = derive_diversity([support, contradiction])
        scope = derive_scope(
            [support, contradiction],
            dependence,
            diversity,
            DEFAULT_ANALYSIS_POLICY,
        )
        self.assertEqual(scope["derived_scope"], "environment_specific_exception")
        self.assertEqual(scope["proposed_revision_type"], "narrow_applicability")
        self.assertEqual(
            scope["proposed_applicability_change"],
            {"exclude_environment_hashes": ["environment-r2"]},
        )
        self.assertEqual(scope["discriminator"]["state"], "pass")
        self.assertTrue(scope["mixed_dependence_component_ids"])
        self.assertTrue(scope["dependence_uncertainty_present"])
        self.assertEqual(
            scope["dependence_uncertainty_state"],
            "resolved_by_disjoint_discriminator",
        )
        self.assertFalse(scope["uncertainty_increased"])

    def test_missing_discriminator_values_cannot_create_specialization(self) -> None:
        support = self._empirical_observation(
            "support", target_id="target-a", success=True
        )
        contradiction = self._empirical_observation(
            "contradiction", target_id="target-b", success=False
        )
        for item in (support, contradiction):
            item.update(
                {
                    "target_id": "",
                    "target_class": "",
                    "environment_hash": "",
                    "model_family": "",
                }
            )
        support.update(
            {
                "adapter_registration_id": "adapter-a",
                "model_identity_hash": "model-a",
                "provider_family": "provider-a",
                "task_contract_hash": "task-a",
                "witness_suite": "witness-a",
                "transfer_trial_root": "transfer-a",
            }
        )
        contradiction.update(
            {
                "adapter_registration_id": "adapter-b",
                "model_identity_hash": "model-b",
                "provider_family": "provider-b",
                "task_contract_hash": "task-b",
                "witness_suite": "witness-b",
                "transfer_trial_root": "transfer-b",
            }
        )
        complete_axes = [
            "adapter_registration_id",
            "model_identity_hash",
            "provider_family",
            "task_contract_hash",
            "witness_suite",
            "transfer_trial_root",
        ]
        policy = {
            **DEFAULT_ANALYSIS_POLICY,
            "dependence_axes": complete_axes,
            "independence_axes": complete_axes,
        }
        dependence = derive_dependence([support, contradiction], policy)
        diversity = derive_diversity([support, contradiction])
        scope = derive_scope(
            [support, contradiction], dependence, diversity, policy
        )
        self.assertEqual(scope["derived_scope"], "unresolved")
        self.assertEqual(scope["proposed_revision_type"], "unresolved")
        self.assertEqual(scope["discriminator"]["state"], "unknown")
        self.assertEqual(scope["proposed_applicability_change"], {})
        self.assertEqual(
            scope["scope_reason"],
            "support_and_contradiction_lack_disjoint_canonical_discriminator",
        )

    def test_verify_and_advisory_analysis_are_read_only(self) -> None:
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            persist=True,
        )
        before = self._table_counts()
        verification = verify_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"]
        )
        analysis = analyze_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"], persist=False
        )
        after = self._table_counts()
        self.assertTrue(verification["valid"], verification)
        self.assertEqual(before, after)
        self.assertEqual(analysis["persistence"], "advisory_only")
        for flag in (
            "host_mutate_authorized",
            "execution_authorized",
            "memory_admission_authorized",
            "policy_effect",
            "automatic_broadcast",
            "automatic_global_revision",
        ):
            self.assertFalse(analysis[flag])

    def test_post_cutoff_feedback_requires_a_new_cohort(self) -> None:
        cutoff = time.time()
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.competence["competence_id"],
            evidence_cutoff=cutoff,
            persist=True,
        )
        submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=self.package["package_id"],
            kind="counterevidence",
            context={"arrived": "later"},
            package_use_receipt_hash=self.use_hash,
        )
        checked = verify_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"]
        )
        self.assertTrue(checked["valid"], checked)
        self.assertEqual(
            checked["cohort"]["feedback_ids"], cohort["feedback_ids"]
        )


if __name__ == "__main__":
    unittest.main()
