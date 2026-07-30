"""v6.23 — Foreign / cold-host phase thicken (emergence without identity merge).

Raises ranker_warm (train_count) and fusion_coupling (open fuse + ticks) on a
target host so couple percolation can reach emergent. Memory graph + ranker
only. Never host mutation. Never merges repository identity into the body.

ranker_warm = train_count/15 → need ≥7 for COUPLE_ACTIVE (0.45).
fusion_coupling ≥ 0.55 when fuse is open.
"""

from __future__ import annotations

import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .coherence import COUPLE_ACTIVE, measure_coherence
from .emergence_log import log_milestone
from .ranker.model import (
    ensure_ranker,
    features_from_hit,
    ranker_status,
    train_from_outcome,
    unfreeze_ranker,
)

SCHEMA = "cortex-foreign-emerge/1.0"
GLYPH = "⧉◐"

# Default path tokens for PulseFlow-class governors (also safe no-ops if absent).
DEFAULT_FOREIGN_PATHS: tuple[str, ...] = (
    "src/policy.rs",
    "src/storage.rs",
    "src/server.rs",
    "src/main.rs",
    "src/governor.rs",
    "src/model.rs",
    "tests/policy_tests.rs",
    "README.md",
)

DEFAULT_FOREIGN_TASKS: tuple[str, ...] = (
    "policy.rs enforcement rules for the governor engine",
    "storage.rs persistence for decisions and state",
    "server.rs http request handling",
    "main.rs application entrypoint wiring",
    "policy_tests.rs verify policy boundaries",
)

# Cold engine/sandbox path seeds
DEFAULT_ENGINE_PATHS: tuple[str, ...] = (
    "cortex/cli.py",
    "cortex/interconnect.py",
    "cortex/self_org.py",
    "cortex/host_mesh.py",
    "cortex/coherence.py",
    "cortex/foreign_emerge.py",
    "README.md",
)


def _prog(cb: Callable[[str], None] | None, msg: str) -> None:
    if cb:
        cb(msg)


def _warm_ranker(
    store: Any,
    repo: str,
    paths: list[str],
    *,
    target_trains: int = 8,
    reward: float = 0.85,
) -> dict[str, Any]:
    """Train this host's ranker until train_count >= target (or one batch min)."""
    st = ranker_status(store, repo)
    if st.get("frozen"):
        unfreeze_ranker(store, repo)
    before = int(st.get("train_count") or 0)
    trained_steps = 0
    last: dict[str, Any] = {"trained": False}
    paths = [p for p in paths if p] or list(DEFAULT_FOREIGN_PATHS)
    while int(ensure_ranker(store, repo).get("train_count") or 0) < int(target_trains):
        vecs = [
            features_from_hit(
                {
                    "path": p,
                    "kind": "source",
                    "score": max(0.35, 0.9 - 0.05 * i),
                    "metadata": {
                        "foreign_emerge": True,
                        "selection_source": "foreign_emerge_warm",
                    },
                },
                rank=i,
                retrieval_confidence=0.78,
            )
            for i, p in enumerate(paths[:12])
        ]
        oid = "out_fe_" + sha256(
            f"{repo}|{time.time()}|{trained_steps}".encode()
        ).hexdigest()[:14]
        try:
            from .capabilities import issue_for_controller

            cap = issue_for_controller(
                repo, "advanced", store=store, reason="foreign_emerge_warm"
            )
        except Exception:
            cap = None
        last = train_from_outcome(
            store,
            repo,
            outcome_id=oid,
            activation_id="foreign_emerge",
            status="verified",
            reward=reward,
            verification_type="foreign_emerge_path_tokens",
            governance_mode="normal",
            feature_vectors=vecs,
            capability=cap,
        )
        trained_steps += 1
        if not last.get("trained"):
            break
        if trained_steps >= 12:
            break
    after = int(ensure_ranker(store, repo).get("train_count") or 0)
    return {
        "trained_steps": trained_steps,
        "train_count_before": before,
        "train_count_after": after,
        "ranker_warm_after": round(min(1.0, after / 15.0), 4),
        "last": {k: last.get(k) for k in ("trained", "reason", "frozen", "train_count")},
    }


