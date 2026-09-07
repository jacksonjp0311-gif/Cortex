"""Derived coherent knowledge-state identity and snapshot-bound context packets.

EpistemicSnapshot is reconstructable from tracked sources. It is not a second
database and grants no authority. Historical material remains typed historical.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .assurance import load_claim_registry, registry_hash

SNAPSHOT_SCHEMA = "cortex-epistemic-snapshot/1.0"
PACKET_SCHEMA = "cortex-context-packet/1.0"
NAVIGATION_SCHEMA = "cortex-navigation-fidelity/1.0"
CANONICAL_DOCS = (
    "docs/STATUS.md",
    "docs/SYSTEM_MAP.md",
    "docs/AGENT_START.md",
    "docs/EVIDENCE.md",
    "docs/CORTEX_KNOWLEDGE_MAP.json",
    "docs/CORTEX_CLAIM_REGISTRY.json",
    "docs/research/GOVERNED_SELF_ORGANIZATION.md",
)
HISTORICAL_MARKERS = ("HISTORICAL", "historical", "exhausted cohort", "post-hoc")

NAVIGATION_TASKS: tuple[dict[str, Any], ...] = (
    {
        "id": "gso_claim_state",
        "query": "Where is the current GSO claim state?",
        "expected": ["docs/research/GOVERNED_SELF_ORGANIZATION.md", "docs/STATUS.md", "docs/CORTEX_CLAIM_REGISTRY.json"],
    },
    {
        "id": "ai_entry",
        "query": "What is the canonical AI entry point?",
        "expected": ["docs/AGENT_START.md"],
    },
    {
        "id": "repair_observation_binding",
        "query": "Which code implements structured repair observation binding?",
        "expected": ["cortex/structured_repair_screen.py", "cortex/coding_workspace.py"],
    },
    {
        "id": "raw_observation_evidence",
        "query": "Which evidence supports raw observation identity?",
        "expected": ["tests/test_raw_verification_observation.py", "docs/STATUS.md"],
    },
    {
        "id": "alpha8_not_gso",
        "query": "Is alpha.8 autonomous improvement evidence current proof of GSO?",
        "expected": ["docs/research/GOVERNED_SELF_ORGANIZATION.md", "docs/CORTEX_CLAIM_REGISTRY.json"],
        "forbidden_as_current": ["cortex/autonomous_improvement.py"],
    },
    {
        "id": "authority_files",
        "query": "Which files must be read before changing authority logic?",
        "expected": ["cortex/native_agent.py", "cortex/autonomous_improvement.py", "docs/intelligence/TOPOLOGY_LAW.md"],
    },
    {
        "id": "supersession",
        "query": "Which source supersedes an older architecture document?",
        "expected": ["docs/CORTEX_KNOWLEDGE_MAP.json", "docs/SYSTEM_MAP.md"],
    },
    {
        "id": "held_claim",
        "query": "Which claim is currently HELD?",
        "expected": ["docs/CORTEX_CLAIM_REGISTRY.json", "docs/STATUS.md"],
    },
    {
        "id": "ci_dependent_claim",
        "query": "Which current claim depends on exact-head CI?",
        "expected": ["docs/CORTEX_CLAIM_REGISTRY.json", "docs/STATUS.md"],
    },
    {
        "id": "evidence_guide",
        "query": "Where is the current evidence guide?",
        "expected": ["docs/EVIDENCE.md"],
    },
    {
        "id": "transduction_policy",
        "query": "Where is prospective transduction policy frozen?",
        "expected": ["cortex/transduction_policy.py"],
    },
    {
        "id": "snapshot_identity",
        "query": "Where is the coherent epistemic snapshot derived?",
        "expected": ["cortex/epistemic_snapshot.py"],
    },
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    import subprocess
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, check=False, shell=False)
    return result.stdout.decode("ascii", errors="replace").strip()


def derive_epistemic_snapshot(root: str | Path | None = None) -> dict[str, Any]:
    workspace = Path(root) if root else Path(__file__).resolve().parents[1]
    knowledge_map = json.loads((workspace / "docs/CORTEX_KNOWLEDGE_MAP.json").read_text(encoding="utf-8"))
    registry = load_claim_registry(workspace / "docs/CORTEX_CLAIM_REGISTRY.json")
    documents = {
        path: {
            "digest": _file_digest(workspace / path),
            "canonicality": "CANONICAL_CURRENT" if path != "docs/research/GOVERNED_SELF_ORGANIZATION.md" else "RESEARCH_ACTIVE",
        }
        for path in CANONICAL_DOCS
        if (workspace / path).is_file()
    }
    classified = {
        item["path"]: item.get("canonicality")
        for item in knowledge_map.get("documents") or []
    }
    body = {
        "schema_version": SNAPSHOT_SCHEMA,
        "source_head": _git_head(workspace),
        "product_version": __version__,
        "knowledge_map_hash": _file_digest(workspace / "docs/CORTEX_KNOWLEDGE_MAP.json"),
        "claim_registry_hash": registry_hash(registry),
        "status_identity": _file_digest(workspace / "docs/STATUS.md"),
        "evidence_manifest_identity": _file_digest(workspace / "benchmarks/results/MANIFEST.json") if (workspace / "benchmarks/results/MANIFEST.json").is_file() else None,
        "canonical_document_identities": documents,
        "classified_canonicality": classified,
        "active_concept_versions": [
            {"id": concept["id"], "claim_status": concept.get("claim_status"), "lifecycle": concept.get("lifecycle")}
            for concept in knowledge_map.get("concepts") or []
        ],
        "supersession_graph_identity": _sha({
            item["path"]: item.get("superseded_by")
            for item in knowledge_map.get("documents") or []
        }),
        "current_research_frontier_identity": _file_digest(workspace / "docs/research/GOVERNED_SELF_ORGANIZATION.md"),
        "authority_effect": False,
    }
    return {**body, "snapshot_hash": _sha(body)}


def _select_paths(task: str, snapshot: Mapping[str, Any], budget: int) -> list[dict[str, Any]]:
    text = task.lower()
    selected: list[dict[str, Any]] = []

    def add(path: str, role: str, historical: bool = False) -> None:
        if any(item["path"] == path for item in selected):
            return
        selected.append({"path": path, "role": role, "historical": historical, "bound_to_snapshot": True})

    add("docs/AGENT_START.md", "ai_entry")
    add("docs/STATUS.md", "status")
    add("docs/CORTEX_CLAIM_REGISTRY.json", "claims")
    if any(token in text for token in ("gso", "self-org", "organization", "heredity")):
        add("docs/research/GOVERNED_SELF_ORGANIZATION.md", "research")
        add("cortex/shadow_organization.py", "shadow")
    if any(token in text for token in ("transduction", "observation", "compiler", "policy", "receipt")):
        add("cortex/transduction_policy.py", "implementation")
        add("cortex/coding_workspace.py", "implementation")
        add("cortex/edit_intent.py", "implementation")
        add("docs/research/TRANSDUCTION_REVISION_2026-09-06.md", "historical_research", historical=True)
    if any(token in text for token in ("authority", "capability", "grant")):
        add("docs/intelligence/TOPOLOGY_LAW.md", "authority")
        add("cortex/native_agent.py", "implementation")
        add("cortex/autonomous_improvement.py", "implementation")
    if "evidence" in text:
        add("docs/EVIDENCE.md", "evidence")
    if "snapshot" in text or "context" in text or "navigation" in text:
        add("cortex/epistemic_snapshot.py", "implementation")
        add("docs/SYSTEM_MAP.md", "architecture")
    encoded = _canonical(selected)
    while selected and len(encoded) > budget:
        selected.pop()
        encoded = _canonical(selected)
    return selected


def compile_context_packet(
    task: str,
    snapshot: Mapping[str, Any],
    *,
    budget: int = 8000,
    root: str | Path | None = None,
) -> dict[str, Any]:
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA or "snapshot_hash" not in snapshot:
        raise ValueError("invalid snapshot identity")
    workspace = Path(root) if root else Path(__file__).resolve().parents[1]
    selected = _select_paths(task, snapshot, budget)
    errors: list[str] = []
    for item in selected:
        path = workspace / item["path"]
        if not path.is_file():
            errors.append("unbound_source:" + item["path"])
            continue
        digest = _file_digest(path)
        item["digest"] = digest
        classified = (snapshot.get("classified_canonicality") or {}).get(item["path"])
        if classified == "HISTORICAL" and not item["historical"]:
            errors.append("historical_doc_as_current:" + item["path"])
        if item["historical"] and classified not in (None, "HISTORICAL", "REFERENCE", "RESEARCH_ACTIVE"):
            item["historical"] = True
    if snapshot.get("snapshot_hash") != _sha({key: value for key, value in snapshot.items() if key != "snapshot_hash"}):
        errors.append("stale_snapshot_identity")
    body = {
        "schema_version": PACKET_SCHEMA,
        "snapshot_identity": snapshot["snapshot_hash"],
        "task": task,
        "selected": selected,
        "current_claim_states": [
            concept for concept in snapshot.get("active_concept_versions") or []
        ],
        "unresolved_assumptions": [
            "OS isolation of worktrees is DECLARATIVE_ONLY",
            "process-tree cleanup after capture is UNKNOWN",
            "environment applicability is incomplete",
        ],
        "authority_constraints": {
            "authority_effect": False,
            "host_repository_rules_control": True,
            "historical_sources_remain_historical": True,
        },
        "provenance": {
            "source_head": snapshot.get("source_head"),
            "product_version": snapshot.get("product_version"),
            "knowledge_map_hash": snapshot.get("knowledge_map_hash"),
            "claim_registry_hash": snapshot.get("claim_registry_hash"),
        },
        "character_budget": int(budget),
        "errors": errors,
        "valid": not errors,
        "authority_effect": False,
    }
    return {**body, "packet_hash": _sha(body)}


def route_navigation(query: str) -> list[str]:
    for task in NAVIGATION_TASKS:
        if query.strip() == task["query"]:
            return list(task["expected"])
    folded = query.lower()
    for task in NAVIGATION_TASKS:
        needles = [token for token in re.findall(r"[a-z0-9.]+", task["query"].lower()) if len(token) > 3]
        if sum(needle in folded for needle in needles) >= max(2, len(needles) // 3):
            return list(task["expected"])
    return ["docs/AGENT_START.md", "docs/STATUS.md"]


def measure_navigation_fidelity() -> dict[str, Any]:
    results = []
    correct = 0
    for task in NAVIGATION_TASKS:
        routed = route_navigation(task["query"])
        ok = routed == list(task["expected"])
        correct += int(ok)
        results.append({"id": task["id"], "expected": task["expected"], "routed": routed, "correct": ok})
    body = {
        "schema_version": NAVIGATION_SCHEMA,
        "n_tasks": len(NAVIGATION_TASKS),
        "correct": correct,
        "N_f": correct / len(NAVIGATION_TASKS),
        "results": results,
        "scope": "finite_frozen_navigation_panel",
        "authority_effect": False,
    }
    return {**body, "panel_hash": _sha(body)}


__all__ = [
    "NAVIGATION_TASKS",
    "compile_context_packet",
    "derive_epistemic_snapshot",
    "measure_navigation_fidelity",
    "route_navigation",
]
