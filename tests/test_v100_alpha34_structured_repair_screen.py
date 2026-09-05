"""Alpha.34 structured-edit live-screen tests."""

from __future__ import annotations

import json
import copy
import hashlib
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.edit_intent import INTENT_SCHEMA
from cortex.executable_repair_forge import build_executable_repair_bundle
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.store import Store
from cortex.structured_repair_screen import (
    execute_structured_repair_screen,
    freeze_structured_repair_screen,
    verify_structured_repair_screen,
)
from cortex.will import register_will_principal


def _unit_specs() -> list[dict[str, str]]:
    return [
        {
            "case_id": f"structured_{index}",
            "task": "Repair value() so it returns the required value.",
            "source": "def value():\n    return 0\n",
            "test": "from module import value\nassert value() == 1\n",
            "patch": (
                "diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n"
                "@@ -1,2 +1,2 @@\n def value():\n-    return 0\n+    return 1\n"
            ),
        }
        for index in range(4)
    ]


class ExternalStructuredAdapter:
    provider_family = "external-structured-provider"
    model_id = "frontier-structured-model"
    model_version = "2026-09"
    adapter_id = "tests.external-structured-adapter"
    adapter_version = "1"

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)

    def invoke_agent(self, request):
        return {
            "request_hash": request.request_hash,
            "public_output": self.answers.pop(0),
            "finish_reason": "stop",
            "token_usage": {"input_tokens": 10, "output_tokens": 10},
        }


