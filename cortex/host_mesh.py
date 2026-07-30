"""Multi-host mesh — one body, many attached repositories.

v6.17: Make the “whoa” explicit. Cortex already stores many hosts in one SQLite
body; this pulse observes them, compares coupling, and directs evolution
without merging identities or host authority.

Pulse that lists every attached repository with role coherence and ranker trains
without merging identities. run_host_mesh / host-mesh CLI — mesh_role metadata.

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

SCHEMA = "cortex-host-mesh/1.1"
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


MESH_ROLES = frozenset(
    {
        "durable_body",
        "engine_tree",
        "engine_alias",
        "sandbox",
        "foreign_host",
        "unknown",
    }
)


def _metadata_dict(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metadata")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            val = json.loads(raw)
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}
    return {}


def _classify_role(
    name: str,
    path: str,
    home_engine: Path | None,
    *,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Prefer explicit mesh_role metadata; fall back to conservative heuristics."""
    meta = metadata or {}
    explicit = str(meta.get("mesh_role") or meta.get("role") or "").strip()
    if explicit in MESH_ROLES:
        return explicit
    n = name.casefold()
    if n == "cortexteach" or n.endswith("teach"):
        return "durable_body"
    if home_engine and path:
        try:
            if Path(path).resolve() == home_engine.resolve():
                return "engine_tree" if n == "cortex" else "durable_body"
        except Exception:
            pass
    if "sandbox" in n:
        return "sandbox"
    if n == "cortex":
        return "engine_alias"
    return "foreign_host"


def set_mesh_role(store: Any, repo: str, role: str, **extra: Any) -> dict[str, Any]:
    """Persist explicit mesh_role on repository metadata (v6.18)."""
    if role not in MESH_ROLES:
        raise ValueError(f"Unknown mesh_role {role!r}; choose {sorted(MESH_ROLES)}")
    row = store.repo(repo)
    if not row:
        raise ValueError(f"Unknown repository: {repo}")
    rd = _row_dict(row)
    meta = _metadata_dict(rd)
    meta["mesh_role"] = role
    meta["authority_domain"] = extra.get(
        "authority_domain",
        "isolated" if role == "foreign_host" else "body",
    )
    meta["learning_policy"] = extra.get(
        "learning_policy", "verified_outcomes_only"
    )
    meta["topology_class"] = "G_federated" if role == "foreign_host" else "G_learned"
    store.update_repo_state(repo, metadata=meta)
    return meta


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
    meta = _metadata_dict(rd)
    role = _classify_role(repo, path, engine, metadata=meta)
    # Auto-stamp explicit role once so future pulses are not heuristic-only.
    if not meta.get("mesh_role") and path_ok:
        try:
            meta = set_mesh_role(store, repo, role)
        except Exception:
            pass

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

    # v7.0: per-host body epoch + runtime phase (distributed alignment inputs)
    continuity: dict[str, Any] = {}
    try:
        from .epoch import ensure_current_epoch, verify_body_epoch
        from .phases import current_phase

        ep = ensure_current_epoch(store, repo, reason="host_mesh_observe")
        ph = current_phase(store, repo)
        ver = verify_body_epoch(store, repo, ep)
        continuity = {
            "body_epoch_id": ep.epoch_id,
            "epoch_verified": bool(ver.get("ok")),
            "runtime_phase": ph.phase,
            "phase_bound": ph.epoch_id == ep.epoch_id,
            "cortex_version": ep.cortex_version,
            "repository_id": ep.repository_id,
            "evidence_root_prefix": (ep.evidence_root_hash or "")[:12],
            "adaptive_root_prefix": (ep.adaptive_root_hash or "")[:12],
            "constitutional_prefix": (ep.constitutional_config_hash or "")[:12],
        }
    except Exception as exc:
        continuity = {"error": f"{type(exc).__name__}: {exc}"}

    return {
        "name": repo,
        "attached": True,
        "role": role,
        "mesh_role": meta.get("mesh_role") or role,
        "authority_domain": meta.get("authority_domain"),
        "learning_policy": meta.get("learning_policy"),
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
        "continuity": continuity,
        "body_epoch_id": continuity.get("body_epoch_id"),
        "runtime_phase": continuity.get("runtime_phase"),
        "emergence_latest": latest if isinstance(latest, dict) else None,
    }


