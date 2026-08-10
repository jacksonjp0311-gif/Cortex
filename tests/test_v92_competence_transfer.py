"""v9.2 controlled cross-model competence transfer tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.competence import derive_competence_candidate, get_competence_candidate
from cortex.competence_transfer import (
    TransferTrialError,
    run_cross_model_transfer_trial,
    verify_transfer_trial,
)
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class TransferProbeAdapter(FixtureAdapter):
    provider_family = "fresh-family"

    def __init__(self, arm: str, *, model_id: str | None = None, success: bool = True):
        super().__init__(model_id=model_id or f"fresh-{arm}")
        self.arm = arm
        self.success = success
        self.seen_context: dict[str, object] | None = None

    def invoke(self, request):
        self.seen_context = dict(
            request.context_projection.get("predictions", {}).get("transfer_context", {})
        )
        included = bool(self.seen_context.get("competence_included"))
        text = "transfer success" if self.success and included else "baseline"
        return {
            "public_output": {"text": text},
            "proposal": {"proposed_action": "report the observed result"},
            "declared_uncertainty": {"overall": 0.1},
            "request_hash": request.request_hash,
        }


class V92CompetenceTransferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        self.host = base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("transfer fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V92Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v92-transfer-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="transfer success",
        )
        origin_session = open_symbiotic_session(self.store, self.repo, task="origin experience")
        run_model_circulation(
            self.store,
            self.repo,
            origin_session,
            adapter=FixtureAdapter(model_id="origin-a"),
            task_contract=self.contract,
            observed_result={"text": "transfer success"},
        )
        self.candidate = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=origin_session["session_id"],
            turn_id=1,
            capability={"id": "cap.transfer", "description": "public origin wording"},
            intended_outcome={"id": "out.transfer"},
            counterevidence=[{"kind": "known_limit", "text": "fixture boundary"}],
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_matched_arms_freeze_contract_and_classify_cross_model(self) -> None:
        adapters: dict[str, TransferProbeAdapter] = {}

        def factory(arm: str) -> TransferProbeAdapter:
            adapters[arm] = TransferProbeAdapter(arm)
            return adapters[arm]

        trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=factory,
            task="apply the transferred procedure",
            trial_nonce="matched-1",
        )
        self.assertEqual(trial["portability_status"], "cross_model_verified")
        self.assertEqual(set(trial["arm_results"]), {"A", "B", "C", "D", "E"})
        self.assertGreater(trial["gains"]["G_continuity"], 0.0)
        self.assertGreater(trial["gains"]["G_distillation"], 0.0)
        self.assertGreater(trial["gains"]["G_governance"], 0.0)
        self.assertEqual(trial["task_contract_hash"], self.contract.contract_hash)
        self.assertEqual(
            len({item["context_hash"] for item in trial["arm_results"].values()}), 5
        )
        self.assertTrue(trial["evidence"]["origin_model_detached"])
        self.assertFalse(trial["distribution_authorized"])
        self.assertTrue(verify_transfer_trial(self.store, self.repo, trial["trial_id"])["valid"])
        self.assertFalse(
            get_competence_candidate(self.store, self.repo, self.candidate["competence_id"])[
                "distribution_authorized"
            ]
        )

    def test_arm_isolation_only_d_and_e_receive_competence(self) -> None:
        adapters: dict[str, TransferProbeAdapter] = {}

        def factory(arm: str) -> TransferProbeAdapter:
            adapter = TransferProbeAdapter(arm)
            adapters[arm] = adapter
            return adapter

        run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=factory,
            task="isolate arms",
            trial_nonce="isolation-1",
        )
        for arm in ("A", "B", "C"):
            self.assertFalse(adapters[arm].seen_context["competence_included"])
        self.assertTrue(adapters["D"].seen_context["competence_included"])
        self.assertTrue(adapters["E"].seen_context["competence_included"])
        self.assertGreater(len(adapters["D"].seen_context["competence"]["counterevidence"]), 0)

    def test_usage_feedback_is_separate_and_requires_prior_canonical_trial(self) -> None:
        first = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: TransferProbeAdapter(arm),
            task="first transfer",
            trial_nonce="feedback-1",
        )
        adapters: dict[str, TransferProbeAdapter] = {}

        def factory(arm: str) -> TransferProbeAdapter:
            adapters[arm] = TransferProbeAdapter(arm, model_id=f"fresh-2-{arm}")
            return adapters[arm]

        second = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=factory,
            task="second transfer",
            prior_feedback=[{"trial_id": first["trial_id"]}],
            trial_nonce="feedback-2",
        )
        self.assertTrue(adapters["E"].seen_context["usage_feedback"])
        self.assertTrue(second["arm_results"]["E"]["metrics"]["feedback_available"])
        self.assertFalse(second["distribution_authorized"])

    def test_negative_transfer_stays_unresolved(self) -> None:
        trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: TransferProbeAdapter(arm, success=False),
            task="negative transfer",
            policy={"min_success_gain": 0.2},
            trial_nonce="negative-1",
        )
        self.assertEqual(trial["portability_status"], "unresolved")
        self.assertFalse(trial["promotion_eligible"])
        self.assertIn("declared_gain_threshold_not_met", trial["classification_reasons"])

    def test_reusing_origin_model_fails_closed_as_incompatible(self) -> None:
        trial = run_cross_model_transfer_trial(
            self.store,
            self.repo,
            competence_id=self.candidate["competence_id"],
            task_contract=self.contract,
            adapter_factory=lambda arm: FixtureAdapter(model_id="origin-a"),
            task="not fresh",
            trial_nonce="same-origin-1",
        )
        self.assertEqual(trial["portability_status"], "incompatible")
        self.assertTrue(trial["arm_errors"])
        self.assertFalse(trial["distribution_authorized"])

    def test_stale_applicability_blocks_trial_without_changing_candidate(self) -> None:
        stale = derive_competence_candidate(
            self.store,
            self.repo,
            session_id=(
                self.candidate["evidence_lineage"]["originating_trajectories"][0]["session_id"]
            ),
            turn_id=1,
            capability={"id": "cap.stale"},
            intended_outcome={"id": "out.stale"},
            applicability_conditions=[{"body_epoch_id": "never-current"}],
            counterevidence=[{"kind": "stale"}],
        )
        before = stale["revision_state"]
        with self.assertRaises(TransferTrialError):
            run_cross_model_transfer_trial(
                self.store,
                self.repo,
                competence_id=stale["competence_id"],
                task_contract=self.contract,
                adapter_factory=lambda arm: TransferProbeAdapter(arm),
                task="stale use",
                trial_nonce="stale-1",
            )
        after = get_competence_candidate(self.store, self.repo, stale["competence_id"])
        self.assertEqual(after["revision_state"], before)


if __name__ == "__main__":
    unittest.main()
