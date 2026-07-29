"""Native and host-integrated ARIA semantic-language discovery.

Cortex remains implemented and executed in Python. Meta-languages may describe
intent, plans, governance, continuation, and coordination, but they never
replace Cortex code or grant mutation authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aria_meta import bundle_identity, bundle_root, verify_bundle


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def detect_meta_language(root: Path, file_rows: list[Any]) -> dict[str, Any]:
    """Return a bounded ARIA descriptor from repository evidence only."""

    bundled_prefix = "cortex/aria_meta/vendor/"
    local_runtime = root / "ARIA-RUNTIME.json"
    local_contract = root / "ARIA-CONNECT.json"
    local_aria_paths = sorted(
        row["path"].replace("\\", "/")
        for row in file_rows
        if row["status"] == "indexed"
        and not str(row["path"]).replace("\\", "/").startswith(bundled_prefix)
        and (
            str(row["path"]).lower().endswith(".aria")
            or str(row["path"]).replace("\\", "/")
            in {"ARIA-CONNECT.json", "ARIA-RUNTIME.json"}
        )
    )
    host_local = local_runtime.is_file() or local_contract.is_file() or bool(
        local_aria_paths
    )
    meta_root = root if host_local else bundle_root()
    runtime_path = meta_root / "ARIA-RUNTIME.json"
    contract_path = meta_root / "ARIA-CONNECT.json"
    runtime = _json_object(runtime_path)
    contract = _json_object(contract_path)
    aria_paths = (
        local_aria_paths
        if host_local
        else [
            "ARIA-CONNECT.json",
            "ARIA-RUNTIME.json",
            *sorted(
                path.relative_to(meta_root).as_posix()
                for path in meta_root.rglob("*.aria")
                if path.is_file()
            ),
        ]
    )
    detected = bool(runtime or contract or aria_paths)
    base: dict[str, Any] = {
        "schema_version": "cortex-meta-language/1.0",
        "available": detected,
        "cortex_implementation_language": "python",
        "cortex_execution_language": "python",
        "role": (
            "host_meta_language"
            if host_local
            else "native_semantic_language"
            if detected
            else "optional_meta_language"
        ),
        "execution_policy": {
            "automatic_execution": False,
            "automatic_translation_to_core": False,
            "verification_required": True,
            "host_governance_controls": True,
        },
        "authority": {
            "grants_mutation_authority": False,
            "proposal_is_not_authority": True,
            "evidence_is_not_authority": True,
            "human_authority_required": True,
        },
    }
    if not detected:
        return {
            **base,
            "name": None,
            "reason": "No ARIA runtime, connection contract, or indexed .aria artifacts detected.",
        }

    commands = contract.get("commands") if isinstance(contract.get("commands"), dict) else {}
    continuity = contract.get("continuity") if isinstance(contract.get("continuity"), list) else []
    repository = (
        runtime.get("repository") if isinstance(runtime.get("repository"), dict) else {}
    )
    return {
        **base,
        "name": "ARIA",
        "label": (
            "HOST ARIA META-LANGUAGE"
            if host_local
            else bundle_identity()["label"]
        ),
        "source_kind": "host_repository" if host_local else "bundled_internal",
        "knowledge_relationship": (
            "integrated_host_language" if host_local else "native_internal_language"
        ),
        "purpose": contract.get(
            "purpose",
            "Represent verified intent, governance, continuity, and coordination.",
        ),
        "release": runtime.get("release"),
        "language_evolution": runtime.get("languageEvolution"),
        "status": runtime.get("status"),
        "protocol": contract.get("protocol"),
        "canonical_cli": repository.get("canonicalCli"),
        "artifact_count": len(aria_paths),
        "artifact_paths": aria_paths[:50],
        "bundle": (
            None
            if host_local
            else {
                **verify_bundle(),
                "root": str(meta_root),
            }
        ),
        "responsibilities": [
            "intent_representation",
            "semantic_planning",
            "governance_contracts",
            "constitutional_supervision",
            "context_preservation_and_adjacency",
            "verified_continuation",
            "cooperative_agent_coordination",
        ],
        "excluded_responsibilities": [
            "cortex_core_execution",
            "automatic_repository_mutation",
            "authority_aggregation",
            "unverified_external_effects",
        ],
        "recommended_commands": {
            key: str(commands[key])
            for key in (
                "handshake",
                "baseline",
                "health",
                "conformance",
                "replayCreate",
                "handoffCreate",
                "bridgeCreate",
                "meshCreate",
            )
            if key in commands
        },
        "continuity_protocols": [
            {
                "artifact": item.get("artifact"),
                "boundary": item.get("boundary"),
            }
            for item in continuity
            if isinstance(item, dict) and item.get("artifact")
        ],
        "source": {
            "runtime": (
                "ARIA-RUNTIME.json"
                if host_local and runtime
                else "bundled://ARIA-RUNTIME.json"
                if runtime
                else None
            ),
            "contract": (
                "ARIA-CONNECT.json"
                if host_local and contract
                else "bundled://ARIA-CONNECT.json"
                if contract
                else None
            ),
        },
    }