def _epoch_alignment(hosts: list[dict[str, Any]]) -> dict[str, Any]:
    """Distributed host alignment: versions, constitution prefixes, phase diversity.

    Hosts keep distinct body_epoch_ids (repo identity). Alignment is about
    cortex_version + constitutional prefix compatibility — not merging epochs.
    """
    versions: dict[str, list[str]] = {}
    constitutions: dict[str, list[str]] = {}
    phases: dict[str, list[str]] = {}
    stale: list[str] = []
    unbound: list[str] = []
    for h in hosts:
        if not h.get("path_exists"):
            continue
        name = str(h.get("name") or "")
        c = h.get("continuity") or {}
        if c.get("error"):
            stale.append(name)
            continue
        if c.get("epoch_verified") is False:
            stale.append(name)
        if c.get("phase_bound") is False:
            unbound.append(name)
        ver = str(c.get("cortex_version") or "unknown")
        versions.setdefault(ver, []).append(name)
        cp = str(c.get("constitutional_prefix") or "unknown")
        constitutions.setdefault(cp, []).append(name)
        ph = str(c.get("runtime_phase") or "unknown")
        phases.setdefault(ph, []).append(name)
    version_aligned = len(versions) <= 1
    constitution_aligned = len(constitutions) <= 1
    return {
        "schema_version": "cortex-epoch-alignment/1.0",
        "version_aligned": version_aligned,
        "constitution_aligned": constitution_aligned,
        "cortex_versions": {k: sorted(v) for k, v in versions.items()},
        "constitutional_prefixes": {k: sorted(v) for k, v in constitutions.items()},
        "runtime_phases": {k: sorted(v) for k, v in phases.items()},
        "stale_epoch_hosts": stale,
        "phase_unbound_hosts": unbound,
        "aligned": version_aligned and constitution_aligned and not stale and not unbound,
        "law": (
            "Hosts share one body SQLite but never merge repository epochs. "
            "Alignment requires same cortex_version and constitutional prefix; "
            "distinct body_epoch_id per repo is required and expected."
        ),
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
            f"emergent={(top.get('coherence') or {}).get('emergent_coupling')}, "
            f"epoch={((top.get('continuity') or {}).get('body_epoch_id') or '')[:12]}, "
            f"phase={(top.get('continuity') or {}).get('runtime_phase')})."
        )
    if cold_ranker:
        dirs.append(
            "Warm cold rankers with real tasks + verified outcomes: "
            + ", ".join(cold_ranker[:6])
        )
    if non_emergent_foreign:
        dirs.append(
            "Foreign hosts not emergent yet — run foreign-emerge / host-mesh --thicken: "
            + ", ".join(non_emergent_foreign[:6])
        )
    if missing_path:
        dirs.append("Re-attach or prune missing paths: " + ", ".join(missing_path[:4]))
    align = _epoch_alignment(hosts)
    if not align.get("version_aligned"):
        dirs.append(
            "Cortex version skew across hosts — upgrade lagging attachments: "
            + str(align.get("cortex_versions"))
        )
    if not align.get("constitution_aligned"):
        dirs.append(
            "Constitutional prefix skew — re-seal epochs after policy/version align."
        )
    if align.get("stale_epoch_hosts"):
        dirs.append(
            "Stale body epochs (roots drifted): "
            + ", ".join(align["stale_epoch_hosts"][:6])
            + " — run: cortex epoch --repo <name> seal"
        )
    if align.get("phase_unbound_hosts"):
        dirs.append(
            "Phase unbound from epoch: "
            + ", ".join(align["phase_unbound_hosts"][:6])
            + " — re-enter legal phase under current epoch"
        )
    dirs.append(
        "Prefer host-mesh + fuse ticks over live continuum on large graphs; "
        "no prune thrash; recommend-only."
    )
    dirs.append(
        "Cross-repo search: cortex federate / host-mesh --query — boundaries preserved. "
        "Federate only when host epochs share constitutional prefix (epoch-compatible influence)."
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

    alignment = _epoch_alignment(hosts)
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
    non_em_foreign = [
        h["name"]
        for h in hosts
        if h.get("role") == "foreign_host"
        and not (h.get("coherence") or {}).get("emergent_coupling")
    ]
    if non_em_foreign:
        next_moves.append(
            "foreign_emerge_or_host_mesh_thicken=" + ",".join(non_em_foreign[:4])
        )
    if emergent_n == 0 and hosts:
        next_moves.append("raise_body_coupling_via_fuse_and_measure")
    elif foreign_n and emergent_n < len(hosts):
        next_moves.append("deepen_foreign_hosts_without_merging_identity")
    if not alignment.get("aligned"):
        next_moves.append("seal_or_align_body_epochs_before_federated_promote")
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
        "epoch_alignment": alignment,
        "hosts": hosts,
        "federated_query": federated,
        "directives": directives,
        "next": next_moves,
        "claim_boundary": (
            "Host mesh observes attached repositories in one SQLite body. "
            "Does not merge repo identity or body epochs, grant host mutation, "
            "or claim consciousness. v7 alignment is version/constitution compatibility only."
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
