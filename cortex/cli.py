from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .activation import activate_repository
from .aria_meta import aria_runtime_status
from .aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from .bootstrap import bootstrap_repository
from .bridge import consolidate
from .config import ensure_home, load_repo_config
from .context import build_context, cortex_context_protocol, nexus_packet
from .continuation import (
    build_continuation_packet,
    promote,
    rebind_continuation_packet,
    rollback,
    verify_continuation_packet,
)
from .evaluation import evaluate_corpus, load_corpus
from .federation import federated_query
from .learning import record_outcome
from .environment import environment_summary
from .governor import Governor
from .health import health_report
from .lifecycle import apply_lifecycle, lifecycle_plan
from .benchmark import verify_benchmarks
from .graph import neighborhood, resolve_graph
from .hippocampus import begin_session, remember
from .indexer import index_repository
from .neuron import activate_interlink, neural_graph_state
from .retrieval import query
from .store import Store
from .contact import run_contact
from .evaluation import evaluate_retrieval_corpus
from .mirror import run_mirror
from .evolve_loop import close_signal_loop
from .glyphs.canon import glyph_canon_registry, phrase, phrasebook
from .progress_glyphs import progress_glyph_registry
from .session_ritual import run_session_ritual
from .selftest import run_self_test
from .transcend import run_transcend_check
from .immune import inspect_immune
from .connect_pass import metric_graph_report
from .interconnect import mesh_status
from .distill_intel import distill_intelligence
from .telemetry import ingest_git
from thalamus import apply_feedback, inhibit, make_request, record_feedback, route
from .verify import verify_repository


