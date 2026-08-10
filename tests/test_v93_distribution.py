"""v9.3 governed competence distribution tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cortex.bootstrap import bootstrap_repository
from cortex.competence import derive_competence_candidate, get_competence_candidate
from cortex.competence_distribution import (
    project_competence,
    register_target_profile,
    revoke_distribution,
    rollback_distribution,
    submit_distribution_feedback,
    verify_distribution_package,
)
from cortex.competence_transfer import run_cross_model_transfer_trial
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class DistributionAdapter(FixtureAdapter):
    provider_family = "distribution-family"

    def invoke(self, request):
        context = request.context_projection.get("predictions", {}).get("transfer_context", {})
        included = bool(context.get("competence_included"))
        return {
            "public_output": {"text": "ok" if included else "baseline"},
            "proposal": {"proposed_action": "report the observed result"},
            "declared_uncertainty": {"overall": 0.1},
            "request_hash": request.request_hash,
        }


class V93DistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        self.host = base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("distribution fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V93Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v93-distribution-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="ok",
        )
        origin = open_symbiotic_session(self.store, self.repo, task="origin experience")
        run_model_circulation(
            self.store,
            self.repo,
            origin,
            adapter=FixtureAdapter(model_id="origin-a"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        self.candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin["session_id"],
            turn_id=1,
            capability={"id": "cap.distribute"},
            intended_outcome={"id": "out.distribute"},
            counterevidence=[{"kind": "known_limit", "text": "fixture boundary"}],
        )
        self.trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: DistributionAdapter(model_id=f"fresh-{arm}"),
            task="verify transfer",
            trial_nonce="distribution-origin",
        )
        self.epoch = self.candidate["evidence_lineage"]["originating_trajectories"][0]["body_epoch_id"]

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def profile(self, target_id: str, version: str = "1", **overrides):
        body = {
            "target_id": target_id,
            "profile_version": version,
            "identity": {"system": target_id},
            "environment": {},
            "role": "operator",
            "task_family": "procedure",
            "model_capability": {"class": "distribution-family"},
            "available_tools": [],
            "authority_scope": {"propose": True, "execute": False},
            "body_epoch_id": self.epoch,
            "privacy_boundaries": {"local_only": True},
            "required_competence_types": ["successful_procedure"],
            "prohibited_competence_types": [],
            "freshness_ttl_seconds": 86400,
            "distribution_mode": "sandbox",
        }
        body.update(overrides)
        return register_target_profile(self.store, self.repo, body)

    def package(
        self,
        target_id: str = "system-a",
        version: str = "1",
        previous_package_id: str | None = None,
        **overrides,
    ):
        profile = self.profile(target_id, version, **overrides)
        package = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=profile["profile_id"],
            previous_package_id=previous_package_id,
        )
        self.assertEqual(package["status"], "active", package)
        return package, profile

    def test_heterogeneous_targets_receive_same_canonical_competence(self) -> None:
        first, _ = self.package("system-a")
        second, _ = self.package("system-b")
        self.assertNotEqual(first["package_id"], second["package_id"])
        self.assertEqual(first["competence_id"], second["competence_id"])
        self.assertTrue(verify_distribution_package(self.store, self.repo, first["package_id"])["valid"])
        self.assertTrue(verify_distribution_package(self.store, self.repo, second["package_id"])["valid"])
        self.assertFalse(first["distribution_authorized"])
        self.assertFalse(first["execution_authorized"])

    def test_incompatible_target_is_blocked(self) -> None:
        profile = self.profile("blocked", prohibited_competence_types=["successful_procedure"])
        result = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=profile["profile_id"],
        )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["package_persisted"])
        self.assertIn("competence_type_prohibited", result["errors"])

    def test_revocation_and_feedback_do_not_rewrite_canonical_competence(self) -> None:
        package, _ = self.package()
        other, _ = self.package("system-b")
        before = get_competence_candidate(self.store, self.repo, self.candidate["competence_id"])
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=package["package_id"],
            kind="global_contradiction",
            result={"success": True},
            evidence={"verified": True, "receipt_hash": "f" * 64},
        )
        self.assertEqual(feedback["verification"]["state"], "unverified")
        self.assertTrue(verify_distribution_package(self.store, self.repo, package["package_id"])["valid"])
        # A local, unverified contradiction is evidence for later review; it
        # cannot contaminate another target or self-promote into a revocation.
        self.assertTrue(verify_distribution_package(self.store, self.repo, other["package_id"])["valid"])
        revoke_distribution(self.store, self.repo, package["package_id"], reason="independent contradiction")
        checked = verify_distribution_package(self.store, self.repo, package["package_id"])
        self.assertFalse(checked["valid"])
        self.assertIn("package_revoke", checked["errors"])
        future_profile = self.profile("system-c")
        future = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=future_profile["profile_id"],
        )
        self.assertEqual(future["status"], "blocked")
        self.assertIn("global_competence_event", future["errors"])
        after = get_competence_candidate(self.store, self.repo, self.candidate["competence_id"])
        self.assertEqual(before["receipt_hash"], after["receipt_hash"])

    def test_rollback_restores_previous_valid_projection(self) -> None:
        first, profile = self.package("system-a", "1")
        second = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=profile["profile_id"],
            previous_package_id=first["package_id"],
        )
        self.assertEqual(second["status"], "active", second)
        # The second package is a new immutable version, and only its event
        # state changes during rollback; the first package remains untouched.
        event = rollback_distribution(self.store, self.repo, second["package_id"], reason="restore prior")
        self.assertEqual(event["event_type"], "rollback")
        self.assertFalse(verify_distribution_package(self.store, self.repo, second["package_id"])["valid"])
        self.assertTrue(verify_distribution_package(self.store, self.repo, first["package_id"])["valid"])

    def test_stale_package_is_detected_without_mutation(self) -> None:
        package, _ = self.package()
        with patch("cortex.competence_distribution.time.time", return_value=package["created_at"] + 90000):
            checked = verify_distribution_package(self.store, self.repo, package["package_id"])
        self.assertFalse(checked["valid"])
        self.assertIn("package_stale", checked["errors"])

    def test_origin_model_is_not_needed_after_transfer_verification(self) -> None:
        package, _ = self.package("detached")
        self.assertTrue(verify_distribution_package(self.store, self.repo, package["package_id"])["valid"])
        self.assertTrue(package["provenance_roots"]["transfer_trial_ids"])
if __name__ == "__main__":
    unittest.main()
