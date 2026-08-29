#!/usr/bin/env python3
"""Focused Cortex UI telemetry contract compiler.

This is the fast sidecar gate for the local operator console. It exercises one
deterministic streamed turn through the real loopback service, compiles the
backend metric schema against visible DOM targets, and fails if an available
metric is disconnected from the interface. It does not run the repository test
suite or contact a live model provider.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import threading
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import serve_cortex_ui
from cortex.config import ensure_home
from cortex.native_agent import ScriptedAgentAdapter
from cortex.provider_fabric import CortexModelDescriptor, ProviderFabric
from cortex.secret_store import MemorySecretStore
from cortex.store import Store


VISIBLE_METRICS = {
    "input_tokens": "inputTokenMetric",
    "output_tokens": "outputTokenMetric",
    "total_tokens": "totalTokenMetric",
    "tokens_per_second": "tokenRate",
    "first_token_latency": "firstTokenMetric",
    "model_latency": "latencyMetric",
    "total_latency": "totalLatencyMetric",
    "context_projection_latency": "contextProjectionMetric",
    "context_tokens": "contextLoad",
    "stream_chunks": "streamChunkMetric",
    "tool_calls": "toolMetric",
    "cost": "costMetric",
}


class _IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        for key, value in attrs:
            if key == "id" and value:
                self.ids.add(value)


class _TelemetryAdapter(ScriptedAgentAdapter):
    provider_family = "fixture-telemetry"
    adapter_id = "cortex.ui.telemetry-smoke"

    def __init__(self) -> None:
        super().__init__([], model_id="telemetry-fixture")

    def invoke_agent_stream(self, request, emit_delta, cancel_event):
        for part in ("TELEMETRY", "_", "OK"):
            if cancel_event.is_set():
                raise RuntimeError("cancelled")
            emit_delta(part)
            time.sleep(0.005)
        return {
            "request_hash": request.request_hash,
            "public_output": {"text": "TELEMETRY_OK"},
            "finish_reason": "stop",
            "token_usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
            "cost": {"total": 0.0025},
        }


class _TelemetryProvider:
    provider_id = "openai"
    display_name = "Telemetry Fixture"

    @staticmethod
    def validate_credentials(credential):
        return {"state": "CONNECTED", "model_count": 1}

    @staticmethod
    def list_models(credential, *, sort=""):
        del credential, sort
        return [CortexModelDescriptor(
            provider="openai",
            model_id="telemetry-fixture",
            display_name="Telemetry Fixture",
            canonical_id="telemetry-fixture",
            context_length=32_768,
            supports_chat=True,
            supports_streaming=True,
            discovered_at=time.time(),
        )]

    @staticmethod
    def get_model(credential, model_id):
        del credential
        return _TelemetryProvider.list_models("")[0] if model_id == "telemetry-fixture" else None

    @staticmethod
    def adapter(credential, model_id):
        del credential, model_id
        return _TelemetryAdapter()


def _request(base: str, path: str, *, method: str = "GET", body: Any = None) -> tuple[Any, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
    return (json.loads(raw) if "json" in content_type else raw), content_type


def _require(condition: bool, failure: str, failures: list[str]) -> None:
    if not condition:
        failures.append(failure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the complete diagnostic receipt")
    args = parser.parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cortex-telemetry-smoke-") as temporary:
        base_path = Path(temporary)
        home = ensure_home(base_path / "home")
        host = base_path / "host"
        host.mkdir()
        (host / "README.md").write_text("CORTEX_TELEMETRY_SMOKE\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        server = None
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                bootstrap_repository(home, store, host, "TelemetrySmoke")
            secrets = MemorySecretStore()
            secrets.set("openai", "fixture-secret-never-persisted")
            fabric = ProviderFabric(store, secrets, providers={"openai": _TelemetryProvider()})
            server = serve_cortex_ui(
                store,
                "TelemetrySmoke",
                port=0,
                open_browser=False,
                secrets=secrets,
                fabric=fabric,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            html, _ = _request(base, "/")
            javascript, _ = _request(base, "/cortex.js")
            parser = _IdParser()
            parser.feed(html)

            session, _ = _request(
                base,
                "/v1/sessions",
                method="POST",
                body={"provider": "openai", "model_id": "telemetry-fixture"},
            )
            session_id = session["session_id"]
            _request(
                base,
                f"/v1/sessions/{session_id}/messages",
                method="POST",
                body={"text": "Compile the telemetry contract."},
            )
            deadline = time.time() + 10
            live = {}
            while time.time() < deadline:
                live, _ = _request(base, f"/v1/sessions/{session_id}/live")
                if not live.get("active") and live.get("telemetry", {}).get("state") == "COMPLETE":
                    break
                time.sleep(0.02)
            telemetry = live.get("telemetry") or {}
            metrics = telemetry.get("metrics") or {}
            events = server.cortex_service.events.since(session_id, 0)
            event_types = [event["event_type"] for event in events]

            _require(telemetry.get("state") == "COMPLETE", "turn_not_complete", failures)
            _require("model.delta" in event_types, "stream_event_missing", failures)
            _require("trajectory.sealed" in event_types, "trajectory_seal_missing", failures)
            for metric_name, dom_id in VISIBLE_METRICS.items():
                metric = metrics.get(metric_name) or {}
                _require(metric.get("value") is not None, f"metric_unavailable:{metric_name}", failures)
                _require(dom_id in parser.ids, f"dom_target_missing:{dom_id}", failures)
                _require(f"metrics.{metric_name}" in javascript, f"ui_binding_missing:{metric_name}", failures)
                _require(f'#{dom_id}' in javascript, f"dom_binding_missing:{dom_id}", failures)
            _require("AWAITING PROVIDER" in javascript, "live_reset_binding_missing", failures)
            _require(metrics.get("stream_chunks", {}).get("value") == 3, "stream_chunk_count_invalid", failures)
            _require(metrics.get("total_tokens", {}).get("value") == 150, "total_token_count_invalid", failures)
            _require(metrics.get("cost", {}).get("value") == 0.0025, "cost_binding_invalid", failures)
            _require(telemetry.get("authority", {}).get("execution_authorized") is False, "execution_authority_open", failures)
            _require(telemetry.get("authority", {}).get("host_mutate_authorized") is False, "host_authority_open", failures)

            report = {
                "schema_version": "cortex-ui-telemetry-smoke/1.0",
                "status": "PASS" if not failures else "FAIL",
                "session_id": session_id,
                "visible_metric_count": len(VISIBLE_METRICS),
                "event_types": event_types,
                "metrics": {name: metrics.get(name) for name in VISIBLE_METRICS},
                "explicitly_unavailable": {
                    name: metrics.get(name)
                    for name in ("confidence", "reasoning_depth", "cpu", "gpu", "network")
                },
                "authority": telemetry.get("authority"),
                "failures": failures,
            }
            if args.json or failures:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    "CORTEX UI TELEMETRY SMOKE PASS"
                    f" | {len(VISIBLE_METRICS)}/{len(VISIBLE_METRICS)} visible bindings"
                    f" | {metrics['stream_chunks']['value']} stream chunks"
                    " | authority closed"
                )
            return 0 if not failures else 1
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
