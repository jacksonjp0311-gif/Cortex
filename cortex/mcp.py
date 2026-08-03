"""Dependency-free MCP stdio server for Cortex's agent-neutral surfaces."""

from __future__ import annotations

import argparse
import json
import os
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
from .session_ritual import run_session_ritual
from .store import Store

MCP_STABLE_VERSION = "2025-11-25"
MCP_DRAFT_VERSION = "2026-07-28"
MCP_SUPPORTED_VERSIONS = [MCP_DRAFT_VERSION, MCP_STABLE_VERSION]

_REFUSE = (
    "Never grants mutation authority. Do not auto-execute ARIA. "
    "Obey agent_protocol.state.governor_mode (read_only = no edits)."
)

TOOLS = [
    {
        "name": "cortex_status",
        "description": f"Inspect attached repositories and database integrity. {_REFUSE}",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cortex_query",
        "description": f"Retrieve provenance-backed evidence from one repository. {_REFUSE}",
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
        "description": f"Search attached repositories while preserving boundaries. {_REFUSE}",
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
        "description": (
            "Build cortex-context packet with instructions + agent_protocol "
            "(activate→remember→consolidate). " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 800},
                "token_id": {"type": "string"},
            },
        },
    },
    {
        "name": "cortex_activate",
        "description": (
            "Full activate packet (same agent_protocol as CLI activate). " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 800},
                "token_id": {"type": "string"},
            },
        },
    },
    {
        "name": "cortex_ritual",
        "description": (
            "Session ritual: activate → optional remember → consolidate on one substrate. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 800},
                "remember_kind": {"type": "string", "default": "discovery"},
                "remember_text": {"type": "string"},
                "consolidate": {"type": "boolean", "default": True},
                "token_id": {"type": "string"},
            },
        },
    },
    {
        "name": "cortex_organism",
        "description": (
            "Living organism interlink (⊛): shared session body for agent+Cortex co-process. "
            + _REFUSE
            + " Not consciousness."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 800},
            },
        },
    },
    {
        "name": "cortex_breathe",
        "description": (
            "Mid-session organism rebind (∽): continue pulse without full re-assimilate. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 800},
            },
        },
    },
    {
        "name": "cortex_immune",
        "description": (
            "Immune gate (⚠): read block + immune_action before any host work. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "cortex_metrics",
        "description": (
            "Connect metric graph (⧉): rollups and co-activations grown each connect. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "cortex_predict",
        "description": (
            "Proactive evidence prediction (recommend-only prefetch). " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "task"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 200},
            },
        },
    },
    {
        "name": "cortex_ranker_status",
        "description": "Local ranker status (verified-only learning). " + _REFUSE,
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_vectors_query",
        "description": "Query local HNSW vector index. " + _REFUSE,
        "inputSchema": {
            "type": "object",
            "required": ["repo", "text"],
            "properties": {
                "repo": {"type": "string"},
                "text": {"type": "string"},
                "k": {"type": "integer", "default": 12},
            },
        },
    },
    {
        "name": "cortex_causal_report",
        "description": "Causal outcome ledger report. " + _REFUSE,
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_interconnect",
        "description": (
            "Interconnect mesh health (⧉): bottlenecks, gates, glyphic medium. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_interlock",
        "description": (
            "Typed informational interlock field (⟁): epoch-scoped E→L→O synergy, "
            "lesion gates, and optional full-graph sampling audit. " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "geometry": {"type": "boolean", "default": False},
                "bridges": {"type": "boolean", "default": False},
                "trial_suite": {
                    "type": "string",
                    "enum": ["easy", "hard", "full", "stress", "train", "holdout", "all", "bridge64"],
                },
                "source_trial_suite": {
                    "type": "string",
                    "enum": ["bridge64"],
                },
                "resonance": {"type": "boolean", "default": False},
                "top_k": {"type": "integer", "default": 5},
                "limit": {"type": "integer", "default": 2048},
            },
        },
    },
    {
        "name": "cortex_kernels",
        "description": (
            "Retention regimes (≋): reset/integrate/retain priors — not consciousness. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_fuse_open",
        "description": (
            "Open fusion co-process (⊛⇄): shared mind-state; host must tick each token. "
            + _REFUSE
            + " Not model-weight fusion; not consciousness."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "task": {"type": "string"},
                "budget": {"type": "integer", "default": 600},
            },
        },
    },
    {
        "name": "cortex_fuse_tick",
        "description": (
            "Fusion tick: regenerate geometry for this token/step; returns injection for the model. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "token": {"type": "string", "description": "Current token or step text"},
                "tokens": {"type": "integer", "default": 1},
            },
        },
    },
    {
        "name": "cortex_fuse_state",
        "description": "Read fusion self-model / mind_hash / U / attention. " + _REFUSE,
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_fuse_close",
        "description": "Close fusion co-process session. " + _REFUSE,
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_coherence",
        "description": (
            "Emergent coupling indicators ⧉≈: score, threshold, active couples "
            "(blood/geometry/spectral/ranker/fusion). Not consciousness. " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
    },
    {
        "name": "cortex_emergence_log",
        "description": (
            "MUST READ each turn ⧉◎: emergence/progress log (threshold crosses, "
            "couple activations, directives). Enhance work; not consciousness. "
            + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "limit": {"type": "integer", "default": 16},
                "note": {
                    "type": "string",
                    "description": "Optional milestone to append",
                },
            },
        },
    },
    {
        "name": "cortex_eval_coupling",
        "description": (
            "Measure gate ⌖⧉: fixed corpus + ablations (baseline / no_spectral / "
            "no_ranker). Suites: easy|hard|full|stress|all. Proves spectral+ranker "
            "lift via recall@k + MRR. Directs evolution. Not consciousness. " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "suite": {
                    "type": "string",
                    "enum": ["easy", "hard", "full", "stress", "train", "holdout", "all"],
                    "default": "full",
                },
                "limit": {"type": "integer", "default": 16},
                "top_k": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "cortex_self_org",
        "description": (
            "Self-org / alignment pulse ⧉⟳: listen to emergence + measure gate, "
            "warm ranker, invent coactivation edges, fuse tick if open, seal. "
            "Not consciousness. Not host mutation. " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "invent": {"type": "boolean", "default": True},
                "fuse_tick": {"type": "boolean", "default": True},
                "warm_ranker": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "cortex_host_mesh",
        "description": (
            "Multi-host mesh ⧉⬡: one SQLite body, many attached hosts. Observe "
            "coherence/ranker per host; optional federated query. Boundaries "
            "preserved. Not consciousness. " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "primary": {"type": "string", "default": "CortexTeach"},
                "query": {"type": "string"},
                "fast": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "cortex_distill",
        "description": (
            "Distill mesh observation + doctrine into durable memory (☰). " + _REFUSE
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "seal": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "cortex_continuation",
        "description": f"Build a verified cortex-continuation packet. {_REFUSE}",
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
        "description": f"Dry-run selective learned-association decay. {_REFUSE}",
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
        "description": f"Run a repository-native replay corpus. {_REFUSE}",
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
        if name == "cortex_activate":
            from .activation import activate_repository
            from .agents.tokens import require_scope

            gate = require_scope(
                self.store,
                str(arguments["repo"]),
                token_id=arguments.get("token_id"),
                scope="packet.activate",
            )
            if gate.get("required") and not gate.get("valid"):
                return {
                    "blocked": True,
                    "token_gate": gate,
                    "claim_boundary": "Multi-agent mode requires token_id.",
                }
            return activate_repository(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                str(arguments["task"]),
                int(arguments.get("budget", 800)),
            )
        if name == "cortex_ritual":
            from .agents.tokens import require_scope

            gate = require_scope(
                self.store,
                str(arguments["repo"]),
                token_id=arguments.get("token_id"),
                scope="packet.activate",
            )
            if gate.get("required") and not gate.get("valid"):
                return {
                    "blocked": True,
                    "token_gate": gate,
                    "claim_boundary": "Multi-agent mode requires token_id.",
                }
            memories = []
            text = arguments.get("remember_text")
            if text:
                memories.append(
                    {
                        "kind": str(arguments.get("remember_kind") or "discovery"),
                        "text": str(text),
                    }
                )
            return run_session_ritual(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                str(arguments["task"]),
                budget=int(arguments.get("budget", 800)),
                memories=memories,
                consolidate_session=bool(arguments.get("consolidate", True)),
            )
        if name == "cortex_organism":
            from .activation import activate_repository

            result = activate_repository(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                str(arguments["task"]),
                int(arguments.get("budget", 800)),
                profile="agent",
            )
            return {
                "organism": result.get("organism"),
                "session": result.get("session"),
                "control_error": result.get("control_error"),
                "activation": result.get("activation"),
                "claim_boundary": (
                    "Organism is session co-process state; not consciousness or authority."
                ),
            }
        if name == "cortex_fuse_open":
            from .coprocess import fuse_open

            return fuse_open(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                task=str(arguments.get("task") or "fusion"),
                budget=int(arguments.get("budget", 600)),
            )
        if name == "cortex_fuse_tick":
            from .coprocess import fuse_tick

            return fuse_tick(
                self.store,
                self.governor,
                str(arguments["repo"]),
                token=str(arguments.get("token") or ""),
                tokens=int(arguments.get("tokens") or 1),
            )
        if name == "cortex_fuse_state":
            from .coprocess import fuse_state

            return fuse_state(self.store, str(arguments["repo"]))
        if name == "cortex_fuse_close":
            from .coprocess import fuse_close

            return fuse_close(self.store, str(arguments["repo"]))
        if name == "cortex_coherence":
            from .coherence import measure_coherence

            return measure_coherence(
                self.store,
                str(arguments["repo"]),
                governor=self.governor,
                home=self.home,
            )
        if name == "cortex_interlock":
            from .math_net.info_interlock import (
                graph_sampling_audit,
                interlock_report,
                refresh_bridge_shadow,
            )

            repo = str(arguments["repo"])
            if bool(arguments.get("geometry")):
                return graph_sampling_audit(self.store, repo)
            if bool(arguments.get("bridges")):
                return refresh_bridge_shadow(self.store, repo)
            if arguments.get("trial_suite"):
                from .bridge_trials import run_bridge_trial_suite

                return run_bridge_trial_suite(
                    self.home,
                    self.store,
                    repo,
                    suite=str(arguments["trial_suite"]),
                    limit=max(8, min(64, int(arguments.get("limit") or 24))),
                    top_k=max(1, int(arguments.get("top_k") or 5)),
                )
            if arguments.get("source_trial_suite"):
                from .source_admission import run_source_admission_suite

                requested_limit = int(arguments.get("limit") or 24)
                limit = 24 if requested_limit == 2048 else max(8, min(48, requested_limit))
                return run_source_admission_suite(
                    self.home,
                    self.store,
                    repo,
                    suite="bridge64",
                    pool_size=limit,
                    widened_size=max(48, min(96, limit * 2)),
                    top_k=max(1, int(arguments.get("top_k") or 5)),
                )
            if bool(arguments.get("resonance")):
                from .resonance_sweep import run_frequency_sweep

                return run_frequency_sweep(
                    self.store,
                    repo,
                    home=self.home,
                    persist=True,
                )
            return interlock_report(
                self.store, repo, limit=int(arguments.get("limit") or 2048)
            )
        if name == "cortex_emergence_log":
            from .emergence_log import log_milestone, read_emergence_log

            repo = str(arguments["repo"])
            if arguments.get("note"):
                log_milestone(
                    self.home,
                    self.store,
                    repo,
                    summary=str(arguments["note"]),
                    kind="agent_note",
                    source="mcp",
                )
            return read_emergence_log(
                self.home,
                self.store,
                repo,
                limit=int(arguments.get("limit") or 16),
            )
        if name == "cortex_eval_coupling":
            from .eval_coupling import run_eval_coupling

            return run_eval_coupling(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                suite=str(arguments.get("suite") or "full"),
                limit=max(4, int(arguments.get("limit") or 16)),
                top_k=max(1, int(arguments.get("top_k") or 5)),
            )
        if name == "cortex_self_org":
            from .self_org import run_self_org

            return run_self_org(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                invent=bool(arguments.get("invent", True)),
                fuse_tick=bool(arguments.get("fuse_tick", True)),
                warm_ranker=bool(arguments.get("warm_ranker", True)),
            )
        if name == "cortex_host_mesh":
            from .host_mesh import run_host_mesh

            return run_host_mesh(
                self.home,
                self.store,
                self.governor,
                primary_repo=str(arguments.get("primary") or "CortexTeach"),
                query=arguments.get("query"),
                measure_coherence_field=not bool(arguments.get("fast")),
            )
        if name == "cortex_breathe":
            from .organism import breathe as organism_breathe

            return organism_breathe(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                arguments.get("task"),
                budget=int(arguments.get("budget", 800)),
            )
        if name == "cortex_immune":
            from .immune import inspect_immune

            return inspect_immune(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
            )
        if name == "cortex_metrics":
            from .connect_pass import metric_graph_report

            return metric_graph_report(self.store, str(arguments["repo"]))
        if name == "cortex_predict":
            from .predict import predict_context

            gov = self.governor.evaluate(str(arguments["repo"]))
            return predict_context(
                self.store,
                str(arguments["repo"]),
                str(arguments["task"]),
                budget=int(arguments.get("budget", 200)),
                governor_mode=str(gov.get("mode") or "normal"),
            )
        if name == "cortex_ranker_status":
            from .ranker import ranker_status

            return ranker_status(self.store, str(arguments["repo"]))
        if name == "cortex_vectors_query":
            from .vectors import query_hnsw

            return {
                "hits": query_hnsw(
                    self.store,
                    str(arguments["repo"]),
                    str(arguments["text"]),
                    k=int(arguments.get("k", 12)),
                ),
                "claim_boundary": "HNSW query is evidence only.",
            }
        if name == "cortex_causal_report":
            from .causal import causal_report

            return causal_report(self.store, str(arguments["repo"]))
        if name == "cortex_interconnect":
            from .interconnect import mesh_status

            return mesh_status(
                self.store,
                str(arguments["repo"]),
                governor=self.governor,
                home=self.home,
            )
        if name == "cortex_kernels":
            from .kernels import kernels_status

            return kernels_status(self.store, str(arguments["repo"]))
        if name == "cortex_distill":
            from .distill_intel import distill_intelligence

            return distill_intelligence(
                self.home,
                self.store,
                self.governor,
                str(arguments["repo"]),
                seal=bool(arguments.get("seal", True)),
                force=True,
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
                        "You share organism (⊛) session state with Cortex: you are temporary "
                        "working cortex; Cortex is durable body. Follow agent_protocol and "
                        "organism.immune first. Loop: activate → work (obey governor) → "
                        "remember → consolidate (cortex_ritual). Use cortex_organism for the "
                        "living pulse. Never mutation authority. read_only = diagnose only."
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
    os.environ["CORTEX_ACTIVE_HOME"] = str(home)
    serve_stdio(home)


if __name__ == "__main__":
    main()
