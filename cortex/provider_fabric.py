"""Provider-neutral live model fabric for the Cortex native runtime."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .model_circulation import ModelAdapterError
from .native_agent import AgentModelRequest
from .secret_store import SecretStore

CATALOG_SCHEMA = "cortex-model-catalog/1.0"
PROVIDER_ADAPTER_VERSION = "10.0.0-alpha.2"
DEFAULT_CACHE_SECONDS = 300.0
MAX_HTTP_BODY_BYTES = 8 * 1024 * 1024
PROVIDER_NAMES = ("openai", "xai", "openrouter")


class ProviderError(ModelAdapterError):
    def __init__(self, state: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.state = state
        self.retryable = bool(retryable)


@dataclass(frozen=True)
class CortexModelDescriptor:
    provider: str
    model_id: str
    display_name: str
    canonical_id: str
    context_length: int | None = None
    input_modalities: tuple[str, ...] = ()
    output_modalities: tuple[str, ...] = ()
    supports_chat: bool | None = None
    supports_tools: bool | None = None
    supports_streaming: bool | None = None
    supports_reasoning: bool | None = None
    supports_vision: bool | None = None
    pricing: Mapping[str, str] = field(default_factory=dict)
    free: bool | None = None
    availability: str = "AVAILABLE"
    metadata_source: str = "live_provider_catalog"
    discovered_at: float = 0.0
    created_at: float | None = None
    provider_author: str = ""
    aliases: tuple[str, ...] = ()
    supported_parameters: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelProvider(Protocol):
    provider_id: str
    display_name: str

    def validate_credentials(self, credential: str) -> dict[str, Any]: ...
    def list_models(self, credential: str, *, sort: str = "") -> list[CortexModelDescriptor]: ...
    def get_model(self, credential: str, model_id: str) -> CortexModelDescriptor | None: ...
    def adapter(self, credential: str, model_id: str) -> "HttpProviderAgentAdapter": ...


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _request_json(url: str, credential: str, *, timeout: float = 20.0) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {credential}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_HTTP_BODY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise ProviderError("INVALID_KEY", "Provider authentication failed.") from exc
        if exc.code == 429:
            raise ProviderError("RATE_LIMITED", "Provider rate limit reached.", retryable=True) from exc
        raise ProviderError("PROVIDER_ERROR", f"Provider returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError("NETWORK_ERROR", "Provider network request failed.", retryable=True) from exc
    if len(body) > MAX_HTTP_BODY_BYTES:
        raise ProviderError("PROVIDER_ERROR", "Provider response exceeded the safe limit.")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("PROVIDER_ERROR", "Provider returned malformed model metadata.") from exc
    if not isinstance(value, Mapping):
        raise ProviderError("PROVIDER_ERROR", "Provider model response was not an object.")
    return value


class OpenAIProvider:
    provider_id = "openai"
    display_name = "OpenAI"
    base_url = "https://api.openai.com/v1"

    def list_models(self, credential: str, *, sort: str = "") -> list[CortexModelDescriptor]:
        del sort
        payload = _request_json(f"{self.base_url}/models", credential)
        values = payload.get("data")
        if not isinstance(values, list):
            raise ProviderError("PROVIDER_ERROR", "OpenAI model catalog is malformed.")
        now = time.time()
        result: list[CortexModelDescriptor] = []
        non_chat_tokens = ("embedding", "moderation", "tts", "whisper", "image", "dall-e")
        for raw in values:
            if not isinstance(raw, Mapping) or not str(raw.get("id") or "").strip():
                continue
            model_id = str(raw["id"])
            is_non_chat = any(token in model_id.lower() for token in non_chat_tokens)
            result.append(CortexModelDescriptor(
                provider=self.provider_id,
                model_id=model_id,
                canonical_id=model_id,
                display_name=model_id,
                supports_chat=False if is_non_chat else None,
                supports_streaming=False if is_non_chat else None,
                provider_author=str(raw.get("owned_by") or ""),
                created_at=float(raw["created"]) if isinstance(raw.get("created"), (int, float)) else None,
                discovered_at=now,
            ))
        return sorted(result, key=lambda item: item.display_name.lower())

    def validate_credentials(self, credential: str) -> dict[str, Any]:
        models = self.list_models(credential)
        return {"state": "CONNECTED", "model_count": len(models)}

    def get_model(self, credential: str, model_id: str) -> CortexModelDescriptor | None:
        return next((item for item in self.list_models(credential) if item.model_id == model_id), None)

    def adapter(self, credential: str, model_id: str) -> "HttpProviderAgentAdapter":
        return HttpProviderAgentAdapter(self.provider_id, model_id, credential, self.base_url)


class XAIProvider(OpenAIProvider):
    provider_id = "xai"
    display_name = "xAI / Grok"
    base_url = "https://api.x.ai/v1"

    def list_models(self, credential: str, *, sort: str = "") -> list[CortexModelDescriptor]:
        del sort
        try:
            payload = _request_json(f"{self.base_url}/language-models", credential)
            values = payload.get("models")
        except ProviderError as exc:
            if exc.state in {"INVALID_KEY", "RATE_LIMITED", "NETWORK_ERROR"}:
                raise
            payload = _request_json(f"{self.base_url}/models", credential)
            values = payload.get("data")
        if not isinstance(values, list):
            raise ProviderError("PROVIDER_ERROR", "xAI model catalog is malformed.")
        now = time.time()
        result = []
        for raw in values:
            if not isinstance(raw, Mapping) or not str(raw.get("id") or "").strip():
                continue
            model_id = str(raw["id"])
            inputs = _tuple_strings(raw.get("input_modalities"))
            outputs = _tuple_strings(raw.get("output_modalities"))
            pricing = {
                key: str(raw[key])
                for key in (
                    "prompt_text_token_price", "cached_prompt_text_token_price",
                    "prompt_image_token_price", "completion_text_token_price",
                )
                if raw.get(key) is not None
            }
            result.append(CortexModelDescriptor(
                provider=self.provider_id,
                model_id=model_id,
                canonical_id=model_id,
                display_name=model_id,
                input_modalities=inputs,
                output_modalities=outputs or ("text",),
                supports_chat=True,
                supports_tools=None,
                supports_streaming=True,
                supports_vision=("image" in inputs) if inputs else None,
                pricing=pricing,
                provider_author=str(raw.get("owned_by") or "xai"),
                aliases=_tuple_strings(raw.get("aliases")),
                created_at=float(raw["created"]) if isinstance(raw.get("created"), (int, float)) else None,
                discovered_at=now,
            ))
        return sorted(result, key=lambda item: item.display_name.lower())


class OpenRouterProvider(OpenAIProvider):
    provider_id = "openrouter"
    display_name = "OpenRouter"
    base_url = "https://openrouter.ai/api/v1"
    allowed_sorts = {
        "pricing-low-to-high", "pricing-high-to-low", "context-high-to-low",
        "throughput-high-to-low", "latency-low-to-high", "most-popular",
        "top-weekly", "newest",
    }

    def list_models(self, credential: str, *, sort: str = "") -> list[CortexModelDescriptor]:
        suffix = f"?output_modalities=all&sort={sort}" if sort in self.allowed_sorts else "?output_modalities=all"
        payload = _request_json(f"{self.base_url}/models{suffix}", credential)
        values = payload.get("data")
        if not isinstance(values, list):
            raise ProviderError("PROVIDER_ERROR", "OpenRouter model catalog is malformed.")
        now = time.time()
        result: list[CortexModelDescriptor] = []
        for raw in values:
            if not isinstance(raw, Mapping) or not str(raw.get("id") or "").strip():
                continue
            model_id = str(raw["id"])
            architecture = raw.get("architecture") if isinstance(raw.get("architecture"), Mapping) else {}
            inputs = _tuple_strings(architecture.get("input_modalities"))
            outputs = _tuple_strings(architecture.get("output_modalities"))
            supported = _tuple_strings(raw.get("supported_parameters"))
            pricing_raw = raw.get("pricing") if isinstance(raw.get("pricing"), Mapping) else {}
            pricing = {str(k): str(v) for k, v in pricing_raw.items() if v is not None}
            price_values: list[float] = []
            for key in ("prompt", "completion", "request"):
                try:
                    price_values.append(float(pricing[key]))
                except (KeyError, TypeError, ValueError):
                    pass
            free = model_id == "openrouter/free" or model_id.endswith(":free")
            if not free and "prompt" in pricing and "completion" in pricing:
                try:
                    free = (
                        float(pricing["prompt"]) == 0.0
                        and float(pricing["completion"]) == 0.0
                        and float(pricing.get("request", "0")) == 0.0
                    )
                except (TypeError, ValueError):
                    free = False
            result.append(CortexModelDescriptor(
                provider=self.provider_id,
                model_id=model_id,
                canonical_id=str(raw.get("canonical_slug") or model_id),
                display_name=str(raw.get("name") or model_id),
                context_length=_positive_int(raw.get("context_length")),
                input_modalities=inputs,
                output_modalities=outputs,
                supports_chat=("text" in outputs) if outputs else None,
                supports_tools="tools" in supported,
                supports_streaming=True,
                supports_reasoning=("reasoning" in supported or "include_reasoning" in supported),
                supports_vision=("image" in inputs) if inputs else None,
                pricing=pricing,
                free=free,
                provider_author=model_id.split("/", 1)[0] if "/" in model_id else "openrouter",
                supported_parameters=supported,
                created_at=float(raw["created"]) if isinstance(raw.get("created"), (int, float)) else None,
                discovered_at=now,
            ))
        if not any(item.model_id == "openrouter/free" for item in result):
            result.append(CortexModelDescriptor(
                provider=self.provider_id,
                model_id="openrouter/free",
                canonical_id="openrouter/free",
                display_name="Free Models Router",
                supports_chat=True,
                supports_tools=None,
                supports_streaming=True,
                free=True,
                provider_author="openrouter",
                discovered_at=now,
                metadata_source="openrouter_documented_router",
            ))
        result.sort(key=lambda item: (item.model_id != "openrouter/free", item.display_name.lower()))
        return result


class HttpProviderAgentAdapter:
    """OpenAI-compatible streaming transport behind Cortex's native contract."""

    adapter_id = "cortex.provider-fabric.http"
    adapter_version = PROVIDER_ADAPTER_VERSION
    model_version = "provider-declared"

    def __init__(self, provider_family: str, model_id: str, credential: str, base_url: str) -> None:
        self.provider_family = str(provider_family)
        self.model_id = str(model_id)
        self._credential = str(credential)
        self._base_url = str(base_url).rstrip("/")

    @staticmethod
    def _messages(request: AgentModelRequest) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for message in request.messages:
            body = message.to_dict()
            if message.role == "assistant" and message.tool_calls:
                body["tool_calls"] = [
                    {
                        "id": str(call.get("call_id") or call.get("id") or ""),
                        "type": "function",
                        "function": {
                            "name": str(call.get("name") or ""),
                            "arguments": json.dumps(
                                dict(call.get("arguments") or {}),
                                separators=(",", ":"),
                            ),
                        },
                    }
                    for call in message.tool_calls
                ]
            result.append(body)
        return result

    @staticmethod
    def _tools(request: AgentModelRequest) -> list[dict[str, Any]]:
        result = []
        for tool in request.tools:
            result.append({
                "type": "function",
                "function": {
                    "name": str(tool.get("name") or ""),
                    "description": str(tool.get("description") or ""),
                    "parameters": dict(tool.get("input_schema") or {}),
                },
            })
        return result

    def invoke_agent(self, request: AgentModelRequest) -> Mapping[str, Any]:
        return self.invoke_agent_stream(request, lambda _delta: None, threading.Event())

    def invoke_agent_stream(
        self,
        request: AgentModelRequest,
        emit_delta: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> Mapping[str, Any]:
        if not request.verify():
            raise ModelAdapterError("provider adapter received invalid Cortex request")
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": self._messages(request),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools = self._tools(request)
        if tools:
            payload["tools"] = tools
        if self.provider_family == "openai":
            payload["store"] = False
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._credential}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "User-Agent": "Cortex-Native-Agent/10",
            },
        )
        try:
            response = urllib.request.urlopen(http_request, timeout=180.0)
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise ProviderError("INVALID_KEY", "Provider authentication failed.") from exc
            if exc.code == 429:
                raise ProviderError("RATE_LIMITED", "Model request rate limited.", retryable=True) from exc
            raise ProviderError("PROVIDER_ERROR", f"Provider returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError("NETWORK_ERROR", "Model provider connection failed.", retryable=True) from exc

        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        finish_reason = "stop"
        usage: dict[str, Any] = {}
        try:
            for raw_line in response:
                if cancel_event.is_set():
                    raise ProviderError("INTERRUPTED", "Generation interrupted by operator.")
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                item = line[5:].strip()
                if item == "[DONE]":
                    break
                try:
                    event = json.loads(item)
                except json.JSONDecodeError:
                    continue
                if isinstance(event.get("usage"), Mapping):
                    usage = dict(event["usage"])
                choices = event.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                choice = choices[0] if isinstance(choices[0], Mapping) else {}
                if choice.get("finish_reason"):
                    finish_reason = str(choice["finish_reason"])
                delta = choice.get("delta") if isinstance(choice.get("delta"), Mapping) else {}
                content = delta.get("content")
                if isinstance(content, str) and content:
                    text_parts.append(content)
                    emit_delta(content)
                for raw_call in delta.get("tool_calls") or ():
                    if not isinstance(raw_call, Mapping):
                        continue
                    index = int(raw_call.get("index") or 0)
                    call = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if raw_call.get("id"):
                        call["id"] += str(raw_call["id"])
                    function = raw_call.get("function") if isinstance(raw_call.get("function"), Mapping) else {}
                    call["name"] += str(function.get("name") or "")
                    call["arguments"] += str(function.get("arguments") or "")
        finally:
            response.close()
        tool_calls = [
            {"id": value["id"] or f"call_{index}", "name": value["name"], "arguments": value["arguments"] or "{}"}
            for index, value in sorted(calls.items())
        ]
        if tool_calls:
            finish_reason = "tool_calls"
        if finish_reason not in {"stop", "tool_calls", "length", "content_filter"}:
            finish_reason = "stop"
        return {
            "request_hash": request.request_hash,
            "public_output": {"text": "".join(text_parts)},
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
            "token_usage": usage,
            "rationale_public": "provider public output",
            "declared_uncertainty": 1.0,
        }


class ProviderFabric:
    def __init__(
        self,
        store: Any,
        secrets: SecretStore,
        *,
        providers: Mapping[str, ModelProvider] | None = None,
        cache_seconds: float = DEFAULT_CACHE_SECONDS,
    ) -> None:
        self.store = store
        self.secrets = secrets
        self.providers: dict[str, ModelProvider] = dict(providers or {
            "openai": OpenAIProvider(),
            "xai": XAIProvider(),
            "openrouter": OpenRouterProvider(),
        })
        self.cache_seconds = max(5.0, min(float(cache_seconds), 3600.0))

    def _provider(self, provider: str) -> ModelProvider:
        name = str(provider or "").lower()
        if name not in self.providers:
            raise ProviderError("UNKNOWN", "Unknown model provider.")
        return self.providers[name]

    def _credential(self, provider: str) -> str:
        value = self.secrets.get(provider)
        if not value:
            raise ProviderError("INVALID_KEY", "No provider credential is configured.")
        return value

    def save_credential(self, provider: str, credential: str) -> dict[str, Any]:
        self._provider(provider)
        self.secrets.set(provider, credential)
        self.store.set_setting(f"ui:model_catalog:{provider}:default", {})
        return self.secrets.describe(provider)

    def provider_statuses(self) -> list[dict[str, Any]]:
        result = []
        validations = self.store.get_setting("ui:provider_validation", {}) or {}
        for provider, implementation in self.providers.items():
            description = self.secrets.describe(provider)
            validation = validations.get(provider) if isinstance(validations, Mapping) else {}
            result.append({
                "provider": provider,
                "display_name": implementation.display_name,
                **description,
                "status": str((validation or {}).get("state") or ("CONFIGURED" if description["configured"] else "NOT_CONFIGURED")),
                "last_validated": (validation or {}).get("validated_at"),
                "model_count": int((validation or {}).get("model_count") or 0),
            })
        return result

    def validate(self, provider: str) -> dict[str, Any]:
        implementation = self._provider(provider)
        try:
            result = dict(implementation.validate_credentials(self._credential(provider)))
        except ProviderError as exc:
            result = {"state": exc.state, "message": str(exc), "model_count": 0}
        result["validated_at"] = time.time()
        validations = self.store.get_setting("ui:provider_validation", {}) or {}
        validations = dict(validations) if isinstance(validations, Mapping) else {}
        validations[str(provider)] = result
        self.store.set_setting("ui:provider_validation", validations)
        return result

    def models(self, provider: str, *, refresh: bool = False, sort: str = "") -> dict[str, Any]:
        implementation = self._provider(provider)
        key = f"ui:model_catalog:{provider}:{sort or 'default'}"
        cached = self.store.get_setting(key, {}) or {}
        now = time.time()
        if (
            not refresh
            and isinstance(cached, Mapping)
            and isinstance(cached.get("models"), list)
            and now - float(cached.get("fetched_at") or 0.0) <= self.cache_seconds
        ):
            return {**dict(cached), "cached": True}
        try:
            models = implementation.list_models(self._credential(provider), sort=sort)
        except ProviderError as exc:
            if isinstance(cached, Mapping) and isinstance(cached.get("models"), list):
                return {**dict(cached), "cached": True, "stale": True, "error": {"state": exc.state, "message": str(exc)}}
            raise
        payload = {
            "schema_version": CATALOG_SCHEMA,
            "provider": provider,
            "models": [item.to_dict() for item in models],
            "fetched_at": now,
            "cached": False,
            "stale": False,
            "sort": sort,
        }
        self.store.set_setting(key, payload)
        return payload

    def adapter(self, provider: str, model_id: str) -> HttpProviderAgentAdapter:
        return self._provider(provider).adapter(self._credential(provider), str(model_id))


__all__ = [
    "CATALOG_SCHEMA", "CortexModelDescriptor", "HttpProviderAgentAdapter",
    "ModelProvider", "OpenAIProvider", "OpenRouterProvider", "ProviderError",
    "ProviderFabric", "XAIProvider",
]