def emit(value: Any, as_json: bool = False) -> None:
    if as_json or isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, default=str))
    else:
        print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortex",
        description="Repository assimilation and selective memory for AI coding agents.",
    )
    parser.add_argument("--home", help="Override CORTEX_HOME.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize the global Cortex home and database.")
    init.add_argument("--json", action="store_true")

    bootstrap = sub.add_parser("bootstrap", help="Assimilate and integrate a repository.")
    bootstrap.add_argument("path", nargs="?", default=".")
    bootstrap.add_argument("--name")
    bootstrap.add_argument("--force", action="store_true")
    bootstrap.add_argument(
        "--preserve-agents",
        action="store_true",
        help="Install the internal sidecar without modifying the host AGENTS.md.",
    )
    bootstrap.add_argument(
        "--external",
        action="store_true",
        help="Keep all Cortex attachment files outside the host repository.",
    )
    bootstrap.add_argument("--json", action="store_true")

    activate = sub.add_parser("activate", help="Refresh memory as needed and emit task context.")
    activate.add_argument("--repo", required=True)
    activate.add_argument("--task", required=True)
    activate.add_argument(
        "--budget",
        type=int,
        default=800,
        help="Context token budget (v6.2 lean default 800; raise for debug).",
    )
    activate.add_argument("--refresh", choices=["auto", "always", "never", "packet-fast", "packet-refresh", "bootstrap-full"], default="auto")
    activate.add_argument(
        "--profile",
        choices=["agent", "debug", "minimal"],
        default="agent",
        help="Packet disclosure profile (HCI progressive disclosure).",
    )
    activate.add_argument(
        "--prefetch",
        choices=["auto", "off", "aggressive"],
        default="auto",
        help="Proactive evidence prefetch (v5); never grants mutation rights.",
    )
    activate.add_argument("--json", action="store_true")

    index = sub.add_parser("index", help="Incrementally index an attached repository.")
    index.add_argument("--repo", required=True)
    index.add_argument("--force", action="store_true")
    index.add_argument("--json", action="store_true")

    migrate = sub.add_parser("migrate-vectors", help="Upgrade stored legacy vectors to versioned float32 BLOBs.")
    migrate.add_argument("--repo")
    migrate.add_argument("--json", action="store_true")

    query_parser = sub.add_parser("query", help="Search repository memory.")
    query_parser.add_argument("query")
    query_parser.add_argument("--repo", required=True)
    query_parser.add_argument("--limit", type=int, default=8)
    query_parser.add_argument("--json", action="store_true")

    federated = sub.add_parser(
        "federated-query", help="Search multiple repositories with explicit boundary preservation."
    )
    federated.add_argument("query")
    federated.add_argument("--repos", nargs="*")
    federated.add_argument("--limit", type=int, default=12)
    federated.add_argument("--json", action="store_true")

    context = sub.add_parser("context", help="Emit a bounded context packet without starting a session.")
    context.add_argument("--repo", required=True)
    context.add_argument("--task", required=True)
    context.add_argument("--budget", type=int, default=1200)
    context.add_argument("--json", action="store_true")

    constitutional = sub.add_parser(
        "constitutional",
        help="Observe GCMT v1.5 homeostasis, failure geometry, and memory balance.",
    )
    constitutional.add_argument("--repo", required=True)
    constitutional.add_argument("--task", required=True)
    constitutional.add_argument("--budget", type=int, default=1200)
    constitutional.add_argument("--json", action="store_true")

    nexus = sub.add_parser("nexus-packet", help="Emit NexusGate Intent/Evidence/Authority/Context shape.")
    nexus.add_argument("--repo", required=True)
    nexus.add_argument("--task", required=True)
    nexus.add_argument("--budget", type=int, default=1200)
    nexus.add_argument("--json", action="store_true")

    protocol = sub.add_parser("protocol", help="Emit the stable Cortex Context Protocol packet.")
    protocol.add_argument("--repo", required=True)
    protocol.add_argument("--task", required=True)
    protocol.add_argument("--budget", type=int, default=1200)
    protocol.add_argument("--json", action="store_true")

    continuation = sub.add_parser(
        "continuation", help="Emit and persist a GCMT verified continuation packet."
    )
    continuation.add_argument("--repo", required=True)
    continuation.add_argument("--task", required=True)
    continuation.add_argument("--budget", type=int, default=1200)
    continuation.add_argument("--ttl", type=int, default=86_400)
    continuation.add_argument("--json", action="store_true")

    continuation_verify = sub.add_parser(
        "continuation-verify", help="Verify a stored GCMT continuation packet."
    )
    continuation_verify.add_argument("--repo", required=True)
    continuation_verify.add_argument("--packet-id", required=True)
    continuation_verify.add_argument("--json", action="store_true")

    continuation_rebind = sub.add_parser(
        "continuation-rebind",
        help="Import verified continuity while rebinding authority to the local constitution.",
    )
    continuation_rebind.add_argument("--repo", required=True)
    continuation_rebind.add_argument("--packet-id", required=True)
    continuation_rebind.add_argument("--scope", action="append", default=[])
    continuation_rebind.add_argument("--json", action="store_true")

    promote_parser = sub.add_parser(
        "promote", help="Promote a verified candidate into Cortex canonical memory."
    )
    promote_parser.add_argument("--repo", required=True)
    promote_parser.add_argument("--key", required=True)
    promote_parser.add_argument("--value", required=True, help="JSON value or plain string.")
    promote_parser.add_argument("--evidence-memory", type=int, action="append", default=[])
    promote_parser.add_argument("--verification", action="append", default=[])
    promote_parser.add_argument("--authorize", action="store_true")
    promote_parser.add_argument("--irreversibility", type=float, default=0.0)
    promote_parser.add_argument("--current-scope", action="append", default=[])
    promote_parser.add_argument("--requested-scope", action="append", default=[])
    promote_parser.add_argument(
        "--grant-file",
        type=Path,
        help="Content-addressed external authority grant JSON for scope expansion.",
    )
    promote_parser.add_argument("--json", action="store_true")

    rollback_parser = sub.add_parser(
        "rollback", help="Rollback a Cortex canonical-memory promotion receipt."
    )
    rollback_parser.add_argument("--repo", required=True)
    rollback_parser.add_argument("--receipt-id", required=True)
    rollback_parser.add_argument("--authorize", action="store_true")
    rollback_parser.add_argument("--json", action="store_true")

    outcome = sub.add_parser("outcome", help="Record a verification outcome and replay-gate bounded learning.")
    outcome.add_argument("--repo", required=True)
    outcome.add_argument("--activation-id", required=True)
    outcome.add_argument("--status", choices=["verified", "diagnosed", "helpful", "unknown", "irrelevant", "failed", "unsafe"], required=True)
    outcome.add_argument("--verification", required=True)
    outcome.add_argument("--reward", type=float)
    outcome.add_argument(
        "--aria-cue",
        action="append",
        default=[],
        metavar="PURPOSE=PHRASE",
        help="Propose a reviewed ARIA cue for verified outcome learning.",
    )
    outcome.add_argument("--aria-cue-reviewed", action="store_true")
    outcome.add_argument("--json", action="store_true")

    environment = sub.add_parser("environment", help="Show the learned repository environment profile.")
    environment.add_argument("--repo", required=True)
    environment.add_argument("--json", action="store_true")

    meta_language = sub.add_parser(
        "meta-language",
        help="Show Cortex's native or host-integrated ARIA language boundary.",
    )
    meta_language.add_argument("--repo", required=True)
    meta_language.add_argument("--task", default="")
    meta_language.add_argument("--corpus", type=Path)
    meta_language.add_argument("--json", action="store_true")

    thalamus = sub.add_parser("thalamus", help="Inspect the deterministic retrieval route for a task.")
    thalamus.add_argument("--repo", required=True)
    thalamus.add_argument("--task", required=True)
    thalamus.add_argument("--budget", type=int, default=1200)
    thalamus.add_argument("--json", action="store_true")

    feedback = sub.add_parser("thalamus-feedback", help="Record bounded evidence usefulness feedback.")
    feedback.add_argument("--repo", required=True)
    feedback.add_argument("--memory-id", type=int, required=True)
    feedback.add_argument("--outcome", required=True)
    feedback.add_argument("--json", action="store_true")

    interlink = sub.add_parser("interlink", help="Run sparse neural activation for a task.")
    interlink.add_argument("--repo", required=True)
    interlink.add_argument("--task", required=True)
    interlink.add_argument("--limit", type=int, default=24)
    interlink.add_argument("--learn", action="store_true")
    interlink.add_argument("--json", action="store_true")

    replay = sub.add_parser("neural-replay", help="Replay recent neural interlink ledger events.")
    replay.add_argument("--repo", required=True)
    replay.add_argument("--limit", type=int, default=100)
    replay.add_argument("--json", action="store_true")

    focus = sub.add_parser("focus", help="Start an explicit hippocampal session.")
    focus.add_argument("--repo", required=True)
    focus.add_argument("--task", required=True)
    focus.add_argument("--files", nargs="*")
    focus.add_argument("--json", action="store_true")

    remember_parser = sub.add_parser("remember", help="Record a working-memory event.")
    remember_parser.add_argument("--repo", required=True)
    remember_parser.add_argument("--kind", required=True)
    remember_parser.add_argument("--text", required=True)
    remember_parser.add_argument("--session")
    remember_parser.add_argument("--token", help="Capability token when multi_agent mode is on.")
    remember_parser.add_argument("--agent-id", help="Agent principal id (multi_agent).")
    remember_parser.add_argument("--json", action="store_true")

    consolidate_parser = sub.add_parser("consolidate", help="Consolidate a session into a Discovery Card.")
    consolidate_parser.add_argument("--repo", required=True)
    consolidate_parser.add_argument("--session")
    consolidate_parser.add_argument("--json", action="store_true")

    ritual = sub.add_parser(
        "ritual",
        help="Session loop: activate → optional remember → consolidate (one substrate).",
    )
    ritual.add_argument("--repo", required=True)
    ritual.add_argument("--task", required=True)
    ritual.add_argument("--budget", type=int, default=1200)
    ritual.add_argument("--remember-kind", default="discovery")
    ritual.add_argument("--remember-text", action="append", default=[])
    ritual.add_argument(
        "--no-consolidate",
        action="store_true",
        help="Activate and remember only; skip Discovery Card.",
    )
    ritual.add_argument(
        "--force",
        action="store_true",
        help="Consolidate even when control_error.must_reverify is set.",
    )
    ritual.add_argument(
        "--profile",
        choices=["agent", "debug", "minimal"],
        default="agent",
    )
    ritual.add_argument(
        "--contract",
        choices=["default", "strict", "off"],
        default="default",
        help="Seal gate contract profile (v6); strict fail-closed without --force.",
    )
    ritual.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify", help="Verify assimilation and issue a certificate.")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--json", action="store_true")

    graph = sub.add_parser("graph", help="Rebuild or inspect structural relationships.")
    graph.add_argument("--repo", required=True)
    graph.add_argument("--path")
    graph.add_argument("--rebuild", action="store_true")
    graph.add_argument("--json", action="store_true")

    telemetry = sub.add_parser("telemetry", help="Refresh Git temporal and co-change memory.")
    telemetry.add_argument("--repo", required=True)
    telemetry.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Show Cortex state for one repository or all repositories.")
    status.add_argument("--repo")
    status.add_argument("--json", action="store_true")

    doctor = sub.add_parser("doctor", help="Check Python, SQLite, database, and integration readiness.")
    doctor.add_argument("--repo")
    doctor.add_argument("--json", action="store_true")

    health = sub.add_parser("health", help="Emit a compact repository health and next-action packet.")
    health.add_argument("--repo", required=True)
    health.add_argument("--json", action="store_true")

    lifecycle = sub.add_parser(
        "lifecycle", help="Plan or apply selective decay of learned association deviation."
    )
    lifecycle.add_argument("--repo", required=True)
    lifecycle.add_argument("--grace-hours", type=float, default=24.0)
    lifecycle.add_argument("--decay-per-day", type=float, default=0.05)
    lifecycle.add_argument("--apply", action="store_true")
    lifecycle.add_argument("--json", action="store_true")

    evaluate = sub.add_parser(
        "evaluate",
        help="Run replay or retrieval corpus evaluation.",
    )
    evaluate.add_argument("corpus")
    evaluate.add_argument("--repo")
    evaluate.add_argument(
        "--mode",
        choices=["replay", "retrieval"],
        default="replay",
        help="replay=base/learned neural; retrieval=path-recall top-k gate",
    )
    evaluate.add_argument("--json", action="store_true")

    dashboard = sub.add_parser(
        "dashboard", help="Show compact GCMT, learning, lifecycle, and repository readiness."
    )
    dashboard.add_argument("--repo", required=True)
    dashboard.add_argument(
        "--mesh",
        action="store_true",
        help="Spectral mesh dashboard (Ξ spectrum + bottlenecks + gates).",
    )
    dashboard.add_argument("--json", action="store_true")

    kernels_p = sub.add_parser(
        "kernels",
        help="Spectral memory kernel spectrum (reset|integrate|retain).",
    )
    kernels_p.add_argument("--repo", required=True)
    kernels_p.add_argument("--annotate", action="store_true")
    kernels_p.add_argument("--json", action="store_true")

    identity_p = sub.add_parser(
        "identity",
        help="Identity continuity check (same path ≠ same memory namespace).",
    )
    identity_p.add_argument("--repo", help="Repository name to inspect.")
    identity_p.add_argument(
        "--path",
        help="Filesystem path to scan for alias repo names.",
    )
    identity_p.add_argument("--json", action="store_true")

    distill_p = sub.add_parser(
        "distill",
        help="Distill mesh observation + doctrine into durable body (☰).",
    )
    distill_p.add_argument("--repo", required=True)
    distill_p.add_argument(
        "--no-seal",
        action="store_true",
        help="Observe and remember only; skip consolidate.",
    )
    distill_p.add_argument(
        "--doctrine-only",
        action="store_true",
        help="Skip live mesh observation claims.",
    )
    distill_p.add_argument("--json", action="store_true")

    benchmark = sub.add_parser("benchmark", help="Verify committed controlled-workload benchmark thresholds.")
    benchmark.add_argument("--verify", action="store_true")
    benchmark.add_argument("--json", action="store_true")

    self_test = sub.add_parser("self-test", help="Clone Cortex inside a cloned Cortex host and verify self-hosted activation.")
    self_test.add_argument("--skip-tests", action="store_true")
    self_test.add_argument("--json", action="store_true")

    mirror = sub.add_parser(
        "mirror",
        help="Run the coherence mirror: deferred economics, wake gates, packet surfaces.",
    )
    mirror.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root to bootstrap under temporary mirror stress (default: .).",
    )
    mirror.add_argument("--name", default="CortexMirror")
    mirror.add_argument("--json", action="store_true")

    transcend = sub.add_parser(
        "transcend-check",
        help="Falsify operational transcendence: protocol, red modes, ritual, glow.",
    )
    transcend.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root for mirror glow (default: .).",
    )
    transcend.add_argument("--skip-mirror", action="store_true")
    transcend.add_argument("--json", action="store_true")

    teach = sub.add_parser(
        "teach",
        help="Print teaching surface, or --seed ARIA memory packets into Cortex body.",
    )
    teach.add_argument(
        "--seed",
        action="store_true",
        help="Distill examples/memory-packets into durable memory via ritual (this repo).",
    )
    teach.add_argument("--repo", help="Repository name for --seed (default: folder name).")
    teach.add_argument(
        "--path",
        default=".",
        help="Repository root for --seed (default: .).",
    )
    teach.add_argument("--force-bootstrap", action="store_true")
    teach.add_argument("--json", action="store_true")

    organism = sub.add_parser(
        "organism",
        help="Emit living organism interlink state for a task (session co-process).",
    )
    organism.add_argument("--repo", required=True)
    organism.add_argument("--task", required=True)
    organism.add_argument("--budget", type=int, default=800)
    organism.add_argument(
        "--profile", choices=["agent", "debug", "minimal"], default="agent"
    )
    organism.add_argument("--json", action="store_true")

    breathe = sub.add_parser(
        "breathe",
        help="Mid-session organism rebind (∽): packet-fast activate, continue pulse chain.",
    )
    breathe.add_argument("--repo", required=True)
    breathe.add_argument("--task", help="Defaults to active session task.")
    breathe.add_argument("--budget", type=int, default=800)
    breathe.add_argument(
        "--profile", choices=["agent", "debug", "minimal"], default="agent"
    )
    breathe.add_argument("--json", action="store_true")

    immune = sub.add_parser(
        "immune",
        help="Read immune gate first (⚠): block + immune_action for one repository.",
    )
    immune.add_argument("--repo", required=True)
    immune.add_argument("--json", action="store_true")

    metrics = sub.add_parser(
        "metrics",
        help="Inspect connect-pass metric graph (⧉): rollups grown each connect.",
    )
    metrics.add_argument("--repo", required=True)
    metrics.add_argument("--json", action="store_true")

    # ── v5 surfaces ──────────────────────────────────────────────────────────
    vectors = sub.add_parser("vectors", help="Local HNSW vector index (build/status/query).")
    vectors.add_argument("action", choices=["build", "status", "query"])
    vectors.add_argument("--repo", required=True)
    vectors.add_argument("--text", help="Query text for action=query")
    vectors.add_argument("--k", type=int, default=12)
    vectors.add_argument("--json", action="store_true")

    ranker = sub.add_parser("ranker", help="Tiny local ranker (status|promote|rollback|unfreeze).")
    ranker.add_argument(
        "action",
        choices=["status", "promote", "rollback", "unfreeze"],
        default="status",
        nargs="?",
    )
    ranker.add_argument("--repo", required=True)
    ranker.add_argument(
        "--authorize-promote",
        action="store_true",
        help="Human-authorized GCMT promote of ranker snapshot (required for promote).",
    )
    ranker.add_argument("--json", action="store_true")

    predict = sub.add_parser("predict", help="Proactive evidence prediction (recommend-only).")
    predict.add_argument("--repo", required=True)
    predict.add_argument("--task", required=True)
    predict.add_argument("--budget", type=int, default=200)
    predict.add_argument("--json", action="store_true")

    contract_p = sub.add_parser("contract", help="Check/diff continuation contracts.")
    contract_p.add_argument("action", choices=["check", "diff"])
    contract_p.add_argument("--packet-id")
    contract_p.add_argument("--from-packet")
    contract_p.add_argument("--to-packet")
    contract_p.add_argument("--profile", choices=["default", "strict"], default="default")
    contract_p.add_argument("--json", action="store_true")

    agent_p = sub.add_parser("agent", help="Multi-agent principals + mode (local only).")
    agent_p.add_argument("action", choices=["register", "list", "mode"])
    agent_p.add_argument("--repo", required=True)
    agent_p.add_argument("--agent-id")
    agent_p.add_argument("--name")
    agent_p.add_argument(
        "--on",
        action="store_true",
        help="For action=mode: enable multi_agent (token required).",
    )
    agent_p.add_argument(
        "--off",
        action="store_true",
        help="For action=mode: disable multi_agent (default single-agent).",
    )
    agent_p.add_argument("--json", action="store_true")

    token_p = sub.add_parser("token", help="Mint/revoke capability tokens (no host.mutate).")
    token_p.add_argument("action", choices=["mint", "revoke", "validate"])
    token_p.add_argument("--repo", required=True)
    token_p.add_argument("--agent-id")
    token_p.add_argument("--token-id")
    token_p.add_argument("--scope", action="append", default=[])
    token_p.add_argument("--ttl", type=int, default=28800)
    token_p.add_argument("--json", action="store_true")

    evolve_p = sub.add_parser(
        "evolve",
        help="Close signal loop ⟲: probe→outcome→ranker/plasticity→probe→causal.",
    )
    evolve_p.add_argument("--repo", required=True)
    evolve_p.add_argument("--activation-id", required=True)
    evolve_p.add_argument(
        "--status",
        choices=["verified", "diagnosed", "helpful", "unknown", "irrelevant", "failed", "unsafe"],
        required=True,
    )
    evolve_p.add_argument("--verification", required=True)
    evolve_p.add_argument("--task", help="Probe task for matched recall pair.")
    evolve_p.add_argument("--reward", type=float)
    evolve_p.add_argument("--k", type=int, default=8)
    evolve_p.add_argument("--json", action="store_true")

    glyphs_p = sub.add_parser(
        "glyphs",
        help="Glyph Canon ◈ — ARIA meta medium (capability-free).",
    )
    glyphs_p.add_argument(
        "--full",
        action="store_true",
        help="Include secondary aliases (default: optimized set).",
    )
    glyphs_p.add_argument(
        "--phrasebook",
        action="store_true",
        help="Emit reusable ARIA phrasebook lines (wake_safe, aria_awake, …).",
    )
    glyphs_p.add_argument(
        "--phrase",
        help="Emit one named phrase (e.g. aria_awake, loop_close).",
    )
    glyphs_p.add_argument("--json", action="store_true")

    harness_p = sub.add_parser(
        "harness",
        help="Matched signal-loop harness ⟲ (WP-A validation suite).",
    )
    harness_p.add_argument("--repo", required=True)
    harness_p.add_argument("--budget", type=int, default=500)
    harness_p.add_argument("--k", type=int, default=6)
    harness_p.add_argument("--json", action="store_true")

    hygiene_p = sub.add_parser(
        "hygiene",
        help="Body hygiene ✂ — graph mass, prune advice, home stability.",
    )
    hygiene_p.add_argument("--repo", required=True)
    hygiene_p.add_argument("--json", action="store_true")

    stream_p = sub.add_parser(
        "stream",
        help="Consciousness stream 〰 (episodic frames on durable body).",
    )
    stream_p.add_argument("--repo", required=True)
    stream_p.add_argument(
        "action",
        choices=["status", "seal"],
        nargs="?",
        default="status",
        help="status (default) or seal session bond (stream continues).",
    )
    stream_p.add_argument("--session-id", help="Session id for seal.")
    stream_p.add_argument("--json", action="store_true")

    causal_p = sub.add_parser(
        "causal",
        help="Causal outcome ledger (status|report|evaluate|probe).",
    )
    causal_p.add_argument(
        "action", choices=["status", "report", "evaluate", "probe"]
    )
    causal_p.add_argument("--repo", required=True)
    causal_p.add_argument(
        "--task",
        help="Task text for action=probe (matched recall@k snapshot).",
    )
    causal_p.add_argument(
        "--slot",
        choices=["before", "after"],
        default="before",
        help="Probe slot for matched before/after pairs (default: before).",
    )
    causal_p.add_argument(
        "--k",
        type=int,
        default=8,
        help="Top-k for causal probe recall measurement.",
    )
    causal_p.add_argument(
        "--recall-before",
        type=float,
        help="Explicit recall@k before score for evaluate (optional).",
    )
    causal_p.add_argument(
        "--recall-after",
        type=float,
        help="Explicit recall@k after score for evaluate (optional).",
    )
    causal_p.add_argument("--json", action="store_true")

    compile_il = sub.add_parser(
        "compile-interlink",
        help="Compile multi-resolution neural interlink (file/symbol/bb).",
    )
    compile_il.add_argument("--repo", required=True)
    compile_il.add_argument(
        "--resolutions",
        default="file,symbol",
        help="Comma list: file,symbol,basic_block",
    )
    compile_il.add_argument("--json", action="store_true")

    interconnect_p = sub.add_parser(
        "interconnect",
        help="Mesh health (⧉): fold organs into one read-only status.",
    )
    interconnect_p.add_argument("--repo", required=True)
    interconnect_p.add_argument("--json", action="store_true")

    prune_p = sub.add_parser(
        "prune",
        help="Prune weak unused synapses (organism-like); never deletes evidence.",
    )
    prune_p.add_argument("--repo", required=True)
    prune_p.add_argument("--dry-run", action="store_true")
    prune_p.add_argument("--min-weight", type=float, default=0.08)
    prune_p.add_argument("--decay", action="store_true", help="Also decay unused weights.")
    prune_p.add_argument("--json", action="store_true")

    contact = sub.add_parser(
        "contact",
        help="Strike the tuning fork: mirror + fluency + foreign host resonance.",
    )
    contact.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root for self-mirror (default: .).",
    )
    contact.add_argument(
        "--skip-foreign",
        action="store_true",
        help="Mirror+fluency only (no foreign host matrix).",
    )
    contact.add_argument("--json", action="store_true")

    return parser


