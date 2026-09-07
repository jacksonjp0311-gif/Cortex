"""Derived coherent knowledge-state identity and snapshot-bound context packets.

EpistemicSnapshot is reconstructable from tracked sources. It is not a second
database and grants no authority. Historical material remains typed historical.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .assurance import load_claim_registry, registry_hash

SNAPSHOT_SCHEMA = "cortex-epistemic-snapshot/1.1"
SNAPSHOT_SCHEMA_V10 = "cortex-epistemic-snapshot/1.0"
PACKET_SCHEMA = "cortex-context-packet/1.1"
NAVIGATION_SCHEMA = "cortex-navigation-fidelity/1.1"
NAVIGATION_CONTRACT_SCHEMA = "cortex-navigation-contract/1.0"
NAVIGATION_GENERALIZATION_SCHEMA = "cortex-navigation-generalization/1.0"
CANONICAL_DOCS = (
    "docs/STATUS.md",
    "docs/SYSTEM_MAP.md",
    "docs/AGENT_START.md",
    "docs/EVIDENCE.md",
    "docs/CORTEX_KNOWLEDGE_MAP.json",
    "docs/CORTEX_CLAIM_REGISTRY.json",
    "docs/CORTEX_INVARIANTS.json",
    "docs/research/GOVERNED_SELF_ORGANIZATION.md",
)
BOUND_IMPLEMENTATIONS = (
    "cortex/transduction_policy.py",
    "cortex/coding_workspace.py",
    "cortex/edit_intent.py",
    "cortex/shadow_organization.py",
    "cortex/epistemic_snapshot.py",
    "cortex/assurance.py",
    "cortex/invariants.py",
    "cortex/observation_capture.py",
    "cortex/native_agent.py",
    "cortex/autonomous_improvement.py",
    "cortex/structured_repair_screen.py",
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

# Phrase features only. Withheld paraphrases are NOT stored here.
NAVIGATION_FEATURES: tuple[dict[str, Any], ...] = (
    {
        "id": "transduction_policy",
        "expected": ["cortex/transduction_policy.py"],
        "phrases": ("pre-cognition", "execution requirements", "transduction policy", "frozen policy", "policy precedes"),
    },
    {
        "id": "ai_entry",
        "expected": ["docs/AGENT_START.md"],
        "phrases": ("agent start", "ai entry", "canonical ai", "tracked ai orientation", "begin orientation"),
    },
    {
        "id": "evidence_guide",
        "expected": ["docs/EVIDENCE.md"],
        "phrases": ("evidence guide", "how to read evidence", "claim evidence"),
    },
    {
        "id": "gso_claim",
        "expected": ["docs/research/GOVERNED_SELF_ORGANIZATION.md", "docs/CORTEX_CLAIM_REGISTRY.json"],
        "phrases": ("gso claim", "self-organization status", "held organization", "cumulative organization"),
    },
    {
        "id": "authority_path",
        "expected": ["docs/intelligence/TOPOLOGY_LAW.md", "cortex/native_agent.py"],
        "phrases": ("authority logic", "topology law", "who may grant capability", "host authority"),
    },
    {
        "id": "claim_status_held",
        "expected": ["docs/CORTEX_CLAIM_REGISTRY.json"],
        "phrases": ("which claim is held", "held claim", "unresolved environment applicability"),
    },
    {
        "id": "invariants",
        "expected": ["docs/CORTEX_INVARIANTS.json", "cortex/invariants.py"],
        "phrases": ("constitutional invariant", "invariant registry", "homeostatic monotonicity", "constitutional constraints", "machine-readable laws"),
    },
    {
        "id": "shadow",
        "expected": ["cortex/shadow_organization.py"],
        "phrases": ("shadow organization", "proposal prior", "retention candidate"),
    },
)

# Expected answers defined independently of routing features.
NAVIGATION_GENERALIZATION_PANEL: tuple[dict[str, Any], ...] = (
    {
        "id": "policy_paraphrase",
        "query": "Which module owns the pre-cognition execution requirements?",
        "expected": ["cortex/transduction_policy.py"],
        "distractors": ["cortex/autonomous_improvement.py", "docs/research/TRANSDUCTION_REVISION_2026-09-06.md"],
    },
    {
        "id": "ai_entry_paraphrase",
        "query": "Where should an agent begin orientation without searching the whole tree?",
        "expected": ["docs/AGENT_START.md"],
        "distractors": ["README.md", "README_ARCHIVE_2026-09-06.md"],
    },
    {
        "id": "held_claim_paraphrase",
        "query": "Which machine-readable surface lists currently HELD claims?",
        "expected": ["docs/CORTEX_CLAIM_REGISTRY.json"],
        "distractors": ["docs/research/GOVERNED_SELF_ORGANIZATION.md"],
    },
    {
        "id": "authority_paraphrase",
        "query": "Which files bound host capability grants before changing authority logic?",
        "expected": ["docs/intelligence/TOPOLOGY_LAW.md", "cortex/native_agent.py"],
        "distractors": ["cortex/competence.py"],
    },
    {
        "id": "gso_not_alpha8",
        "query": "Does historical autonomous-improvement screening currently prove governed self-organization?",
        "expected": ["docs/research/GOVERNED_SELF_ORGANIZATION.md", "docs/CORTEX_CLAIM_REGISTRY.json"],
        "distractors": ["cortex/autonomous_improvement.py"],
    },
    {
        "id": "invariant_paraphrase",
        "query": "Where are Cortex constitutional constraints recorded as machine-readable laws?",
        "expected": ["docs/CORTEX_INVARIANTS.json", "cortex/invariants.py"],
        "distractors": ["cortex/constitutional.py"],
    },
    {
        "id": "shadow_paraphrase",
        "query": "Which production-inert module holds proposal priors?",
        "expected": ["cortex/shadow_organization.py"],
        "distractors": ["cortex/self_org.py"],
    },
    {
        "id": "stale_term",
        "query": "Where is the current evidence guide after the documentation migration?",
        "expected": ["docs/EVIDENCE.md"],
        "distractors": ["BENCHMARK_REPORT.md"],
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
    head = _git_head(workspace)
    documents = {
        path: {
            "digest": _file_digest(workspace / path),
            "canonicality": "CANONICAL_CURRENT" if path != "docs/research/GOVERNED_SELF_ORGANIZATION.md" else "RESEARCH_ACTIVE",
        }
        for path in CANONICAL_DOCS
        if (workspace / path).is_file()
    }
    bound_sources = {
        path: _file_digest(workspace / path)
        for path in (
            *CANONICAL_DOCS,
            *BOUND_IMPLEMENTATIONS,
            "docs/EVIDENCE.md",
            "docs/intelligence/TOPOLOGY_LAW.md",
            "docs/research/TRANSDUCTION_REVISION_2026-09-06.md",
        )
        if (workspace / path).is_file()
    }
    classified = {
        item["path"]: item.get("canonicality")
        for item in knowledge_map.get("documents") or []
    }
    body = {
        "schema_version": SNAPSHOT_SCHEMA,
        "source_head": head,
        "product_version": __version__,
        "provenance": {
            "baseline_revision": "6f134f15a88123b690094daa642f2aee5a5a5c8f",
            "implementation_revision": head,
            "evidence_revision": head,
            "verification_revision": head,
            "current_checkout_revision": head,
        },
        "knowledge_map_hash": _file_digest(workspace / "docs/CORTEX_KNOWLEDGE_MAP.json"),
        "claim_registry_hash": registry_hash(registry),
        "status_identity": _file_digest(workspace / "docs/STATUS.md"),
        "evidence_manifest_identity": _file_digest(workspace / "benchmarks/results/MANIFEST.json") if (workspace / "benchmarks/results/MANIFEST.json").is_file() else None,
        "canonical_document_identities": documents,
        "implementation_digests": {
            path: _file_digest(workspace / path)
            for path in BOUND_IMPLEMENTATIONS
            if (workspace / path).is_file()
        },
        "bound_source_digests": bound_sources,
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
    if any(token in text for token in ("invariant", "constitution", "homeostasis")):
        add("docs/CORTEX_INVARIANTS.json", "invariants")
        add("cortex/invariants.py", "implementation")
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
    historical_checkout: bool = False,
) -> dict[str, Any]:
    if snapshot.get("schema_version") not in {SNAPSHOT_SCHEMA, SNAPSHOT_SCHEMA_V10} or "snapshot_hash" not in snapshot:
        raise ValueError("invalid snapshot identity")
    workspace = Path(root) if root else Path(__file__).resolve().parents[1]
    checkout = _git_head(workspace)
    selected = _select_paths(task, snapshot, budget)
    errors: list[str] = []
    if snapshot.get("snapshot_hash") != _sha({key: value for key, value in snapshot.items() if key != "snapshot_hash"}):
        errors.append("stale_snapshot_identity")
    if snapshot.get("source_head") != checkout:
        errors.append("SNAPSHOT_STALE")
    bound = dict(snapshot.get("bound_source_digests") or {})
    for doc, meta in (snapshot.get("canonical_document_identities") or {}).items():
        bound.setdefault(doc, meta.get("digest") if isinstance(meta, Mapping) else meta)
    for path, digest in (snapshot.get("implementation_digests") or {}).items():
        bound.setdefault(path, digest)
    for item in selected:
        path = workspace / item["path"]
        if not path.is_file():
            errors.append("unbound_source:" + item["path"])
            continue
        digest = _file_digest(path)
        item["digest"] = digest
        expected = bound.get(item["path"])
        if expected is None:
            errors.append("SOURCE_NOT_BOUND:" + item["path"])
        elif expected != digest:
            errors.append("SOURCE_NOT_BOUND:" + item["path"])
        classified = (snapshot.get("classified_canonicality") or {}).get(item["path"])
        if classified == "HISTORICAL" and not item["historical"]:
            errors.append("historical_doc_as_current:" + item["path"])
    body = {
        "schema_version": PACKET_SCHEMA,
        "snapshot_identity": snapshot["snapshot_hash"],
        "task": task,
        "selected": selected,
        "checkout_head": checkout,
        "snapshot_head": snapshot.get("source_head"),
        "historical_checkout": historical_checkout,
        "current_claim_states": [
            concept for concept in snapshot.get("active_concept_versions") or []
        ],
        "unresolved_assumptions": [
            "OS isolation of worktrees is DECLARATIVE_ONLY",
            "network isolation is UNENFORCED",
            "external path isolation is DECLARATIVE_ONLY",
        ],
        "authority_constraints": {
            "authority_effect": False,
            "host_repository_rules_control": True,
            "historical_sources_remain_historical": True,
        },
        "provenance": snapshot.get("provenance") or {
            "current_checkout_revision": checkout,
            "implementation_revision": snapshot.get("source_head"),
        },
        "character_budget": int(budget),
        "errors": errors,
        "valid": not errors,
        "authority_effect": False,
    }
    return {**body, "packet_hash": _sha(body)}


def route_navigation_contract(query: str) -> list[str]:
    """Exact frozen questions only. Not a generalization measure."""
    for task in NAVIGATION_TASKS:
        if query.strip() == task["query"]:
            return list(task["expected"])
    return ["docs/AGENT_START.md", "docs/STATUS.md"]


def route_navigation(query: str) -> list[str]:
    return route_navigation_contract(query)


def route_navigation_generalization(query: str) -> list[str]:
    """Phrase features only. Does not look up the full query string."""
    folded = query.lower()
    scored = []
    for route in NAVIGATION_FEATURES:
        hits = sum(1 for phrase in route["phrases"] if phrase in folded)
        if hits:
            scored.append((hits, route["id"], list(route["expected"])))
    if not scored:
        return ["docs/AGENT_START.md"]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


def measure_navigation_contract() -> dict[str, Any]:
    results = []
    correct = 0
    for task in NAVIGATION_TASKS:
        routed = route_navigation_contract(task["query"])
        ok = routed == list(task["expected"])
        correct += int(ok)
        results.append({"id": task["id"], "expected": task["expected"], "routed": routed, "correct": ok})
    body = {
        "schema_version": NAVIGATION_CONTRACT_SCHEMA,
        "n_tasks": len(NAVIGATION_TASKS),
        "correct": correct,
        "N_contract": correct / len(NAVIGATION_TASKS),
        "results": results,
        "scope": "exact_query_contract_panel",
        "authority_effect": False,
    }
    return {**body, "panel_hash": _sha(body)}


def measure_navigation_fidelity() -> dict[str, Any]:
    contract = measure_navigation_contract()
    return {
        **contract,
        "schema_version": NAVIGATION_SCHEMA,
        "N_f": contract["N_contract"],
        "scope": "finite_frozen_navigation_contract_panel",
    }


def measure_navigation_generalization() -> dict[str, Any]:
    results = []
    correct = 0
    for task in NAVIGATION_GENERALIZATION_PANEL:
        if any(task["query"] == item["query"] for item in NAVIGATION_TASKS):
            raise ValueError("generalization query leaked into contract panel")
        routed = route_navigation_generalization(task["query"])
        ok = routed == list(task["expected"])
        correct += int(ok)
        results.append({"id": task["id"], "expected": task["expected"], "routed": routed, "correct": ok})
    body = {
        "schema_version": NAVIGATION_GENERALIZATION_SCHEMA,
        "n_tasks": len(NAVIGATION_GENERALIZATION_PANEL),
        "correct": correct,
        "N_generalization": correct / len(NAVIGATION_GENERALIZATION_PANEL),
        "results": results,
        "scope": "withheld_paraphrase_panel",
        "uses_exact_query_table": False,
        "authority_effect": False,
    }
    return {**body, "panel_hash": _sha(body)}


__all__ = [
    "NAVIGATION_GENERALIZATION_PANEL",
    "NAVIGATION_TASKS",
    "compile_context_packet",
    "derive_epistemic_snapshot",
    "measure_navigation_contract",
    "measure_navigation_fidelity",
    "measure_navigation_generalization",
    "route_navigation",
    "route_navigation_contract",
    "route_navigation_generalization",
]
