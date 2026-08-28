"""Cortex v10 alpha.2 provider, chat, secret, UI, and local E2E gates."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService, SessionEventBus, UI_ROOT, serve_cortex_ui
from cortex.config import ensure_home
from cortex.native_agent import ScriptedAgentAdapter
from cortex.provider_fabric import (
    CortexModelDescriptor,
    OpenAIProvider,
    OpenRouterProvider,
    ProviderError,
    ProviderFabric,
    XAIProvider,
)
from cortex.secret_store import MemorySecretStore
from cortex.store import Store


class StreamingFixtureAdapter(ScriptedAgentAdapter):
    provider_family = "fixture-ui"
    adapter_id = "test.alpha2.streaming"

    def __init__(self, text: str = "Hello from Cortex.", *, wait: bool = False) -> None:
        super().__init__([{"public_output": text, "finish_reason": "stop"}], model_id="fixture-chat")
        self.text = text
        self.wait = wait

    def invoke_agent_stream(self, request, emit_delta, cancel_event):
        parts = self.text.split(" ")
        for index, part in enumerate(parts):
            if cancel_event.is_set():
                raise RuntimeError("cancelled")
            emit_delta(part + (" " if index < len(parts) - 1 else ""))
            if self.wait:
                time.sleep(0.02)
        return {
            "request_hash": request.request_hash,
            "public_output": {"text": self.text},
            "finish_reason": "stop",
        }


class FixtureProvider:
    provider_id = "openai"
    display_name = "Fixture OpenAI"

    def __init__(self, *, wait: bool = False) -> None:
        self.calls = 0
        self.wait = wait

    def validate_credentials(self, credential):
        self.calls += 1
        return {"state": "CONNECTED", "model_count": 1}

    def list_models(self, credential, *, sort=""):
        self.calls += 1
        return [CortexModelDescriptor(
            provider="openai",
            model_id="fixture-chat",
            display_name="Fixture Chat",
            canonical_id="fixture-chat",
            supports_chat=True,
            supports_tools=True,
            supports_streaming=True,
            discovered_at=time.time(),
        )]

    def get_model(self, credential, model_id):
        return self.list_models(credential)[0] if model_id == "fixture-chat" else None

    def adapter(self, credential, model_id):
        return StreamingFixtureAdapter(wait=self.wait)


class ToolFixtureProvider(FixtureProvider):
    def adapter(self, credential, model_id):
        return ScriptedAgentAdapter([
            {
                "tool_calls": [{
                    "id": "read-alpha2",
                    "name": "filesystem.read",
                    "arguments": {"path": "README.md"},
                }],
                "finish_reason": "tool_calls",
            },
            {"public_output": "Observed ALPHA2.", "finish_reason": "stop"},
        ], model_id=model_id)


class FailureFixtureProvider(FixtureProvider):
    def adapter(self, credential, model_id):
        class FailingAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request):
                raise RuntimeError("bounded fixture provider failure")

        return FailingAdapter([], model_id=model_id)


class Alpha2InterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("ALPHA2\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha2Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.secrets = MemorySecretStore()
        self.secrets.set("openai", "sk-fixture-super-secret")
        self.fixture_provider = FixtureProvider()
        self.fabric = ProviderFabric(
            self.store,
            self.secrets,
            providers={"openai": self.fixture_provider},
            cache_seconds=60,
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_openai_catalog_is_conservative(self) -> None:
        payload = {"data": [
            {"id": "future-chat", "owned_by": "openai", "created": 1},
            {"id": "text-embedding-next", "owned_by": "openai"},
        ]}
        with patch("cortex.provider_fabric._request_json", return_value=payload):
            models = OpenAIProvider().list_models("secret")
        self.assertIsNone(models[0].supports_chat)
        embedding = next(item for item in models if "embedding" in item.model_id)
        self.assertFalse(embedding.supports_chat)
        self.assertNotIn("secret", json.dumps([item.to_dict() for item in models]))

    def test_xai_catalog_uses_live_language_metadata(self) -> None:
        payload = {"models": [{
            "id": "grok-future", "aliases": ["latest"],
            "input_modalities": ["text", "image"], "output_modalities": ["text"],
            "prompt_text_token_price": 1, "completion_text_token_price": 2,
        }]}
        with patch("cortex.provider_fabric._request_json", return_value=payload):
            model = XAIProvider().list_models("secret")[0]
        self.assertEqual(model.model_id, "grok-future")
        self.assertTrue(model.supports_chat)
        self.assertTrue(model.supports_vision)
        self.assertEqual(model.aliases, ("latest",))

    def test_openrouter_free_models_and_router_are_dynamic(self) -> None:
        payload = {"data": [
            {"id": "vendor/specific:free", "name": "Specific", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}, "supported_parameters": ["tools"], "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "vendor/zero", "name": "Zero", "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0", "completion": "0", "request": "0"}},
            {"id": "vendor/paid", "name": "Paid", "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0.1", "completion": "0.2"}},
        ]}
        with patch("cortex.provider_fabric._request_json", return_value=payload):
            models = OpenRouterProvider().list_models("secret")
        self.assertEqual(models[0].model_id, "openrouter/free")
        free_ids = {item.model_id for item in models if item.free}
        self.assertEqual(free_ids, {"openrouter/free", "vendor/specific:free", "vendor/zero"})
        self.assertTrue(next(item for item in models if item.model_id.endswith(":free")).supports_tools)

    def test_malformed_catalog_fails_closed(self) -> None:
        with patch("cortex.provider_fabric._request_json", return_value={"data": "bad"}):
            with self.assertRaises(ProviderError):
                OpenRouterProvider().list_models("secret")

    def test_model_cache_refresh_is_bounded(self) -> None:
        first = self.fabric.models("openai")
        second = self.fabric.models("openai")
        third = self.fabric.models("openai", refresh=True)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertFalse(third["cached"])
        self.assertEqual(self.fixture_provider.calls, 2)

    def test_settings_and_persistence_never_return_or_store_keys(self) -> None:
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=self.fabric)
        serialized_status = json.dumps(service.status())
        serialized_settings = json.dumps(service.settings())
        database_text = " ".join(str(row[0]) for row in self.store.db.execute("SELECT value FROM settings"))
        self.assertNotIn("sk-fixture-super-secret", serialized_status)
        self.assertNotIn("sk-fixture-super-secret", serialized_settings)
        self.assertNotIn("sk-fixture-super-secret", database_text)
        self.assertIn("••••", service.status()["providers"][0]["masked"])

    def test_message_streams_through_native_runtime_and_seals_trajectory(self) -> None:
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=self.fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        service.send_message(session["session_id"], "hello")
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        loaded = service.get_session(session["session_id"])
        self.assertEqual([item["role"] for item in loaded["messages"]], ["user", "assistant"])
        self.assertEqual(loaded["messages"][-1]["content"], "Hello from Cortex.")
        trajectory = service.trajectory(session["session_id"])
        self.assertEqual(trajectory["state"], "SEALED")
        self.assertEqual(trajectory["continuity_id"], session["session_id"])
        self.assertFalse(trajectory["authority"]["execution_authorized"])
        event_types = [item["event_type"] for item in service.events.since(session["session_id"], 0)]
        self.assertIn("model.delta", event_types)
        receipt = self.store.symbiotic_receipt(trajectory["receipt_hash"], repo=self.repo)
        self.assertNotIn("sk-fixture-super-secret", json.dumps(receipt))

    def test_interrupt_propagates_and_ui_session_survives(self) -> None:
        slow = FixtureProvider(wait=True)
        fabric = ProviderFabric(self.store, self.secrets, providers={"openai": slow})
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        service.send_message(session["session_id"], "hello")
        time.sleep(0.01)
        self.assertTrue(service.interrupt(session["session_id"])["interrupted"])
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        self.assertFalse(service.is_active(session["session_id"]))
        self.assertIn(service.trajectory(session["session_id"])["status"], {"interrupted", "completed"})

    def test_model_switch_preserves_cortex_session_identity(self) -> None:
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=self.fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        switched = service.switch_model(session["session_id"], "openai", "fixture-next")
        self.assertEqual(switched["session_id"], session["session_id"])
        self.assertEqual(switched["model_id"], "fixture-next")
        events = service.messages(session["session_id"])
        self.assertEqual(events[0]["kind"], "chat.model_changed")

    def test_tool_call_round_trips_through_native_runtime(self) -> None:
        fabric = ProviderFabric(
            self.store,
            self.secrets,
            providers={"openai": ToolFixtureProvider()},
        )
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=fabric)
        service.update_settings({"default_tool_mode": "read_only"})
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        service.send_message(session["session_id"], "inspect")
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        trajectory = service.trajectory(session["session_id"])
        self.assertEqual(trajectory["tool_call_count"], 1)
        types = [event["event_type"] for event in service.events.since(session["session_id"], 0)]
        self.assertIn("tool.requested", types)
        self.assertIn("tool.completed", types)

    def test_provider_failure_keeps_conversation_alive(self) -> None:
        fabric = ProviderFabric(
            self.store,
            self.secrets,
            providers={"openai": FailureFixtureProvider()},
        )
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        service.send_message(session["session_id"], "fail safely")
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        loaded = service.get_session(session["session_id"])
        self.assertFalse(loaded["active"])
        self.assertEqual(loaded["messages"][-1]["kind"], "chat.error")
        self.assertIn("bounded fixture provider failure", loaded["messages"][-1]["content"])

    def test_packaged_ui_has_required_truthful_surfaces_and_responsive_tokens(self) -> None:
        html = (UI_ROOT / "index.html").read_text(encoding="utf-8")
        css = (UI_ROOT / "cortex.css").read_text(encoding="utf-8")
        js = (UI_ROOT / "cortex.js").read_text(encoding="utf-8")
        for marker in ("CORTEX CHANNEL", "LIVE TELEMETRY", "TOKEN RATE", "MODEL LATENCY", "EVIDENCE", "MEMORY", "COMPETENCE", "TRAJECTORY"):
            self.assertIn(marker, html)
        self.assertIn("@media", css)
        self.assertIn("--cortex-cyan", css)
        self.assertIn("--cortex-violet", css)
        self.assertNotIn("--cortex-orange", css)
        self.assertIn("/v1/sessions/", js)
        self.assertIn("data-core-state", html)
        self.assertIn("corePlasmaCanvas", html)
        self.assertIn("core-plasma-canvas", css)
        self.assertIn("drawCorePlasma", js)
        self.assertIn("coreEnergy", js)
        self.assertIn("eventSequence", js)
        self.assertIn("reconcileLiveState", js)
        self.assertIn("/live", js)
        self.assertIn("LAST TURN · AWAITING LIVE", js)
        self.assertIn("updateLiveDelta", js)
        self.assertNotIn("api.openai.com", js)
        self.assertNotIn("openrouter.ai/api", js)

    def test_live_telemetry_is_derived_from_runtime_events(self) -> None:
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=self.fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        service.send_message(session["session_id"], "measure this turn")
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        telemetry = service.telemetry(session["session_id"])
        self.assertEqual(telemetry["state"], "COMPLETE")
        self.assertEqual(telemetry["metrics"]["model_latency"]["measurement"], "measured")
        self.assertGreaterEqual(telemetry["metrics"]["model_latency"]["value"], 0)
        self.assertEqual(telemetry["metrics"]["context_tokens"]["measurement"], "unavailable")
        self.assertEqual(telemetry["metrics"]["confidence"]["measurement"], "unavailable")
        self.assertFalse(telemetry["authority"]["execution_authorized"])

    def test_event_sequences_remain_monotonic_when_history_is_bounded(self) -> None:
        bus = SessionEventBus()
        for index in range(2_005):
            bus.publish("session", "model.delta", {"index": index})
        retained = bus.since("session", 0)
        self.assertEqual(len(retained), 2_000)
        self.assertEqual(retained[0]["sequence"], 6)
        self.assertEqual(retained[-1]["sequence"], 2_005)
        self.assertEqual(bus.publish("session", "model.responded", {})["sequence"], 2_006)
        self.assertEqual(bus.latest_sequence("session"), 2_006)

    def test_live_reconciliation_surface_tracks_active_then_complete(self) -> None:
        slow = FixtureProvider(wait=True)
        fabric = ProviderFabric(self.store, self.secrets, providers={"openai": slow})
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        initial = service.live_state(session["session_id"])
        self.assertFalse(initial["active"])
        self.assertGreaterEqual(initial["last_sequence"], 1)
        service.send_message(session["session_id"], "measure live state")
        active = service.live_state(session["session_id"])
        self.assertTrue(active["active"])
        deadline = time.time() + 10
        while service.is_active(session["session_id"]) and time.time() < deadline:
            time.sleep(0.02)
        completed = service.live_state(session["session_id"])
        self.assertFalse(completed["active"])
        self.assertEqual(completed["telemetry"]["state"], "COMPLETE")
        self.assertGreater(completed["last_sequence"], initial["last_sequence"])
        self.assertFalse(completed["authority"]["host_mutate_authorized"])

    def test_telemetry_counts_only_the_latest_turn_chunks(self) -> None:
        service = CortexChatService(self.store, self.repo, secrets=self.secrets, fabric=self.fabric)
        session = service.create_session({"provider": "openai", "model_id": "fixture-chat"})
        for prompt in ("first", "second"):
            service.send_message(session["session_id"], prompt)
            deadline = time.time() + 10
            while service.is_active(session["session_id"]) and time.time() < deadline:
                time.sleep(0.02)
        telemetry = service.telemetry(session["session_id"])
        self.assertEqual(telemetry["metrics"]["stream_chunks"]["value"], 3)

    def test_real_loopback_http_e2e_uses_cortex_service(self) -> None:
        server = serve_cortex_ui(
            self.store,
            self.repo,
            open_browser=False,
            secrets=self.secrets,
            fabric=self.fabric,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def request(path, method="GET", body=None):
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode(), response.headers.get("Content-Type", "")

        try:
            html, content_type = request("/")
            self.assertIn("CORTEX", html)
            self.assertIn("text/html", content_type)
            session_json, _ = request("/v1/sessions", "POST", {"provider": "openai", "model_id": "fixture-chat"})
            session_id = json.loads(session_json)["session_id"]
            first_cursor = server.cortex_service.events.latest_sequence(session_id)
            published = server.cortex_service.events.publish(session_id, "test.transport.one", {"ok": True})

            def read_sse(after, last_event_id=None):
                headers = {"Accept": "text/event-stream"}
                if last_event_id is not None:
                    headers["Last-Event-ID"] = str(last_event_id)
                req = urllib.request.Request(
                    f"{base}/v1/events?session_id={session_id}&after={after}",
                    headers=headers,
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    for _ in range(12):
                        line = response.readline().decode("utf-8").strip()
                        if line.startswith("data: "):
                            return json.loads(line[6:])
                self.fail("SSE stream did not yield a Cortex event")

            replayed = read_sse(first_cursor)
            self.assertEqual(replayed["sequence"], published["sequence"])
            second = server.cortex_service.events.publish(session_id, "test.transport.two", {"ok": True})
            resumed = read_sse(0, last_event_id=published["sequence"])
            self.assertEqual(resumed["sequence"], second["sequence"])
            request(f"/v1/sessions/{session_id}/messages", "POST", {"text": "hello"})
            deadline = time.time() + 10
            trajectory = {}
            while time.time() < deadline:
                value, _ = request(f"/v1/sessions/{session_id}/trajectory")
                trajectory = json.loads(value)
                if trajectory.get("state") == "SEALED":
                    break
                time.sleep(0.03)
            self.assertEqual(trajectory.get("state"), "SEALED")
            self.assertEqual(trajectory.get("continuity_id"), session_id)
            live_json, _ = request(f"/v1/sessions/{session_id}/live")
            live = json.loads(live_json)
            self.assertFalse(live["active"])
            self.assertEqual(live["telemetry"]["state"], "COMPLETE")
            self.assertGreater(live["last_sequence"], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
