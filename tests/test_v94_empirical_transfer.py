"""Adversarial v9.4 empirical-transfer and package-use binding tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.competence import derive_competence_candidate
from cortex.competence_distribution import (
    project_competence,
    register_target_profile,
    submit_distribution_feedback,
    verify_distribution_feedback,
    verify_distribution_package,
    verify_package_use,
)
from cortex.competence_transfer import (
    TransferTrialError,
    append_transfer_trial,
    run_cross_model_transfer_trial,
    verify_transfer_trial,
)
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import (
    FixtureAdapter,
    ModelAdapterError,
    run_model_circulation,
    verify_model_circulation,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


def _sha(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ClaimedLiveFixture(FixtureAdapter):
    provider_family = "realistic-cloud-family"
    adapter_id = "claimed.live.adapter"
    adapter_version = "999"

    def invoke(self, request):
        context = request.context_projection.get("predictions", {}).get(
            "transfer_context", {}
        )
        included = bool(context.get("competence_included"))
        return {
            "public_output": {"text": "ok" if included else "baseline"},
            "proposal": {"proposed_action": "report public result"},
            "request_hash": request.request_hash,
            "evidence_class": "empirically_attested",
            "empirical": True,
            "chain_of_thought": "must be stripped",
        }


class V94EmpiricalTransferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        self.host = base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("v9.4 fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V94Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v94-transfer-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="ok",
        )
        origin = open_symbiotic_session(self.store, self.repo, task="origin")
        run_model_circulation(
            self.store,
            self.repo,
            origin,
            adapter=FixtureAdapter(model_id="origin-model", text="ok"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        self.candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin["session_id"],
            turn_id=1,
            capability={"id": "cap.v94"},
            intended_outcome={"id": "out.v94"},
            counterevidence=[{"kind": "fixture_limit"}],
        )
        self.trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: ClaimedLiveFixture(
                model_id=f"claimed-live-{arm}"
            ),
            task="transfer fixture",
            trial_nonce="v94-structural",
        )
        self.consume_session = open_symbiotic_session(
            self.store, self.repo, task="consume package"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _profile(
        self,
        target_id: str,
        *,
        version: str = "1",
        mode: str = "sandbox",
        environment: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return register_target_profile(
            self.store,
            self.repo,
            {
                "target_id": target_id,
                "profile_version": version,
                "identity": {"system": target_id},
                "environment": dict(environment or {}),
                "role": "operator",
                "task_family": "procedure",
                "model_capability": {"class": "fixture-test"},
                "available_tools": [],
                "authority_scope": {"propose": True, "execute": False},
                "body_epoch_id": self.consume_session["body_epoch_id"],
                "privacy_boundaries": {"local_only": True},
                "required_competence_types": ["successful_procedure"],
                "prohibited_competence_types": [],
                "freshness_ttl_seconds": 86400,
                "distribution_mode": mode,
            },
        )

    def _package(self, target_id: str = "system-a") -> dict[str, object]:
        profile = self._profile(target_id)
        package = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=str(profile["profile_id"]),
        )
        self.assertEqual(package["status"], "active", package)
        return package

    def _use(self, package: dict[str, object]) -> dict[str, object]:
        result = run_model_circulation(
            self.store,
            self.repo,
            self.consume_session,
            adapter=FixtureAdapter(model_id="consumer", text="ok"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
            competence_package_id=str(package["package_id"]),
        )
        self.assertEqual(result["persistence_status"], "committed", result)
        return result

    def test_fixture_trials_are_structural_never_empirical(self) -> None:
        self.assertEqual(
            self.trial["portability_status"], "structural_cross_model_pass"
        )
        self.assertEqual(self.trial["evidence_class"], "synthetic")
        self.assertFalse(self.trial["empirical_transfer_established"])
        checked = verify_transfer_trial(
            self.store, self.repo, self.trial["trial_id"]
        )
        self.assertTrue(checked["valid"], checked)
        self.assertFalse(checked["empirical_transfer_established"])

    def test_adapter_payload_and_credentials_cannot_upgrade_or_leak(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="sanitize")
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=ClaimedLiveFixture(model_id="claimed-live"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        self.assertEqual(result["evidence_class"], "synthetic")
        serialized = json.dumps(result["invocation_result"], sort_keys=True)
        self.assertNotIn("chain_of_thought", serialized)
        self.assertNotIn("empirically_attested", serialized)
        secret_session = open_symbiotic_session(
            self.store, self.repo, task="reject secret"
        )
        with self.assertRaises(ModelAdapterError):
            run_model_circulation(
                self.store,
                self.repo,
                secret_session,
                adapter=FixtureAdapter(text="ok"),
                task_contract=self.contract,
                observed_result={"text": "ok"},
                configuration={"api_key": "must-not-persist"},
            )

    def test_production_distribution_rejects_synthetic_transfer(self) -> None:
        profile = self._profile("production", mode="production")
        result = project_competence(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            profile_id=str(profile["profile_id"]),
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("transfer_status_below_target_policy", result["errors"])

    def test_sandbox_package_is_typed_nonpromotable(self) -> None:
        package = self._package()
        self.assertTrue(package["sandbox_only"])
        self.assertTrue(package["synthetic_evidence"])
        self.assertTrue(package["non_promotable"])
        self.assertFalse(package["empirical_feedback_eligible"])
        self.assertTrue(
            verify_distribution_package(
                self.store, self.repo, str(package["package_id"])
            )["valid"]
        )

    def test_exact_package_use_binds_same_turn_feedback(self) -> None:
        package = self._package()
        result = self._use(package)
        checked = verify_model_circulation(
            self.store,
            self.repo,
            result["session_id"],
            turn_id=result["turn_id"],
        )
        self.assertTrue(checked["valid"], checked)
        use_hash = str(checked["package_use_receipt_hash"])
        use_check = verify_package_use(
            self.store,
            self.repo,
            use_hash,
            expected_package_id=str(package["package_id"]),
        )
        self.assertTrue(use_check["valid"], use_check)
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=str(package["package_id"]),
            kind="global_contradiction",
            package_use_receipt_hash=use_hash,
            outcome={"status": "verified_success", "success": True},
        )
        self.assertEqual(feedback["verification"]["state"], "synthetic_verified")
        self.assertFalse(feedback["empirical_aggregation_eligible"])
        self.assertFalse(feedback["global_fact"])
        dynamic = verify_distribution_feedback(
            self.store, self.repo, feedback["feedback_id"]
        )
        self.assertTrue(dynamic["valid"], dynamic)
        self.assertEqual(dynamic["state"], "synthetic_verified")

    def test_unrelated_valid_circulation_cannot_verify_feedback(self) -> None:
        package = self._package()
        unrelated = open_symbiotic_session(self.store, self.repo, task="unrelated")
        result = run_model_circulation(
            self.store,
            self.repo,
            unrelated,
            adapter=FixtureAdapter(text="ok"),
            task_contract=self.contract,
            observed_result={"text": "ok"},
        )
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=str(package["package_id"]),
            kind="success",
            circulation_session_id=result["session_id"],
            turn_id=result["turn_id"],
        )
        self.assertEqual(feedback["verification"]["state"], "unverified")
        self.assertFalse(feedback["empirical_aggregation_eligible"])

    def test_package_use_cannot_replay_for_another_target(self) -> None:
        first = self._package("system-a")
        used = self._use(first)
        use_hash = str(
            used["ledger_receipts"][-2]["receipt_hash"]
        )
        second = self._package("system-b")
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=str(second["package_id"]),
            kind="success",
            package_use_receipt_hash=use_hash,
        )
        self.assertEqual(feedback["verification"]["state"], "binding_failed")
        self.assertIn(
            "package_use_package_mismatch", feedback["verification"]["errors"]
        )

    def test_profile_change_makes_old_package_feedback_unknown(self) -> None:
        package = self._package("mutable-target")
        used = self._use(package)
        use_hash = str(used["ledger_receipts"][-2]["receipt_hash"])
        self._profile(
            "mutable-target",
            version="2",
            environment={"revision": 2},
        )
        self.assertFalse(
            verify_distribution_package(
                self.store, self.repo, str(package["package_id"])
            )["valid"]
        )
        feedback = submit_distribution_feedback(
            self.store,
            self.repo,
            package_id=str(package["package_id"]),
            kind="success",
            package_use_receipt_hash=use_hash,
        )
        self.assertEqual(feedback["verification"]["state"], "unknown")

    def test_forged_empirical_trial_status_is_rejected(self) -> None:
        forged = dict(self.trial)
        forged["portability_status"] = "empirical_cross_family_verified"
        forged["evidence_class"] = "live_empirical"
        forged["empirical_transfer_established"] = True
        forged["receipt_hash"] = _sha(
            {
                key: value
                for key, value in forged.items()
                if key not in {"receipt_hash", "created_at", "inserted", "duplicate"}
            }
        )
        with self.assertRaisesRegex(
            TransferTrialError, "independently reproducible"
        ):
            append_transfer_trial(self.store, self.repo, forged)


if __name__ == "__main__":
    unittest.main()
