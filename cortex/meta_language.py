"""Optional repository meta-language discovery.

Cortex remains implemented and executed in Python. Meta-languages may describe
intent, plans, governance, continuation, and coordination, but they never
replace Cortex code or grant mutation authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def detect_meta_language(root: Path, file_rows: list[Any]) -> dict[str, Any]:
    """Return a bounded ARIA descriptor from repository evidence only."""

    runtime_path = root / "ARIA-RUNTIME.json"
    contract_path = root / "ARIA-CONNECT.json"
    runtime = _json_object(runtime_path)
    contract = _json_object(contract_path)
    aria_paths = sorted(
        row["path"].replace("\\", "/")
        for row in file_rows
        if row["status"] == "indexed"
        and (
            str(row["path"]).lower().endswith(".aria")
            or str(row["path"]).replace("\\", "/")
            in {"ARIA-CONNECT.json", "ARIA-RUNTIME.json"}
        )
    )
    detected = bool(runtime or contract or aria_paths)
    base: dict[str, Any] = {
        "schema_version": "cortex-meta-language/1.0",
        "available": detected,
        "cortex_implementation_language": "python",
        "cortex_execution_language": "python",
        "role": "meta_language" if detected else "optional_meta_language",
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
        "responsibilities": [
            "intent_representation",
            "semantic_planning",
            "governance_contracts",
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
            "runtime": "ARIA-RUNTIME.json" if runtime else None,
            "contract": "ARIA-CONNECT.json" if contract else None,
        },
    }
