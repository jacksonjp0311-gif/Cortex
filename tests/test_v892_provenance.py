"""Adversarial v8.9.2 canonical provenance and read-purity checks."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex.admitted_memory import (
    commit_admitted_memories,
    deep_verify_admitted_memory,
    list_admitted_memories,
)
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.cognitive.measured import capture_measured_state, measured_delta
from cortex.distillation_candidates import extract_distillation_candidates
from cortex.epoch import ensure_current_epoch
from cortex.interconnect_frame import (
    build_interconnect_transition,
    capture_atomic_interconnect_frame,
)
from cortex.membrane import apply_will_bound_membrane
from cortex.memory_projection import evaluate_memory_eligibility, project_memories
from cortex.semantic_projection import (
    build_semantic_memory_projection,
    verify_semantic_memory_projection,
)
from cortex.symbiosis import open_symbiotic_session
from cortex.store import Store
from cortex.ostt.conformance import build_activation_conformance_receipt
from cortex.provenance import sha
from cortex.will import issue_will, register_will_principal
from cortex.witness import commit_manifest, run_witness


class V892ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# provenance host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "ProvenanceHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(self.store, self.repo, "operator", "Operator", secret="v892-secret")
        self.epoch = ensure_current_epoch(self.store, self.repo, reason="v8.9.2-test")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def _canonical_memory(self) -> tuple[dict, dict, dict]:
        session_id = "v892-session"
        epoch_id = self.epoch.epoch_id
        self.store.record_neural_activation(
            self.repo,
            session_id,
            {"activation_id": "v892-activation", "task_hash": "task", "state_hash": "state"},
        )
        outcome = {
            "outcome_id": "v892-outcome",
            "receipt_hash": "o" * 64,
            "verified": True,
            "repo": self.repo,
            "session_id": session_id,
            "turn_id": 1,
            "activation_id": "v892-activation",
        }
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            session_id=session_id,
            body_epoch_id=epoch_id,
            clauses=[
                {"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]},
                {"kind": "prefer_support_min", "min_support": "none"},
            ],
        )
        # Build actual canonical constitutional/cohort evidence.  The old
        # fixture used random hashes plus booleans; those are intentionally no
        # longer capable of opening a membrane gate.
        before_state = capture_measured_state(self.store, self.repo)
        after_state = capture_measured_state(self.store, self.repo)
        measured = measured_delta(before_state, after_state, event_id="v892-measurement")
        manifest_hash = str(self.store.repo(self.repo)["manifest_hash"])
        conformance_candidate = build_activation_conformance_receipt(
            self.store,
            self.repo,
            task="v892 canonical evidence",
            controller="evidence_baseline",
            realized_action="bounded_observe",
            capability_id="v892-capability",
            pre_epoch_id=epoch_id,
            body_epoch=self.epoch.to_dict(),
            measured_transition=measured,
            host_manifest_before=manifest_hash,
            host_manifest_after=manifest_hash,
        )
        conformance_append = self.store.append_activation_conformance_receipt(
            self.repo, conformance_candidate
        )
        conformance = dict(conformance_append.get("receipt") or conformance_append)
        cohort_id = str(conformance["measurement_cohort_id"])
        self.store.set_setting(f"measurement_cohort:{self.repo}", cohort_id)
        measured["measurement_cohort_id"] = cohort_id
        self.store.set_setting(f"measured_event_latest:{self.repo}", measured)
        # Canonical stable telemetry fixture: hashes cover the declared
        # observation material and all regime/binding conditions are explicit.
        sense = {
            "repo": self.repo,
            "classification": "NOMINAL",
            "reasons": ["within_verified_regime"],
            "z_vector": [0.0],
            "residual_r": 0.0,
            "F_t": 1.0,
            "gates": {"epoch_current": True, "phase_bound": True},
            "baseline_n_updates": 16,
            "version": __import__("cortex").__version__,
            "observation_id": "sense_v892",
        }
        sense["observation_hash"] = sha(
            {key: sense[key] for key in ("repo", "classification", "reasons", "z_vector", "residual_r", "F_t", "gates", "baseline_n_updates", "version")}
        )
        binding = {
            "repo": self.repo,
            "classification": "VERIFIED_REGIME",
            "reasons": ["bound_and_warm"],
            "field_vector": {"binding_ok": 1.0},
            "version": __import__("cortex").__version__,
            "signals": {"last_frame_classification": "QUIESCENT"},
            "observation_id": "bind_v892",
        }
        binding["observation_hash"] = sha(
            {key: binding[key] for key in ("repo", "classification", "reasons", "field_vector", "version")}
        )
        self.store.set_setting(f"self_sensing_latest:{self.repo}", sense)
        self.store.set_setting(f"binding_field_latest:{self.repo}", binding)
        prior = capture_atomic_interconnect_frame(
            self.store, self.repo, session_id=session_id, turn_id=1,
            body_epoch_id=epoch_id, repository_id=will["repository_id"],
        )
        self.store.append_interconnect_frame(self.repo, prior)
        nxt = capture_atomic_interconnect_frame(
            self.store, self.repo, session_id=session_id, turn_id=2,
            body_epoch_id=epoch_id, repository_id=will["repository_id"],
            prior_frame_hash=prior["receipt_hash"],
        )
        self.store.append_interconnect_frame(self.repo, nxt)
        transition = build_interconnect_transition(
            prior_frame=prior, next_frame=nxt, outcome=outcome
        )
        self.store.append_interconnect_transition(self.repo, transition)
        self.store.record_outcome(
            self.repo,
            outcome_id="v892-outcome",
            activation_id="v892-activation",
            status="success",
            reward=1.0,
            verification_type="independent",
            verification_payload={"transition_hash": transition["receipt_hash"]},
            credits=[],
            updates=[],
            apply_updates=False,
        )
        witness = commit_manifest(
            [{"id": "v892-case", "query": "README provenance", "expected_substrings": ["README"]}],
            store=self.store,
        )
        witness_result = run_witness(
            self.store,
            self.repo,
            commitment=witness,
            revealed_cases=[{"id": "v892-case", "query": "README provenance", "expected_substrings": ["README"]}],
            controller="evidence_baseline",
            body_epoch_id=epoch_id,
            session_id=session_id,
            outcome_id=outcome["outcome_id"],
            activation_id=outcome["activation_id"],
            transition_hash=transition["receipt_hash"],
        )
        self.assertTrue(witness_result.get("canonical_persistence") in {"committed", "duplicate"}, witness_result)
        outcome["witness_result_hash"] = witness_result["witness_result_hash"]
        batch = extract_distillation_candidates(
            prior_frame=prior, next_frame=nxt, transition=transition, outcome=outcome
        )
        self.store.append_distillation_candidate_batch(self.repo, batch)
        gate_evidence = {
            "constitutional_receipt_hash": conformance["receipt_hash"],
            "stability_receipt_hash": sense["observation_hash"],
            "measurement_cohort_id": cohort_id,
            "transition_hash": transition["receipt_hash"],
            "witness_result_hash": witness_result["witness_result_hash"],
        }
        admission = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            batches=[batch],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
            witness={"witness_result_hash": witness_result["witness_result_hash"], "controller": "evidence_baseline"},
            outcome=outcome,
            gate_evidence=gate_evidence,
            session_id=session_id,
            body_epoch_id=epoch_id,
            turn_id=2,
        )
        self.assertEqual(admission["gates"]["overall"], "pass", admission)
        self.assertEqual(admission["admitted_count"], 1, admission)
        committed = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={
                "session_id": session_id,
                "body_epoch_id": epoch_id,
                "repository_id": will["repository_id"],
            },
        )
        self.assertEqual(committed["committed_count"], 1, committed)
        memory = list_admitted_memories(self.store, self.repo)[0]
        return memory, will, admission

    def test_caller_true_cannot_open_naked_candidate(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        receipt = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            candidates=[{
                "candidate_id": "naked",
                "candidate_type": "unresolved_ambiguity",
                "summary": "caller assertion",
                "support_level": "none",
            }],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertNotEqual(receipt["gates"]["overall"], "pass")
        self.assertEqual(receipt["admitted_count"], 0)
        self.assertFalse(receipt["durable_write_authorized"])

    def test_unknown_gate_and_structural_inspection_cannot_promote(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        unknown = apply_will_bound_membrane(
            self.store,
            self.repo,
            will=will,
            will_secret="v892-secret",
            candidates=[],
            constitutional_gate=True,
            epoch_compatible=True,
            witness_present=True,
            outcome_closed=True,
            stable_regime=True,
        )
        self.assertEqual(unknown["gates"]["overall"], "unknown")
        self.assertFalse(unknown["durable_write_authorized"])
        memory, will, _ = self._canonical_memory()
        shallow = dict(memory)
        shallow["membrane_receipt_hash"] = "x" * 64
        # A structural report may be requested, but cannot become guidance.
        projection = project_memories(
            self.store,
            self.repo,
            task="stable route",
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
            structural_inspection=True,
        )
        self.assertNotIn(shallow.get("memory_id"), projection["selected_memory_ids"])

    def test_canonical_append_failure_does_not_advance_latest(self) -> None:
        will = issue_will(
            self.store,
            self.repo,
            principal_id="operator",
            secret="v892-secret",
            clauses=[{"kind": "admit_type", "candidate_types": ["unresolved_ambiguity"]}],
        )
        original = self.store.append_membrane_admission

        def fail_append(repo: str, receipt: dict) -> dict:
            raise RuntimeError("forced canonical failure")

        self.store.append_membrane_admission = fail_append  # type: ignore[method-assign]
        try:
            receipt = apply_will_bound_membrane(
                self.store,
                self.repo,
                will=will,
                will_secret="v892-secret",
                candidates=[],
                persist=True,
            )
        finally:
            self.store.append_membrane_admission = original  # type: ignore[method-assign]
        self.assertEqual(receipt["canonical_persistence"], "failed")
        self.assertIsNone(self.store.get_setting(f"membrane_latest:{self.repo}", None))
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_read_projection_and_epoch_mismatch_do_not_append_state(self) -> None:
        memory, will, _ = self._canonical_memory()
        before = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        projection = project_memories(
            self.store,
            self.repo,
            task="stable route",
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
        )
        after = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        self.assertEqual(before, after)
        self.assertEqual(projection["durable_state_before"], projection["durable_state_after"])
        self.assertFalse(projection["persisted"])
        stale = evaluate_memory_eligibility(
            self.store,
            self.repo,
            memory,
            live_epoch_id="prior-or-future-epoch",
            current_will=will,
            will_secret="v892-secret",
        )
        self.assertFalse(stale["eligible"])
        self.assertIn("epoch_mismatch", stale["exclusions"])
        self.assertEqual(before, self.store.list_memory_state_receipts(self.repo, memory["memory_id"]))

    def test_deep_verification_rejects_tamper_and_shallow_lineage(self) -> None:
        memory, _, _ = self._canonical_memory()
        tampered = dict(memory)
        tampered["summary"] = "rewritten"
        report = deep_verify_admitted_memory(self.store, self.repo, tampered)
        self.assertFalse(report["structural_validity"])
        self.assertFalse(report["valid"])
        shallow = dict(memory)
        shallow["membrane_receipt_hash"] = "f" * 64
        shallow_report = deep_verify_admitted_memory(self.store, self.repo, shallow)
        self.assertFalse(shallow_report["lineage_validity"])
        self.assertFalse(shallow_report["valid"])

    def test_projection_persist_is_receipt_only(self) -> None:
        memory, will, _ = self._canonical_memory()
        before = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        receipt = project_memories(
            self.store,
            self.repo,
            task="stable route",
            session_id="projection-session",
            turn_id=1,
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
            will_secret="v892-secret",
            persist=True,
        )
        after = self.store.list_memory_state_receipts(self.repo, memory["memory_id"])
        self.assertEqual(before, after)
        self.assertIn(receipt["canonical_persistence"], {"committed", "duplicate"})
        self.assertFalse(receipt["policy_effect"])
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_expired_will_is_not_current_authority(self) -> None:
        memory, will, _ = self._canonical_memory()
        expired = dict(will)
        expired["not_after"] = time.time() - 1
        eligibility = evaluate_memory_eligibility(
            self.store,
            self.repo,
            memory,
            current_will=expired,
            will_secret="v892-secret",
            live_epoch_id=self.epoch.epoch_id,
        )
        self.assertFalse(eligibility["gates"]["will"])
        self.assertFalse(eligibility["eligible"])
        self.assertFalse(eligibility["host_mutate_authorized"])
        self.assertFalse(eligibility["execution_authorized"])

    def test_duplicate_admission_is_exactly_once(self) -> None:
        memory, will, admission = self._canonical_memory()
        replay = commit_admitted_memories(
            self.store,
            self.repo,
            admission=admission,
            will=will,
            session={"session_id": "v892-session", "body_epoch_id": self.epoch.epoch_id},
        )
        self.assertEqual(replay["committed_count"], 0)
        self.assertEqual(replay["canonical_persistence"], "duplicate")
        self.assertEqual(len(list_admitted_memories(self.store, self.repo)), 1)
        self.assertFalse(memory["host_mutate_authorized"])
        self.assertFalse(memory["execution_authorized"])

    def test_canonical_memory_reaches_model_as_verified_semantic_guidance(self) -> None:
        memory, will, _ = self._canonical_memory()
        task = str(memory["summary"])
        semantic = build_semantic_memory_projection(
            self.store,
            self.repo,
            task=task,
            selected_memory_ids=[memory["memory_id"]],
            body_epoch_id=self.epoch.epoch_id,
            current_will=will,
        )
        self.assertEqual(
            semantic["projected_memory_ids"], [memory["memory_id"]], semantic
        )
        self.assertEqual(semantic["lessons"][0]["guidance"], memory["summary"])
        report = verify_semantic_memory_projection(
            self.store, self.repo, semantic, task=task
        )
        self.assertTrue(report["valid"], report)

        self.store.set_setting(
            f"projection_budget_active:{self.repo}",
            {
                "policy": {"max_memories": 8, "min_support": "none"},
                "mode": "DEFAULT",
                "budget_policy_hash": "test-semantic-budget",
            },
        )
        session = open_symbiotic_session(
            self.store,
            self.repo,
            task=task,
            provider="fixture",
            model_id="fixture",
            persist=True,
        )
        context = session["receipts"]["cortex_context"]
        self.assertEqual(context["semantic_memory_lesson_count"], 1)
        self.assertEqual(
            context["semantic_memory_lessons"][0]["memory_receipt_hash"],
            memory["receipt_hash"],
        )
        self.assertFalse(context["semantic_memory_lessons"][0]["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
