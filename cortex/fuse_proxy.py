"""OpenAI-compatible fusion proxy — auto fuse_tick on every streamed token.

Closes the last gap: host points OPENAI_BASE_URL at this proxy; each
chat.completion token regenerates Cortex geometry without manual tick calls.

Stdlib only. Upstream is any OpenAI-compatible HTTP API (or a dry mock).
Recommend-only; never host mutation authority.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from . import __version__
from .config import ensure_home
from .coprocess import fuse_close, fuse_open, fuse_state, fuse_tick
from .governor import Governor
from .store import Store

SCHEMA = "cortex-fuse-proxy/1.0"
GLYPH = "⊛⇄proxy"


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, default=str).encode("utf-8")


def extract_stream_token(line: str) -> str | None:
    """Parse one SSE data line from OpenAI-style stream; return content delta or None."""
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if line.startswith("data:"):
        payload = line[5:].strip()
    else:
        payload = line
    if payload == "[DONE]":
        return None
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    choices = obj.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    if content is None:
        # non-stream style chunk
        msg = choices[0].get("message") or {}
        content = msg.get("content")
    if isinstance(content, str) and content:
        return content
    return None


class FusionBridge:
    """Holds home/store/governor and ticks fusion on tokens."""

    def __init__(
        self,
        home: Path,
        repo: str,
        *,
        task: str = "",
        tick_every: int = 1,
        invent: bool = True,
    ) -> None:
        self.home = ensure_home(home)
        self.repo = repo
        self.task = task or "fusion proxy session"
        self.tick_every = max(1, int(tick_every))
        self.invent = invent
        db_path = self.home / "cortex.db"
        self.store = Store(db_path)
        # Proxy serves requests off the opener thread; allow cross-thread SQLite.
        try:
            self.store.db.close()
        except Exception:
            pass
        self.store.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.store.db.row_factory = sqlite3.Row
        try:
            self.store.db.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        self.governor = Governor(self.home, self.store)
        self._buf = ""
        self._chars = 0
        self._lock = threading.Lock()
        self.last_injection: dict[str, Any] | None = None
        self.stats = {"tokens": 0, "ticks": 0, "requests": 0}

    def open(self) -> dict[str, Any]:
        return fuse_open(
            self.home,
            self.store,
            self.governor,
            self.repo,
            task=self.task,
            invent_structure=self.invent,
            spectral_primary=True,
        )

    def on_token(self, piece: str) -> dict[str, Any] | None:
        """Accumulate token; tick every tick_every chars/pieces."""
        if not piece:
            return None
        with self._lock:
            self._buf += piece
            self._chars += len(piece)
            self.stats["tokens"] += 1
            if self.stats["tokens"] % self.tick_every != 0:
                return None
            token_window = self._buf[-240:]
            result = fuse_tick(
                self.store,
                self.governor,
                self.repo,
                token=token_window,
                tokens=self.tick_every,
                invent=self.invent,
            )
            self.stats["ticks"] += 1
            self.last_injection = result.get("injection")
            return result

    def flush(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._buf:
                return None
            result = fuse_tick(
                self.store,
                self.governor,
                self.repo,
                token=self._buf[-240:],
                tokens=1,
                invent=self.invent,
            )
            self.stats["ticks"] += 1
            self.last_injection = result.get("injection")
            return result

    def state(self) -> dict[str, Any]:
        return {
            **fuse_state(self.store, self.repo),
            "proxy_stats": dict(self.stats),
            "last_injection": self.last_injection,
        }

    def close(self) -> dict[str, Any]:
        out = fuse_close(self.store, self.repo)
        self.store.close()
        return out


def upstream_chat_completion(
    upstream_base: str,
    body: dict[str, Any],
    *,
    api_key: str | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes, str]:
    """Non-streaming upstream call; returns status, body, content-type."""
    base = upstream_base.rstrip("/")
    url = base + "/chat/completions"
    data = _json_bytes(body)
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or os.environ.get('OPENAI_API_KEY', '')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type") or "application/json"
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), "application/json"


def stream_upstream_and_tick(
    upstream_base: str,
    body: dict[str, Any],
    bridge: FusionBridge,
    write: Callable[[bytes], None],
    *,
    api_key: str | None = None,
    timeout: float = 300.0,
) -> int:
    """Proxy SSE stream; tick fusion on each content delta; write through to client."""
    base = upstream_base.rstrip("/")
    # force stream
    body = {**body, "stream": True}
    url = base + "/chat/completions"
    data = _json_bytes(body)
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {api_key or os.environ.get('OPENAI_API_KEY', '')}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        err = exc.read()
        write(err)
        return exc.code
    except Exception as exc:
        write(_json_bytes({"error": str(exc)}))
        return 502

    status = getattr(resp, "status", 200) or 200
    try:
        while True:
            raw = resp.readline()
            if not raw:
                break
            write(raw if raw.endswith(b"\n") else raw + b"\n")
            try:
                line = raw.decode("utf-8", errors="replace")
            except Exception:
                continue
            piece = extract_stream_token(line)
            if piece:
                bridge.on_token(piece)
        bridge.flush()
    finally:
        resp.close()
    return int(status)


def make_handler(
    bridge: FusionBridge,
    upstream_base: str,
    *,
    api_key: str | None = None,
    mock: bool = False,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            # quieter default
            pass

        def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Cortex-Fusion-Proxy", __version__)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/health", "/v1/health"}:
                body = _json_bytes(
                    {
                        "schema_version": SCHEMA,
                        "glyph": GLYPH,
                        "ok": True,
                        "version": __version__,
                        "repo": bridge.repo,
                        "fusion": bridge.state(),
                        "claim_boundary": (
                            "Proxy ticks Cortex on each streamed token; "
                            "not model-weight fusion; recommend-only."
                        ),
                    }
                )
                self._send(200, body)
                return
            if path in {"/v1/fusion/state", "/fusion/state"}:
                self._send(200, _json_bytes(bridge.state()))
                return
            self._send(404, _json_bytes({"error": "not_found"}))

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send(400, _json_bytes({"error": "invalid_json"}))
                return

            if path not in {"/v1/chat/completions", "/chat/completions"}:
                self._send(404, _json_bytes({"error": "not_found", "path": path}))
                return

            bridge.stats["requests"] += 1
            want_stream = bool(body.get("stream"))

            if mock:
                # Deterministic local stream for tests / offline demo
                text = "Cortex fusion geometry regenerates each token."
                if want_stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("X-Cortex-Fusion-Proxy", __version__)
                    self.end_headers()
                    for ch in text.split(" "):
                        piece = ch + " "
                        bridge.on_token(piece)
                        chunk = {
                            "id": "chatcmpl-cortex-mock",
                            "object": "chat.completion.chunk",
                            "choices": [{"index": 0, "delta": {"content": piece}}],
                        }
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    bridge.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    return
                for ch in text.split(" "):
                    bridge.on_token(ch + " ")
                bridge.flush()
                self._send(
                    200,
                    _json_bytes(
                        {
                            "id": "chatcmpl-cortex-mock",
                            "object": "chat.completion",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {"role": "assistant", "content": text},
                                    "finish_reason": "stop",
                                }
                            ],
                            "cortex_fusion": bridge.state(),
                        }
                    ),
                )
                return

            if want_stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Cortex-Fusion-Proxy", __version__)
                self.end_headers()

                def write(b: bytes) -> None:
                    self.wfile.write(b)
                    self.wfile.flush()

                stream_upstream_and_tick(
                    upstream_base, body, bridge, write, api_key=api_key
                )
                return

            # non-stream: tick after full response (and on words if mock-like)
            code, resp_body, ctype = upstream_chat_completion(
                upstream_base, body, api_key=api_key
            )
            try:
                obj = json.loads(resp_body.decode("utf-8"))
                content = (
                    ((obj.get("choices") or [{}])[0].get("message") or {}).get("content")
                    or ""
                )
                for word in str(content).split(" "):
                    if word:
                        bridge.on_token(word + " ")
                bridge.flush()
                if isinstance(obj, dict):
                    obj["cortex_fusion"] = {
                        "mind_hash": (bridge.state() or {}).get("mind_hash"),
                        "ticks": bridge.stats.get("ticks"),
                        "last_injection": bridge.last_injection,
                    }
                    resp_body = _json_bytes(obj)
            except Exception:
                pass
            self._send(code, resp_body, ctype)

    return Handler


def serve_fuse_proxy(
    *,
    home: Path,
    repo: str,
    host: str = "127.0.0.1",
    port: int = 8787,
    upstream: str = "https://api.openai.com/v1",
    task: str = "",
    tick_every: int = 1,
    mock: bool = False,
    api_key: str | None = None,
) -> HTTPServer:
    # Single-threaded server: one SQLite connection safe on the server thread.
    bridge = FusionBridge(home, repo, task=task, tick_every=tick_every)
    opened = bridge.open()
    handler = make_handler(bridge, upstream, api_key=api_key, mock=mock)
    server = HTTPServer((host, port), handler)
    server.cortex_bridge = bridge  # type: ignore[attr-defined]
    server.cortex_opened = opened  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Cortex fusion OpenAI-compatible proxy")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument(
        "--upstream",
        default=os.environ.get("CORTEX_FUSE_UPSTREAM", "https://api.openai.com/v1"),
    )
    ap.add_argument("--task", default="")
    ap.add_argument("--tick-every", type=int, default=1)
    ap.add_argument(
        "--mock",
        action="store_true",
        help="No upstream; stream mock tokens + fuse ticks",
    )
    ap.add_argument("--home", default=None, help="CORTEX_HOME (default: env/user home)")
    args = ap.parse_args(argv)

    if args.home:
        home = ensure_home(Path(args.home))
    else:
        env_home = os.environ.get("CORTEX_HOME")
        home = ensure_home(Path(env_home) if env_home else None)

    server = serve_fuse_proxy(
        home=home,
        repo=args.repo,
        host=args.host,
        port=args.port,
        upstream=args.upstream,
        task=args.task,
        tick_every=args.tick_every,
        mock=args.mock,
    )
    print(
        json.dumps(
            {
                "listening": f"http://{args.host}:{args.port}/v1",
                "repo": args.repo,
                "mock": args.mock,
                "opened": getattr(server, "cortex_opened", {}),
                "hint": "OPENAI_BASE_URL=http://127.0.0.1:8787/v1",
            },
            indent=2,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        bridge = getattr(server, "cortex_bridge", None)
        if bridge:
            print(json.dumps(bridge.close(), indent=2))
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
