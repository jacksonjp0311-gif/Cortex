"""Loopback Cortex chat service and persistent native conversation bridge."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import threading
import time
import uuid
import webbrowser
from collections import defaultdict
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .coding_workspace import apply_approved_patch, approval_challenge, rollback_applied_patch
from .native_agent import AgentMessage, CapabilityGrant, NativeAgentRuntime
from .provider_fabric import ProviderError, ProviderFabric
from .secret_store import HostSecretStore, SecretStore
from .store import Store

SERVICE_SCHEMA = "cortex-native-interface/1.0"
UI_ROOT = Path(__file__).with_name("ui") / "static"
MAX_REQUEST_BYTES = 256 * 1024


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


class SessionEventBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._conditions: dict[str, threading.Condition] = defaultdict(threading.Condition)
        self._sequences: dict[str, int] = defaultdict(int)

    def publish(self, session_id: str, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        condition = self._conditions[session_id]
        with condition:
            self._sequences[session_id] += 1
            sequence = self._sequences[session_id]
            event = {
                "schema_version": SERVICE_SCHEMA,
                "sequence": sequence,
                "session_id": session_id,
                "event_type": str(event_type),
                "payload": _json_safe(dict(payload)),
                "emitted_at": time.time(),
            }
            self._events[session_id].append(event)
            if len(self._events[session_id]) > 2_000:
                self._events[session_id] = self._events[session_id][-2_000:]
            condition.notify_all()
        return event

    def latest_sequence(self, session_id: str) -> int:
        condition = self._conditions[session_id]
        with condition:
            return int(self._sequences[session_id])

    def since(self, session_id: str, sequence: int) -> list[dict[str, Any]]:
        return [event for event in self._events[session_id] if int(event["sequence"]) > sequence]

    def wait(self, session_id: str, sequence: int, timeout: float = 15.0) -> list[dict[str, Any]]:
        condition = self._conditions[session_id]
        with condition:
            events = self.since(session_id, sequence)
            if events:
                return events
            condition.wait(timeout=max(0.1, min(timeout, 30.0)))
            return self.since(session_id, sequence)


class CortexChatService:
    def __init__(
        self,
        store: Any,
        repo: str,
        *,
        secrets: SecretStore | None = None,
        fabric: ProviderFabric | None = None,
    ) -> None:
        repository = store.repo(repo)
        if not repository:
            raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
        self.store = store
        self.repo = repo
        self.repository_path = str(Path(repository["path"]).resolve())
        self.secrets = secrets or HostSecretStore()
        self.fabric = fabric or ProviderFabric(store, self.secrets)
        self.events = SessionEventBus()
        self.started_at = time.time()
        self._runs: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.RLock()
        self._db_lock = threading.RLock()

    def status(self) -> dict[str, Any]:
        return {
            "schema_version": SERVICE_SCHEMA,
            "product": "CORTEX",
            "subtitle": "NATIVE AGENT RUNTIME",
            "version": "10.0.0-alpha.3",
            "repo": self.repo,
            "repository_path": self.repository_path,
            "connection": "CONNECTED",
            "loopback_only": True,
            "started_at": self.started_at,
            "uptime_seconds": max(0.0, time.time() - self.started_at),
            "providers": self.fabric.provider_statuses(),
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }

    def settings(self) -> dict[str, Any]:
        current = self.store.get_setting(f"ui:settings:{self.repo}", {}) or {}
        allowed = {
            "selected_provider", "selected_model", "reasoning_effort",
            "temperature", "max_output_tokens", "default_tool_mode", "appearance",
        }
        defaults = {"default_tool_mode": "proposal", "appearance": "standard"}
        defaults.update({key: current[key] for key in allowed if key in current})
        return defaults

    def update_settings(self, values: Mapping[str, Any]) -> dict[str, Any]:
        current = self.settings()
        allowed = {
            "selected_provider", "selected_model", "reasoning_effort",
            "temperature", "max_output_tokens", "default_tool_mode", "appearance",
        }
        for key, value in values.items():
            if key in allowed:
                if key == "default_tool_mode" and value not in {"off", "read_only", "proposal"}:
                    raise ValueError("default_tool_mode must be off, read_only, or proposal")
                current[key] = _json_safe(value)
        self.store.set_setting(f"ui:settings:{self.repo}", current)
        return current

    @staticmethod
    def _session_dict(row: Any) -> dict[str, Any]:
        metadata = json.loads(row["metadata"] or "{}")
        return {
            "session_id": row["session_id"],
            "repo": row["repo"],
            "title": row["task"],
            "started_at": float(row["started_at"]),
            "ended_at": float(row["ended_at"]) if row["ended_at"] is not None else None,
            "status": row["status"],
            "provider": str(metadata.get("provider") or ""),
            "model_id": str(metadata.get("model_id") or ""),
        }

    def create_session(self, values: Mapping[str, Any]) -> dict[str, Any]:
        settings = self.settings()
        provider = str(values.get("provider") or settings.get("selected_provider") or "")
        model_id = str(values.get("model_id") or settings.get("selected_model") or "")
        session_id = f"chat_{uuid.uuid4().hex}"
        title = str(values.get("title") or "New Cortex conversation").strip()[:160]
        self.store.start_session(
            session_id,
            self.repo,
            title,
            {"kind": "cortex_chat", "provider": provider, "model_id": model_id},
        )
        self.events.publish(session_id, "chat.session.created", {"provider": provider, "model_id": model_id})
        return self.get_session(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            self._session_dict(row)
            for row in self.store.list_sessions(self.repo, 100)
            if json.loads(row["metadata"] or "{}").get("kind") == "cortex_chat"
        ]

    def get_session(self, session_id: str) -> dict[str, Any]:
        row = self.store.session(session_id)
        if not row or row["repo"] != self.repo:
            raise KeyError("Cortex conversation not found")
        session = self._session_dict(row)
        session["messages"] = self.messages(session_id)
        session["active"] = self.is_active(session_id)
        return session

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        result = []
        for row in self.store.events(self.repo, session_id):
            if row["kind"] not in {"chat.user", "chat.assistant", "chat.error", "chat.model_changed"}:
                continue
            metadata = json.loads(row["metadata"] or "{}")
            result.append({
                "id": int(row["id"]),
                "role": "user" if row["kind"] == "chat.user" else ("assistant" if row["kind"] == "chat.assistant" else "system"),
                "kind": row["kind"],
                "content": row["text"],
                "created_at": float(row["created_at"]),
                "provider": str(metadata.get("provider") or ""),
                "model_id": str(metadata.get("model_id") or ""),
                "trajectory_receipt_hash": str(metadata.get("trajectory_receipt_hash") or ""),
            })
        return result

    def switch_model(self, session_id: str, provider: str, model_id: str) -> dict[str, Any]:
        if self.is_active(session_id):
            raise RuntimeError("Stop the active generation before switching models.")
        row = self.store.session(session_id)
        if not row or row["repo"] != self.repo:
            raise KeyError("Cortex conversation not found")
        metadata = json.loads(row["metadata"] or "{}")
        old = {"provider": metadata.get("provider", ""), "model_id": metadata.get("model_id", "")}
        metadata.update({"provider": str(provider), "model_id": str(model_id), "kind": "cortex_chat"})
        self.store.update_session_metadata(session_id, metadata)
        self.store.add_event(session_id, self.repo, "chat.model_changed", "Reasoning engine changed.", {"from": old, "provider": provider, "model_id": model_id})
        self.events.publish(session_id, "chat.model.changed", {"from": old, "provider": provider, "model_id": model_id})
        return self.get_session(session_id)

    def is_active(self, session_id: str) -> bool:
        with self._lock:
            run = self._runs.get(session_id)
            return bool(run and run[0].is_alive())

    def send_message(self, session_id: str, text: str) -> dict[str, Any]:
        message = str(text or "").strip()
        if not message:
            raise ValueError("Message is required.")
        if self.is_active(session_id):
            raise RuntimeError("A generation is already active for this conversation.")
        session = self.get_session(session_id)
        provider = str(session.get("provider") or "")
        model_id = str(session.get("model_id") or "")
        if not provider or not model_id:
            raise ValueError("Choose a reasoning provider and model first.")
        if str(session.get("title") or "") == "New Cortex conversation":
            self.store.update_session_task(session_id, message[:80])
        self.store.add_event(session_id, self.repo, "chat.user", message, {"provider": provider, "model_id": model_id})
        history = tuple(
            AgentMessage(item["role"], item["content"])
            for item in self.messages(session_id)
            if item["role"] in {"user", "assistant"}
        )
        tool_mode = str(self.settings().get("default_tool_mode") or "off")
        cancellation = threading.Event()
        thread = threading.Thread(
            target=self._run_turn,
            args=(session_id, message, provider, model_id, history, tool_mode, cancellation),
            daemon=True,
            name=f"cortex-chat-{session_id[-8:]}",
        )
        with self._lock:
            self._runs[session_id] = (thread, cancellation)
        self.events.publish(session_id, "chat.message.accepted", {"provider": provider, "model_id": model_id})
        thread.start()
        return {"accepted": True, "session_id": session_id, "provider": provider, "model_id": model_id}

    def _run_turn(
        self,
        session_id: str,
        text: str,
        provider: str,
        model_id: str,
        history: tuple[AgentMessage, ...],
        tool_mode: str,
        cancellation: threading.Event,
    ) -> None:
        worker_store = Store(Path(self.store.path))
        try:
            adapter = self.fabric.adapter(provider, model_id)
            if tool_mode == "proposal":
                allowed_tools = ("filesystem.list", "filesystem.read", "workspace.propose_patch")
            elif tool_mode == "read_only":
                allowed_tools = ("filesystem.list", "filesystem.read")
            else:
                allowed_tools = ()
            grant = CapabilityGrant(
                workspace_root=self.repository_path,
                allowed_tools=allowed_tools,
            )

            def receive(event: Mapping[str, Any]) -> None:
                event_type = str(event.get("event_type") or "agent.event")
                payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
                self.events.publish(session_id, event_type, dict(payload))

            result = NativeAgentRuntime(
                worker_store,
                self.repo,
                event_sink=receive,
            ).run(
                text,
                adapter=adapter,
                grant=grant,
                conversation_messages=history,
                continuity_id=session_id,
                cancel_event=cancellation,
            )
            worker_store.add_event(
                session_id,
                self.repo,
                "chat.assistant",
                str(result["final_answer"]),
                {
                    "provider": provider,
                    "model_id": model_id,
                    "trajectory_receipt_hash": result["trajectory_receipt_hash"],
                    "status": result["status"],
                },
            )
            worker_store.set_setting(f"ui:chat:last_trajectory:{session_id}", result["trajectory_receipt_hash"])
            self.events.publish(session_id, "chat.turn.completed", result)
        except Exception as exc:
            state = exc.state if isinstance(exc, ProviderError) else "ERROR"
            message = str(exc) if isinstance(exc, (ProviderError, ValueError, RuntimeError)) else "Cortex could not complete this turn."
            worker_store.add_event(session_id, self.repo, "chat.error", message, {"state": state})
            self.events.publish(session_id, "chat.turn.failed", {"state": state, "message": message})
        finally:
            with self._lock:
                self._runs.pop(session_id, None)
            worker_store.close()

    def interrupt(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._runs.get(session_id)
            if not run or not run[0].is_alive():
                return {"interrupted": False, "state": "IDLE"}
            run[1].set()
        self.events.publish(session_id, "chat.interrupt.requested", {"reason": "operator"})
        return {"interrupted": True, "state": "CANCELLING"}

    def archive(self, session_id: str) -> dict[str, Any]:
        if self.is_active(session_id):
            self.interrupt(session_id)
        self.store.end_session(session_id, "archived")
        return {"archived": True, "session_id": session_id}

    def context(self, session_id: str) -> dict[str, Any]:
        receipt = self._trajectory(session_id)
        if not receipt:
            return {"state": "INACTIVE", "projected_items": 0, "token_estimate": None, "source_classes": []}
        requests = receipt.get("requests") or []
        request = requests[-1] if requests else {}
        projection = request.get("context_projection") if isinstance(request, Mapping) else {}
        if isinstance(projection, Mapping):
            projected_items = (
                1
                + len(projection.get("evidence_digests") or ())
                + len(projection.get("memory_episode_digests") or ())
                + len(projection.get("unresolved_contradictions") or ())
                + len(projection.get("constitutional_restrictions") or ())
            )
            serialized_projection = json.dumps(
                projection,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
            token_estimate = max(1, (len(serialized_projection) + 3) // 4)
            source_classes = ["cortex_identity", "constitutional"]
            if projection.get("evidence_digests"):
                source_classes.append("evidence")
            if projection.get("memory_episode_digests"):
                source_classes.append("memory")
        else:
            projected_items, token_estimate, source_classes = 0, None, []
        return {
            "state": "ACTIVE",
            "projection_hash": receipt.get("context_projection_hash"),
            "projected_items": projected_items,
            "token_estimate": token_estimate,
            "source_classes": source_classes,
            "projection": projection,
        }

    def evidence(self, session_id: str) -> dict[str, Any]:
        receipt = self._trajectory(session_id)
        if not receipt:
            return {
                "verified": 0, "supported": 0, "unknown": 0, "contradicted": 0,
                "memory": {"considered": 0, "projected": 0, "state": "No governed memory projected."},
                "competence": {"considered": 0, "projected": 0, "state": "No verified competence projected."},
                "trajectory": "UNSEALED",
            }
        verification = self.store.verify_symbiotic_session(self.repo, str(receipt.get("session_id") or ""))
        return {
            "verified": 1 if verification.get("valid") else 0,
            "supported": 0,
            "unknown": 0 if verification.get("valid") else 1,
            "contradicted": 0,
            "memory": {"considered": 0, "projected": 0, "state": "No governed memory projected."},
            "competence": {"considered": 0, "projected": 0, "state": "No verified competence projected."},
            "trajectory": "SEALED" if verification.get("valid") else "INVALID",
            "receipt_hash": receipt.get("receipt_hash"),
        }

    def _trajectory(self, session_id: str) -> dict[str, Any] | None:
        receipt_hash = str(self.store.get_setting(f"ui:chat:last_trajectory:{session_id}", "") or "")
        return self.store.symbiotic_receipt(receipt_hash, repo=self.repo) if receipt_hash else None

    def trajectory(self, session_id: str) -> dict[str, Any]:
        receipt = self._trajectory(session_id)
        if not receipt:
            return {"state": "UNSEALED", "session_id": session_id}
        return {
            "state": "SEALED",
            "receipt_hash": receipt.get("receipt_hash"),
            "native_session_id": receipt.get("session_id"),
            "continuity_id": receipt.get("continuity_id"),
            "provider_identity": receipt.get("provider_identity"),
            "event_count": len(receipt.get("events") or ()),
            "tool_call_count": len(receipt.get("tool_results") or ()),
            "status": receipt.get("status"),
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }

    def workspace(self, session_id: str) -> dict[str, Any]:
        receipt = self._trajectory(session_id)
        if not receipt:
            return {"state": "NO_PROPOSAL", "proposals": []}
        verification = self.store.verify_symbiotic_session(self.repo, str(receipt.get("session_id") or ""))
        if not verification.get("valid"):
            return {"state": "INVALID_TRAJECTORY", "proposals": []}
        applications = {
            str(item.get("proposal_hash") or ""): {
                **item,
                "targets_current": self._application_targets_current(item),
            }
            for item in self.store.symbiotic_session_receipts(self.repo, str(receipt.get("session_id") or ""))
            if item.get("kind") == "coding_patch_application"
        }
        proposals = []
        for index, result in enumerate(receipt.get("tool_results") or ()):
            if not isinstance(result, Mapping) or result.get("tool_name") != "workspace.propose_patch":
                continue
            output = result.get("output") if isinstance(result.get("output"), Mapping) else {}
            proposal_hash = str(output.get("proposal_hash") or "")
            if not proposal_hash:
                continue
            proposals.append({
                **dict(output),
                "source_trajectory_hash": receipt.get("receipt_hash"),
                "source_session_id": receipt.get("session_id"),
                "proposal_index": index,
                "approval_challenge": approval_challenge(session_id, proposal_hash),
                "application": applications.get(proposal_hash),
            })
        return {"state": "REVIEW_REQUIRED" if proposals else "NO_PROPOSAL", "proposals": proposals}

    def _application_targets_current(self, application: Mapping[str, Any]) -> bool:
        root = Path(self.repository_path).resolve()
        for relative, expected in dict(application.get("postimage_hashes") or {}).items():
            path = (root / str(relative)).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                return False
            current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
            if current != expected:
                return False
        return True

    def apply_workspace_patch(self, session_id: str, values: Mapping[str, Any]) -> dict[str, Any]:
        if self.is_active(session_id):
            raise RuntimeError("Stop the active generation before applying a proposal.")
        proposal_hash = str(values.get("proposal_hash") or "")
        challenge = str(values.get("approval_challenge") or "")
        surface = self.workspace(session_id)
        proposal = next(
            (item for item in surface["proposals"] if item.get("proposal_hash") == proposal_hash),
            None,
        )
        if not proposal:
            raise ValueError("Canonical patch proposal was not found.")
        if challenge != approval_challenge(session_id, proposal_hash):
            raise ValueError("Operator approval challenge does not match this proposal.")

        native_session_id = str(proposal["source_session_id"])
        turn_id = 100 + int(proposal["proposal_index"])
        existing = next(
            (
                item for item in self.store.symbiotic_session_receipts(self.repo, native_session_id)
                if item.get("kind") == "coding_patch_application" and int(item.get("turn_id") or 0) == turn_id
            ),
            None,
        )
        if existing:
            if existing.get("proposal_hash") != proposal_hash:
                raise RuntimeError("Application receipt slot already contains different content.")
            return {**existing, "duplicate": True}

        application = apply_approved_patch(self.repository_path, proposal)
        trajectory = self._trajectory(session_id) or {}
        try:
            receipt = self.store.append_symbiotic_receipt(
                self.repo,
                {
                    **application,
                    "kind": "coding_patch_application",
                    "session_id": native_session_id,
                    "turn_id": turn_id,
                    "event_id": f"coding_apply_{proposal_hash[:24]}",
                    "body_epoch_id": str(trajectory.get("body_epoch_id") or ""),
                    "source_trajectory_hash": proposal["source_trajectory_hash"],
                    "advisory_only": True,
                    "update_authorized": False,
                },
            )
        except Exception:
            rollback_applied_patch(self.repository_path, proposal)
            raise
        self.events.publish(
            session_id,
            "workspace.patch.applied",
            {
                "proposal_hash": proposal_hash,
                "receipt_hash": receipt["receipt_hash"],
                "targets": proposal["targets"],
                "status": receipt["status"],
            },
        )
        return receipt

    def telemetry(self, session_id: str) -> dict[str, Any]:
        """Return truthful call telemetry without turning estimates into measurements."""
        session = self.get_session(session_id)
        events = self.events.since(session_id, 0)
        receipt = self._trajectory(session_id)
        persisted_events = list(receipt.get("events") or ()) if receipt else []
        source_events = events or persisted_events

        context_event: Mapping[str, Any] = {}
        response_event: Mapping[str, Any] = {}
        latest_delta: Mapping[str, Any] = {}
        seal_event: Mapping[str, Any] = {}
        delta_count = 0
        tool_calls = 0
        for event in source_events:
            event_type = str(event.get("event_type") or "")
            payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
            if event_type == "chat.message.accepted":
                context_event = {}
                response_event = {}
                seal_event = {}
                latest_delta = {}
                delta_count = 0
                tool_calls = 0
            elif event_type == "context.prepared":
                context_event = payload
            elif event_type == "model.delta":
                delta_count += 1
                latest_delta = payload
            elif event_type == "model.responded":
                response_event = payload
            elif event_type == "trajectory.sealed":
                seal_event = payload
            elif event_type == "tool.completed":
                tool_calls += 1

        usage = response_event.get("token_usage") if isinstance(response_event.get("token_usage"), Mapping) else {}
        cost = response_event.get("cost") if isinstance(response_event.get("cost"), Mapping) else {}
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", usage.get("input")))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", usage.get("output")))
        total_tokens = usage.get("total_tokens", usage.get("total"))
        if total_tokens is None and isinstance(input_tokens, (int, float)) and isinstance(output_tokens, (int, float)):
            total_tokens = input_tokens + output_tokens

        def metric(value: Any, measurement: str = "measured", unit: str = "") -> dict[str, Any]:
            return {
                "value": value,
                "measurement": measurement if value is not None else "unavailable",
                "unit": unit,
            }

        return {
            "schema_version": SERVICE_SCHEMA,
            "session_id": session_id,
            "state": "STREAMING" if self.is_active(session_id) else ("COMPLETE" if receipt else "IDLE"),
            "provider": session.get("provider") or "",
            "model_id": session.get("model_id") or "",
            "metrics": {
                "input_tokens": metric(input_tokens, "provider_reported", "tokens"),
                "output_tokens": metric(output_tokens, "provider_reported", "tokens"),
                "total_tokens": metric(total_tokens, "provider_reported", "tokens"),
                "tokens_per_second": metric(response_event.get("tokens_per_second"), str(response_event.get("token_rate_measurement") or "measured"), "tokens/s"),
                "first_token_latency": metric(response_event.get("first_token_latency_ms", latest_delta.get("first_token_latency_ms")), "measured", "ms"),
                "model_latency": metric(
                    response_event.get("model_latency_ms", latest_delta.get("elapsed_ms")),
                    "measured" if response_event else "measured_elapsed",
                    "ms",
                ),
                "total_latency": metric(seal_event.get("total_latency_ms"), "measured", "ms"),
                "context_projection_latency": metric(context_event.get("duration_ms"), "measured", "ms"),
                "context_tokens": metric(context_event.get("estimated_tokens"), "estimated", "tokens"),
                "projected_items": metric(context_event.get("projected_item_count"), "measured", "items"),
                "stream_chunks": metric(delta_count, "measured", "chunks"),
                "tool_calls": metric(tool_calls, "measured", "calls"),
                "cost": metric(cost.get("total", cost.get("total_cost")), "provider_reported", "provider currency"),
                "confidence": metric(None),
                "reasoning_depth": metric(None),
                "cpu": metric(None),
                "gpu": metric(None),
                "network": metric(None),
            },
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }

    def live_state(self, session_id: str) -> dict[str, Any]:
        """Return the canonical reconciliation surface for the local UI."""
        session = self.get_session(session_id)
        return {
            "schema_version": SERVICE_SCHEMA,
            "session_id": session_id,
            "active": self.is_active(session_id),
            "last_sequence": self.events.latest_sequence(session_id),
            "telemetry": self.telemetry(session_id),
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }


class CortexUIHandler(BaseHTTPRequestHandler):
    server_version = "CortexNativeInterface/1.0"

    @property
    def cortex(self) -> CortexChatService:
        return self.server.cortex_service  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Deliberately omit request bodies and headers. The default path-only
        # access log is unnecessary for a private loopback console.
        return

    def _json(self, status: int, value: Any) -> None:
        body = json.dumps(_json_safe(value), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as exc:
            raise ValueError("Invalid request length.") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request exceeds the safe limit.")
        if not length:
            return {}
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Request body must be an object.")
        return value

    def _error(self, exc: Exception) -> None:
        if isinstance(exc, KeyError):
            status = HTTPStatus.NOT_FOUND
        elif isinstance(exc, ProviderError):
            status = HTTPStatus.BAD_GATEWAY
        elif isinstance(exc, (ValueError, RuntimeError)):
            status = HTTPStatus.BAD_REQUEST
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        message = str(exc) if isinstance(exc, (KeyError, ValueError, RuntimeError, ProviderError)) else "Cortex service error."
        self._json(status, {"error": message, "state": getattr(exc, "state", "ERROR")})

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/v1/events":
                return self._sse(str((query.get("session_id") or [""])[0]), int((query.get("after") or ["0"])[0]))
            if not path.startswith("/v1/"):
                return self._static(path)
            with self.cortex._db_lock:
                if path == "/v1/status":
                    return self._json(200, self.cortex.status())
                if path == "/v1/providers":
                    return self._json(200, {"providers": self.cortex.fabric.provider_statuses()})
                if path == "/v1/settings":
                    return self._json(200, self.cortex.settings())
                if path == "/v1/sessions":
                    return self._json(200, {"sessions": self.cortex.list_sessions()})
                parts = [part for part in path.split("/") if part]
                if len(parts) == 4 and parts[:2] == ["v1", "providers"] and parts[3] == "models":
                    provider = parts[2]
                    refresh = str((query.get("refresh") or [""])[0]).lower() in {"1", "true", "yes"}
                    sort = str((query.get("sort") or [""])[0])
                    return self._json(200, self.cortex.fabric.models(provider, refresh=refresh, sort=sort))
                if len(parts) >= 3 and parts[:2] == ["v1", "sessions"]:
                    session_id = parts[2]
                    if len(parts) == 3:
                        return self._json(200, self.cortex.get_session(session_id))
                    if len(parts) == 4 and parts[3] == "context":
                        return self._json(200, self.cortex.context(session_id))
                    if len(parts) == 4 and parts[3] == "evidence":
                        return self._json(200, self.cortex.evidence(session_id))
                    if len(parts) == 4 and parts[3] == "trajectory":
                        return self._json(200, self.cortex.trajectory(session_id))
                    if len(parts) == 4 and parts[3] == "workspace":
                        return self._json(200, self.cortex.workspace(session_id))
                    if len(parts) == 4 and parts[3] == "telemetry":
                        return self._json(200, self.cortex.telemetry(session_id))
                    if len(parts) == 4 and parts[3] == "live":
                        return self._json(200, self.cortex.live_state(session_id))
                return self._json(404, {"error": "Endpoint not found."})
        except Exception as exc:
            self._error(exc)

    def do_POST(self) -> None:
        try:
            with self.cortex._db_lock:
                path = urlparse(self.path).path
                body = self._body()
                if path == "/v1/sessions":
                    return self._json(201, self.cortex.create_session(body))
                parts = [part for part in path.split("/") if part]
                if len(parts) == 4 and parts[:2] == ["v1", "providers"]:
                    provider, action = parts[2], parts[3]
                    if action == "credential":
                        return self._json(200, self.cortex.fabric.save_credential(provider, str(body.get("api_key") or "")))
                    if action == "validate":
                        return self._json(200, self.cortex.fabric.validate(provider))
                    if action == "models":
                        return self._json(200, self.cortex.fabric.models(provider, refresh=True, sort=str(body.get("sort") or "")))
                if len(parts) == 4 and parts[:2] == ["v1", "sessions"]:
                    session_id, action = parts[2], parts[3]
                    if action == "messages":
                        return self._json(202, self.cortex.send_message(session_id, str(body.get("text") or "")))
                    if action == "interrupt":
                        return self._json(200, self.cortex.interrupt(session_id))
                    if action == "archive":
                        return self._json(200, self.cortex.archive(session_id))
                    if action == "model":
                        return self._json(200, self.cortex.switch_model(session_id, str(body.get("provider") or ""), str(body.get("model_id") or "")))
                if len(parts) == 5 and parts[:2] == ["v1", "sessions"] and parts[3:] == ["workspace", "apply"]:
                    return self._json(200, self.cortex.apply_workspace_patch(parts[2], body))
                self._json(404, {"error": "Endpoint not found."})
        except Exception as exc:
            self._error(exc)

    def do_PATCH(self) -> None:
        try:
            with self.cortex._db_lock:
                if urlparse(self.path).path == "/v1/settings":
                    return self._json(200, self.cortex.update_settings(self._body()))
                self._json(404, {"error": "Endpoint not found."})
        except Exception as exc:
            self._error(exc)

    def _sse(self, session_id: str, after: int) -> None:
        if not session_id:
            raise ValueError("session_id is required")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            self.wfile.write(b"retry: 1000\n\n")
            self.wfile.flush()
            try:
                header_sequence = int(self.headers.get("Last-Event-ID") or 0)
            except ValueError:
                header_sequence = 0
            sequence = max(0, int(after), header_sequence)
            deadline = time.time() + 55.0
            while time.time() < deadline:
                events = self.cortex.events.wait(session_id, sequence, timeout=5.0)
                if not events:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                for event in events:
                    sequence = int(event["sequence"])
                    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                    self.wfile.write(f"id: {sequence}\nevent: cortex\ndata: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (UI_ROOT / relative).resolve()
        try:
            candidate.relative_to(UI_ROOT.resolve())
        except ValueError:
            return self._json(404, {"error": "Asset not found."})
        if not candidate.is_file():
            candidate = UI_ROOT / "index.html"
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class CortexHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], service: CortexChatService) -> None:
        self.cortex_service = service
        super().__init__(address, CortexUIHandler)


def serve_cortex_ui(
    store: Any,
    repo: str,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    secrets: SecretStore | None = None,
    fabric: ProviderFabric | None = None,
) -> CortexHTTPServer:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Cortex UI binds to loopback only in alpha.2")
    service = CortexChatService(store, repo, secrets=secrets, fabric=fabric)
    server = CortexHTTPServer((host, int(port)), service)
    url = f"http://{host}:{server.server_address[1]}/"
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    return server


__all__ = [
    "CortexChatService", "CortexHTTPServer", "CortexUIHandler", "SessionEventBus",
    "serve_cortex_ui",
]
