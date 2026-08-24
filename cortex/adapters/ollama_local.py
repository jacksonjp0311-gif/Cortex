"""Optional loopback Ollama adapter for provider-neutral model circulation.

This module is an integration boundary, not part of Cortex's canonical model
ontology.  It translates one :class:`ModelInvocationRequest` into Ollama's
local HTTP API and returns only the public ``ModelAdapter`` result surface.
Provider-native response bodies and hidden reasoning never cross that boundary.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from ..model_circulation import (
    ModelAdapterError,
    ModelInvocationRequest,
)

ADAPTER_ID = "cortex.optional.ollama-local-http"
ADAPTER_VERSION = "1"
DEFAULT_ENDPOINT = "http://127.0.0.1:11434/api/generate"
MAX_RESPONSE_BYTES = 1_048_576
MAX_PROMPT_CHARS = 131_072

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "public_output": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "proposal": {
            "type": "object",
            "properties": {
                "interpreted_objective": {"type": "string"},
                "proposed_action": {"type": "string"},
            },
            "required": ["proposed_action"],
            "additionalProperties": False,
        },
        "declared_uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence_citations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rationale_public": {"type": "string"},
    },
    "required": ["public_output", "proposal"],
    "additionalProperties": False,
}


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _loopback_endpoint(value: str) -> str:
    try:
        parsed = urlsplit(str(value or ""))
        port = parsed.port
    except ValueError as exc:
        raise ModelAdapterError("Ollama endpoint is malformed") from exc
    if parsed.scheme != "http":
        raise ModelAdapterError("Ollama local adapter requires an http loopback endpoint")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ModelAdapterError("Ollama endpoint may not contain credentials or query material")
    host = str(parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ModelAdapterError("Ollama local adapter refuses non-loopback endpoints")
    if parsed.path.rstrip("/") != "/api/generate":
        raise ModelAdapterError("Ollama endpoint must target /api/generate")
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc += f":{port}"
    return urlunsplit(("http", netloc, "/api/generate", "", ""))


class OllamaLocalAdapter:
    """Host-registerable live adapter for a loopback Ollama inference server."""

    provider_family = "ollama-local"
    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(
        self,
        *,
        model_id: str,
        model_version: str = "undeclared",
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_seconds: float = 120.0,
        temperature: float = 0.0,
        max_output_tokens: int = 256,
        keep_alive: str = "0s",
    ) -> None:
        model = str(model_id or "").strip()
        if not model or any(char in model for char in ("\x00", "\r", "\n")):
            raise ModelAdapterError("Ollama model_id is required and must be bounded text")
        timeout = float(timeout_seconds)
        if timeout <= 0 or timeout > 600:
            raise ModelAdapterError("Ollama timeout must be in (0, 600] seconds")
        output_tokens = int(max_output_tokens)
        if output_tokens < 1 or output_tokens > 4096:
            raise ModelAdapterError("Ollama output token budget must be in [1, 4096]")
        temp = float(temperature)
        if temp < 0 or temp > 2:
            raise ModelAdapterError("Ollama temperature must be in [0, 2]")

        self.model_id = model
        self.model_version = str(model_version or "undeclared")
        self.endpoint = _loopback_endpoint(endpoint)
        self.timeout_seconds = timeout
        self.temperature = temp
        self.max_output_tokens = output_tokens
        self.keep_alive = str(keep_alive or "0s")

    def _prompt(self, request: ModelInvocationRequest) -> str:
        configuration = dict(request.configuration or {})
        instruction = str(configuration.get("task_instruction") or "").strip()
        if not instruction:
            transfer = (
                request.context_projection.get("predictions", {}).get("transfer_context", {})
                if isinstance(request.context_projection, Mapping)
                else {}
            )
            instruction = str(transfer.get("task") or "").strip() if isinstance(transfer, Mapping) else ""
        if not instruction:
            raise ModelAdapterError(
                "live model invocation requires a canonical task_instruction or transfer task"
            )

        public_context = {
            "task_instruction": instruction,
            "task_contract_hash": request.task_contract_hash,
            "context_projection": dict(request.context_projection),
            "tool_scopes": list(request.tool_scopes),
            "constitutional_restrictions": list(
                request.context_projection.get("constitutional_restrictions") or ()
            ),
        }
        prompt = (
            "You are a replaceable model behind the Cortex ModelAdapter boundary. "
            "Return only one JSON object matching the supplied schema. Do not reveal or "
            "describe private chain-of-thought. The public rationale must be concise. "
            "A proposal is advisory and has no execution, mutation, memory, or policy authority.\n\n"
            + _canonical(public_context)
        )
        if len(prompt) > MAX_PROMPT_CHARS:
            raise ModelAdapterError("canonical Ollama prompt exceeds the bounded adapter limit")
        return prompt

    def invoke(self, request: ModelInvocationRequest) -> Mapping[str, Any]:
        if not isinstance(request, ModelInvocationRequest):
            raise ModelAdapterError("Ollama adapter requires ModelInvocationRequest")
        if request.verify().get("valid") is not True:
            raise ModelAdapterError("Ollama adapter refuses an invalid canonical request")

        payload = {
            "model": self.model_id,
            "prompt": self._prompt(request),
            "stream": False,
            "format": _OUTPUT_SCHEMA,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_output_tokens,
            },
        }
        encoded = _canonical(payload).encode("utf-8")
        http_request = Request(
            self.endpoint,
            data=encoded,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        started = time.time()
        try:
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ModelAdapterError(f"Ollama inference boundary failed: {type(exc).__name__}") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ModelAdapterError("Ollama response exceeds the bounded adapter limit")
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelAdapterError("Ollama response envelope is not valid JSON") from exc
        if not isinstance(envelope, Mapping):
            raise ModelAdapterError("Ollama response envelope must be a mapping")
        response_model = str(envelope.get("model") or "")
        if response_model and response_model != self.model_id:
            raise ModelAdapterError("Ollama response model does not match the registered model")
        try:
            public = json.loads(str(envelope.get("response") or ""))
        except json.JSONDecodeError as exc:
            raise ModelAdapterError("Ollama public response is not valid structured JSON") from exc
        if not isinstance(public, Mapping):
            raise ModelAdapterError("Ollama public response must be a mapping")

        prompt_tokens = int(envelope.get("prompt_eval_count") or 0)
        output_tokens = int(envelope.get("eval_count") or 0)
        return {
            "request_hash": request.request_hash,
            "public_output": public.get("public_output"),
            "proposal": public.get("proposal"),
            "declared_uncertainty": public.get("declared_uncertainty", 1.0),
            "evidence_citations": public.get("evidence_citations") or [],
            "tool_call_intents": [],
            "rationale_public": str(public.get("rationale_public") or ""),
            "token_usage": {
                "input": prompt_tokens,
                "output": output_tokens,
                "total": prompt_tokens + output_tokens,
            },
            "cost": {"currency": "none", "amount": 0.0, "local_inference": True},
            "completed_at": time.time(),
            # Diagnostic values below are intentionally ignored by
            # ModelInvocationResult.from_adapter and never become authority.
            "transport_elapsed_ms": round((time.time() - started) * 1000.0, 3),
        }


__all__ = [
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "DEFAULT_ENDPOINT",
    "OllamaLocalAdapter",
]
