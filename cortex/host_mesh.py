"""Multi-host mesh — one body, many attached repositories.

v6.17: Make the “whoa” explicit. Cortex already stores many hosts in one SQLite
body; this pulse observes them, compares coupling, and directs evolution
without merging identities or host authority.

Recommend-only. Not consciousness. Boundaries preserved.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .coherence import measure_coherence
from .emergence_log import log_milestone, read_emergence_log
from .federation import federated_query
from .ranker.model import ranker_status

SCHEMA = "cortex-host-mesh/1.0"
GLYPH = "⧉⬡"


def _row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        return {"name": str(row)}


def _memory_count(store: Any, repo: str) -> int:
    try:
        r = store.db.execute(
            "SELECT COUNT(1) AS c FROM memories WHERE repo=?", (repo,)
        ).fetchone()
        return int(r["c"] if hasattr(r, "keys") else r[0])
    except Exception:
        return 0


def _synapse_count(store: Any, repo: str) -> int:
    try:
        from .prune import graph_census

        c = graph_census(store, repo)
        syn = c.get("synapses")
        if isinstance(syn, dict):
            return int(syn.get("total") or 0)
        return int(syn or 0)
    except Exception:
        return 0


def _classify_role(name: str, path: str, home_engine: Path | None) -> str:
    n = name.casefold()
    p = path.replace("\\", "/").casefold()
    if "teach" in n:
        return "durable_body"
    if home_engine and path:
        try:
            if Path(path).resolve() == home_engine.resolve():
                return "engine_tree"
        except Exception:
            pass
    if "sandbox" in n:
        return "sandbox"
    if "cortex" in n and "teach" not in n:
        return "engine_alias"
    return "foreign_host"


def observe_host(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    measure_coherence_field: bool = True,
) -> dict[str, Any]:
    """Observe one attached host (boundary-preserving)."""
    row = store.repo(repo)
    if not row:
        return {"name": repo, "attached": False, "error": "unknown_repo"}
    rd = _row_dict(row)
    path = str(rd.get("path") or "")
    path_ok = bool(path and Path(path).exists())
    engine = Path(__file__).resolve().parents[1]
    role = _classify_role(repo, path, engine)

    coh: dict[str, Any] = {}
    if measure_coherence_field and path_ok:
        try:
            coh = measure_coherence(
                store, repo, governor=governor, home=home, retrieval_confidence=0.55
            )
        except Exception as exc:
            coh = {"error": f"{type(exc).__name__}: {exc}"}

    ranker = {}
    try:
        ranker = ranker_status(store, repo)
    except Exception as exc:
        ranker = {"error": f"{type(exc).__name__}: {exc}"}

    latest = None
    try:
        latest = store.get_setting(f"emergence_latest:{repo}", None)
    except Exception:
        latest = None

    return {
        "name": repo,
        "attached": True,
        "role": role,
        "path": path,
        "path_exists": path_ok,
        "repository_id": rd.get("repository_id"),
        "bootstrap_status": rd.get("bootstrap_status"),
        "last_indexed": rd.get("last_indexed"),
        "memories": _memory_count(store, repo),
        "synapses": _synapse_count(store, repo),
        "coherence": {
            "score": coh.get("score"),
            "above_threshold": coh.get("above_threshold"),
            "emergent_coupling": coh.get("emergent_coupling"),
            "active_indicator_ids": coh.get("active_indicator_ids") or [],
            "component_panel": coh.get("component_panel"),
            "error": coh.get("error"),
        },
        "ranker": {
            "train_count": ranker.get("train_count"),
            "frozen": ranker.get("frozen"),
        },
        "emergence_latest": latest if isinstance(latest, dict) else None,
    }


def _directives_from_mesh(hosts: list[dict[str, Any]]) -> list[str]:
    dirs: list[str] = []
    foreign = [h for h in hosts if h.get("role") == "foreign_host" and h.get("path_exists")]
    bodies = [
        h
        for h in hosts
        if h.get("role") in {"durable_body", "engine_tree", "engine_alias"}
        and h.get("path_exists")
    ]
    cold_ranker = [
        h["name"]
        for h in hosts
        if h.get("path_exists") and int((h.get("ranker") or {}).get("train_count") or 0) < 3
    ]
    non_emergent_foreign = [
        h["name"]
        for h in foreign
        if not (h.get("coherence") or {}).get("emergent_coupling")
    ]
    missing_path = [h["name"] for h in hosts if not h.get("path_exists")]

    dirs.append(
        "One SQLite body · many hosts — never merge repository identity or authority."
    )
    if bodies:
        top = max(
            bodies,
            key=lambda h: float((h.get("coherence") or {}).get("score") or 0.0),
        )
        dirs.append(
            f"Durable/engine body focus: {top['name']} "
            f"(coh={(top.get('coherence') or {}).get('score')}, "
            f"emergent={(top.get('coherence') or {}).get('emergent_coupling')})."
        )
    if cold_ranker:
        dirs.append(
            "Warm cold rankers with real tasks + verified outcomes: "
            + ", ".join(cold_ranker[:6])
        )
    if non_emergent_foreign:
        dirs.append(
            "Foreign hosts not emergent yet — more activate/remember/seal loops: "
            + ", ".join(non_emergent_foreign[:6])
        )
    if missing_path:
        dirs.append("Re-attach or prune missing paths: " + ", ".join(missing_path[:4]))
    dirs.append(
        "Prefer host-mesh + fuse ticks over live continuum on large graphs; "
        "no prune thrash; recommend-only."
    )
    dirs.append(
        "Cross-repo search: cortex federate / host-mesh --query — boundaries preserved."
    )
    return dirs


def run_host_mesh(
    home: Path,
    store: Any,
    governor: Any,
    *,
    primary_repo: str | None = None,
    query: str | None = None,
    measure_coherence_field: bool = True,
    federate_limit: int = 10,
    persist: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Observe all attached hosts; optional federated query; direct next evolution."""

    def prog(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    t0 = time.time()
    rows = list(store.repos() or [])
    names = []
    for row in rows:
        rd = _row_dict(row)
        n = str(rd.get("name") or "")
        if n:
            names.append(n)

    # Prefer CortexTeach as primary log sink
    primary = primary_repo
    if not primary:
        if "CortexTeach" in names:
            primary = "CortexTeach"
        elif names:
            primary = names[0]
        else:
            primary = "Cortex"

    hosts: list[dict[str, Any]] = []
    for name in sorted(names):
        prog(f"host:{name}")
        hosts.append(
            observe_host(
                home,
                store,
                governor,
                name,
                measure_coherence_field=measure_coherence_field,
            )
        )

    federated: dict[str, Any] | None = None
    if query and query.strip():
        prog("federate_query")
        try:
            federated = federated_query(
                store,
                query.strip(),
                repositories=names,
                limit=federate_limit,
                per_repo=6,
            )
        except Exception as exc:
            federated = {"error": f"{type(exc).__name__}: {exc}"}

    # Mesh health summary
    scores = [
        float((h.get("coherence") or {}).get("score") or 0.0)
        for h in hosts
        if (h.get("coherence") or {}).get("score") is not None
    ]
    emergent_n = sum(
        1 for h in hosts if (h.get("coherence") or {}).get("emergent_coupling")
    )
    foreign_n = sum(1 for h in hosts if h.get("role") == "foreign_host")
    mesh_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    directives = _directives_from_mesh(hosts)
    next_moves: list[str] = []
    cold = [
        h["name"]
        for h in hosts
        if h.get("role") == "foreign_host"
        and int((h.get("ranker") or {}).get("train_count") or 0) < 5
    ]
    if cold:
        next_moves.append("real_task_loops_on=" + ",".join(cold[:4]))
    if emergent_n == 0 and hosts:
        next_moves.append("raise_body_coupling_via_fuse_and_measure")
    elif foreign_n and emergent_n < len(hosts):
        next_moves.append("deepen_foreign_hosts_without_merging_identity")
    next_moves.append("keep_spectral_ranker_on_primary_body")
    next_moves.append("host_mesh_is_observe_not_authority")

    report: dict[str, Any] = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "elapsed_s": round(time.time() - t0, 3),
        "primary_repo": primary,
        "host_count": len(hosts),
        "foreign_count": foreign_n,
        "emergent_host_count": emergent_n,
        "mesh_mean_coherence": mesh_score,
        "hosts": hosts,
        "federated_query": federated,
        "directives": directives,
        "next": next_moves,
        "claim_boundary": (
            "Host mesh observes attached repositories in one SQLite body. "
            "Does not merge repo identity, grant host mutation, or claim consciousness."
        ),
    }

    if persist and primary and store.repo(primary):
        try:
            store.set_setting(f"host_mesh_latest:{primary}", report)
            store.set_setting("host_mesh_latest", report)
        except Exception:
            pass
        try:
            log_milestone(
                home,
                store,
                primary,
                kind="host_mesh",
                summary=(
                    f"host-mesh hosts={len(hosts)} foreign={foreign_n} "
                    f"emergent={emergent_n} mean_coh={mesh_score} "
                    f"query={'yes' if federated and not federated.get('error') else 'no'}"
                ),
                payload={
                    "host_count": len(hosts),
                    "foreign_count": foreign_n,
                    "emergent_host_count": emergent_n,
                    "mesh_mean_coherence": mesh_score,
                    "next": next_moves[:4],
                    "names": [h.get("name") for h in hosts],
                },
                source="host_mesh",
            )
            report["emergence_log"] = read_emergence_log(
                home, store, primary, limit=6
            )
        except Exception as exc:
            report["emergence_error"] = f"{type(exc).__name__}: {exc}"

    prog("done")
    return report
