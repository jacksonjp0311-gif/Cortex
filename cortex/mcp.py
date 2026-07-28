"""Dependency-free MCP stdio server for Cortex's agent-neutral surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from . import __version__
from .config import ensure_home, load_repo_config
from .context import build_context, cortex_context_protocol
from .continuation import build_continuation_packet
from .evaluation import evaluate_corpus, load_corpus
from .federation import federated_query
from .governor import Governor
from .lifecycle import lifecycle_plan
from .retrieval import query
from .store import Store

MCP_STABLE_VERSION = "2025-11-25"
MCP_DRAFT_VERSION = "2026-07-28"
MCP_SUPPORTED_VERSIONS = [MCP_DRAFT_VERSION, MCP_STABLE_VERSION]


TOOLS = [
    {
        "name": "cortex_status",
        "description": "Inspect attached repositories and database integrity.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cortex_query",
        "description": "Retrieve provenance-backed evidence from one repository.",
        "inputSchema": {
            "type": "object",
            "required": ["repo", "query"],
            "properties": {
                "repo": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
        },
    },
    {
        "name": "cortex_federated_query",
        "description": "Search attached repositories while preserving boundaries.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "repositories": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 12},
            },
        },
    },
    {
        "name": "cortex_context",
        "description": "Build the stable cortex-context/1.0 agent packet.",
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 1200},
            },
        },
    },
    {
        "name": "cortex_continuation",
        "description": "Build a verified cortex-continuation/1.0 packet.",
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 1200},
            },
        },
    },
    {
        "name": "cortex_lifecycle_plan",
        "description": "Dry-run selective learned-association decay.",
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "grace_hours": {"type": "number", "default": 24},
                "decay_per_day": {"type": "number", "default": 0.05},
            },
        },
    },
    {
        "name": "cortex_evaluate",
        "description": "Run a repository-native replay corpus against base and learned routing.",
        "inputSchema": {
            "type": "object",
            "required": ["corpus"],
            "properties": {
                "corpus": {"type": "string"},
                "repo": {"type": "string"},
            },
        },
    },
]


class CortexMCP:
    def __init__(self, home: Path) -> None:
        self.home = ensure_home(home)
        self.store = Store(self.home / "cortex.db")
        self.governor = Governor(self.home, self.store)

    def close(self) -> None:
        self.store.close()

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "cortex_status":
            return {
                "version": __version__,
                "home": str(self.home),
                "database_integrity": self.store.integrity_check(),
                "repositories": [dict(row) for row in self.store.repos()],
            }
        if name == "cortex_query":
            repo = str(arguments["repo"])
            row = self.store.repo(repo)
            if not row:
                raise ValueError(f"Unknown repository: {repo}")
            config = load_repo_config(Path(row["path"]))
            return [
                hit.to_dict()
                for hit in query(
                    self.store,
                    repo,
                    str(arguments["query"]),
                    int(arguments.get("limit", 8)),
                    config.semantic_scan_limit,
                )
            ]
        if name == "cortex_federated_query":
            return federated_query(
                self.store,
                str(arguments["query"]),
                repositories=arguments.get("repositories"),
                limit=int(arguments.get("limit", 12)),
            )
        if name in {"cortex_context", "cortex_continuation"}:
            packet = build_context(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                str(arguments["task"]),
                int(arguments.get("budget", 1200)),
            )
            if name == "cortex_context":
                return cortex_context_protocol(packet)
            return build_continuation_packet(
                self.store, packet, origin_version=__version__
            )
        if name == "cortex_lifecycle_plan":
            return lifecycle_plan(
                self.store,
                str(arguments["repo"]),
                grace_hours=float(arguments.get("grace_hours", 24.0)),
                decay_per_day=float(arguments.get("decay_per_day", 0.05)),
            )
        if name == "cortex_evaluate":
            return evaluate_corpus(
                self.store,
                load_corpus(Path(str(arguments["corpus"])).expanduser().resolve()),
                default_repo=arguments.get("repo"),
            )
        raise ValueError(f"Unknown Cortex MCP tool: {name}")

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        if request_id is None:
            return None
        try:
            if method == "server/discover":
                result: Any = {
                    "resultType": "complete",
                    "supportedVersions": MCP_SUPPORTED_VERSIONS,
                    "capabilities": {"tools": {}},
                    "_meta": {
                        "io.modelcontextprotocol/serverInfo": {
                            "name": "cortex",
                            "version": __version__,
                        }
                    },
                    "instructions": (
                        "Use Cortex for provenance-backed repository context. "
                        "Its outputs never grant mutation authority."
                    ),
                    "ttlMs": 3_600_000,
                    "cacheScope": "private",
                }
            elif method == "initialize":
                requested = str(
                    (request.get("params") or {}).get(
                        "protocolVersion", MCP_STABLE_VERSION
                    )
                )
                negotiated = (
                    requested if requested in MCP_SUPPORTED_VERSIONS else MCP_STABLE_VERSION
                )
                result: Any = {
                    "protocolVersion": negotiated,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cortex", "version": __version__},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params") or {}
                value = self.call(str(params.get("name")), params.get("arguments") or {})
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(value, indent=2, default=str),
                        }
                    ],
                    "isError": False,
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except (KeyError, TypeError, ValueError, FileNotFoundError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"{type(exc).__name__}: {exc}"},
            }


def serve_stdio(home: Path) -> None:
    server = CortexMCP(home)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = server.dispatch(request)
            except json.JSONDecodeError as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": str(exc)},
                }
            if response is not None:
                print(json.dumps(response, separators=(",", ":"), default=str), flush=True)
    finally:
        server.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cortex-mcp")
    parser.add_argument("--home")
    args = parser.parse_args(argv)
    home = Path(args.home).expanduser().resolve() if args.home else Path.home() / ".cortex"
    serve_stdio(home)


if __name__ == "__main__":
    main()