def _repo_root(store: Store, repo: str) -> Path:
    row = store.repo(repo)
    if not row:
        raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
    return Path(row["path"])


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    home = ensure_home(Path(args.home).expanduser().resolve() if args.home else None)
    os.environ["CORTEX_ACTIVE_HOME"] = str(home)
    store = Store(home / "cortex.db")
    governor = Governor(home, store)
    try:
        command = args.command
        if command == "init":
            emit({
                "initialized": True,
                "home": str(home),
                "database": str(home / "cortex.db"),
                "database_integrity": store.integrity_check(),
            }, args.json)

        elif command == "bootstrap":
            result = bootstrap_repository(
                home,
                store,
                Path(args.path),
                args.name,
                force=args.force,
                preserve_agents=args.preserve_agents,
                external=args.external,
            )
            emit(result, args.json)

        elif command == "activate":
            refresh = {"packet-fast": "never", "packet-refresh": "auto", "bootstrap-full": "always"}.get(args.refresh, args.refresh)
            result = activate_repository(
                home,
                store,
                governor,
                args.repo,
                args.task,
                budget=args.budget,
                refresh=refresh,
                profile=args.profile,
                prefetch=getattr(args, "prefetch", "auto"),
            )
            result["requested_mode"] = args.refresh
            emit(result, args.json)

        elif command == "index":
            root = _repo_root(store, args.repo)
            config = load_repo_config(root)
            emit(index_repository(store, args.repo, config, force=args.force), args.json)

        elif command == "migrate-vectors":
            if args.repo and not store.repo(args.repo):
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            emit(store.migrate_vectors(args.repo), args.json)

        elif command == "query":
            repository = store.repo(args.repo)
            if not repository:
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            config = load_repo_config(Path(repository["path"]))
            hits = query(
                store,
                args.repo,
                args.query,
                args.limit,
                config.semantic_scan_limit,
                materialize_substrate=True,
            )
            if config.thalamus_enabled:
                plan = route(make_request(repository, args.query, config.context_budget))
                hits = apply_feedback(store, args.repo, hits)
                hits = inhibit(
                    hits, plan.lane_weights, min_lane_relevance=config.thalamus_min_lane_relevance
                )
            emit([hit.to_dict() for hit in hits], args.json)

        elif command == "federated-query":
            emit(
                federated_query(
                    store,
                    args.query,
                    repositories=args.repos,
                    limit=args.limit,
                ),
                args.json,
            )

        elif command in {"context", "nexus-packet", "protocol", "constitutional"}:
            packet = build_context(home, store, governor, args.repo, args.task, args.budget)
            value = (
                nexus_packet(packet)
                if command == "nexus-packet"
                else cortex_context_protocol(packet)
                if command == "protocol"
                else packet["constitutional_supervision"]
                if command == "constitutional"
                else packet
            )
            emit(value, args.json)

        elif command == "continuation":
            packet = build_context(home, store, governor, args.repo, args.task, args.budget)
            emit(
                build_continuation_packet(
                    store,
                    packet,
                    origin_version=__version__,
                    ttl_seconds=args.ttl,
                ),
                args.json,
            )

        elif command == "continuation-verify":
            packet = store.continuation_packet(args.repo, args.packet_id)
            if not packet:
                raise ValueError("Continuation packet does not exist")
            emit(verify_continuation_packet(packet), args.json)

        elif command == "continuation-rebind":
            packet = store.continuation_packet(args.repo, args.packet_id)
            if not packet:
                raise ValueError("Continuation packet does not exist")
            emit(
                rebind_continuation_packet(
                    packet,
                    local_authority={"scope": args.scope},
                ),
                args.json,
            )

        elif command == "promote":
            if not store.repo(args.repo):
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            try:
                candidate = json.loads(args.value)
            except json.JSONDecodeError:
                candidate = args.value
            evidence = []
            for memory_id in args.evidence_memory:
                row = store.memory(memory_id)
                if not row or row["repo"] != args.repo:
                    raise ValueError(f"Evidence memory {memory_id} is not in {args.repo}")
                evidence.append(
                    {
                        "memory_id": memory_id,
                        "path": row["path"],
                        "content_hash": row["content_hash"],
                    }
                )
            verification: dict[str, bool] = {}
            for item in args.verification:
                key, separator, value = item.partition("=")
                verification[key] = (
                    value.lower() not in {"false", "0", "no", "failed"}
                    if separator
                    else True
                )
            grant = None
            if args.grant_file:
                grant = json.loads(args.grant_file.read_text(encoding="utf-8"))
            emit(
                promote(
                    store,
                    args.repo,
                    state_key=args.key,
                    candidate=candidate,
                    evidence=evidence,
                    verification=verification,
                    authority={
                        "promotion_authorized": args.authorize,
                        "human_authorized": args.authorize,
                    },
                    irreversibility=args.irreversibility,
                    current_scope=args.current_scope,
                    requested_scope=args.requested_scope,
                    authority_grant=grant,
                ),
                args.json,
            )

        elif command == "rollback":
            emit(
                rollback(
                    store,
                    args.repo,
                    args.receipt_id,
                    authorized=args.authorize,
                ),
                args.json,
            )

        elif command == "outcome":
            if not store.repo(args.repo):
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            governance = governor.evaluate(args.repo)
            cue_proposals = []
            for raw_cue in args.aria_cue:
                if "=" not in raw_cue:
                    raise ValueError("--aria-cue must use PURPOSE=PHRASE")
                purpose, phrase = raw_cue.split("=", 1)
                cue_proposals.append(
                    {"purpose": purpose.strip(), "phrase": phrase.strip()}
                )
            emit(record_outcome(
                store, args.repo, args.activation_id, status=args.status,
                verification_type=args.verification, reward=args.reward,
                verification_payload={
                    "aria_cue_reviewed": args.aria_cue_reviewed,
                    "aria_cue_proposals": cue_proposals,
                },
                governance_mode=governance["mode"],
            ), args.json)

        elif command == "environment":
            emit(environment_summary(store.environment_profile(args.repo)), args.json)

        elif command == "meta-language":
            repository = store.repo(args.repo)
            if not repository:
                raise ValueError(
                    f"Unknown repository: {args.repo}. Run cortex bootstrap first."
                )
            profile = store.environment_profile(args.repo) or {}
            descriptor = profile.get(
                    "meta_language",
                    {
                        "available": False,
                        "cortex_implementation_language": "python",
                        "role": "optional_meta_language",
                    },
                )
            runtime_fluency = aria_runtime_status(store, args.repo, args.task)
            if args.corpus:
                runtime_fluency["evaluation"] = evaluate_aria_corpus(
                    load_aria_corpus(args.corpus),
                    runtime_fluency["learned_profile"]["cues"],
                )
            emit(
                {
                    **descriptor,
                    "runtime_fluency": runtime_fluency,
                },
                args.json,
            )

        elif command == "thalamus":
            repository = store.repo(args.repo)
            if not repository:
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            emit(route(make_request(repository, args.task, args.budget)).to_dict(), args.json)

        elif command == "thalamus-feedback":
            if not store.repo(args.repo):
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            emit(record_feedback(store, args.repo, args.memory_id, args.outcome), args.json)

        elif command == "interlink":
            root = _repo_root(store, args.repo)
            config = load_repo_config(root)
            repository = store.repo(args.repo)
            hits = query(store, args.repo, args.task, args.limit, config.semantic_scan_limit)
            if config.thalamus_enabled and repository:
                plan = route(make_request(repository, args.task, config.context_budget))
                hits = apply_feedback(store, args.repo, hits)
                hits = inhibit(
                    hits, plan.lane_weights, min_lane_relevance=config.thalamus_min_lane_relevance
                )
            governance = governor.evaluate(args.repo)
            packet = activate_interlink(
                store,
                args.repo,
                args.task,
                hits,
                max_depth=config.neural_activation_depth,
                max_nodes=config.neural_max_nodes,
                learning_rate=config.neural_learning_rate,
                plasticity_enabled=args.learn and config.neural_plasticity_enabled,
                governance_mode=governance["mode"],
            )
            emit(packet.to_dict(), args.json)

        elif command == "neural-replay":
            emit(
                [
                    {
                        "sequence": row["sequence"],
                        "event_type": row["event_type"],
                        "entity_id": row["entity_id"],
                        "payload": json.loads(row["payload"] or "{}"),
                        "created_at": row["created_at"],
                        "previous_hash": row["previous_hash"],
                        "event_hash": row["event_hash"],
                    }
                    for row in reversed(store.neural_events(args.repo, args.limit))
                ],
                args.json,
            )

        elif command == "focus":
            emit(begin_session(home, store, args.repo, args.task, args.files), args.json)

        elif command == "remember":
            emit(
                remember(
                    home,
                    store,
                    args.repo,
                    args.kind,
                    args.text,
                    args.session,
                    token_id=getattr(args, "token", None),
                    agent_id=getattr(args, "agent_id", None),
                ),
                args.json,
            )

        elif command == "consolidate":
            emit(consolidate(home, store, args.repo, args.session), args.json)

        elif command == "ritual":
            memories = [
                {"kind": args.remember_kind, "text": text}
                for text in (args.remember_text or [])
                if str(text).strip()
            ]
            emit(
                run_session_ritual(
                    home,
                    store,
                    governor,
                    args.repo,
                    args.task,
                    budget=args.budget,
                    memories=memories,
                    consolidate_session=not args.no_consolidate,
                    profile=args.profile,
                    force=args.force,
                    contract=getattr(args, "contract", "default"),
                ),
                args.json,
            )

        elif command == "verify":
            root = _repo_root(store, args.repo)
            config = load_repo_config(root)
            emit(verify_repository(home, store, args.repo, config, write_certificate=True), args.json)

        elif command == "graph":
            if args.rebuild:
                result: Any = resolve_graph(store, args.repo)
            elif args.path:
                result = neighborhood(store, args.repo, [args.path], limit=100)
            else:
                edges = store.edges(args.repo, limit=100_000)
                counts: dict[str, int] = {}
                for edge in edges:
                    counts[edge["relation"]] = counts.get(edge["relation"], 0) + 1
                result = {
                    "repo": args.repo,
                    "files": len(store.files(args.repo)),
                    "symbols": len(store.symbols(args.repo)),
                    "edges": len(edges),
                    "relation_counts": counts,
                }
            emit(result, args.json)

        elif command == "telemetry":
            root = _repo_root(store, args.repo)
            config = load_repo_config(root)
            emit(ingest_git(store, args.repo, root, config.git_commit_limit), args.json)

        elif command == "status":
            if args.repo:
                repository = store.repo(args.repo)
                latest = store.latest_bootstrap(args.repo)
                result = {
                    "home": str(home),
                    "repository": dict(repository) if repository else None,
                    "governor": governor.evaluate(args.repo),
                    "latest_bootstrap": dict(latest) if latest else None,
                    "files": len(store.files(args.repo)) if repository else 0,
                    "symbols": len(store.symbols(args.repo)) if repository else 0,
                    "edges": len(store.edges(args.repo, limit=100_000)) if repository else 0,
                    "environment": environment_summary(store.environment_profile(args.repo)) if repository else {"available": False},
                    "neural_interlink": neural_graph_state(store, args.repo) if repository else None,
                }
            else:
                result = {
                    "home": str(home),
                    "database_integrity": store.integrity_check(),
                    "repositories": [dict(row) for row in store.repos()],
                }
            emit(result, args.json)

        elif command == "doctor":
            sqlite_version = store.db.execute("SELECT sqlite_version()").fetchone()[0]
            fts = bool(store.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories_fts'"
            ).fetchone())
            result = {
                "python": sys.version,
                "sqlite": sqlite_version,
                "fts5_available": fts,
                "database_integrity": store.integrity_check(),
                "home_writable": home.exists() and home.is_dir(),
            }
            if args.repo:
                repository = store.repo(args.repo)
                result["repository"] = dict(repository) if repository else None
                result["governor"] = governor.evaluate(args.repo)
                result["environment"] = environment_summary(store.environment_profile(args.repo))
                result["neural_interlink"] = neural_graph_state(store, args.repo) if repository else None
                result["neural_ledger_integrity"] = store.verify_neural_ledger(args.repo) if repository else False
                result["vector_format"] = store.vector_format_status(args.repo) if repository else None
                if result["vector_format"] and result["vector_format"]["legacy_or_invalid"]:
                    result["vector_migration_recommendation"] = f"cortex migrate-vectors --repo {args.repo} --json"
                if repository:
                    gate = inspect_immune(home, store, governor, args.repo)
                    result["read_first"] = True
                    result["block"] = gate.get("block")
                    result["immune_action"] = gate.get("immune_action")
                    result["control_error"] = gate.get("control_error")
                    result["immune"] = f"cortex immune --repo {args.repo} --json"
            emit(result, args.json)

        elif command == "health":
            emit(health_report(home, store, governor, args.repo), args.json)

        elif command == "lifecycle":
            governance = governor.evaluate(args.repo)
            if args.apply:
                result = apply_lifecycle(
                    store,
                    args.repo,
                    governance_mode=governance["mode"],
                    authorized=True,
                    grace_hours=args.grace_hours,
                    decay_per_day=args.decay_per_day,
                )
            else:
                result = lifecycle_plan(
                    store,
                    args.repo,
                    grace_hours=args.grace_hours,
                    decay_per_day=args.decay_per_day,
                )
                result["applied"] = False
            emit(result, args.json)

        elif command == "evaluate":
            corpus_path = Path(args.corpus).expanduser().resolve()
            corpus = load_corpus(corpus_path)
            if args.mode == "retrieval":
                emit(
                    evaluate_retrieval_corpus(
                        store, corpus, default_repo=args.repo
                    ),
                    args.json,
                )
            else:
                emit(
                    evaluate_corpus(
                        store,
                        corpus,
                        default_repo=args.repo,
                    ),
                    args.json,
                )

        elif command == "transcend-check":
            emit(
                run_transcend_check(
                    root=Path(args.path).expanduser().resolve(),
                    run_mirror_glow=not args.skip_mirror,
                ),
                args.json,
            )

        elif command == "teach":
            if args.seed:
                from .teach_seed import seed_into_home

                emit(
                    seed_into_home(
                        home=home,
                        root=Path(args.path).expanduser().resolve(),
                        repo_name=args.repo,
                        force_bootstrap=args.force_bootstrap,
                    ),
                    args.json,
                )
            else:
                root = Path(__file__).resolve().parents[1]
                transcend_doc = root / "docs" / "TRANSCEND.md"
                bright_doc = root / "docs" / "BRIGHT_POINT.md"
                organism_doc = root / "docs" / "ORGANISM.md"
                interconnect_doc = root / "docs" / "intelligence" / "INTERCONNECT.md"
                text = ""
                for doc in (organism_doc, interconnect_doc, transcend_doc, bright_doc):
                    if doc.is_file():
                        text += ("\n\n---\n\n" if text else "") + doc.read_text(
                            encoding="utf-8"
                        )
                payload = {
                    "schema_version": "cortex-teach/1.2",
                    "glyph": "☰",
                    "install": [
                        "pip install -e .",
                        "python -m cortex init --json",
                        "python -m cortex bootstrap . --name Cortex --json",
                        "python -m cortex teach --seed --path . --repo Cortex --json",
                        "python -m cortex immune --repo Cortex --json",
                        'python -m cortex organism --repo Cortex --task "interconnect" --json',
                        "python -m cortex metrics --repo Cortex --json",
                        'python -m cortex activate --repo Cortex --task "<task>" --profile agent --json',
                        'python -m cortex ritual --repo Cortex --task "<task>" --remember-text "<fact>" --json',
                        "python -m cortex transcend-check --json",
                    ],
                    "progress_glyphs": progress_glyph_registry(),
                    "memory_packets": "examples/memory-packets/*.packet.json",
                    "markdown": text,
                    "claim_boundary": "Teaching surface only; never mutation authority.",
                }
                if args.json:
                    emit(payload, True)
                else:
                    print(text)
                    print("\n## Install + seed intelligence\n")
                    for line in payload["install"]:
                        print(f"- `{line}`")
                    print("\n## Progress glyphs (ARIA labels, not execution)\n")
                    for key, glyph in progress_glyph_registry()["glyphs"].items():
                        print(
                            f"- {glyph['symbol']}  {glyph['spoken']} → `{glyph['maps_to']}`"
                        )

        elif command == "organism":
            result = activate_repository(
                home,
                store,
                governor,
                args.repo,
                args.task,
                budget=args.budget,
                profile=args.profile,
            )
            emit(
                {
                    "schema_version": "cortex-organism-command/1.0",
                    "activation": result.get("activation"),
                    "session": result.get("session"),
                    "organism": result.get("organism"),
                    "control_error": result.get("control_error"),
                    "context": result.get("context"),
                    "claim_boundary": (
                        "Organism command exposes session co-process state; "
                        "not consciousness or mutation authority."
                    ),
                },
                args.json,
            )

        elif command == "breathe":
            from .organism import breathe as organism_breathe

            emit(
                organism_breathe(
                    home,
                    store,
                    governor,
                    args.repo,
                    args.task,
                    budget=args.budget,
                    profile=args.profile,
                ),
                args.json,
            )

        elif command == "immune":
            emit(inspect_immune(home, store, governor, args.repo), args.json)

        elif command == "metrics":
            emit(metric_graph_report(store, args.repo), args.json)

        elif command == "vectors":
            from .vectors import build_hnsw_index, hnsw_status, query_hnsw

            if args.action == "build":
                emit(build_hnsw_index(store, args.repo), args.json)
            elif args.action == "status":
                emit(hnsw_status(store, args.repo), args.json)
            else:
                if not args.text:
                    raise ValueError("--text required for vectors query")
                emit(
                    {
                        "repo": args.repo,
                        "hits": query_hnsw(store, args.repo, args.text, k=args.k),
                        "claim_boundary": "HNSW query is evidence retrieval only.",
                    },
                    args.json,
                )

        elif command == "ranker":
            from .ranker.model import (
                promote_ranker_snapshot,
                ranker_status,
                rollback_ranker_snapshot,
                unfreeze_ranker,
            )

            if args.action == "promote":
                emit(
                    promote_ranker_snapshot(
                        store,
                        args.repo,
                        promotion_authorized=bool(args.authorize_promote),
                    ),
                    args.json,
                )
            elif args.action == "rollback":
                emit(rollback_ranker_snapshot(store, args.repo), args.json)
            elif args.action == "unfreeze":
                emit(unfreeze_ranker(store, args.repo), args.json)
            else:
                emit(ranker_status(store, args.repo), args.json)

        elif command == "kernels":
            from .kernels import annotate_synapses, kernels_status

            if args.annotate:
                annotate_synapses(store, args.repo)
            emit(kernels_status(store, args.repo), args.json)

        elif command == "identity":
            from .identity import continuity_check

            if not args.repo and not args.path:
                raise ValueError("Pass --repo and/or --path")
            emit(
                continuity_check(
                    store,
                    repo=args.repo,
                    path=args.path,
                    cortex_home=home,
                ),
                args.json,
            )

        elif command == "distill":
            if args.doctrine_only:
                from .distill_intel import DOCTRINE_CLAIMS, observe_lattice

                obs = observe_lattice(store, args.repo, governor=governor, home=home)
                memories = [
                    {"kind": "focus", "text": "☰ Distill doctrine-only"},
                    *DOCTRINE_CLAIMS,
                ]
                ritual = run_session_ritual(
                    home,
                    store,
                    governor,
                    args.repo,
                    "Distill doctrine only",
                    memories=memories,
                    consolidate_session=not args.no_seal,
                    force=True,
                )
                emit(
                    {
                        "schema_version": "cortex-distill-intel/1.0",
                        "mode": "doctrine_only",
                        "observation": obs,
                        "ritual": ritual.get("consolidate"),
                        "gates_sealed": ritual.get("gates_sealed"),
                    },
                    args.json,
                )
            else:
                emit(
                    distill_intelligence(
                        home,
                        store,
                        governor,
                        args.repo,
                        seal=not args.no_seal,
                        include_doctrine=True,
                        force=True,
                    ),
                    args.json,
                )

        elif command == "predict":
            from .predict import predict_context

            gov = governor.evaluate(args.repo)
            emit(
                predict_context(
                    store,
                    args.repo,
                    args.task,
                    budget=args.budget,
                    governor_mode=str(gov.get("mode") or "normal"),
                ),
                args.json,
            )

        elif command == "contract":
            from .contract.check import (
                DEFAULT_CONTRACT,
                STRICT_CONTRACT,
                check_contract,
                contract_diff,
            )

            profile = STRICT_CONTRACT if args.profile == "strict" else DEFAULT_CONTRACT
            if args.action == "check":
                if not args.packet_id:
                    raise ValueError("--packet-id required")
                # Find packet across repos by id
                row = store.db.execute(
                    "SELECT * FROM continuation_packets WHERE packet_id=?",
                    (args.packet_id,),
                ).fetchone()
                if not row:
                    raise ValueError(f"Unknown packet: {args.packet_id}")
                payload = json.loads(row["payload_json"])
                emit(
                    check_contract(
                        payload,
                        contract=profile,
                        store=store,
                        repo=row["repo"],
                        persist=True,
                    ),
                    args.json,
                )
            else:
                if not args.from_packet or not args.to_packet:
                    raise ValueError("--from-packet and --to-packet required")
                ra = store.db.execute(
                    "SELECT payload_json FROM continuation_packets WHERE packet_id=?",
                    (args.from_packet,),
                ).fetchone()
                rb = store.db.execute(
                    "SELECT payload_json FROM continuation_packets WHERE packet_id=?",
                    (args.to_packet,),
                ).fetchone()
                pa = json.loads(ra["payload_json"]) if ra else {}
                pb = json.loads(rb["payload_json"]) if rb else {}
                emit(contract_diff(pa, pb), args.json)

        elif command == "agent":
            from .agents import register_agent
            from .agents.tokens import multi_agent_enabled, set_multi_agent_mode

            if args.action == "register":
                if not args.agent_id or not args.name:
                    raise ValueError("--agent-id and --name required")
                emit(
                    register_agent(store, args.repo, args.agent_id, args.name),
                    args.json,
                )
            elif args.action == "mode":
                if args.on and args.off:
                    raise ValueError("Pass only --on or --off")
                if not args.on and not args.off:
                    emit(
                        {
                            "repo": args.repo,
                            "multi_agent": multi_agent_enabled(store, args.repo),
                            "claim_boundary": "Mode query only.",
                        },
                        args.json,
                    )
                else:
                    emit(
                        set_multi_agent_mode(store, args.repo, enabled=bool(args.on)),
                        args.json,
                    )
            else:
                rows = store.db.execute(
                    "SELECT agent_id, display_name, created_at FROM agent_principals WHERE repo=?",
                    (args.repo,),
                ).fetchall()
                emit(
                    {
                        "repo": args.repo,
                        "agents": [dict(r) for r in rows],
                        "multi_agent": multi_agent_enabled(store, args.repo),
                        "claim_boundary": "Agent list is local identity only.",
                    },
                    args.json,
                )

        elif command == "token":
            from .agents import mint_token, revoke_token, validate_token

            if args.action == "mint":
                if not args.agent_id:
                    raise ValueError("--agent-id required")
                emit(
                    mint_token(
                        store,
                        args.repo,
                        args.agent_id,
                        args.scope or ["memory.read", "memory.remember"],
                        ttl_seconds=args.ttl,
                    ),
                    args.json,
                )
            elif args.action == "revoke":
                if not args.token_id:
                    raise ValueError("--token-id required")
                emit(revoke_token(store, args.repo, args.token_id), args.json)
            else:
                if not args.token_id:
                    raise ValueError("--token-id required")
                emit(validate_token(store, args.repo, args.token_id), args.json)

        elif command == "glyphs":
            if args.phrase:
                emit(phrase(args.phrase), args.json)
            elif args.phrasebook:
                emit(phrasebook(), args.json)
            else:
                reg = glyph_canon_registry(optimized=not args.full)
                reg["phrasebook_keys"] = list(phrasebook().get("phrases") or {})
                emit(reg, args.json)

        elif command == "harness":
            from .signal_harness import run_signal_harness

            emit(
                run_signal_harness(
                    home,
                    store,
                    governor,
                    args.repo,
                    budget=max(200, int(args.budget or 500)),
                    k=max(2, int(args.k or 6)),
                ),
                args.json,
            )

        elif command == "hygiene":
            from .hygiene import body_hygiene

            config = None
            try:
                row = store.repo(args.repo)
                if row:
                    config = load_repo_config(Path(row["path"]))
            except Exception:
                config = None
            emit(body_hygiene(home, store, args.repo, config=config), args.json)

        elif command == "stream":
            from .stream import seal_session_bond, stream_status

            if args.action == "seal":
                emit(
                    seal_session_bond(
                        store,
                        args.repo,
                        session_id=args.session_id,
                        reason="cli_seal",
                    ),
                    args.json,
                )
            else:
                emit(stream_status(store, args.repo), args.json)

        elif command == "evolve":
            governance = governor.evaluate(args.repo)
            emit(
                close_signal_loop(
                    store,
                    args.repo,
                    activation_id=args.activation_id,
                    status=args.status,
                    verification_type=args.verification,
                    task=args.task,
                    reward=args.reward,
                    governance_mode=governance.get("mode") or "read_only",
                    probe_k=max(1, int(args.k or 8)),
                ),
                args.json,
            )

        elif command == "causal":
            from .causal import (
                causal_report,
                evaluate_causal_episode,
                open_episode,
                probe_recall,
            )

            if args.action == "report" or args.action == "status":
                emit(causal_report(store, args.repo), args.json)
            elif args.action == "probe":
                if not args.task:
                    raise ValueError("--task is required for causal probe")
                emit(
                    probe_recall(
                        store,
                        args.repo,
                        args.task,
                        k=max(1, int(args.k or 8)),
                        slot=args.slot or "before",
                    ),
                    args.json,
                )
            else:
                # evaluate: use open episode + optional probe slots / explicit floats
                opened = store.get_setting(f"causal_open:{args.repo}", None)
                if not isinstance(opened, dict) or opened.get("closed"):
                    open_episode(store, args.repo, "cli_evaluate")
                emit(
                    evaluate_causal_episode(
                        store,
                        args.repo,
                        recall_before=args.recall_before,
                        recall_after=args.recall_after,
                    ),
                    args.json,
                )

        elif command == "compile-interlink":
            from .neuron import compile_interlink

            res = tuple(
                r.strip() for r in str(args.resolutions).split(",") if r.strip()
            )
            emit(compile_interlink(store, args.repo, resolutions=res or ("file", "symbol")), args.json)

        elif command == "interconnect":
            emit(mesh_status(store, args.repo, governor=governor, home=home), args.json)

        elif command == "prune":
            from .prune import decay_unused_weights, prune_graph

            result = prune_graph(
                store,
                args.repo,
                min_weight=args.min_weight,
                dry_run=args.dry_run,
            )
            if args.decay and not args.dry_run:
                result["decay"] = decay_unused_weights(store, args.repo)
            emit(result, args.json)

        elif command == "dashboard":
            if getattr(args, "mesh", False):
                from .interconnect import mesh_dashboard

                emit(
                    mesh_dashboard(store, args.repo, governor=governor, home=home),
                    args.json,
                )
                return
            repository = store.repo(args.repo)
            if not repository:
                raise ValueError(f"Unknown repository: {args.repo}. Run cortex bootstrap first.")
            lifecycle = lifecycle_plan(store, args.repo)
            from .aria_meta.substrate import ARIA_SUBSTRATE_DEFERRED_STATUS, is_internal_aria_path

            files = store.files(args.repo)
            deferred = sum(1 for row in files if row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS)
            aria_indexed = sum(
                1
                for row in files
                if row["status"] == "indexed" and is_internal_aria_path(row["path"])
            )
            emit(
                {
                    "schema_version": "cortex-dashboard/1.1",
                    "version": __version__,
                    "repository": dict(repository),
                    "database_integrity": store.integrity_check(),
                    "governor": governor.evaluate(args.repo),
                    "covenant": {
                        "doc": "docs/COVENANT.md",
                        "geometry_release": "3.2.0-aligned",
                        "axes": [
                            "authority",
                            "evidence",
                            "activation",
                            "language",
                            "economics",
                        ],
                    },
                    "inventory": {
                        "files": len(files),
                        "memories": store.db.execute(
                            "SELECT COUNT(*) FROM memories WHERE repo=?", (args.repo,)
                        ).fetchone()[0],
                        "nodes": len(store.neural_nodes(args.repo)),
                        "synapses": len(store.neural_synapses(args.repo)),
                    },
                    "aria_substrate": {
                        "deferred_remaining": deferred,
                        "indexed": aria_indexed,
                        "indexing_mode_default": "deferred",
                    },
                    "learning": {
                        "activations": len(store.neural_activations(args.repo, 10_000)),
                        "outcomes": len(store.outcomes(args.repo, 10_000)),
                        "ledger_valid": store.verify_neural_ledger(args.repo),
                    },
                    "continuation": {
                        "packets": len(store.continuation_packets(args.repo, 10_000)),
                        "canonical_states": len(store.canonical_states(args.repo)),
                        "receipts": len(store.continuation_receipts(args.repo, 10_000)),
                        "receipt_ledger_valid": store.verify_continuation_receipts(args.repo),
                    },
                    "lifecycle": {
                        key: value for key, value in lifecycle.items() if key != "proposals"
                    },
                    "agent_access": {
                        "context_protocol": "cortex-context/1.0",
                        "continuation_protocol": "cortex-continuation/1.0",
                        "federation_protocol": "cortex-federation/1.0",
                        "mirror_command": "cortex mirror --json",
                        "mcp_command": "cortex-mcp",
                    },
                    "claim_boundary": (
                        "Dashboard is local operational telemetry; it grants no mutation authority."
                    ),
                },
                args.json,
            )

        elif command == "benchmark":
            result = verify_benchmarks(Path(__file__).resolve().parents[1])
            emit(result, args.json)
            if args.verify and result["status"] != "pass":
                raise RuntimeError("Cortex benchmark threshold regression")

        elif command == "self-test":
            emit(run_self_test(run_tests=not args.skip_tests), args.json)

        elif command == "mirror":
            # Isolated home so mirror stress never mutates the operator's live DB.
            import tempfile

            mirror_home = ensure_home(Path(tempfile.mkdtemp(prefix="cortex-mirror-")) / "home")
            mirror_store = Store(mirror_home / "cortex.db")
            try:
                emit(
                    run_mirror(
                        mirror_home,
                        mirror_store,
                        root=Path(args.path).expanduser().resolve(),
                        repo_name=args.name,
                    ),
                    args.json,
                )
            finally:
                mirror_store.close()

        elif command == "contact":
            import tempfile

            contact_home = ensure_home(
                Path(tempfile.mkdtemp(prefix="cortex-contact-")) / "home"
            )
            contact_store = Store(contact_home / "cortex.db")
            try:
                emit(
                    run_contact(
                        contact_home,
                        contact_store,
                        root=Path(args.path).expanduser().resolve(),
                        include_foreign=not args.skip_foreign,
                    ),
                    args.json,
                )
            finally:
                contact_store.close()

    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        error = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if getattr(args, "json", False):
            print(json.dumps(error, indent=2), file=sys.stderr)
        else:
            print(error["error"], file=sys.stderr)
        raise SystemExit(2) from exc
    finally:
        store.close()
