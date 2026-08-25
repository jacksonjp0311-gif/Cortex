"""Optional provider-neutral JSON subprocess adapter.

The host supplies an executable and argument template. Cortex never invokes a
shell, never supplies tools, and persists only the bounded public answer and
usage metadata returned through the ModelAdapter contract.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..model_circulation import ModelAdapterError, ModelInvocationRequest

ADAPTER_ID = "cortex.optional.json-subprocess"
ADAPTER_VERSION = "1"
MAX_OUTPUT_BYTES = 1_048_576


class JsonSubprocessAdapter:
    """Run one host-selected CLI that emits a structured public answer."""

    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(
        self,
        *,
        command: str,
        argument_template: Sequence[str],
        provider_family: str,
        model_id: str,
        model_version: str = "undeclared",
        cwd: str | Path | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        executable = str(Path(command).expanduser().resolve())
        if not Path(executable).is_file():
            raise ModelAdapterError("JSON subprocess executable does not exist")
        if "{prompt}" not in argument_template or "{schema}" not in argument_template:
            raise ModelAdapterError("argument template must bind prompt and schema")
        self.command = executable
        self.argument_template = tuple(str(value) for value in argument_template)
        self.provider_family = str(provider_family or "").strip()
        self.model_id = str(model_id or "").strip()
        self.model_version = str(model_version or "undeclared")
        self.cwd = str(Path(cwd or Path.cwd()).resolve())
        self.timeout_seconds = float(timeout_seconds)
        if not self.provider_family or not self.model_id:
            raise ModelAdapterError("provider family and model identity are required")
        if not 1 <= self.timeout_seconds <= 600:
            raise ModelAdapterError("subprocess timeout must be in [1, 600] seconds")

    @staticmethod
    def _schema() -> str:
        return json.dumps({
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        }, separators=(",", ":"))

    @staticmethod
    def _parse(stdout: str) -> Mapping[str, Any]:
        start = stdout.find("{")
        if start < 0:
            raise ModelAdapterError("JSON subprocess returned no object")
        try:
            envelope = json.loads(stdout[start:])
        except json.JSONDecodeError as exc:
            raise ModelAdapterError("JSON subprocess output is malformed") from exc
        if not isinstance(envelope, Mapping):
            raise ModelAdapterError("JSON subprocess envelope must be a mapping")
        structured = envelope.get("structuredOutput")
        if not isinstance(structured, Mapping) or not isinstance(structured.get("answer"), str):
            raise ModelAdapterError("JSON subprocess did not return a public answer")
        return envelope

    def invoke(self, request: ModelInvocationRequest) -> Mapping[str, Any]:
        if not isinstance(request, ModelInvocationRequest) or request.verify().get("valid") is not True:
            raise ModelAdapterError("JSON subprocess requires a valid canonical request")
        instruction = str(request.configuration.get("task_instruction") or "").strip()
        if not instruction:
            raise ModelAdapterError("canonical task_instruction is required")
        prompt = (
            "This is a no-tools development calibration task. Follow the stated "
            "algorithm exactly. Return only the requested answer in the answer field. "
            "Do not provide or reveal private chain-of-thought. " + instruction
        )
        replacements = {
            "{prompt}": prompt,
            "{schema}": self._schema(),
            "{model}": self.model_id,
        }
        arguments = [replacements.get(value, value) for value in self.argument_template]
        started = time.time()
        try:
            completed = subprocess.run(
                [self.command, *arguments],
                cwd=self.cwd,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ModelAdapterError(f"JSON subprocess boundary failed: {type(exc).__name__}") from exc
        if completed.returncode != 0:
            raise ModelAdapterError(f"JSON subprocess exited with code {completed.returncode}")
        if len(completed.stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ModelAdapterError("JSON subprocess output exceeds bounded limit")
        envelope = self._parse(completed.stdout)
        answer = str((envelope.get("structuredOutput") or {}).get("answer") or "")
        return {
            "request_hash": request.request_hash,
            "public_output": {"text": answer},
            "proposal": {
                "interpreted_objective": "solve the exact development calibration case",
                "proposed_action": "return bounded public answer",
                "requested_permissions": [],
            },
            "declared_uncertainty": 1.0,
            "evidence_citations": [],
            "tool_call_intents": [],
            "rationale_public": "bounded public answer; private reasoning not requested or stored",
            "token_usage": dict(envelope.get("usage") or {}),
            "cost": {
                "currency": "USD",
                "amount": float(envelope.get("total_cost_usd") or 0.0),
            },
            "completed_at": time.time(),
            "transport_elapsed_ms": round((time.time() - started) * 1000.0, 3),
        }


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "JsonSubprocessAdapter"]