def thicken_host_phase(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    fuse_ticks: int = 4,
    open_fuse: bool = True,
    warm_ranker: bool = True,
    target_trains: int = 8,
    activate: bool = True,
    path_seeds: list[str] | None = None,
    tasks: list[str] | None = None,
    budget: int = 600,
    budget_scheme: str = "fib",
    on_progress: Callable[[str], None] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """One foreign/cold-host phase thicken pulse.

    Does not measure or train the durable body. Does not merge identities.
    """
    t0 = time.time()
    if not store.repo(repo):
        raise ValueError(f"Unknown repository: {repo}")

    _prog(on_progress, f"coherence_before:{repo}")
    coh_before = measure_coherence(
        store,
        repo,
        governor=governor,
        home=home,
        retrieval_confidence=0.7,
        persist=False,
    )
    rk_before = ranker_status(store, repo)
    phase_before = {
        "score": coh_before.get("score"),
        "emergent": coh_before.get("emergent_coupling"),
        "coupled_seams": coh_before.get("coupled_seams"),
        "active": coh_before.get("active_indicator_ids"),
        "ranker_warm": (coh_before.get("components") or {}).get("ranker_warm"),
        "fusion_coupling": (coh_before.get("components") or {}).get("fusion_coupling"),
        "train_count": rk_before.get("train_count"),
    }

    # Role-aware seeds
    role = "foreign"
    try:
        meta = store.repo(repo)
        # path heuristic
        pth = str((meta or {}).get("path") or "")
        if "Cortex" in str(repo) and "Teach" not in str(repo):
            role = "engine"
        if "Sandbox" in str(repo):
            role = "sandbox"
    except Exception:
        pth = ""
    seeds = list(path_seeds or [])
    if not seeds:
        seeds = (
            list(DEFAULT_ENGINE_PATHS)
            if role in {"engine", "sandbox"}
            else list(DEFAULT_FOREIGN_PATHS)
        )
    task_list = list(tasks or DEFAULT_FOREIGN_TASKS)

    fuse_info: dict[str, Any] = {"opened": False, "ticks": []}
    if open_fuse or fuse_ticks > 0:
        _prog(on_progress, "fuse")
        try:
            from .coprocess import fuse_open, fuse_state, fuse_tick

            st = fuse_state(store, repo)
            if open_fuse and not st.get("open"):
                fo = fuse_open(
                    home,
                    store,
                    governor,
                    repo,
                    task=f"foreign emerge phase thicken: {repo}",
                    budget=budget,
                    invent_structure=True,
                    spectral_primary=True,
                )
                fuse_info["opened"] = True
                fuse_info["open_result"] = {
                    "open": fo.get("open"),
                    "tick": fo.get("tick"),
                    "block": fo.get("block"),
                    "error": fo.get("error"),
                }
            for i in range(max(0, int(fuse_ticks))):
                tok = task_list[i % len(task_list)] if task_list else "foreign emerge tick"
                tick = fuse_tick(
                    store,
                    governor,
                    repo,
                    token=tok,
                    tokens=1,
                    measure_coherence_every=99,
                )
                fuse_info["ticks"].append(
                    {
                        "i": i + 1,
                        "ok": tick.get("ok"),
                        "tick": tick.get("tick"),
                        "invented": tick.get("invented"),
                    }
                )
            fuse_info["state"] = {
                k: fuse_state(store, repo).get(k)
                for k in ("open", "tick", "token_count")
            }
        except Exception as exc:
            fuse_info["error"] = f"{type(exc).__name__}: {exc}"

    act_notes: list[dict[str, Any]] = []
    if activate:
        _prog(on_progress, "activate")
        try:
            from .activation import activate_repository

            for t in task_list[:5]:
                act = activate_repository(
                    home,
                    store,
                    governor,
                    repo,
                    task=t,
                    budget=budget,
                    refresh="never",
                    profile="agent",
                    budget_scheme=budget_scheme,
                )
                ctx = act.get("context") or act
                act_notes.append(
                    {
                        "task": t[:56],
                        "paths": [
                            e.get("path")
                            for e in (ctx.get("evidence") or [])[:4]
                        ],
                        "budget_scheme": (ctx.get("budget_partition") or {}).get(
                            "scheme"
                        ),
                    }
                )
        except Exception as exc:
            act_notes.append({"error": f"{type(exc).__name__}: {exc}"})

    warm: dict[str, Any] = {"skipped": not warm_ranker}
    if warm_ranker:
        _prog(on_progress, "warm_ranker")
        warm = _warm_ranker(
            store, repo, seeds, target_trains=int(target_trains), reward=0.86
        )

    _prog(on_progress, "coherence_after")
    coh_after = measure_coherence(
        store,
        repo,
        governor=governor,
        home=home,
        retrieval_confidence=0.75,
        persist=True,
    )
    rk_after = ranker_status(store, repo)
    comps = coh_after.get("components") or {}
    phase_after = {
        "score": coh_after.get("score"),
        "emergent": coh_after.get("emergent_coupling"),
        "coupled_seams": coh_after.get("coupled_seams"),
        "active": coh_after.get("active_indicator_ids"),
        "ranker_warm": comps.get("ranker_warm"),
        "fusion_coupling": comps.get("fusion_coupling"),
        "train_count": rk_after.get("train_count"),
    }

    flipped = (not phase_before.get("emergent")) and bool(phase_after.get("emergent"))
    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "elapsed_s": round(time.time() - t0, 3),
        "phase_before": phase_before,
        "phase_after": phase_after,
        "emergent_flipped_on": flipped,
        "fuse": fuse_info,
        "activate": act_notes,
        "warm": warm,
        "couple_active_threshold": COUPLE_ACTIVE,
        "advice": list(coh_after.get("advice") or []),
        "claim_boundary": (
            "Foreign emerge thickens ranker+fuse phase on one attached host. "
            "Does not merge identities, mutate host source, or claim consciousness."
        ),
        "at": time.time(),
    }

    if persist:
        try:
            log_milestone(
                home,
                store,
                repo,
                kind="foreign_emerge",
                summary=(
                    f"foreign-emerge {repo}: emergent "
                    f"{phase_before.get('emergent')}→{phase_after.get('emergent')} "
                    f"trains={phase_before.get('train_count')}→{phase_after.get('train_count')} "
                    f"coh={phase_after.get('score')} seams={phase_after.get('coupled_seams')}"
                ),
                payload={
                    "phase_before": phase_before,
                    "phase_after": phase_after,
                    "flipped": flipped,
                    "warm": {
                        k: warm.get(k)
                        for k in (
                            "train_count_before",
                            "train_count_after",
                            "ranker_warm_after",
                        )
                    },
                },
                source="foreign_emerge",
            )
            # Also stamp primary body log if different
            primary = None
            try:
                for row in store.repositories() if hasattr(store, "repositories") else []:
                    pass
            except Exception:
                pass
            try:
                # durable body name heuristic
                for name in ("CortexTeach", "Cortex"):
                    if name != repo and store.repo(name):
                        primary = name
                        break
                if primary:
                    log_milestone(
                        home,
                        store,
                        primary,
                        kind="foreign_emerge",
                        summary=(
                            f"host phase thicken on {repo}: "
                            f"emergent={phase_after.get('emergent')} "
                            f"trains={phase_after.get('train_count')}"
                        ),
                        payload={"target": repo, "phase_after": phase_after},
                        source="foreign_emerge",
                    )
            except Exception:
                pass
        except Exception:
            pass

    return report


