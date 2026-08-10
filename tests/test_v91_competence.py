"""v9.1 competence-distillation boundary tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.competence import (
    CompetenceAdmissionError,
    competence_is_applicable,
    build_competence_candidate,
    derive_competence_candidate,
    get_competence_candidate,
    verify_competence_candidate,
)
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import FixtureAdapter, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class V91CompetenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.home = ensure_home(base / "home")
        self.host = base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("competence fixture\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V91Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.contract = TaskEvaluationContract(
            contract_id="v91-text-v1",
            task_type="text_contains",
            target_field="text",
            expected_value="fixture observation",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _origin(self, *, success: bool = True, model_id: str = "origin-a"):
        session = open_symbiotic_session(self.store, self.repo, task="distill competence")
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=FixtureAdapter(model_id=model_id),
            task_contract=self.contract,
            observed_result={
                "text": "fixture observation" if success else "not the observation"
            },
        )
        self.assertEqual(result["persistence_status"], "committed")
        return session

    def _derive(self, session_id: str, *, candidate_type: str = "successful_procedure", **kw):
        return derive_competence_candidate(
            self.store,
            self.repo,
            session_id=session_id,
            turn_id=1,
            capability=kw.pop("capability", {"id": "cap.fixture", "description": "first prose"}),
            intended_outcome=kw.pop("intended_outcome", {"id": "out.fixture"}),
            candidate_type=candidate_type,
            counterevidence=kw.pop("counterevidence", [{"kind": "limit", "text": "fixture only"}]),
            **kw,
        )

    def test_verified_origin_creates_separate_model_independent_candidate(self) -> None:
        session = self._origin()
        candidate = self._derive(session["session_id"])
        self.assertEqual(candidate["kind"], "competence_candidate")
        self.assertTrue(candidate["evidence_lineage"]["canonical"])
        self.assertTrue(candidate["evidence_lineage"]["model_origin"]["model_id"])
        verified = verify_competence_candidate(self.store, self.repo, candidate["competence_id"])
        self.assertTrue(verified["valid"], verified["errors"])
        self.assertTrue(verified["model_independent_verification"])
        self.assertFalse(verified["origin_model_required"])

    def test_unsupported_fluent_advice_has_no_origin_and_no_competence(self) -> None:
        with self.assertRaises(CompetenceAdmissionError):
            self._derive("missing-session")
        self.assertEqual(self.store.list_competence_candidates(self.repo), [])

    def test_forged_build_cannot_bypass_canonical_origin_at_append(self) -> None:
        repository_id = self.store.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (self.repo,)
        ).fetchone()[0]
        forged = build_competence_candidate(
            repo=self.repo,
            repository_id=repository_id,
            origin={
                "repo": self.repo,
                "repository_id": repository_id,
                "session_id": "not-canonical",
                "turn_id": 1,
                "body_epoch_id": "fake",
                "trajectory_receipt_hash": "0" * 64,
                "outcome_receipt_hash": "0" * 64,
                "outcome_content_hash": "0" * 64,
                "outcome_status": "verified_success",
                "outcome_success": True,
                "witness_receipt_hash": "0" * 64,
                "witness_result_hash": "0" * 64,
                "model_origin": {"model_id": "fluent-advice"},
            },
            capability={"id": "cap.forged"},
            intended_outcome={"id": "out.forged"},
            counterevidence=[{"kind": "unsupported"}],
        )
        with self.assertRaises(CompetenceAdmissionError):
            self.store.append_competence_candidate(self.repo, forged)

    def test_origin_model_identity_is_provenance_not_semantic_identity(self) -> None:
        first = self._derive(self._origin(model_id="model-a")["session_id"])
        second = self._derive(
            self._origin(model_id="model-b")["session_id"],
            capability={"id": "cap.fixture", "description": "different wording"},
            public_description="A revised public explanation",
        )
        self.assertEqual(first["semantic_identity_hash"], second["semantic_identity_hash"])
        self.assertTrue(second["duplicate"])
        stored = get_competence_candidate(self.store, self.repo, first["competence_id"])
        self.assertEqual(stored["evidence_lineage"]["model_origin"]["model_id"], "model-a")

    def test_failure_cannot_become_successful_procedure_but_negative_knowledge_survives(self) -> None:
        session = self._origin(success=False)
        with self.assertRaises(CompetenceAdmissionError):
            self._derive(session["session_id"], counterevidence=[{"kind": "failure"}])
        failure = self._derive(
            session["session_id"],
            candidate_type="failed_hypothesis",
            counterevidence=[{"kind": "failure", "reason": "criterion not met"}],
        )
        self.assertEqual(failure["evidence_lineage"]["outcome_evidence"]["success"], False)
        self.assertEqual(failure["counterevidence"][0]["kind"], "failure")
        self.assertTrue(verify_competence_candidate(self.store, self.repo, failure["competence_id"])["valid"])

    def test_model_specific_preference_is_not_universal(self) -> None:
        session = self._origin()
        candidate = self._derive(session["session_id"], candidate_type="model_specific_preference")
        self.assertEqual(candidate["portability_status"], "model_specific_blocked")
        self.assertFalse(competence_is_applicable(candidate, {})["applicable"])

    def test_pending_transfer_and_stale_applicability_are_read_only_and_blocked(self) -> None:
        session = self._origin()
        candidate = self._derive(
            session["session_id"],
            applicability_conditions=[{"body_epoch_id": "epoch-new"}],
        )
        before = self.store.db.execute(
            "SELECT COUNT(*) FROM competence_candidates"
        ).fetchone()[0]
        projection = competence_is_applicable(
            candidate, {"body_epoch_id": "epoch-old", "repository_id": "wrong"}
        )
        after = self.store.db.execute("SELECT COUNT(*) FROM competence_candidates").fetchone()[0]
        self.assertFalse(projection["applicable"])
        self.assertFalse(projection["state_transition_persisted"])
        self.assertEqual(before, after)

    def test_candidate_cannot_authorize_distribution_or_execution(self) -> None:
        session = self._origin()
        candidate = self._derive(session["session_id"])
        for flag in (
            "distribution_authorized",
            "memory_admission_authorized",
            "host_mutate_authorized",
            "execution_authorized",
            "policy_effect",
            "update_authorized",
        ):
            self.assertFalse(candidate[flag])
        checked = verify_competence_candidate(self.store, self.repo, candidate["competence_id"])
        self.assertFalse(checked["host_mutate_authorized"])
        self.assertFalse(checked["execution_authorized"])

    def test_canonical_candidate_is_immutable(self) -> None:
        session = self._origin()
        candidate = self._derive(session["session_id"])
        with self.assertRaises(Exception):
            self.store.db.execute(
                "UPDATE competence_candidates SET state='transfer_verified' WHERE competence_id=?",
                (candidate["competence_id"],),
            )
        self.store.db.rollback()
        self.assertTrue(verify_competence_candidate(self.store, self.repo, candidate["competence_id"])["valid"])


if __name__ == "__main__":
    unittest.main()
