"""Adversarial v8.9.3 canonical evidence and witness-gate checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.membrane import apply_will_bound_membrane
from cortex.provenance import derive_gate_state
from cortex.store import Store
from cortex.will import issue_will, register_will_principal, verify_will
from cortex.witness import commit_manifest, run_witness, verify_witness_result


class V893GateProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# v8.9.3 evidence\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "GateProofHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store, self.repo, "operator", "Operator", secret="gate-secret"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _will(self, *, session_id: str = "gate-session", epoch: str = "gate-epoch") -> dict:
        return issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="gate-secret",
            session_id=session_id,
            body_epoch_id=epoch,
            clauses=[
                {"kind": "admit_type", "candidate_types": ["successful_procedure"]},
                {"kind": "prefer_support_min", "min_support": "none"},
            ],
        )

    def _activation_outcome(
        self,
        *,
        outcome_id: str = "outcome-a",
        status: str = "success",
        verification_type: str = "independent",
    ) -> dict:
        activation_id = "activation-a"
        session_id = "gate-session"
        self.store.record_neural_activation(
            self.repo,
            session_id,
            {"activation_id": activation_id, "task_hash": "task", "state_hash": "state"},
        )
        self.store.record_outcome(
            self.repo,
            outcome_id=outcome_id,
            activation_id=activation_id,
            status=status,
            reward=1.0 if status == "success" else 0.0,
            verification_type=verification_type,
            verification_payload={"source": "v8.9.3-test"},
            credits=[],
            updates=[],
            apply_updates=False,
        )
        return {
            "outcome_id": outcome_id,
            "activation_id": activation_id,
            "status": status,
            "verified": True,  # reference only; canonical row decides.
        }

    def _witness(self, *, outcome_id: str | None = None) -> tuple[dict, dict]:
        case = {"id": "case", "query": "README evidence", "expected_substrings": ["README"]}
        commitment = commit_manifest([case], store=self.store)
        result = run_witness(
            self.store,
            self.repo,
            commitment=commitment,
            revealed_cases=[case],
            controller="evidence_baseline",
            outcome_id=outcome_id,
            activation_id="activation-a" if outcome_id else None,
        )
        self.assertIn(result.get("canonical_persistence"), {"committed", "duplicate"})
        return commitment, result

    def test_fake_constitutional_receipt_and_boolean_do_not_pass(self) -> None:
        will = self._will()
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            constitutional_gate=True,
            gate_evidence={
                "constitutional_receipt_hash": "c" * 64,
                "constitutional_verified": True,
            },
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(proof["constitutional"]["state"], "pass")
        self.assertNotEqual(proof["overall"], "pass")

    def test_fake_stability_receipt_and_boolean_do_not_pass(self) -> None:
        will = self._will()
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            stable_regime=True,
            gate_evidence={
                "stability_receipt_hash": "s" * 64,
                "stability_verified": True,
            },
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(proof["stability"]["state"], "pass")

    def test_commitment_and_caller_passed_witness_are_not_results(self) -> None:
        will = self._will()
        commitment = commit_manifest(
            [{"id": "case", "query": "README evidence", "expected_substrings": ["README"]}],
            store=self.store,
        )
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            witness_present=True,
            witness={"witness_id": commitment["witness_id"], "passed": True},
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(proof["witness"]["state"], "pass")
        self.assertFalse(verify_witness_result(self.store, self.repo, "d" * 64)["verified"])

    def test_tampered_result_and_bad_chronology_fail(self) -> None:
        commitment, result = self._witness()
        result_hash = result["witness_result_hash"]
        self.store.db.execute("DROP TRIGGER witness_results_no_update")
        row = self.store.db.execute(
            "SELECT result_json FROM witness_results WHERE witness_result_hash=?",
            (result_hash,),
        ).fetchone()
        body = json.loads(row["result_json"])
        body["success"] = False
        self.store.db.execute(
            "UPDATE witness_results SET result_json=? WHERE witness_result_hash=?",
            (json.dumps(body, sort_keys=True, separators=(",", ":")), result_hash),
        )
        self.store.db.commit()
        tampered = verify_witness_result(self.store, self.repo, result_hash)
        self.assertFalse(tampered["verified"])
        self.assertIn("witness_result_hash_mismatch", tampered["errors"])

        # Restore a clean result and then make the commitment post-date reveal.
        self.store.close()
        self.store = Store(self.home / "cortex.db")
        self.store.db.execute(
            "UPDATE witness_commitments SET created_at=? WHERE witness_id=?",
            (float(result["revealed_at"]) + 10.0, commitment["witness_id"]),
        )
        self.store.db.commit()
        chronology = verify_witness_result(self.store, self.repo, result_hash)
        self.assertFalse(chronology["verified"])
        self.assertIn("witness_chronology_invalid", chronology["errors"])

    def test_outcome_row_controls_verification_and_binding(self) -> None:
        will = self._will()
        outcome = self._activation_outcome()
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            outcome=outcome,
            candidate_type="successful_procedure",
        )
        self.assertEqual(proof["outcome"]["state"], "pass")

        mismatched = dict(outcome, status="failure", verified=True)
        bad = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            outcome=mismatched,
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(bad["outcome"]["state"], "pass")

    def test_cohort_missing_and_unknown_propagate(self) -> None:
        will = self._will()
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            epoch_compatible=True,
            constitutional_gate=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            measurement_cohort_id="missing-cohort",
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(proof["epoch_cohort"]["state"], "pass")
        self.assertNotEqual(proof["overall"], "pass")

    def test_principal_secret_mismatch_is_explicit(self) -> None:
        will = self._will()
        verification = verify_will(
            self.store,
            self.repo,
            will,
            secret="attacker-secret",
            require_session_id="gate-session",
            require_body_epoch_id="gate-epoch",
        )
        self.assertFalse(verification["verified"])
        self.assertFalse(verification["checks"]["principal_secret_match"])

    def test_naked_candidate_is_noncanonical_and_durable_admission_stays_closed(self) -> None:
        will = self._will()
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            candidates=[
                {
                    "candidate_id": "naked",
                    "candidate_type": "successful_procedure",
                    "summary": "caller assertion",
                    "support_level": "high",
                }
            ],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertGreater(admission["noncanonical_candidate_count"], 0)
        self.assertGreater(admission["invented_or_unresolved_count"], 0)
        self.assertFalse(admission["durable_write_authorized"])

    def test_caller_true_never_promotes_unknown_planes(self) -> None:
        will = self._will()
        proof = derive_gate_state(
            self.store,
            self.repo,
            will=will,
            will_secret="gate-secret",
            body_epoch_id="gate-epoch",
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            witness={"passed": True},
            outcome={"verified": True, "outcome_id": "unknown"},
            gate_evidence={
                "constitutional_receipt_hash": "c" * 64,
                "constitutional_verified": True,
                "stability_receipt_hash": "s" * 64,
                "stability_verified": True,
            },
            candidate_type="successful_procedure",
        )
        self.assertNotEqual(proof["overall"], "pass")
        self.assertTrue(proof["caller_true_is_not_evidence"])
        self.assertFalse(proof["host_mutate_authorized"])
        self.assertFalse(proof["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
