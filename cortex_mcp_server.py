"""Cortex MCP Server — expose Cortex as Model Context Protocol tools.

Wraps Cortex's CLI surface (index, query, self-test, vector search, neural
activation) as MCP tools that any MCP-compatible client can consume.

Tools exposed:
    cortex_index          (repo_path, name?) → bootstrap + index a repository
    cortex_query          (repo_name, query, limit?) → semantic search
    cortex_lexical        (repo_name, query, limit?) → keyword search
    cortex_neural_activate (repo_name, task) → bounded spreading activation
    cortex_status         (repo_name?) → health + stats
    cortex_self_test      () → run internal self-test
    cortex_migrate_vectors(repo_name?) → migrate legacy JSON vectors to BLOBs

Usage:
    python3 cortex_mcp_server.py [--home /path/to/cortex/home]

In Reasonix config.toml or kimi mcp.json:
    [[plugins]] / "mcpServers": {
        "cortex": {
            "command": "python3",
            "args": ["/path/to/cortex_mcp_server.py"]
        }
    }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any


def _import_cortex():
    """Lazy import — Cortex needs to be on the Python path."""
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cortex.config import ensure_home
    from cortex.context import build_context
    from cortex.governor import Governor
    from cortex.indexer import index_repository
    from cortex.config import load_repo_config, save_repo_config
    from cortex.retrieval import query
    from cortex.selftest import run_self_test
    from cortex.store import Store
    from cortex.neuron import activate_interlink
    return {
        "ensure_home": ensure_home,
        "build_context": build_context,
        "Governor": Governor,
        "index_repository": index_repository,
        "load_repo_config": load_repo_config,
        "save_repo_config": save_repo_config,
        "query": query,
        "run_self_test": run_self_test,
        "Store": Store,
        "activate_interlink": activate_interlink,
    }


# ── MCP Server Implementation ──────────────────────────────────────────────

TOOLS = {
    "cortex_status": {
        "description": "Get Cortex health status and statistics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "Optional repo name to scope stats to."},
            },
        },
    },
    "cortex_index": {
        "description": "Bootstrap and index a repository into Cortex.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Filesystem path to the repo."},
                "name": {"type": "string", "description": "Optional display name (defaults to dir name)."},
                "force": {"type": "boolean", "description": "Re-index even if already indexed.", "default": False},
            },
            "required": ["repo_path"],
        },
    },
    "cortex_query": {
        "description": "Semantic + lexical query against a Cortex repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
            "required": ["repo_name", "query"],
        },
    },
    "cortex_neural_activate": {
        "description": "Run bounded spreading activation through the neural interlink.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "task": {"type": "string"},
            },
            "required": ["repo_name", "task"],
        },
    },
    "cortex_self_test": {
        "description": "Run Cortex's internal self-test (verifies integrity, ledger, etc).",
        "input_schema": {"type": "object", "properties": {}},
    },
    "cortex_migrate_vectors": {
        "description": "Migrate legacy JSON vectors to float32 BLOBs (idempotent).",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "Optional — defaults to all repos."},
            },
        },
    },
    "cortex_decay_synapses": {
        "description": "Apply time-based decay to neural synapses. Returns summary stats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "decay_rate": {"type": "number", "default": 0.005},
                "grace_hours": {"type": "number", "default": 24.0},
            },
            "required": ["repo_name"],
        },
    },
}


def handle_tool_call(name: str, arguments: dict) -> dict[str, Any]:
    """Dispatch an MCP tool call to the appropriate Cortex function."""
    if name not in TOOLS:
        return {"error": f"Unknown tool: {name}", "available": list(TOOLS.keys())}

    try:
        cx = _import_cortex()
        ensure_home = cx["ensure_home"]
        Store = cx["Store"]

        if name == "cortex_status":
            home = ensure_home()
            db_path = home / "cortex.db"
            if not db_path.exists():
                return {"status": "no_database", "home": str(home)}
            store = Store(db_path)  # Cortex Store doesn't take readonly
            try:
                repo = arguments.get("repo_name")
                stats = {}
                if repo:
                    stats["repo"] = repo
                    stats["files"] = len(store.files(repo))
                    row = store.db.execute(
                        "SELECT COUNT(*) FROM memories WHERE repo=?", (repo,)
                    ).fetchone()
                    stats["memories"] = int(row[0]) if row else 0
                    # Cortex calls them "edges", not "associations"
                    row = store.db.execute(
                        "SELECT COUNT(*) FROM edges WHERE repo=?", (repo,)
                    ).fetchone()
                    stats["edges"] = int(row[0]) if row else 0
                    row = store.db.execute(
                        "SELECT COUNT(*) FROM neural_synapses WHERE repo=?", (repo,)
                    ).fetchone()
                    stats["neural_synapses"] = int(row[0]) if row else 0
                else:
                    row = store.db.execute("SELECT COUNT(*) FROM repositories").fetchone()
                    stats["repositories"] = int(row[0]) if row else 0
                stats["integrity"] = store.integrity_check()
                return {"status": "ok", "stats": stats, "db_path": str(db_path)}
            finally:
                store.close()

        elif name == "cortex_index":
            repo_path = Path(arguments["repo_path"]).resolve()
            if not repo_path.exists():
                return {"error": f"Path does not exist: {repo_path}"}
            name_arg = arguments.get("name") or repo_path.name
            force = arguments.get("force", False)
            cortex_home = ensure_home()
            store = Store(cortex_home / "cortex.db")
            try:
                # Auto-bootstrap if not yet configured
                config_path = repo_path / ".cortex" / "config.json"
                if not config_path.exists():
                    from cortex.bootstrap import bootstrap_repository
                    bootstrap_repository(cortex_home, store, repo_path, name=name_arg)
                config = cx["load_repo_config"](repo_path)
                cx["index_repository"](store, name_arg, config, force=force)
                # Get stats via direct queries (Store has no .stats() method)
                file_count = len(store.files(name_arg))
                mem_count_row = store.db.execute(
                    "SELECT COUNT(*) FROM memories WHERE repo=?", (name_arg,)
                ).fetchone()
                mem_count = mem_count_row[0] if mem_count_row else 0
                # Cortex stores vectors in memories.vector column (TEXT)
                vec_count_row = store.db.execute(
                    "SELECT COUNT(*) FROM memories WHERE repo=? AND vector IS NOT NULL",
                    (name_arg,),
                ).fetchone()
                vec_count = vec_count_row[0] if vec_count_row else 0
                return {
                    "status": "indexed",
                    "repo": name_arg,
                    "stats": {
                        "files": file_count,
                        "memories": mem_count,
                        "vectors": vec_count,
                    },
                }
            finally:
                store.close()

        elif name == "cortex_query":
            repo = arguments["repo_name"]
            query_text = arguments["query"]
            limit = arguments.get("limit", 8)
            ensure_home()
            store = Store(ensure_home() / "cortex.db")  # no readonly kwarg
            try:
                hits = cx["query"](store, repo, query_text, limit=limit)
                return {
                    "status": "ok",
                    "repo": repo,
                    "query": query_text,
                    "hit_count": len(hits),
                    "hits": [
                        {
                            "path": h.path,
                            "score": h.score,
                            "kind": h.kind,
                            "text": h.text[:300],
                            "start_line": h.start_line,
                            "end_line": h.end_line,
                        }
                        for h in hits
                    ],
                }
            finally:
                store.close()

        elif name == "cortex_neural_activate":
            repo = arguments["repo_name"]
            task = arguments["task"]
            ensure_home()
            store = Store(ensure_home() / "cortex.db")  # no readonly kwarg
            try:
                packet = cx["activate_interlink"](store, repo, task)
                return {
                    "status": "ok",
                    "repo": repo,
                    "task": task,
                    "activation_id": packet.get("activation_id"),
                    "evidence_count": len(packet.get("evidence", [])),
                    "packet": packet,
                }
            finally:
                store.close()

        elif name == "cortex_self_test":
            result = cx["run_self_test"]()
            return {"status": "ok", "result": result}

        elif name == "cortex_migrate_vectors":
            repo = arguments.get("repo_name")
            ensure_home()
            store = Store(ensure_home() / "cortex.db")
            try:
                result = store.migrate_vectors(repo)
                return {"status": "ok", "migration": result}
            finally:
                store.close()

        elif name == "cortex_decay_synapses":
            repo = arguments["repo_name"]
            decay_rate = arguments.get("decay_rate", 0.005)
            grace_hours = arguments.get("grace_hours", 24.0)
            ensure_home()
            store = Store(ensure_home() / "cortex.db")
            try:
                result = store.decay_neural_synapses(
                    repo, decay_rate=decay_rate, grace_hours=grace_hours
                )
                return {"status": "ok", "repo": repo, "decay": result}
            finally:
                store.close()

        else:
            return {"error": f"Tool not implemented: {name}"}

    except Exception as e:
        return {"error": str(e), "type": type(e).__name__, "traceback": traceback.format_exc()}


def handle_initialize(params: dict) -> dict:
    """MCP initialize handshake."""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "cortex-memory-server",
            "version": "1.0.0",
        },
        "capabilities": {"tools": {}},
    }


def handle_list_tools() -> dict:
    """Return the tool list per MCP spec."""
    return {"tools": [
        {"name": name, **spec} for name, spec in TOOLS.items()
    ]}


def handle_request(request: dict) -> dict:
    """Route an MCP JSON-RPC request to the appropriate handler."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        result = handle_initialize(params)
    elif method == "tools/list":
        result = handle_list_tools()
    elif method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_tool_call(name, arguments)
    else:
        result = {"error": f"Unknown method: {method}"}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


# ── Transport: stdio (JSON-RPC line-delimited) ─────────────────────────────

def stdio_server() -> None:
    """Read JSON-RPC requests from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()


# ── Transport: HTTP (FastAPI/Flask-style) ───────────────────────────────────

def make_http_app():
    """Create a minimal Flask app exposing MCP over HTTP/SSE.

    Returns a Flask app with /mcp endpoint accepting JSON-RPC POSTs.
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        return None

    app = Flask("cortex_mcp")

    @app.route("/mcp", methods=["POST"])
    def mcp_endpoint():
        request_data = request.get_json(force=True)
        response = handle_request(request_data)
        return jsonify(response)

    @app.route("/mcp/tools", methods=["GET"])
    def list_tools():
        return jsonify(handle_list_tools())

    return app


def http_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    """Run the MCP server over HTTP."""
    app = make_http_app()
    if app is None:
        print("Flask not installed. Install with: pip install flask", file=sys.stderr)
        sys.exit(1)
    app.run(host=host, port=port, debug=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cortex MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                        help="Transport: stdio (line-delimited JSON-RPC) or http")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.transport == "stdio":
        stdio_server()
    else:
        http_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())