class Alpha34StructuredRepairScreenTests(unittest.TestCase):
    def test_evaluator_challenge_blocks_new_calls_not_historical_reconstruction(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, host, forge, private, adapter = fixture
            answers = list(adapter.answers)
            try:
                _, prior = self._run(fixture)
                adapter.answers = answers
                prereg = freeze_structured_repair_screen(
                    store, repo, forge_artifact=forge, private_bundle=private, adapter=adapter,
                )
                store.append_symbiotic_receipt(repo, {
                    "kind": "repair_evaluator_challenge", "session_id": prereg["session_id"],
                    "turn_id": 50, "body_epoch_id": prereg["body_epoch_id"],
                    "event_id": "test-evaluator-challenge",
                    "evaluator_commitment": prereg["cases"][0]["private_evaluator_commitment"],
                    "state": "resolved",  # Caller assertion cannot reopen the gate.
                })
                self.assertTrue(verify_structured_repair_screen(store, repo, result_receipt_hash=prior["receipt_hash"])["valid"])
                with self.assertRaisesRegex(ValueError, "evaluator challenged"):
                    freeze_structured_repair_screen(
                        store, repo, forge_artifact=forge, private_bundle=private, adapter=adapter,
                    )
                now = time.time()
                with patch("cortex.structured_repair_screen.NativeAgentRuntime") as runtime:
                    with self.assertRaisesRegex(ValueError, "evaluator challenged"):
                        execute_structured_repair_screen(
                            store, repo, preregistration=prereg, private_bundle=private,
                            adapter=adapter, tools=ToolRegistry(), grant=CapabilityGrant(
                                workspace_root=str(host), allowed_tools=(), principal_id="challenge-test",
                                purpose="must not invoke", issued_at=now, expires_at=now + 120,
                                max_tool_calls=0, max_total_tool_seconds=0,
                            ),
                        )
                    runtime.assert_not_called()
                from cortex.structured_repair_screen import _assert_evaluators_unchallenged
                _assert_evaluators_unchallenged(store, repo, [{"private_evaluator_commitment": "new-commitment"}])
            finally:
                store.close()

    def test_repeatability_is_frozen_noncalibrating_fresh_and_one_shot(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, host, forge, private, adapter = fixture
            answers = list(adapter.answers)
            try:
                _, prior = self._run(fixture)
                adapter.answers = list(answers)
                prereg = freeze_structured_repair_screen(
                    store, repo, forge_artifact=forge, private_bundle=private,
                    adapter=adapter, repeat_of_result_receipt_hash=prior["receipt_hash"],
                )
                now = time.time()
                args = dict(
                    preregistration=prereg, private_bundle=private, adapter=adapter,
                    tools=ToolRegistry(), grant=CapabilityGrant(
                        workspace_root=str(host), allowed_tools=(), principal_id="repeat-test",
                        purpose="four-call repeatability check", issued_at=now, expires_at=now + 120,
                        max_tool_calls=0, max_total_tool_seconds=0,
                    ),
                )
                result = execute_structured_repair_screen(store, repo, **args)
                audit = verify_structured_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])
                self.assertTrue(audit["valid"], audit["errors"])
                self.assertEqual(result["screen"]["state"], "repeatability_observed")
                self.assertFalse(result["baseline_calibrated"])
                self.assertEqual(result["repeatability"]["changed_outcomes"], 0)
                self.assertEqual(result["repeatability"]["distinct_task_count"], 4)
                self.assertIsNone(result["repeatability"]["independent_task_sample_size"])
                adapter.answers = list(answers)
                with patch("cortex.structured_repair_screen.NativeAgentRuntime") as runtime:
                    with self.assertRaises(ValueError):
                        execute_structured_repair_screen(store, repo, **args)
                    runtime.assert_not_called()
                # A canonical hash alone cannot make a false comparison true.
                forged = copy.deepcopy(result)
                forged["turn_id"] = 91
                forged["event_id"] = "wrong-repeat-comparison"
                forged["repeatability"]["changed_outcomes"] = 1
                forged = store.append_symbiotic_receipt(repo, forged)
                audit = verify_structured_repair_screen(store, repo, result_receipt_hash=forged["receipt_hash"])
                self.assertIn("repeatability_comparison_invalid", audit["errors"])
                # Reusing the old valid trajectories is not a fresh invocation.
                from cortex.structured_repair_screen import _sha
                replayed = []
                for index, value in enumerate(prior["case_receipt_hashes"]):
                    old = store.symbiotic_receipt(value, repo=repo)
                    old.update(preregistration_receipt_hash=prereg["receipt_hash"],
                               turn_id=92, event_id=f"replayed-case-{index}")
                    old["case_hash"] = _sha(prereg["cases"][index])
                    replayed.append(store.append_symbiotic_receipt(repo, old)["receipt_hash"])
                forged = {**result, "turn_id": 93, "event_id": "replay-result", "case_receipt_hashes": replayed}
                # Correct the aggregates so the replay guard, not a score mismatch, must reject it.
                forged["screen"] = {**result["screen"], "success_count": 4, "success_rate": 1.0}
                forged = store.append_symbiotic_receipt(repo, forged)
                audit = verify_structured_repair_screen(store, repo, result_receipt_hash=forged["receipt_hash"])
                self.assertIn("repeatability_trajectory_replay", audit["errors"])
            finally:
                store.close()

    def test_repeatability_cannot_change_contract_or_hide_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, forge, private, adapter = fixture
            answers = list(adapter.answers)
            try:
                _, prior = self._run(fixture)
                adapter.answers = answers
                changed = copy.deepcopy(forge)
                changed["public_corpus"]["cases"][0]["task"] += " Changed requirement."
                # A valid but different corpus still may not masquerade as a repeat.
                other_specs = _unit_specs()
                other_specs[0]["task"] += " Changed requirement."
                public, other_private = build_executable_repair_bundle(secret_seed="different", case_specs=other_specs)
                changed["public_corpus"] = public
                with self.assertRaisesRegex(ValueError, "repeatability prerequisite"):
                    freeze_structured_repair_screen(
                        store, repo, forge_artifact=changed, private_bundle=other_private,
                        adapter=adapter, repeat_of_result_receipt_hash=prior["receipt_hash"],
                    )
                prereg = freeze_structured_repair_screen(
                    store, repo, forge_artifact=forge, private_bundle=private,
                    adapter=adapter, repeat_of_result_receipt_hash=prior["receipt_hash"],
                )
                from cortex.structured_repair_screen import _repeat_binding_errors
                for field, value in (("new_calls", 8), ("difficulty_change_authorized", True), ("automatic_retries", False)):
                    altered = copy.deepcopy(prereg)
                    altered["repeatability_binding"]["policy"][field] = value
                    self.assertEqual(_repeat_binding_errors(store, repo, altered), ["repeatability_policy_invalid"])
                del prereg["repeatability_binding"]
                self.assertEqual(_repeat_binding_errors(store, repo, prereg), ["screen_policy_missing"])
            finally:
                store.close()

    def test_changed_private_evaluator_is_rejected_before_any_model_call(self):
        with tempfile.TemporaryDirectory() as temp:
            store, repo, host, forge, private, adapter = self._fixture(temp)
            try:
                prereg = freeze_structured_repair_screen(
                    store, repo, forge_artifact=forge, private_bundle=private, adapter=adapter,
                )
                private = copy.deepcopy(private)
                private["cases"][0]["external_test"] = "assert True\n"
                now = time.time()
                grant = CapabilityGrant(
                    workspace_root=str(host), allowed_tools=(), principal_id="audit",
                    purpose="private-binding-test", issued_at=now, expires_at=now + 120,
                    max_tool_calls=0, max_total_tool_seconds=0,
                )
                with patch("cortex.structured_repair_screen.NativeAgentRuntime") as runtime:
                    with self.assertRaisesRegex(ValueError, "private evaluator binding"):
                        execute_structured_repair_screen(
                            store, repo, preregistration=prereg, private_bundle=private,
                            adapter=adapter, tools=ToolRegistry(), grant=grant,
                        )
                    runtime.assert_not_called()
            finally:
                store.close()

    def test_hash_valid_receipts_cannot_substitute_for_cross_receipt_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, _, _, _ = fixture
            try:
                _, result = self._run(fixture)
                first = store.symbiotic_receipt(result["case_receipt_hashes"][0], repo=repo)
                serial = 0

                def seal(body):
                    nonlocal serial
                    serial += 1
                    body = copy.deepcopy(body)
                    body["turn_id"] = 100 + serial
                    body["event_id"] = f"audit-resealed-{serial}"
                    return store.append_symbiotic_receipt(repo, body)

                accepted = []
                for field, value in (
                    ("calls_executed", 99), ("baseline_calibrated", True),
                    ("next_action", "promote"), ("model_identity", {"model_id": "unrelated"}),
                    ("kind", "unrelated_result"), ("evidence_class", "synthetic"),
                    ("repeatability", {"changed_outcomes": 0}),
                ):
                    forged = seal({**result, field: value})
                    if verify_structured_repair_screen(store, repo, result_receipt_hash=forged["receipt_hash"])["valid"]:
                        accepted.append("result:" + field)
                for field, value in (
                    ("case_hash", "0" * 64),
                    ("preregistration_receipt_hash", "0" * 64),
                    ("kind", "unrelated_case"), ("evidence_class", "synthetic"),
                    ("execution_authorized", True),
                ):
                    forged_case = seal({**first, field: value})
                    forged = seal({**result, "case_receipt_hashes": [forged_case["receipt_hash"], *result["case_receipt_hashes"][1:]]})
                    if verify_structured_repair_screen(store, repo, result_receipt_hash=forged["receipt_hash"])["valid"]:
                        accepted.append("case:" + field)
                evaluation = copy.deepcopy(first["evaluation"])
                evaluation["evaluator_commitment"] = "0" * 64
                evaluation["evaluation_hash"] = hashlib.sha256(json.dumps(
                    {k: v for k, v in evaluation.items() if k != "evaluation_hash"},
                    sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                ).encode()).hexdigest()
                forged_case = seal({**first, "evaluation": evaluation})
                forged = seal({**result, "case_receipt_hashes": [forged_case["receipt_hash"], *result["case_receipt_hashes"][1:]]})
                if verify_structured_repair_screen(store, repo, result_receipt_hash=forged["receipt_hash"])["valid"]:
                    accepted.append("evaluation:evaluator_commitment")
                self.assertEqual(accepted, [], "Hash-valid substitutions accepted: " + str(accepted))
            finally:
                store.close()

    def _fixture(self, temp: str, *, valid_answers: bool = True):
        root = Path(temp)
        home = ensure_home(root / "home")
        host = root / "host"
        host.mkdir()
        (host / "README.md").write_text("alpha34\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        repo = "Alpha34Host"
        bootstrap_repository(home, store, host, repo)
        public, private = build_executable_repair_bundle(secret_seed="alpha34-unit-secret", case_specs=_unit_specs())
        intent = json.dumps({
            "schema_version": INTENT_SCHEMA,
            "summary": "return the required value",
            "edits": [{"path": "module.py", "old": "    return 0\n", "new": "    return 1\n"}],
        })
        adapter = ExternalStructuredAdapter([intent] * 4 if valid_answers else ["not structured json"] * 4)
        register_will_principal(store, repo, "alpha34-operator", "Alpha.34 test operator", secret="alpha34-secret")
        register_adapter_provenance(
            store,
            repo,
            adapter,
            boundary_kind="external_api",
            principal_id="alpha34-operator",
            principal_secret="alpha34-secret",
            endpoint_descriptor={"transport": "test_external_boundary"},
            model_family="frontier-structured-family",
            capability_class="structured_code_repair",
        )
        forge = {
            "state": "EXECUTABLE_REPAIR_FORGE_READY",
            "result_hash": "b" * 64,
            "corpus_hash": public["corpus_hash"],
            "public_corpus": public,
        }
        return store, repo, host, forge, private, adapter

    def _run(self, fixture):
        store, repo, host, forge, private, adapter = fixture
        prereg = freeze_structured_repair_screen(
            store,
            repo,
            forge_artifact=forge,
            private_bundle=private,
            adapter=adapter,
        )
        now = time.time()
        grant = CapabilityGrant(
            workspace_root=str(host),
            allowed_tools=(),
            principal_id="alpha34-test",
            purpose="four-call structured repair screen",
            issued_at=now,
            expires_at=now + 120,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_structured_repair_screen(
            store,
            repo,
            preregistration=prereg,
            private_bundle=private,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        return prereg, result

    def test_structured_intents_produce_reconstructed_ceiling_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, _, _, _ = fixture
            try:
                prereg, result = self._run(fixture)
                self.assertEqual(prereg["response_contract"]["schema_version"], INTENT_SCHEMA)
                self.assertEqual(prereg["tools"], [])
                self.assertEqual(result["screen"]["success_count"], 4)
                self.assertEqual(result["screen"]["state"], "screening_ceiling")
                audit = verify_structured_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])
                self.assertTrue(audit["valid"], audit["errors"])
                for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
                    self.assertFalse(result[field])
            finally:
                store.close()

    def test_malformed_intents_are_measured_failures_and_reconstruct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp, valid_answers=False)
            store, repo, _, _, _, _ = fixture
            try:
                _, result = self._run(fixture)
                self.assertEqual(result["screen"]["success_count"], 0)
                self.assertEqual(result["screen"]["state"], "screening_floor")
                audit = verify_structured_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])
                self.assertTrue(audit["valid"], audit["errors"])
            finally:
                store.close()

    def test_harder_followup_requires_canonical_same_model_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, forge, private, adapter = fixture
            try:
                _, ceiling = self._run(fixture)
                register_adapter_provenance(
                    store,
                    repo,
                    adapter,
                    boundary_kind="external_api",
                    principal_id="alpha34-operator",
                    principal_secret="alpha34-secret",
                    endpoint_descriptor={"transport": "test_external_boundary"},
                    model_family="frontier-structured-family",
                    capability_class="structured_code_repair",
                )
                followup = freeze_structured_repair_screen(
                    store,
                    repo,
                    forge_artifact=forge,
                    private_bundle=private,
                    adapter=adapter,
                    prior_result_receipt_hash=ceiling["receipt_hash"],
                )
                binding = followup["prior_screen_binding"]
                self.assertEqual(binding["prior_screen_state"], "screening_ceiling")
                self.assertEqual(binding["difficulty_transition"], "move_harder")
                other_adapter = ExternalStructuredAdapter([])
                other_adapter.model_id = "different-frontier-model"
                register_adapter_provenance(
                    store,
                    repo,
                    other_adapter,
                    boundary_kind="external_api",
                    principal_id="alpha34-operator",
                    principal_secret="alpha34-secret",
                    endpoint_descriptor={"transport": "test_external_boundary"},
                    model_family="different-frontier-family",
                    capability_class="structured_code_repair",
                )
                with self.assertRaisesRegex(ValueError, "canonical same-model"):
                    freeze_structured_repair_screen(
                        store,
                        repo,
                        forge_artifact=forge,
                        private_bundle=private,
                        adapter=other_adapter,
                        prior_result_receipt_hash=ceiling["receipt_hash"],
                    )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
