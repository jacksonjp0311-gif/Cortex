"""Fusion proxy: SSE token parse + mock auto-tick."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.fuse_proxy import extract_stream_token, serve_fuse_proxy
from cortex.store import Store


class FuseProxyTests(unittest.TestCase):
    def test_extract_stream_token(self) -> None:
        line = 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
        self.assertEqual(extract_stream_token(line), "Hello")
        self.assertIsNone(extract_stream_token("data: [DONE]"))
        self.assertIsNone(extract_stream_token(": keep-alive"))

    def test_mock_proxy_ticks_fusion(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            base = Path(temp.name)
            home = ensure_home(base / "home")
            repo = base / "proxy_host"
            repo.mkdir()
            (repo / "README.md").write_text("# Proxy\n\n## Architecture\n\nx\n", encoding="utf-8")
            (repo / "a.py").write_text("x=1\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            bootstrap_repository(home, store, repo, "ProxyHost")
            store.close()

            server = serve_fuse_proxy(
                home=home,
                repo="ProxyHost",
                host="127.0.0.1",
                port=18787,
                mock=True,
                tick_every=1,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.3)
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:18787/v1/chat/completions",
                    data=json.dumps(
                        {
                            "model": "mock",
                            "stream": True,
                            "messages": [{"role": "user", "content": "hi"}],
                        }
                    ).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                self.assertIn("data:", raw)
                bridge = server.cortex_bridge
                self.assertGreaterEqual(bridge.stats["ticks"], 1)
                self.assertGreaterEqual(bridge.stats["tokens"], 1)
                health = urllib.request.urlopen(
                    "http://127.0.0.1:18787/health", timeout=10
                ).read()
                self.assertIn(b"cortex-fuse-proxy", health)
            finally:
                server.shutdown()
                bridge = getattr(server, "cortex_bridge", None)
                if bridge:
                    bridge.close()
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
