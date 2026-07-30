"""v6.25.1 Quarantine as runtime influence cut."""

from __future__ import annotations

from typing import Any, Iterable

from .quarantine import active_quarantined_ids, ensure_quarantine_tables

SCHEMA = "cortex-influence-policy/1.0"

CLAIM = (
    "Influence policy excludes quarantined/invalidated adaptive artifacts from "
    "learned paths. Evidence Kernel host evidence remains available."
)


def resolve_artifact_identity(raw: Any) -> set[str]:
    """Map an identifier to all equivalent keys used across subsystems."""
    if raw is None:
        return set()
    s = str(raw)
    out = {s}
    if s.startswith("syn_"):
        out.add(f"edge:{s}")
    if s.startswith("edge:"):
        out.add(s[5:])
    if s.startswith("mem:"):
        out.add(s[4:])
    else:
        # numeric memory ids
        try:
            int(s)
            out.add(f"mem:{s}")
        except ValueError:
            pass
    return out


def active_exclusions(store: Any, repo: str) -> set[str]:
    ensure_quarantine_tables(store)
    excl = set(active_quarantined_ids(store, repo))
    # invalidated lineage artifacts
    try:
        rows = store.db.execute(
            "SELECT artifact_id FROM lineage_artifacts WHERE repo=? AND invalidated=1",
            (repo,),
        ).fetchall()
        for r in rows:
            excl |= resolve_artifact_identity(r["artifact_id"])
    except Exception:
        pass
    # expand with all identity aliases
    expanded: set[str] = set()
    for e in excl:
        expanded |= resolve_artifact_identity(e)
    return expanded


def _hit_ids(hit: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(hit, dict):
        for k in ("memory_id", "artifact_id", "synapse_id", "path"):
            if hit.get(k) is not None:
                ids |= resolve_artifact_identity(hit.get(k))
        meta = hit.get("metadata") or {}
        if isinstance(meta, dict):
            for k in ("artifact_id", "synapse_id", "concept_route_id"):
                if meta.get(k) is not None:
                    ids |= resolve_artifact_identity(meta.get(k))
    else:
        mid = getattr(hit, "memory_id", None)
        if mid is not None:
            ids |= resolve_artifact_identity(mid)
        path = getattr(hit, "path", None)
        if path:
            ids |= resolve_artifact_identity(path)
        meta = getattr(hit, "metadata", None) or {}
        if isinstance(meta, dict):
            for k in ("artifact_id", "synapse_id"):
                if meta.get(k) is not None:
                    ids |= resolve_artifact_identity(meta.get(k))
    return ids


def filter_memory_hits(store: Any, repo: str, hits: list[Any]) -> list[Any]:
    excl = active_exclusions(store, repo)
    if not excl:
        return hits
    out = []
    for h in hits:
        ids = _hit_ids(h)
        if ids & excl:
            continue
        # discovery cards often adaptive
        path = ""
        if isinstance(h, dict):
            path = str(h.get("path") or "")
            kind = str(h.get("kind") or "")
        else:
            path = str(getattr(h, "path", "") or "")
            kind = str(getattr(h, "kind", "") or "")
        if ".cortex/cards/" in path.replace("\\", "/"):
            # cards may be quarantined by path key
            if any(p in excl for p in resolve_artifact_identity(path)):
                continue
        out.append(h)
    return out


def filter_synapses(store: Any, repo: str, synapses: Iterable[Any]) -> list[Any]:
    excl = active_exclusions(store, repo)
    if not excl:
        return list(synapses)
    out = []
    for s in synapses:
        if isinstance(s, dict):
            sid = str(s.get("synapse_id") or "")
        else:
            try:
                sid = str(s["synapse_id"])
            except Exception:
                sid = str(getattr(s, "synapse_id", "") or "")
        if resolve_artifact_identity(sid) & excl:
            continue
        out.append(s)
    return out


def filter_training_events(store: Any, repo: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excl = active_exclusions(store, repo)
    if not excl:
        return [e for e in events if not e.get("excluded")]
    out = []
    for e in events:
        if e.get("excluded"):
            continue
        origins = e.get("origin_artifact_ids") or []
        try:
            if isinstance(origins, str):
                import json

                origins = json.loads(origins)
        except Exception:
            origins = []
        bad = False
        for o in origins:
            if resolve_artifact_identity(o) & excl:
                bad = True
                break
        eid = str(e.get("event_id") or "")
        if resolve_artifact_identity(eid) & excl:
            bad = True
        if not bad:
            out.append(e)
    return out


def assert_influence_allowed(store: Any, repo: str, artifact_id: str) -> None:
    excl = active_exclusions(store, repo)
    if resolve_artifact_identity(artifact_id) & excl:
        raise PermissionError(f"influence denied for quarantined/invalidated {artifact_id}")


def influence_status(store: Any, repo: str) -> dict[str, Any]:
    excl = active_exclusions(store, repo)
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "n_excluded": len(excl),
        "sample": sorted(excl)[:20],
        "claim_boundary": CLAIM,
    }
