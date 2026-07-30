"""Multi-lane evolution continuum ⟲ — use → teach → measure in one pass.

Lanes (v6.11):
  1. use_teach_measure  — activate / ritual / remember / ranker delta
  2. cadence            — progress-logged observe+inject cycles
  3. packs              — install/index core intel, domain probe
  4. prune_graph        — census + policy dry-run (no silent apply)
  5. stream_glyphs      — stream status + canon phrase state
  6. ops_surface        — single report path + prove-style checklist

Recommend-only; never host.mutate. Glyph: ⟲ + ❖ + 〰 + ✂ + ▣
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .activation import activate_repository
from .cadence import run_cadence
from .evolve_loop import close_signal_loop
from .glyphs.canon import encode_state, glyph_canon_registry, phrase
from .hippocampus import remember
from .hygiene import body_hygiene
from .packs import domain_route, index_packs_into_repo, install_pack, list_packs
from .prune import graph_census, policy_preview, prune_graph
from .ranker.model import ranker_status
from .session_ritual import run_session_ritual
from .stream import stream_status


def _engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _progress(msg: str, enabled: bool) -> None:
    if enabled:
        print(f"  ⟲ {msg}", file=sys.stderr, flush=True)


# Large bodies: full cadence continuum is too slow live (~4k+ synapses).
LARGE_GRAPH_SYNAPSE_THRESHOLD = 2500


def run_continuum(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    cycles: int = 24,
    budget: int = 400,
    pack_dir: Path | None = None,
    progress: bool = True,
    apply_prune: bool = False,
    force_full: bool = False,
    on_lane: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run all evolution lanes once; return a unified continuum report.

    On large graphs (many synapses), auto-throttles cadence unless force_full=True.
    Prune apply remains opt-in (default False) — do not thrash cleanup.
    """

    t0 = time.time()
    pack_dir = pack_dir or (_engine_root() / "packs" / "cortex-core-intel-v1")
    lanes: dict[str, Any] = {}
    checklist: list[dict[str, Any]] = []
    large_graph_note: dict[str, Any] = {"throttled": False}

    # ── Large-graph guard (live continuum too slow) ─────────────────────
    try:
        from .prune import graph_census

        census0 = graph_census(store, repo)
        syn_blk0 = census0.get("synapses") if isinstance(census0.get("synapses"), dict) else {}
        syn_n = int(
            syn_blk0.get("total")
            if syn_blk0 and syn_blk0.get("total") is not None
            else (census0.get("synapses") or 0)
            or 0
        )
        if syn_n >= LARGE_GRAPH_SYNAPSE_THRESHOLD and not force_full:
            # Fast path: tiny cadence, no prune apply, mark deferred full continuum
            cycles = min(int(cycles), 3)
            budget = min(int(budget), 280)
            apply_prune = False
            large_graph_note = {
                "throttled": True,
                "synapse_count": syn_n,
                "threshold": LARGE_GRAPH_SYNAPSE_THRESHOLD,
                "cycles_capped": cycles,
                "advice": (
                    "Large graph — live continuum throttled. Prefer fuse continuity + "
                    "eval-coupling + remember/seal; run full continuum offline with "
                    "--force-full if needed."
                ),
            }
            _progress(
                f"large graph · synapses={syn_n} · continuum throttled "
                f"cycles={cycles} (use force_full for full run)",
                progress,
            )
        else:
            large_graph_note = {
                "throttled": False,
                "synapse_count": syn_n,
                "force_full": bool(force_full),
            }
    except Exception as exc:
        large_graph_note = {
            "throttled": False,
            "census_error": f"{type(exc).__name__}: {exc}",
        }

    def lane_done(name: str, payload: dict[str, Any], ok: bool = True) -> None:
        lanes[name] = {"ok": ok, **payload}
        checklist.append({"lane": name, "ok": ok})
        if on_lane:
            on_lane(name, lanes[name])
        _progress(f"lane {name} · ok={ok}", progress)

    # ── Lane: packs (teach substrate first) ─────────────────────────────
    _progress("lane packs ▣", progress)
    pack_note: dict[str, Any] = {"installed": False, "indexed": False}
    try:
        listed = list_packs(home)
        pack_note["count_before"] = int(listed.get("count") or 0)
        if pack_note["count_before"] == 0 and pack_dir.is_dir():
            install_pack(pack_dir, home, force=True)
            pack_note["installed"] = True
        if pack_dir.is_dir() or pack_note["count_before"] or pack_note["installed"]:
            idx = index_packs_into_repo(store, home, repo)
            pack_note["indexed"] = True
            pack_note["index"] = {
                "cards": idx.get("cards") or idx.get("indexed") or idx.get("count"),
                "detail": {k: idx.get(k) for k in list(idx)[:12]},
            }
        route = domain_route(
            home,
            "evidence uncertainty confidence cite verify pack binary intel",
        )
        pack_note["probe"] = {
            "expand": route.get("expand"),
            "top_domain": route.get("top_domain"),
            "top_score": route.get("top_score"),
        }
        pack_note["count_after"] = int(list_packs(home).get("count") or 0)
        lane_done("packs", pack_note, ok=True)
    except Exception as exc:
        lane_done(
            "packs",
            {"error": f"{type(exc).__name__}: {exc}", **pack_note},
            ok=False,
        )

    # ── Lane: use → teach → measure (single real cycle) ─────────────────
    _progress("lane use_teach_measure", progress)
    utm: dict[str, Any] = {}
    try:
        ranker_before = int(ranker_status(store, repo).get("train_count") or 0)
        task = (
            "continuum use-teach-measure: evidence sparse interconnect evolve "
            "recommend-only local body"
        )
        act = activate_repository(
            home,
            store,
            governor,
            repo,
            task,
            budget=budget,
            profile="agent",
        )
        neural = (act.get("context") or {}).get("neural_interlink") or (
            act.get("context_full") or {}
        ).get("neural_interlink") or {}
        act_id = neural.get("activation_id")
        utm["activate"] = {
            "activation": act.get("activation"),
            "activation_id": act_id,
            "block": bool(act.get("block")),
            "glyph_line": act.get("glyph_line"),
            "packs_expand": (act.get("packs") or {}).get("expand"),
        }
        # teach: durable lesson from this use
        mem = remember(
            home,
            store,
            repo,
            kind="lesson",
            text=(
                f"Continuum v{__version__}: use cycle activation={act.get('activation')} "
                f"expand={(act.get('packs') or {}).get('expand')} — grow packs from evidence, "
                "not chat lore."
            ),
        )
        utm["remember"] = {"memory_id": mem.get("memory_id") or mem.get("id")}

        # measure via signal loop when we have an activation
        if act_id and not act.get("block"):
            mode = "normal"
            try:
                mode = str(governor.evaluate(repo).get("mode") or "normal")
            except Exception:
                pass
            if mode != "read_only":
                looped = close_signal_loop(
                    store,
                    repo,
                    activation_id=str(act_id),
                    status="verified" if act.get("activation") == "ready" else "helpful",
                    verification_type="continuum-utm",
                    task=task,
                    governance_mode=mode,
                    probe_k=4,
                )
                utm["evolve"] = {
                    "verdict": (looped.get("causal") or {}).get("verdict"),
                    "train_count": ((looped.get("outcome") or {}).get("ranker") or {}).get(
                        "train_count"
                    ),
                }
        ranker_after = int(ranker_status(store, repo).get("train_count") or 0)
        utm["measure"] = {
            "ranker_before": ranker_before,
            "ranker_after": ranker_after,
            "ranker_delta": ranker_after - ranker_before,
        }
        # light ritual seal of the teach beat
        try:
            ritual = run_session_ritual(
                home,
                store,
                governor,
                repo,
                "continuum teach seal",
                memories=[
                    {
                        "kind": "discovery",
                        "text": (
                            f"Continuum sealed use-teach-measure ranker_delta="
                            f"{utm['measure']['ranker_delta']}"
                        ),
                    }
                ],
                consolidate_session=True,
                profile="agent",
                force=True,
            )
            utm["ritual"] = {
                "ok": True,
                "session": ritual.get("session_id") or ritual.get("session"),
            }
        except Exception as exc:
            utm["ritual"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        lane_done("use_teach_measure", utm, ok=not bool(act.get("block")))
    except Exception as exc:
        lane_done(
            "use_teach_measure",
            {"error": f"{type(exc).__name__}: {exc}", **utm},
            ok=False,
        )

    # ── Lane: cadence (progress-logged, bounded) ────────────────────────
    _progress(f"lane cadence · cycles={cycles}", progress)
    try:
        cycle_marks: list[int] = []

        def _on_cycle(c: dict[str, Any]) -> None:
            n = int(c.get("cycle") or 0)
            cycle_marks.append(n)
            if progress and (n % max(1, cycles // 4) == 0 or n == cycles):
                obs = c.get("observe") or {}
                _progress(
                    f"  cadence c{n}/{cycles} family={c.get('family')} "
                    f"expand={obs.get('expand')} sparse={obs.get('sparse')}",
                    True,
                )

        cad = run_cadence(
            home,
            store,
            governor,
            repo,
            cycles=max(1, int(cycles)),
            budget=max(200, int(budget)),
            evolve_every=max(1, min(5, cycles)),
            seal_every=max(1, min(10, cycles)),
            hygiene_every=max(1, min(6, cycles)),
            pack_dir=pack_dir,
            on_cycle=_on_cycle,
            progress_every=max(1, min(5, cycles)),
        )
        lane_done(
            "cadence",
            {
                "cycles": cad.get("cycles"),
                "stats": cad.get("stats"),
                "report_path": cad.get("report_path"),
                "progress_ticks": len(cycle_marks),
                "elapsed_s": cad.get("elapsed_s"),
            },
            ok=int((cad.get("stats") or {}).get("activates") or 0) > 0,
        )
    except Exception as exc:
        lane_done("cadence", {"error": f"{type(exc).__name__}: {exc}"}, ok=False)

    # ── Lane: prune + graph ─────────────────────────────────────────────
    _progress("lane prune_graph ✂", progress)
    try:
        census = graph_census(store, repo)
        preview = policy_preview(store, repo)
        dry_soft = prune_graph(store, repo, policy="integrate_soft", dry_run=True)
        applied = None
        would = int(dry_soft.get("would_prune") or 0)
        if apply_prune and would >= 50:
            applied = prune_graph(store, repo, policy="integrate_soft", dry_run=False)
        hygiene = body_hygiene(home, store, repo)
        nodes_blk = census.get("nodes") if isinstance(census.get("nodes"), dict) else {}
        syn_blk = census.get("synapses") if isinstance(census.get("synapses"), dict) else {}
        lane_done(
            "prune_graph",
            {
                "census": {
                    "nodes": nodes_blk.get("total") if nodes_blk else census.get("nodes"),
                    "synapses": syn_blk.get("total") if syn_blk else census.get("synapses"),
                    "by_class": syn_blk.get("by_kernel_class"),
                    "regions": nodes_blk.get("regions"),
                },
                "policy_preview": preview,
                "integrate_soft_dry": {
                    "would_prune": would,
                    "policy": dry_soft.get("policy"),
                },
                "applied": applied,
                "hygiene_advice": hygiene.get("advice"),
                "apply_prune_requested": apply_prune,
            },
            ok=True,
        )
    except Exception as exc:
        lane_done("prune_graph", {"error": f"{type(exc).__name__}: {exc}"}, ok=False)

    # ── Lane: stream + glyphs ───────────────────────────────────────────
    _progress("lane stream_glyphs 〰◈", progress)
    try:
        stream = stream_status(store, repo)
        try:
            grow = phrase("grow_seal")
        except Exception:
            grow = {"line": "❖", "id": "grow_seal"}
        try:
            gstate = encode_state(
                control={"ok": True, "block": False},
                governor=governor.evaluate(repo),
                aria={"mode": "dormant"},
                loop={"closed": True, "continuum": True},
            )
        except Exception as exc:
            gstate = {"error": f"{type(exc).__name__}: {exc}"}
        canon = glyph_canon_registry()
        lane_done(
            "stream_glyphs",
            {
                "stream": {
                    "stream_id": stream.get("stream_id"),
                    "frames": stream.get("frame_count"),
                    "alive": stream.get("alive"),
                },
                "phrase": grow.get("line") or grow,
                "glyph_state": gstate,
                "canon_keys": list((canon.get("glyphs") or canon.get("entries") or {}))[:16]
                if isinstance(canon, dict)
                else [],
            },
            ok=bool(stream.get("stream_id") or stream.get("frame_count") is not None),
        )
    except Exception as exc:
        lane_done("stream_glyphs", {"error": f"{type(exc).__name__}: {exc}"}, ok=False)

    # ── Lane: ops surface (prove-style checklist) ───────────────────────
    _progress("lane ops_surface", progress)
    ops = {
        "version": __version__,
        "command": "cortex continuum --repo <name> --json",
        "lanes_ok": sum(1 for c in checklist if c.get("ok")),
        "lanes_total": len(checklist),
        "checklist": checklist,
        "prove_surface": [
            "cortex continuum --repo R --cycles 24 --json",
            "cortex cadence --repo R --cycles 20 --progress --json",
            "cortex packs list --json",
            "cortex graph --stats --repo R --json",
            "cortex prune --repo R --policy integrate_soft --dry-run --json",
            "cortex stream --repo R --json",
            "cortex glyphs --json",
            "cortex hygiene --repo R --json",
        ],
        "claim_boundary": (
            "Continuum orchestrates existing organs on one SQLite body; "
            "recommend-only; never mutates host source; prune apply is opt-in."
        ),
    }
    lane_done("ops_surface", ops, ok=ops["lanes_ok"] >= 4)

    elapsed = round(time.time() - t0, 3)
    try:
        grow_line = phrase("grow_seal").get("line")
    except Exception:
        grow_line = "❖ continuum"

    # Seam: system coherence + emergence log after multi-lane pass
    coherence: dict[str, Any] | None = None
    emergence: dict[str, Any] | None = None
    try:
        from .coherence import measure_coherence
        from .emergence_log import log_milestone, read_emergence_log

        coherence = measure_coherence(store, repo, governor=governor, home=home)
        log_milestone(
            home,
            store,
            repo,
            kind="continuum_seal",
            summary=(
                f"Continuum sealed cycles={cycles} lanes_ok={ops['lanes_ok']}/"
                f"{ops['lanes_total']} coherence={coherence.get('score')} "
                f"emergent={coherence.get('emergent_coupling')}"
            ),
            payload={
                "cycles": cycles,
                "lanes_ok": ops["lanes_ok"],
                "coherence_score": coherence.get("score"),
                "emergent_coupling": coherence.get("emergent_coupling"),
            },
            source="continuum",
        )
        emergence = read_emergence_log(home, store, repo, limit=10)
    except Exception as exc:
        coherence = {"error": f"{type(exc).__name__}: {exc}"}
        emergence = None

    report: dict[str, Any] = {
        "schema_version": "cortex-continuum/1.3",
        "glyph": "⟲❖〰✂▣",
        "phrase": grow_line,
        "version": __version__,
        "repo": repo,
        "elapsed_s": elapsed,
        "cycles": cycles,
        "large_graph": large_graph_note,
        "lanes": lanes,
        "coherence": coherence,
        "emergence_log": emergence,
        "summary": {
            "lanes_ok": ops["lanes_ok"],
            "lanes_total": ops["lanes_total"],
            "ranker_delta": ((lanes.get("use_teach_measure") or {}).get("measure") or {}).get(
                "ranker_delta"
            ),
            "cadence_activates": ((lanes.get("cadence") or {}).get("stats") or {}).get(
                "activates"
            ),
            "cadence_evolves": ((lanes.get("cadence") or {}).get("stats") or {}).get("evolves"),
            "stream_frames": ((lanes.get("stream_glyphs") or {}).get("stream") or {}).get(
                "frames"
            ),
            "would_prune_integrate_soft": (
                (lanes.get("prune_graph") or {}).get("integrate_soft_dry") or {}
            ).get("would_prune"),
            "packs_count": (lanes.get("packs") or {}).get("count_after"),
            "coherence_score": (coherence or {}).get("score"),
            "coherence_above_threshold": (coherence or {}).get("above_threshold"),
            "emergent_coupling": (coherence or {}).get("emergent_coupling"),
        },
        "claim_boundary": ops["claim_boundary"],
    }

    try:
        log_dir = Path(home) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"continuum-{repo}-{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
        store.set_setting(
            f"continuum_latest:{repo}",
            {
                "at": time.time(),
                "summary": report["summary"],
                "path": str(path),
                "version": __version__,
            },
        )
    except Exception as exc:
        report["report_error"] = f"{type(exc).__name__}: {exc}"

    _progress(
        f"done · lanes_ok={ops['lanes_ok']}/{ops['lanes_total']} · {elapsed}s",
        progress,
    )
    return report