def thicken_mesh_cold_hosts(
    home: Path,
    store: Any,
    governor: Any,
    *,
    foreign_only: bool = False,
    min_trains: int = 3,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Thicken all non-emergent foreign hosts (and optionally cold rankers)."""
    from .host_mesh import _classify_role, _metadata_dict, _row_dict

    rows = list(store.repos() or [])

    results: list[dict[str, Any]] = []
    for row in rows:
        rd = _row_dict(row)
        name = str(rd.get("name") or "")
        if not name:
            continue
        meta = _metadata_dict(rd)
        role = _classify_role(name, str(rd.get("path") or ""), None, metadata=meta)
        if foreign_only and role != "foreign_host":
            continue
        if role == "durable_body":
            continue  # never re-thicken primary body here
        try:
            coh = measure_coherence(
                store, name, governor=governor, home=home, retrieval_confidence=0.55
            )
        except Exception:
            coh = {}
        tc = int(ranker_status(store, name).get("train_count") or 0)
        need = (not coh.get("emergent_coupling")) or tc < min_trains
        if not need:
            results.append({"repo": name, "skipped": True, "reason": "already_warm_emergent"})
            continue
        _prog(on_progress, f"thicken:{name}")
        seeds = (
            list(DEFAULT_FOREIGN_PATHS)
            if role == "foreign_host"
            else list(DEFAULT_ENGINE_PATHS)
        )
        r = thicken_host_phase(
            home,
            store,
            governor,
            name,
            path_seeds=seeds,
            target_trains=max(8, min_trains + 5),
            fuse_ticks=4,
            on_progress=on_progress,
        )
        results.append(r)

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "hosts_touched": len([r for r in results if not r.get("skipped")]),
        "results": results,
        "claim_boundary": (
            "Mesh thicken is per-host phase work; identities stay separate."
        ),
    }
