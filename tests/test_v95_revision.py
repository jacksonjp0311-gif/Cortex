"""Focused v9.5 independent revision and promotion tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.competence import (
    CompetenceAdmissionError,
    append_competence_candidate,
    competence_is_applicable,
    derive_competence_candidate,
    get_competence_candidate,
    verify_competence_candidate,
)
from cortex.competence_assimilation import (
    analyze_evidence_cohort,
    freeze_evidence_cohort,
    verify_evidence_cohort,
)
from cortex.competence_distribution import (
    _freshness,
    get_target_profile,
    list_target_profiles,
    project_competence,
    register_target_profile,
    submit_distribution_feedback,
)
from cortex.competence_revision import (
    CompetenceRevisionError,
    _sha,
    _without_runtime,
    build_revision_candidate,
    competence_successor_state,
    get_revision_candidate,
    get_revision_promotion,
    get_revision_verification,
    list_revision_promotions,
    persist_revision_candidate,
    promote_revision_candidate,
    verify_revision_candidate,
    verify_revision_promotion,
    verify_successor_lineage,
)
from cortex.competence_transfer import (
    TransferTrialError,
    append_transfer_trial,
    run_cross_model_transfer_trial,
    verify_transfer_trial,
)
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class _EphemeralExternalAdapter:
    """A host-registered test boundary, not a real empirical model run."""

    provider_family = "v95-test-boundary"
    adapter_id = "tests.v95.ephemeral-external"
    adapter_version = "1"
    model_version = "1"

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    def invoke(self, request):
        context = request.context_projection.get("predictions", {}).get(
            "transfer_context", {}
        )
        included = bool(context.get("competence_included"))
        return {
            "public_output": {"text": "ok" if included else "baseline"},
            "proposal": {"proposed_action": "report public result"},
            "request_hash": request.request_hash,
        }


class V95RevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("v9.5 revision fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V95RevisionHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Operator",
            secret="ephemeral-principal-secret",
        )
        self.contract = TaskEvaluationContract(
            contract_id="v95-revision-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="ok",
        )
        origin = open_symbiotic_session(self.store, self.repo, task="origin")
        run_model_circulation(
            self.store,
            self.repo,
            origin,
            adapter=self._registered("origin"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        self.parent = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin["session_id"],
            turn_id=1,
            capability={"id": "cap.v95.revision"},
            intended_outcome={"id": "out.v95.revision"},
            counterevidence=[{"kind": "known_origin_limit"}],
        )
        self.trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.parent["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: self._registered(f"fresh-{arm}"),
            task="v9.5 controlled transfer fixture",
            trial_nonce="v95-revision",
        )
        self.assertEqual(
            self.trial["portability_status"], "empirical_cross_model_verified"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _registered(self, model_id: str) -> _EphemeralExternalAdapter:
        adapter = _EphemeralExternalAdapter(model_id)
        register_adapter_provenance(
            self.store,
            self.repo,
            adapter,
            boundary_kind="external_api",
            principal_id="operator",
            principal_secret="ephemeral-principal-secret",
            endpoint_descriptor={"kind": "ephemeral-test-boundary"},
            model_family="v95-test-boundary",
            capability_class="test-live",
        )
        return adapter

    def _feedback(self, index: int, regime: str, success: bool) -> str:
        session = open_symbiotic_session(
            self.store, self.repo, task=f"consume-{index}"
        )
        profile = register_target_profile(
            self.store,
            self.repo,
            {
                "target_id": f"target-{index}",
                "profile_version": "1",
                "identity": {
                    "system": f"target-{index}",
                    "target_class": "worker",
                },
                "environment": {"regime": regime},
                "role": "operator",
                "task_family": "procedure",
                "model_capability": {"class": "test-live"},
                "available_tools": [],
                "authority_scope": {"propose": True, "execute": False},
                "body_epoch_id": session["body_epoch_id"],
                "privacy_boundaries": {"local_only": True},
                "required_competence_types": ["successful_procedure"],
                "prohibited_competence_types": [],
                "freshness_ttl_seconds": 86_400,
                "distribution_mode": "production",
            },
        )
        package = project_competence(
            self.store,
            self.repo,
            competence_id=self.parent["competence_id"],
            profile_id=profile["profile_id"],
        )
        self.assertEqual(package["status"], "active", package)
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=self._registered(f"consumer-{index}"),
            task_contract=self.contract,
            observed_result={"text": "ok" if success else "no"},
            competence_package_id=package["package_id"],
        )
        use_hash = str(result["ledger_receipts"][-2]["receipt_hash"])
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=package["package_id"],
            # This caller label is deliberately overbroad. Assimilation must
            # derive environment scope from canonical outcomes instead.
            kind="global_contradiction",
            package_use_receipt_hash=use_hash,
        )
        self.assertTrue(feedback["empirical_aggregation_eligible"], feedback)
        return str(feedback["feedback_id"])

    def _second_competence(self) -> dict:
        session = open_symbiotic_session(
            self.store, self.repo, task="unrelated-source-competence"
        )
        run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=self._registered("unrelated-origin"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        return derive_competence_candidate(
            self.store,
            self.repo,
            session_id=session["session_id"],
            turn_id=1,
            capability={"id": "cap.v95.unrelated"},
            intended_outcome={"id": "out.v95.unrelated"},
            counterevidence=[{"kind": "unrelated_origin_limit"}],
        )

    def test_independent_narrowing_promotion_preserves_parent_and_evidence(self) -> None:
        feedback_ids = [
            self._feedback(1, "r2", False),
            self._feedback(2, "r2", False),
            self._feedback(3, "r1", True),
        ]
        subset_cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.parent["competence_id"],
            feedback_ids=feedback_ids,
            persist=True,
        )
        subset_analysis = analyze_evidence_cohort(
            self.store, self.repo, subset_cohort["cohort_id"], persist=True
        )
        subset_candidate = build_revision_candidate(
            self.store,
            self.repo,
            analysis_id=subset_analysis["analysis_id"],
            persist=True,
        )
        subset_check = verify_revision_candidate(
            self.store,
            self.repo,
            subset_candidate["revision_candidate_id"],
            persist=True,
        )
        self.assertFalse(subset_check["valid"], subset_check)
        self.assertTrue(
            any("selection_" in error for error in subset_check["errors"]),
            subset_check,
        )
        with self.assertRaisesRegex(
            CompetenceRevisionError, "verification is not passing"
        ):
            promote_revision_candidate(
                self.store,
                self.repo,
                subset_candidate["revision_candidate_id"],
                verification_receipt_hash=subset_check[
                    "verification_receipt_hash"
                ],
                promotion_reason="post-hoc subset must remain structural",
                persist=True,
            )

        # Production revision uses every canonical observation for this
        # competence at the frozen cutoff; callers do not choose the subset.
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.parent["competence_id"],
            persist=True,
        )
        self.assertEqual(
            {
                item["model_family"]
                for item in cohort["observations"]
                if item.get("empirically_eligible") is True
            },
            {"v95-test-boundary"},
        )
        self.assertEqual(
            {
                item["model_capability_class"]
                for item in cohort["observations"]
                if item.get("empirically_eligible") is True
            },
            {"test-live"},
        )
        analysis = analyze_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"], persist=True
        )
        self.assertEqual(
            analysis["scope"]["derived_scope"], "environment_specific_exception"
        )
        self.assertEqual(
            analysis["scope"]["proposed_revision_type"], "narrow_applicability"
        )

        with self.assertRaisesRegex(
            CompetenceRevisionError, "derived from canonical evidence"
        ):
            build_revision_candidate(
                self.store,
                self.repo,
                analysis_id=analysis["analysis_id"],
                proposed_failure_condition_additions=[{"caller": "invented"}],
                persist=True,
            )

        candidate = build_revision_candidate(
            self.store,
            self.repo,
            analysis_id=analysis["analysis_id"],
            persist=True,
        )
        unrelated = self._second_competence()
        transplanted = dict(candidate)
        transplanted["source_competence_id"] = unrelated["competence_id"]
        transplanted["source_competence_receipt_hash"] = unrelated["receipt_hash"]
        transplanted["source_counterevidence_hashes"] = sorted(
            _sha(item) for item in unrelated["counterevidence"]
        )
        transplant_material = _without_runtime(
            transplanted,
            "revision_candidate_id",
            "candidate_hash",
            "persisted",
        )
        transplanted["revision_candidate_id"] = _sha(transplant_material)
        transplanted["candidate_hash"] = transplanted["revision_candidate_id"]
        with self.assertRaisesRegex(
            CompetenceRevisionError, "source_mismatch"
        ):
            persist_revision_candidate(self.store, self.repo, transplanted)
        tampered = dict(candidate)
        tampered["verification_state"] = "pass"
        material = _without_runtime(
            tampered,
            "revision_candidate_id",
            "candidate_hash",
            "persisted",
        )
        tampered["revision_candidate_id"] = _sha(material)
        tampered["candidate_hash"] = tampered["revision_candidate_id"]
        with self.assertRaisesRegex(
            CompetenceRevisionError, "not independently reproducible"
        ):
            persist_revision_candidate(self.store, self.repo, tampered)

        before_parent = get_competence_candidate(
            self.store, self.repo, self.parent["competence_id"]
        )
        verification = verify_revision_candidate(
            self.store,
            self.repo,
            candidate["revision_candidate_id"],
            persist=True,
        )
        self.assertTrue(verification["valid"], verification)
        promotion = promote_revision_candidate(
            self.store,
            self.repo,
            candidate["revision_candidate_id"],
            verification_receipt_hash=verification["verification_receipt_hash"],
            promotion_reason="independently verified environment narrowing",
            persist=True,
        )
        self.assertEqual(promotion["commit_state"], "committed")
        checked = verify_revision_promotion(
            self.store, self.repo, promotion["promotion_receipt_hash"]
        )
        self.assertTrue(checked["valid"], checked)
        successor = checked["successor"]
        self.assertEqual(successor["revision_state"], "transfer_pending")
        self.assertTrue(
            verify_successor_lineage(
                self.store, self.repo, successor["competence_id"]
            )["valid"]
        )
        self.assertTrue(
            verify_competence_candidate(
                self.store, self.repo, successor["competence_id"]
            )["valid"]
        )
        with self.assertRaises(CompetenceAdmissionError):
            append_competence_candidate(self.store, self.repo, successor)
        self.assertEqual(
            successor["applicability_exclusions"][0]["dimension"],
            "environment_fingerprint",
        )
        self.assertEqual(
            successor["applicability_exclusions"][0]["excluded_values"],
            analysis["scope"]["proposed_applicability_change"][
                "exclude_environment_hashes"
            ],
        )
        self.assertEqual(
            successor["applicability_revision"]["verification_receipt_hash"],
            verification["verification_receipt_hash"],
        )
        self.assertTrue(
            any(
                "v9.5_scope_revision" in condition
                for condition in successor["applicability_conditions"]
            )
        )
        active_successor = {
            **successor,
            "revision_state": "transfer_verified",
            "ledger_state": "transfer_verified",
            "portability_status": "empirical_cross_model_verified",
            "ledger_portability_status": "empirical_cross_model_verified",
        }
        revision_expiry = float(
            successor["revision_evidence_freshness"]["evidence_expiry_at"]
        )
        source_profile = get_target_profile(
            self.store,
            self.repo,
            str(cohort["observations"][0]["profile_id"]),
        )
        with patch(
            "cortex.competence_distribution.time.time",
            return_value=revision_expiry + 1.0,
        ):
            expired_projection = _freshness(
                source_profile or {},
                active_successor,
                transfer={"latest_trial_created_at": successor["created_at"]},
            )
        self.assertEqual(expired_projection["state"], "fail")
        self.assertEqual(
            expired_projection["planes"]["revision_evidence"]["state"],
            "fail",
        )
        with patch(
            "cortex.competence.time.time", return_value=revision_expiry + 1.0
        ):
            expired_applicability = competence_is_applicable(
                active_successor,
                {
                    "target_id": "fresh-target",
                    "identity": {"target_class": "worker"},
                    "model_family": "v95-test-boundary",
                    "environment": {"regime": "r1"},
                },
            )
        self.assertFalse(expired_applicability["applicable"])
        self.assertIn("revision_evidence_expired", expired_applicability["reasons"])
        self.assertTrue(
            verify_evidence_cohort(self.store, self.repo, cohort["cohort_id"])[
                "valid"
            ],
            "successor evidence expiry cannot rewrite its historical cohort",
        )
        base_context = {
            "target_id": "fresh-target",
            "identity": {"target_class": "worker"},
            "model_family": "v95-test-boundary",
        }
        r1 = competence_is_applicable(
            active_successor,
            {**base_context, "environment": {"regime": "r1"}},
        )
        self.assertTrue(r1["applicable"], r1)
        r2 = competence_is_applicable(
            active_successor,
            {**base_context, "environment": {"regime": "r2"}},
        )
        self.assertFalse(r2["applicable"], r2)
        self.assertIn(
            "applicability_excluded:environment_fingerprint", r2["reasons"]
        )
        for dimension, allowed, blocked_context in (
            ("target_id", "fresh-target", {**base_context, "target_id": "other"}),
            (
                "target_class",
                "worker",
                {**base_context, "identity": {"target_class": "planner"}},
            ),
            (
                "model_family",
                "v95-test-boundary",
                {**base_context, "model_family": "other-family"},
            ),
        ):
            with self.subTest(applicability_dimension=dimension):
                constrained = {
                    **active_successor,
                    "applicability_constraints": [
                        {
                            "dimension": dimension,
                            "operator": "allow_only",
                            "values": [allowed],
                        }
                    ],
                }
                self.assertTrue(
                    competence_is_applicable(constrained, base_context)["applicable"]
                )
                blocked = competence_is_applicable(constrained, blocked_context)
                self.assertFalse(blocked["applicable"], blocked)
                self.assertIn(
                    f"applicability_not_allowed:{dimension}", blocked["reasons"]
                )
        class_constrained = {
            **active_successor,
            "applicability_constraints": [
                {
                    "dimension": "target_class",
                    "operator": "allow_only",
                    "values": ["worker"],
                }
            ],
        }
        missing_explicit_class = competence_is_applicable(
            class_constrained,
            {
                **base_context,
                "identity": {"system": "worker"},
                "role": "worker",
            },
        )
        self.assertFalse(missing_explicit_class["applicable"])
        self.assertIn(
            "applicability_dimension_missing:target_class",
            missing_explicit_class["reasons"],
        )
        missing_constraints = competence_is_applicable(
            {**active_successor, "applicability_constraints": []},
            {**base_context, "environment": {"regime": "r1"}},
        )
        self.assertFalse(missing_constraints["applicable"])
        self.assertIn(
            "successor_applicability_constraints_missing",
            missing_constraints["reasons"],
        )
        malformed_constraints = competence_is_applicable(
            {**active_successor, "applicability_constraints": "forged"},
            {**base_context, "environment": {"regime": "r1"}},
        )
        self.assertFalse(malformed_constraints["applicable"])
        self.assertIn(
            "applicability_constraints_malformed",
            malformed_constraints["reasons"],
        )

        # Transfer testing is a separate pre-activation boundary. It reuses
        # the same typed constraint law but accepts transfer_pending state so
        # that a successor can earn transfer evidence. Missing or excluded
        # context must close the experiment before any arm is invoked.
        profiles = list_target_profiles(self.store, self.repo)
        r1_profile = next(
            item for item in profiles if item.get("environment") == {"regime": "r1"}
        )
        r2_profile = next(
            item for item in profiles if item.get("environment") == {"regime": "r2"}
        )
        with self.assertRaisesRegex(
            TransferTrialError,
            "applicability_dimension_missing:environment_fingerprint",
        ):
            run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=successor["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: self._registered(
                    f"successor-missing-{arm}"
                ),
                task="successor transfer without declared regime",
                trial_nonce="v95-successor-missing",
            )
        with self.assertRaisesRegex(
            TransferTrialError,
            "canonical profile",
        ):
            run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=successor["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: self._registered(
                    f"successor-bare-hash-{arm}"
                ),
                task="successor transfer with caller hash only",
                applicability_context={
                    "environment_fingerprint": _sha({"regime": "r1"})
                },
                trial_nonce="v95-successor-bare-hash",
            )
        for name, caller_context in (
            ("target", {"target_id": "target-3"}),
            ("class", {"target_class": "worker"}),
            ("model", {"model_family": "v95-test-boundary"}),
        ):
            with self.subTest(caller_only_dimension=name), self.assertRaises(
                TransferTrialError
            ):
                run_cross_model_transfer_trial(
                    self.store,
                    self.repo,
                    competence_id=successor["competence_id"],
                    task_contract=self.contract,
                    adapter_factory=lambda arm, prefix=name: self._registered(
                        f"successor-caller-{prefix}-{arm}"
                    ),
                    task=f"successor transfer with caller {name} only",
                    applicability_context=caller_context,
                    trial_nonce=f"v95-successor-caller-{name}",
                )
        with self.assertRaisesRegex(
            TransferTrialError,
            "applicability_excluded:environment_fingerprint",
        ):
            run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=successor["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: self._registered(
                    f"successor-excluded-{arm}"
                ),
                task="successor transfer in excluded regime",
                target_profile_id=r2_profile["profile_id"],
                applicability_context={"environment": {"regime": "r2"}},
                trial_nonce="v95-successor-excluded",
            )
        allowed_trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=successor["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: self._registered(
                f"successor-allowed-{arm}"
            ),
            task="successor transfer in retained regime",
            target_profile_id=r1_profile["profile_id"],
            applicability_context={"environment": {"regime": "r1"}},
            trial_nonce="v95-successor-allowed",
        )
        self.assertEqual(
            allowed_trial["applicability_verification"]["state"], "pass"
        )
        self.assertEqual(
            allowed_trial["applicability_context"]["environment"],
            {"regime": "r1"},
        )
        self.assertTrue(
            verify_transfer_trial(
                self.store, self.repo, allowed_trial["trial_id"]
            )["valid"]
        )
        successor_expiry = float(
            successor["revision_evidence_freshness"]["evidence_expiry_at"]
        )
        with patch(
            "cortex.competence.time.time", return_value=successor_expiry + 1.0
        ):
            historical_trial = verify_transfer_trial(
                self.store, self.repo, allowed_trial["trial_id"]
            )
        self.assertTrue(historical_trial["valid"], historical_trial)
        self.assertEqual(
            historical_trial["portability_status"],
            allowed_trial["portability_status"],
        )
        with (
            patch(
                "cortex.competence_transfer.time.time",
                return_value=successor_expiry + 1.0,
            ),
            self.assertRaisesRegex(
                TransferTrialError, "revision_evidence_expired"
            ),
        ):
            run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=successor["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: self._registered(
                    f"successor-expired-{arm}"
                ),
                task="successor transfer after revision evidence expiry",
                target_profile_id=r1_profile["profile_id"],
                trial_nonce="v95-successor-expired",
            )
        tampered_trial = dict(allowed_trial)
        tampered_trial["applicability_context"] = {
            **allowed_trial["applicability_context"],
            "environment": {"regime": "r2"},
            "environment_fingerprint": _sha({"regime": "r2"}),
        }
        tampered_trial["receipt_hash"] = _sha(
            {
                key: value
                for key, value in tampered_trial.items()
                if key
                not in {
                    "receipt_hash",
                    "created_at",
                    "inserted",
                    "duplicate",
                }
            }
        )
        with self.assertRaisesRegex(
            TransferTrialError, "independently reproducible"
        ):
            append_transfer_trial(self.store, self.repo, tampered_trial)
        parent_hashes = {_sha(item) for item in before_parent["counterevidence"]}
        successor_hashes = {_sha(item) for item in successor["counterevidence"]}
        self.assertTrue(parent_hashes.issubset(successor_hashes))
        after_parent = get_competence_candidate(
            self.store, self.repo, self.parent["competence_id"]
        )
        self.assertEqual(before_parent["receipt_hash"], after_parent["receipt_hash"])
        self.assertEqual(
            competence_successor_state(
                self.store, self.repo, self.parent["competence_id"]
            )["state"],
            "superseded",
        )

        # Every inspection surface is observationally pure even inside a
        # caller-owned transaction. In particular, schema setup must not
        # accidentally commit the caller's unrelated write.
        self.store.db.execute("CREATE TEMP TABLE revision_read_purity(value TEXT)")
        self.store.db.commit()
        self.store.db.execute("BEGIN")
        self.store.db.execute(
            "INSERT INTO revision_read_purity(value) VALUES('uncommitted')"
        )
        get_revision_candidate(
            self.store, self.repo, candidate["revision_candidate_id"]
        )
        self.assertTrue(self.store.db.in_transaction, "candidate getter committed")
        verify_revision_candidate(
            self.store, self.repo, candidate["revision_candidate_id"]
        )
        self.assertTrue(self.store.db.in_transaction, "candidate verifier committed")
        get_revision_verification(
            self.store, self.repo, verification["verification_receipt_hash"]
        )
        self.assertTrue(self.store.db.in_transaction, "verification getter committed")
        get_revision_promotion(
            self.store, self.repo, promotion["promotion_receipt_hash"]
        )
        self.assertTrue(self.store.db.in_transaction, "promotion getter committed")
        verify_revision_promotion(
            self.store, self.repo, promotion["promotion_receipt_hash"]
        )
        self.assertTrue(self.store.db.in_transaction, "promotion verifier committed")
        list_revision_promotions(
            self.store, self.repo, self.parent["competence_id"]
        )
        self.assertTrue(self.store.db.in_transaction, "promotion list committed")
        competence_successor_state(
            self.store, self.repo, self.parent["competence_id"]
        )
        self.assertTrue(self.store.db.in_transaction, "successor currentness committed")
        self.store.db.rollback()
        remaining = self.store.db.execute(
            "SELECT COUNT(*) AS n FROM revision_read_purity"
        ).fetchone()
        self.assertEqual(int(remaining["n"]), 0)

        # A forged row may never make package currentness look clean.
        fake_hash = "f" * 64
        fake_candidate = "e" * 64
        self.store.db.execute(
            """INSERT INTO competence_revision_promotions(
                promotion_receipt_hash, repository_id, repo,
                source_competence_id, successor_competence_id,
                revision_candidate_id, verification_receipt_hash,
                relationship, promotion_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fake_hash,
                self.parent["repository_id"],
                self.repo,
                self.parent["competence_id"],
                None,
                fake_candidate,
                "d" * 64,
                "annotates",
                "{}",
                1.0,
            ),
        )
        self.store.db.commit()
        state = competence_successor_state(
            self.store, self.repo, self.parent["competence_id"]
        )
        self.assertFalse(state["valid"])
        self.assertEqual(state["state"], "unknown")
        self.assertIn("promotion_verification_failed", state["errors"])

    def test_delayed_or_profile_stale_evidence_cannot_open_promotion(self) -> None:
        for index, regime, success in (
            (1, "r2", False),
            (2, "r2", False),
            (3, "r1", True),
        ):
            self._feedback(index, regime, success)
        cohort = freeze_evidence_cohort(
            self.store,
            self.repo,
            competence_id=self.parent["competence_id"],
            persist=True,
        )
        analysis = analyze_evidence_cohort(
            self.store, self.repo, cohort["cohort_id"], persist=True
        )
        candidate = build_revision_candidate(
            self.store,
            self.repo,
            analysis_id=analysis["analysis_id"],
            persist=True,
        )
        verification = verify_revision_candidate(
            self.store,
            self.repo,
            candidate["revision_candidate_id"],
            persist=True,
        )
        self.assertTrue(verification["valid"], verification)

        expiries = [
            float(plane["expires_at"])
            for observation in cohort["observations"]
            if observation.get("empirically_eligible") is True
            for plane in observation["feedback_currentness"][
                "freshness_planes"
            ].values()
            if plane.get("expires_at") is not None
        ]
        delayed = min(expiries) + 1.0
        with (
            patch("cortex.competence_revision.time.time", return_value=delayed),
            self.assertRaisesRegex(
                CompetenceRevisionError, "evidence is no longer current"
            ),
        ):
            promote_revision_candidate(
                self.store,
                self.repo,
                candidate["revision_candidate_id"],
                verification_receipt_hash=verification[
                    "verification_receipt_hash"
                ],
                promotion_reason="expired evidence must remain historical",
                persist=True,
            )
        self.assertTrue(
            verify_evidence_cohort(self.store, self.repo, cohort["cohort_id"])[
                "valid"
            ],
            "expiry must not rewrite the historical cohort",
        )
        self.assertEqual(
            list_revision_promotions(
                self.store, self.repo, self.parent["competence_id"]
            ),
            [],
        )

        # A newer profile registered after the cutoff does not invalidate the
        # frozen cohort, but it closes promotion under the old profile.
        first = cohort["observations"][0]
        profile = get_target_profile(
            self.store, self.repo, str(first["profile_id"])
        )
        self.assertIsNotNone(profile)
        register_target_profile(
            self.store,
            self.repo,
            {**dict(profile or {}), "profile_version": "2"},
        )
        self.assertTrue(
            verify_evidence_cohort(self.store, self.repo, cohort["cohort_id"])[
                "valid"
            ],
            "newer profiles must not rewrite as-of cohort truth",
        )
        with self.assertRaisesRegex(
            CompetenceRevisionError, "historical_profile_not_current"
        ):
            promote_revision_candidate(
                self.store,
                self.repo,
                candidate["revision_candidate_id"],
                verification_receipt_hash=verification[
                    "verification_receipt_hash"
                ],
                promotion_reason="stale target profile must block promotion",
                persist=True,
            )


if __name__ == "__main__":
    unittest.main()
