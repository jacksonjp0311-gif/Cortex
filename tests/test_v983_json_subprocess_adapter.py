from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from cortex.adapters.json_subprocess import JsonSubprocessAdapter
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import ModelInvocationRequest


class V983JsonSubprocessAdapterTests(unittest.TestCase):
    def _request(self, adapter):
        projection = {
            "schema_version": "cortex-task-context-projection/1.0",
            "repo": "Test", "repository_id": "repo", "session_id": "session",
            "turn_id": 0, "body_epoch_id": "epoch", "context_receipt_hash": "",
            "evidence_digests": [], "memory_episode_digests": [], "predictions": {},
            "unresolved_contradictions": [], "operating_regime": {}, "confidence": {},
            "constitutional_restrictions": ["host_source_mutation_forbidden"],
        }
        import hashlib
        projection["projection_hash"] = hashlib.sha256(
            json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        contract = TaskEvaluationContract(contract_id="adapter-test", expected_value="OK")
        return ModelInvocationRequest(
            repo="Test", repository_id="repo", session_id="session", turn_id=1,
            body_epoch_id="epoch", invocation_id="invoke", task_contract_hash=contract.contract_hash,
            context_projection=projection, context_projection_hash=projection["projection_hash"],
            tool_scopes=(), provider_family=adapter.provider_family, model_id=adapter.model_id,
            model_version=adapter.model_version, adapter_id=adapter.adapter_id,
            adapter_version=adapter.adapter_version,
            configuration={"task_instruction": "Return OK."}, requested_at=1.0,
        )

    def test_public_answer_crosses_without_hidden_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "model.py"
            script.write_text(
                "import json\nprint(json.dumps({'structuredOutput':{'answer':'OK'},'usage':{'output':1},'chain_of_thought':'hidden'}))\n",
                encoding="utf-8",
            )
            adapter = JsonSubprocessAdapter(
                command=sys.executable,
                argument_template=(str(script), "{model}", "{schema}", "{prompt}"),
                provider_family="test-cli", model_id="runtime-model", cwd=directory,
            )
            result = adapter.invoke(self._request(adapter))
            self.assertEqual(result["public_output"], {"text": "OK"})
            self.assertNotIn("chain_of_thought", json.dumps(result))
            self.assertEqual(result["tool_call_intents"], [])

    def test_template_must_bind_prompt_and_schema(self):
        with self.assertRaises(ValueError):
            JsonSubprocessAdapter(
                command=sys.executable, argument_template=("{prompt}",),
                provider_family="test-cli", model_id="runtime-model",
            )


if __name__ == "__main__":
    unittest.main()
