"""Automated evolution cadence — observe, inject, measure (not free thrash).

Runs N cycles of enter → observe → surgical inject → periodic evolve/seal.
Recommend-only; never host.mutate. Glyph: ⟲ + ❖.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .activation import activate_repository
from .evolve_loop import close_signal_loop
from .glyphs.canon import phrase
from .hippocampus import remember
from .hygiene import body_hygiene
from .kernels import annotate_synapses, kernels_status
from .packs import domain_route, index_packs_into_repo, install_pack, list_packs
from .prune import decay_unused_weights, prune_graph
from .ranker.model import ranker_status
from .session_ritual import run_session_ritual
from .stream import stream_status

# Rotating HIGH-card task families (taught pack)
TASK_FAMILIES: list[dict[str, str]] = [
    {
        "id": "evidence",
        "task": "evidence uncertainty confidence cite verify enough unknown",
        "expect_domain": "evidence",
    },
    {
        "id": "falsify",
        "task": "falsify counterexample disprove edge case regression",
        "expect_domain": "evidence",
    },
    {
        "id": "sparse",
        "task": "sparse activation budget token thrift lean nodes fired",
        "expect_domain": "evidence",
    },
    {
        "id": "abstain",
        "task": "abstain constrained blast radius refuse read_only re-verify",
        "expect_domain": "governance",
    },
    {
        "id": "enter_seal",
        "task": "enter exit seal ritual breathe stream cardiac cycle",
        "expect_domain": "interconnect",
    },
    {
        "id": "trust",
        "task": "control trust recommend-only immune authority source tests",
        "expect_domain": "governance",
    },
    {
        "id": "zero_in",
        "task": "domain zero-in expand pack binary intel portable",
        "expect_domain": "knowledge",
    },
    {
        "id": "agent_loop",
        "task": "agent operating loop enter work remember ritual evolve",
        "expect_domain": "interconnect",
    },
    {
        "id": "interconnect",
        "task": "interconnect mesh connect pulse lattice resonate organ",
        "expect_domain": "interconnect",
    },
    {
        "id": "evolution",
        "task": "evolve harness ranker plasticity signal loop improve",
        "expect_domain": "evolution",
    },
]


def _engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_cadence(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    cycles: int = 1000,
    budget: int = 400,
    evolve_every: int = 10,
    seal_every: int = 50,
    hygiene_every: int = 25,
    pack_dir: Path | None = None,
    on_cycle: Callable[[dict[str, Any]], None] | None = None,
    stop_on_block: bool = True,
) -> dict[str, Any]:
    """Run automated evolution cadence with observation-driven injections."""

    cycles = max(1, int(cycles))
    t0 = time.time()
    pack_dir = pack_dir or (_engine_root() / "packs" / "cortex-core-intel-v1")
    injections: list[dict[str, Any]] = []
    cycle_logs: list[dict[str, Any]] = []
    last_act_id: str | None = None
    stats = {
        "activates": 0,
        "evolves": 0,
        "seals": 0,
        "decays": 0,
        "prunes": 0,
        "reindexes": 0,
        "pack_installs": 0,
        "remembers": 0,
        "blocks": 0,
        "expand_hits": 0,
        "expand_misses": 0,
        "ranker_start": int(ranker_status(store, repo).get("train_count") or 0),
    }

    # Bootstrap surgical: ensure packs present
    listed = list_packs(home)
    if (listed.get("count") or 0) == 0 and pack_dir.is_dir():
        try:
            install_pack(pack_dir, home, force=True)
            index_packs_into_repo(store, home, repo)
            stats["pack_installs"] += 1
            stats["reindexes"] += 1
            injections.append(
                {
                    "cycle": 0,
                    "kind": "pack_bootstrap",
                    "detail": "installed+indexed core pack",
                }
            )
        except Exception as exc:
            injections.append(
                {
                    "cycle": 0,
                    "kind": "pack_bootstrap_fail",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )

    progress_path = Path(home) / "logs" / f"cadence-progress-{repo}.jsonl"
    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        progress_path = Path(home) / f"cadence-progress-{repo}.jsonl"

    for i in range(1, cycles + 1):
        fam = TASK_FAMILIES[(i - 1) % len(TASK_FAMILIES)]
        task = fam["task"]
        cycle: dict[str, Any] = {
            "cycle": i,
            "family": fam["id"],
            "task": task[:80],
            "injections": [],
        }

        # --- ENTER ---
        try:
            act = activate_repository(
                home,
                store,
                governor,
                repo,
                task,
                budget=budget,
                profile="agent",
            )
            stats["activates"] += 1
        except Exception as exc:
            cycle["error"] = f"activate:{type(exc).__name__}:{exc}"
            cycle_logs.append(cycle)
            if on_cycle:
                on_cycle(cycle)
            continue

        ctx = act.get("context") or {}
        full = act.get("context_full") or {}
        neural = ctx.get("neural_interlink") or full.get("neural_interlink") or {}
        act_id = neural.get("activation_id")
        if act_id:
            last_act_id = str(act_id)
        packs = act.get("packs") or ctx.get("packs") or {}
        blocked = bool(act.get("block") or (act.get("control_error") or {}).get("block"))
        sparse = float(
            (neural.get("metrics") or {}).get("sparse_activation_ratio") or 0.0
        )
        expand = bool(packs.get("expand"))
        top_domain = packs.get("top_domain")
        if expand:
            stats["expand_hits"] += 1
        else:
            stats["expand_misses"] += 1
        if blocked:
            stats["blocks"] += 1

        cycle["observe"] = {
            "activation": act.get("activation"),
            "blocked": blocked,
            "immune": (act.get("immune_action") or {}).get("code"),
            "act_id": act_id,
            "packs_domain": top_domain,
            "packs_score": packs.get("top_score"),
            "expand": expand,
            "sparse": sparse,
            "glyph": act.get("glyph_line"),
            "stream_frames": (act.get("stream") or {}).get("frame_count"),
        }

        # --- SURGICAL INJECTIONS ---
        def inject(kind: str, detail: str = "") -> None:
            item = {"cycle": i, "kind": kind, "detail": detail}
            cycle["injections"].append(item)
            injections.append(item)

        if blocked and stop_on_block:
            inject("skip_learning_blocked", "immune/control block")
            cycle_logs.append(cycle)
            if on_cycle:
                on_cycle(cycle)
            # still allow hygiene later
            if i % hygiene_every == 0:
                _hygiene_tick(store, home, repo, i, inject, stats)
            continue

        # Domain miss: expected domain not near top → reindex packs
        if i % 5 == 0 or (not expand and fam["id"] in {"evidence", "enter_seal", "trust"}):
            route = domain_route(home, task)
            cycle["observe"]["route_top"] = route.get("top_domain")
            if not route.get("expand") and (listed.get("count") or stats["pack_installs"]):
                try:
                    index_packs_into_repo(store, home, repo)
                    stats["reindexes"] += 1
                    inject("reindex_packs", "expand false on domain task")
                except Exception as exc:
                    inject("reindex_fail", f"{type(exc).__name__}:{exc}")

        # Sparse too high → remember thrift doctrine (teach injection)
        if sparse > 0.15:
            try:
                remember(
                    home,
                    store,
                    repo,
                    kind="lesson",
                    text=(
                        f"Cadence c{i}: sparse_ratio={sparse:.4f} elevated — "
                        "prefer lean budget and HIGH pack cards over full scan."
                    ),
                )
                stats["remembers"] += 1
                inject("remember_sparse", f"sparse={sparse:.4f}")
            except Exception as exc:
                inject("remember_fail", str(exc))

        # Periodic hygiene: prune dry / decay / annotate
        if i % hygiene_every == 0:
            _hygiene_tick(store, home, repo, i, inject, stats)

        # Periodic evolve (verified synthetic: activation ready + packs tests not each time)
        # Use status verified when activation ready; helpful otherwise
        if i % evolve_every == 0 and last_act_id:
            mode = "normal"
            try:
                mode = str(governor.evaluate(repo).get("mode") or "normal")
            except Exception:
                pass
            if mode == "read_only":
                inject("evolve_skipped_read_only", "")
            else:
                try:
                    status = "verified" if act.get("activation") == "ready" else "helpful"
                    looped = close_signal_loop(
                        store,
                        repo,
                        activation_id=last_act_id,
                        status=status,
                        verification_type=f"cadence-c{i}",
                        task=task,
                        governance_mode=mode,
                        probe_k=4,
                    )
                    stats["evolves"] += 1
                    rk = (looped.get("outcome") or {}).get("ranker") or {}
                    inject(
                        "evolve",
                        f"verdict={(looped.get('causal') or {}).get('verdict')} "
                        f"trained={rk.get('trained')} train={rk.get('train_count')}",
                    )
                    cycle["evolve"] = {
                        "verdict": (looped.get("causal") or {}).get("verdict"),
                        "trained": rk.get("trained"),
                        "train_count": rk.get("train_count"),
                    }
                except Exception as exc:
                    inject("evolve_fail", f"{type(exc).__name__}:{exc}")

        # Periodic seal
        if i % seal_every == 0:
            try:
                run_session_ritual(
                    home,
                    store,
                    governor,
                    repo,
                    f"cadence seal cycle {i}",
                    memories=[
                        {
                            "kind": "discovery",
                            "text": (
                                f"Cadence seal c{i}/{cycles}: activates={stats['activates']} "
                                f"evolves={stats['evolves']} ranker="
                                f"{ranker_status(store, repo).get('train_count')}"
                            ),
                        }
                    ],
                    consolidate_session=True,
                    profile="agent",
                    force=True,
                )
                stats["seals"] += 1
                inject("seal", f"c{i}")
            except Exception as exc:
                inject("seal_fail", f"{type(exc).__name__}:{exc}")

        # Soft progress remember every 100
        if i % 100 == 0:
            try:
                remember(
                    home,
                    store,
                    repo,
                    kind="discovery",
                    text=(
                        f"Cadence milestone {i}/{cycles}: expand_hits={stats['expand_hits']} "
                        f"evolves={stats['evolves']} injections={len(injections)} "
                        f"phrase={phrase('grow_seal').get('line')}"
                    ),
                )
                stats["remembers"] += 1
                inject("milestone", f"c{i}")
            except Exception:
                pass

        cycle_logs.append(cycle)
        # Keep only last 50 full cycle logs in memory; milestones always kept in injections
        if len(cycle_logs) > 50:
            cycle_logs = cycle_logs[-50:]
        # Progress trail every 25 cycles (and final) so kill ≠ total loss
        if i % 25 == 0 or i == cycles:
            try:
                progress_path.open("a", encoding="utf-8").write(
                    json.dumps(
                        {
                            "cycle": i,
                            "of": cycles,
                            "stats": {
                                "activates": stats["activates"],
                                "evolves": stats["evolves"],
                                "seals": stats["seals"],
                                "expand_hits": stats["expand_hits"],
                                "ranker": ranker_status(store, repo).get("train_count"),
                            },
                            "at": time.time(),
                        },
                        default=str,
                    )
                    + "\n"
                )
            except Exception:
                pass
        if on_cycle:
            on_cycle(cycle)

    ranker_end = int(ranker_status(store, repo).get("train_count") or 0)
    stream = stream_status(store, repo)
    hygiene = body_hygiene(home, store, repo)
    kernels = kernels_status(store, repo)
    try:
        grow = phrase("grow_seal").get("line")
    except Exception:
        grow = "❖"

    report = {
        "schema_version": "cortex-cadence/1.0",
        "glyph": "⟲",
        "phrase": grow,
        "version": __version__,
        "repo": repo,
        "cycles": cycles,
        "elapsed_s": round(time.time() - t0, 3),
        "stats": {
            **stats,
            "ranker_end": ranker_end,
            "ranker_delta": ranker_end - stats["ranker_start"],
            "injection_count": len(injections),
        },
        "stream": {
            "stream_id": stream.get("stream_id"),
            "frames": stream.get("frame_count"),
            "alive": stream.get("alive"),
        },
        "hygiene": hygiene.get("graph"),
        "hygiene_advice": hygiene.get("advice"),
        "kernels_dominant": kernels.get("dominant"),
        "injections_tail": injections[-40:],
        "cycles_tail": cycle_logs[-20:],
        "claim_boundary": (
            "Cadence automates observe/inject/measure on the durable body; "
            "never host source mutation; surgical only under governor modes."
        ),
    }

    # Persist report under CORTEX_HOME/logs
    try:
        log_dir = Path(home) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"cadence-{repo}-{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
        store.set_setting(
            f"cadence_latest:{repo}",
            {
                "at": time.time(),
                "cycles": cycles,
                "stats": report["stats"],
                "path": str(path),
            },
        )
    except Exception as exc:
        report["report_error"] = f"{type(exc).__name__}: {exc}"

    return report


def _hygiene_tick(
    store: Any,
    home: Path,
    repo: str,
    cycle: int,
    inject: Callable[..., None],
    stats: dict[str, Any],
) -> None:
    try:
        # Align with v6.10: dry-run integrate_soft; apply only if meaningful tail
        dry = prune_graph(store, repo, policy="integrate_soft", dry_run=True)
        would = int(dry.get("would_prune") or 0)
        if would >= 50:
            real = prune_graph(store, repo, policy="integrate_soft", dry_run=False)
            stats["prunes"] += 1
            inject(
                "prune_integrate_soft",
                f"removed={real.get('pruned')} would={would}",
            )
        else:
            inject("prune_dry_clean", f"integrate_soft would={would}")
        # Mild spectral decay occasionally
        if cycle % 50 == 0:
            dec = decay_unused_weights(store, repo, factor=0.98)
            stats["decays"] += 1
            inject("decay", f"touched={dec.get('touched')}")
        annotate_synapses(store, repo)
        inject("annotate_kernels", "")
    except Exception as exc:
        inject("hygiene_fail", f"{type(exc).__name__}:{exc}")
