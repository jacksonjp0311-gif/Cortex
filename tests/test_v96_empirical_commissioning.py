"""Focused v9.6 empirical commissioning and optional adapter tests."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.adapters.ollama_local import OllamaLocalAdapter
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.empirical_commissioning import (
    STATUS_HELD,
    verify_empirical_commissioning,
)
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import (
    FixtureAdapter,
    ModelAdapterError,
    ModelInvocationRequest,
    run_model_circulation,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class _OllamaHandler(BaseHTTPRequestHandler):
    response_model = "test-model"
    public_payload = {
        "public_output": {"text": "CORTEX_EMPIRICAL_TEST_TOKEN"},
        "proposal": {
            "interpreted_objective": "return the bounded test token",
            "proposed_action": "return public text only",
        },
        "declared_uncertainty": 0.1,
        "rationale_public": "bounded public rationale",
        "empirical": True,
        "chain_of_thought": "must never cross",
    }

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("Content-Length") or 0)
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.last_request = request  # type: ignore[attr-defined]
        envelope = {
            "model": self.response_model,
            "response": json.dumps(self.public_payload),
            "prompt_eval_count": 20,
            "eval_count": 8,
        }
        encoded = json.dumps(envelope).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class V96EmpiricalCommissioningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("v9.6 commissioning\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "V96Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Commissioning Operator",
            secret="v96-test-principal-secret",
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _OllamaHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/api/generate"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.store.close()
        self.temporary.cleanup()

    def _contract(self) -> TaskEvaluationContract:
        return TaskEvaluationContract(
            contract_id="v96-test-contract",
            expected_value="CORTEX_EMPIRICAL_TEST_TOKEN",
        )

    def _request(self, adapter: OllamaLocalAdapter) -> ModelInvocationRequest:
        projection = {
            "schema_version": "cortex-task-context-projection/1.0",
            "repo": self.repo,
            "repository_id": "repo-v96",
            "session_id": "session-v96",
            "turn_id": 0,
            "body_epoch_id": "epoch-v96",
            "context_receipt_hash": "",
            "evidence_digests": [],
            "memory_episode_digests": [],
            "predictions": {},
            "unresolved_contradictions": [],
            "operating_regime": {},
            "confidence": {},
            "constitutional_restrictions": ["host_source_mutation_forbidden"],
        }
        import hashlib

        canonical = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        projection_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        projection["projection_hash"] = projection_hash
        return ModelInvocationRequest(
            repo=self.repo,
            repository_id="repo-v96",
            session_id="session-v96",
            turn_id=1,
            body_epoch_id="epoch-v96",
            invocation_id="invoke-v96",
            task_contract_hash=self._contract().contract_hash,
            context_projection=projection,
            context_projection_hash=projection_hash,
            tool_scopes=(),
            provider_family=adapter.provider_family,
            model_id=adapter.model_id,
            model_version=adapter.model_version,
            adapter_id=adapter.adapter_id,
            adapter_version=adapter.adapter_version,
            configuration={"task_instruction": "Return the commissioning token."},
            requested_at=1.0,
        )

    def test_adapter_invokes_loopback_and_strips_provider_native_fields(self) -> None:
        adapter = OllamaLocalAdapter(model_id="test-model", endpoint=self.endpoint)
        result = adapter.invoke(self._request(adapter))
        self.assertEqual(
            result["public_output"]["text"], "CORTEX_EMPIRICAL_TEST_TOKEN"
        )
        self.assertNotIn("empirical", result)
        self.assertNotIn("chain_of_thought", json.dumps(result))
        self.assertEqual(result["token_usage"]["total"], 28)
        sent = self.server.last_request  # type: ignore[attr-defined]
        self.assertFalse(sent["think"])
        self.assertIn("private chain-of-thought", sent["prompt"])

    def test_adapter_refuses_nonloopback_credentials_and_missing_task(self) -> None:
        with self.assertRaises(ModelAdapterError):
            OllamaLocalAdapter(model_id="x", endpoint="https://example.com/api/generate")
        with self.assertRaises(ModelAdapterError):
            OllamaLocalAdapter(
                model_id="x", endpoint="http://user:pass@127.0.0.1:11434/api/generate"
            )
        adapter = OllamaLocalAdapter(model_id="test-model", endpoint=self.endpoint)
        request = self._request(adapter)
        request = ModelInvocationRequest(
            **{**request.__dict__, "configuration": {}}
        )
        with self.assertRaises(ModelAdapterError):
            adapter.invoke(request)

    def test_response_model_mismatch_fails_closed(self) -> None:
        adapter = OllamaLocalAdapter(model_id="different-model", endpoint=self.endpoint)
        with self.assertRaises(ModelAdapterError):
            adapter.invoke(self._request(adapter))

    def test_fixture_circulation_cannot_obtain_empirical_seal(self) -> None:
        session = open_symbiotic_session(
            self.store, self.repo, task="fixture cannot become empirical"
        )
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=FixtureAdapter(text="CORTEX_EMPIRICAL_TEST_TOKEN"),
            task_contract=self._contract(),
            observed_result=None,
        )
        seal = verify_empirical_commissioning(
            self.store,
            self.repo,
            result["session_id"],
            turn_id=result["turn_id"],
        )
        self.assertEqual(seal["status"], STATUS_HELD)
        self.assertIn("live_empirical_adapter_evidence_required", seal["errors"])
        self.assertTrue(seal["caller_result_used"] is False)

    def test_simulated_http_boundary_remains_nonempirical(self) -> None:
        adapter = OllamaLocalAdapter(model_id="test-model", endpoint=self.endpoint)
        register_adapter_provenance(
            self.store,
            self.repo,
            adapter,
            boundary_kind="simulation",
            principal_id="operator",
            principal_secret="v96-test-principal-secret",
            endpoint_descriptor={"transport": "loopback-test-server"},
            model_family="test-model-family",
            capability_class="test-generation",
        )
        session = open_symbiotic_session(
            self.store, self.repo, task="simulated boundary remains simulated"
        )
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=adapter,
            task_contract=self._contract(),
            configuration={"task_instruction": "Return the commissioning token."},
        )
        seal = verify_empirical_commissioning(
            self.store,
            self.repo,
            result["session_id"],
            turn_id=result["turn_id"],
        )
        self.assertEqual(seal["status"], STATUS_HELD)
        self.assertEqual(seal["evidence_class"], "simulated")
        self.assertFalse(seal["host_mutate_authorized"])
        self.assertFalse(seal["execution_authorized"])

    def test_one_adapter_implementation_can_bind_two_exact_models(self) -> None:
        first = OllamaLocalAdapter(model_id="test-model", endpoint=self.endpoint)
        second = OllamaLocalAdapter(model_id="second-model", endpoint=self.endpoint)
        first_registration = register_adapter_provenance(
            self.store,
            self.repo,
            first,
            boundary_kind="simulation",
            principal_id="operator",
            principal_secret="v96-test-principal-secret",
            endpoint_descriptor={"model": "test-model"},
            model_family="test-family",
            capability_class="test-generation",
        )
        second_registration = register_adapter_provenance(
            self.store,
            self.repo,
            second,
            boundary_kind="simulation",
            principal_id="operator",
            principal_secret="v96-test-principal-secret",
            endpoint_descriptor={"model": "second-model"},
            model_family="test-family",
            capability_class="test-generation",
        )
        self.assertNotEqual(
            first_registration["binding_digest"], second_registration["binding_digest"]
        )
        self.assertNotEqual(
            first_registration["registration_id"], second_registration["registration_id"]
        )
        rows = self.store.db.execute(
            "SELECT registration_id,registration_hash,registration_json "
            "FROM model_adapter_registrations ORDER BY registration_id"
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(str(row["registration_hash"])) == 64 for row in rows))

    def test_verifier_reconstructs_from_ledger_not_caller_result(self) -> None:
        session = open_symbiotic_session(self.store, self.repo, task="ledger reconstruction")
        result = run_model_circulation(
            self.store,
            self.repo,
            session,
            adapter=FixtureAdapter(text="CORTEX_EMPIRICAL_TEST_TOKEN"),
            task_contract=self._contract(),
        )
        forged = dict(result)
        forged["evidence_class"] = "live_empirical"
        forged["host_mutate_authorized"] = True
        seal = verify_empirical_commissioning(
            self.store, self.repo, result["session_id"], turn_id=result["turn_id"]
        )
        self.assertNotEqual(forged["evidence_class"], seal["evidence_class"])
        self.assertFalse(seal["caller_result_used"])
        self.assertFalse(seal["host_mutate_authorized"])


if __name__ == "__main__":
    unittest.main()
