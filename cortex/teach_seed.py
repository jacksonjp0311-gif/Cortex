"""Seed teaching intelligence into Cortex memory via ARIA memory packets + ritual.

Distills interconnect doctrine into durable Discovery Cards on the durable body.
Never executes ARIA plans. Never mutates host source beyond Cortex memory store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import __version__
from .bootstrap import bootstrap_repository
from .config import ensure_home, load_repo_config, repo_config_path
from .governor import Governor
from .session_ritual import run_session_ritual
from .store import Store

PACKET_GLOB = "examples/memory-packets/*.packet.json"
INTELLIGENCE_DOCS = (
    "docs/intelligence/INTERCONNECT.md",
    "docs/ORGANISM.md",
    "docs/TRANSCEND.md",
    "docs/COVENANT.md",
)


def _engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_memory_packets(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or _engine_root()
    packets: list[dict[str, Any]] = []
    for path in sorted((base / "examples" / "memory-packets").glob("*.packet.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("ritual_seed"):
            payload["_path"] = str(path.relative_to(base).as_posix())
            packets.append(payload)
    return packets


def claims_to_memories(packet: dict[str, Any]) -> list[dict[str, str]]:
    kind = str(packet.get("kind") or "invariant")
    title = str(packet.get("title") or "memory packet")
    glyph = str(packet.get("glyph") or "⊛")
    memories: list[dict[str, str]] = [
        {
            "kind": "focus",
            "text": f"{glyph} Teach seed: {title}",
        }
    ]
    for claim in packet.get("claims") or []:
        claim_id = str(claim.get("id") or "claim")
        text = str(claim.get("text") or "").strip()
        evidence = claim.get("evidence") or []
        if not text:
            continue
        evidence_note = ""
        if evidence:
            evidence_note = " Evidence: " + ", ".join(str(e) for e in evidence[:6])
        memories.append(
            {
                "kind": kind if kind in {
                    "decision",
                    "discovery",
                    "invariant",
                    "wound",
                    "failure",
                    "fix",
                    "outcome",
                    "lesson",
                    "constraint",
                    "evidence",
                    "focus",
                } else "invariant",
                "text": f"[{claim_id}] {text}{evidence_note}",
            }
        )
    refuse = packet.get("refuse") or []
    if refuse:
        memories.append(
            {
                "kind": "constraint",
                "text": "Refuse: " + ", ".join(str(r) for r in refuse),
            }
        )
    return memories


def seed_intelligence(
    home: Path,
    store: Any,
    governor: Any,
    *,
    root: Path | None = None,
    repo_name: str | None = None,
    force_bootstrap: bool = False,
) -> dict[str, Any]:
    """Bootstrap if needed, then ritual-seed all ARIA memory packets."""

    root = (root or _engine_root()).resolve()
    name = repo_name or root.name or "Cortex"
    packets = load_memory_packets(root)
    if not packets:
        return {
            "seeded": False,
            "reason": "no memory packets found",
            "root": str(root),
        }

    attached = store.repo(name)
    if not attached or force_bootstrap or not repo_config_path(root).exists():
        boot = bootstrap_repository(
            home, store, root, name, force=force_bootstrap
        )
        boot_status = (boot.get("certificate") or {}).get("status")
    else:
        boot_status = attached.get("bootstrap_status") if hasattr(attached, "get") else attached["bootstrap_status"]

    rituals: list[dict[str, Any]] = []
    all_memories: list[dict[str, str]] = []
    for packet in packets:
        all_memories.extend(claims_to_memories(packet))

    # One cardiac cycle for all teaching mass + interconnect doctrine pointer.
    all_memories.append(
        {
            "kind": "lesson",
            "text": (
                "Interconnect intelligence: when systems couple, prefer organism.immune "
                "and control_error before work; continue pulse on remember; breathe mid-session; "
                "seal with ritual. See docs/intelligence/INTERCONNECT.md"
            ),
        }
    )
    all_memories.append(
        {
            "kind": "discovery",
            "text": (
                f"Cortex {__version__} teach-seed distilled {len(packets)} ARIA memory "
                "packets into durable body via session ritual."
            ),
        }
    )

    result = run_session_ritual(
        home,
        store,
        governor,
        name,
        "Teach Cortex interconnect intelligence from ARIA memory packets",
        memories=all_memories,
        consolidate_session=True,
        profile="agent",
        force=True,
    )
    rituals.append(result)

    # Second pass: re-index so Discovery Cards enter FTS if paths changed.
    try:
        from .indexer import index_repository

        config = load_repo_config(root)
        index_repository(store, name, config, force=False)
    except Exception as exc:
        index_note = f"{type(exc).__name__}: {exc}"
    else:
        index_note = "refreshed"

    return {
        "schema_version": "cortex-teach-seed/1.0",
        "glyph": "☰",
        "seeded": True,
        "repo": name,
        "root": str(root),
        "bootstrap_status": boot_status,
        "packets": [
            {
                "title": p.get("title"),
                "path": p.get("_path"),
                "claims": len(p.get("claims") or []),
            }
            for p in packets
        ],
        "memory_events": len(all_memories),
        "ritual": {
            "session_id": result.get("session_id"),
            "activation": result.get("activation"),
            "consolidate": result.get("consolidate"),
            "organism_pulse": (result.get("organism") or {}).get("pulse"),
            "cardiac_cycle": result.get("cardiac_cycle"),
        },
        "index": index_note,
        "version": __version__,
        "claim_boundary": (
            "Teach-seed writes Cortex memory only; never host source mutation; "
            "never ARIA execution."
        ),
    }


def seed_into_home(
    *,
    home: Path | None = None,
    root: Path | None = None,
    repo_name: str | None = None,
    force_bootstrap: bool = False,
) -> dict[str, Any]:
    home = ensure_home(home)
    store = Store(home / "cortex.db")
    governor = Governor(home, store)
    try:
        return seed_intelligence(
            home,
            store,
            governor,
            root=root,
            repo_name=repo_name,
            force_bootstrap=force_bootstrap,
        )
    finally:
        store.close()
