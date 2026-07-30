from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_repo_config, runtime_directory
from .context import build_context
from .environment import learn_environment
from .graph import resolve_graph
from .hippocampus import begin_session
from .indexer import current_manifest_hash, index_repository
from .neuron import compile_interlink, neural_graph_state
from .telemetry import ingest_git
from .verify import verify_repository


def activate_repository(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    task: str,
    budget: int = 1200,
    refresh: str = "auto",
    profile: str = "agent",
    prefetch: str = "auto",
) -> dict[str, Any]:
    repository = store.repo(repo)
    if not repository:
        raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
    root = Path(repository["path"])
    config = load_repo_config(root)
    observed_manifest = current_manifest_hash(root, config)
    manifest_current = observed_manifest == (repository["manifest_hash"] or "")
    refresh_result: dict[str, Any] | None = None

    surprise: dict[str, Any] = {
        "schema_version": "cortex-surprise/1.0",
        "glyph": "Δ",
        "refreshed": False,
        "manifest_current_before": manifest_current,
        "files_reindexed": 0,
        "files_unchanged": 0,
        "surprise_ratio": 0.0,
        "claim_boundary": "Surprise is an incremental work proxy, not biological prediction error.",
    }
    if refresh == "always" or (refresh == "auto" and not manifest_current):
        refresh_result = index_repository(store, repo, config, force=False)
        reindexed = int(refresh_result.get("indexed_files_this_run") or 0)
        unchanged = int(refresh_result.get("unchanged_files") or 0)
        denom = max(1, reindexed + unchanged)
        surprise = {
            "schema_version": "cortex-surprise/1.0",
            "glyph": "Δ",
            "refreshed": True,
            "manifest_current_before": False,
            "files_reindexed": reindexed,
            "files_unchanged": unchanged,
            "deferred_files": int(
                (refresh_result.get("aria_substrate") or {}).get("deferred_files") or 0
            ),
            "surprise_ratio": round(reindexed / denom, 6),
            "claim_boundary": (
                "Surprise is an incremental work proxy, not biological prediction error."
            ),
        }
        resolve_graph(store, repo)
        ingest_git(store, repo, root, config.git_commit_limit)
        environment = (
            learn_environment(root, store, repo, runtime_directory(root, config))
            if config.environment_learning_enabled
            else {"available": False, "disabled": True}
        )
        neural = (
            compile_interlink(store, repo)
            if config.neural_interlink_enabled
            else {"available": False, "disabled": True}
        )
        certificate = verify_repository(home, store, repo, config, write_certificate=True)
        manifest_current = certificate["manifest"]["current"]
    else:
        environment = store.environment_profile(repo)
        if config.environment_learning_enabled and not environment:
            environment = learn_environment(
                root, store, repo, runtime_directory(root, config)
            )
        if not config.environment_learning_enabled:
            environment = {"available": False, "disabled": True}
        if config.neural_interlink_enabled and not store.neural_nodes(repo):
            neural = compile_interlink(store, repo)
        elif config.neural_interlink_enabled:
            neural = neural_graph_state(store, repo)
        else:
            neural = {"available": False, "disabled": True}
        certificate = verify_repository(home, store, repo, config, write_certificate=False)

    context = build_context(
        home,
        store,
        governor,
        repo,
        task,
        budget,
        manifest_current=manifest_current,
        certificate=certificate,
    )
    # Attach surprise to efficiency for agent-visible economics.
    if isinstance(context.get("efficiency"), dict):
        context["efficiency"]["surprise"] = surprise
    # v6.13: end-to-end spectral memory pulse (U, Λ_g, fit δ, diffusion fuel)
    spectral_memory: dict[str, Any] | None = None
    conf = float(
        ((context.get("governance") or {}).get("components") or {}).get(
            "retrieval_confidence"
        )
        or ((context.get("governor") or {}).get("components") or {}).get(
            "retrieval_confidence"
        )
        or 0.5
    )
    try:
        from .math_net.spectral_memory import spectral_memory_pulse

        cert_st = str((certificate or {}).get("status") or "unknown")
        spectral_memory = spectral_memory_pulse(
            store,
            repo,
            retrieval_confidence=conf,
            certificate_status=cert_st,
            manifest_current=manifest_current,
            budget_tokens=budget,
            auto_promote=True,
        )
        context["spectral_memory"] = spectral_memory
        context["u"] = (spectral_memory.get("u") or {}).get("u")
        if isinstance(context.get("governance"), dict) and spectral_memory.get("u"):
            context["governance"] = {
                **context["governance"],
                "uncertainty": spectral_memory["u"],
            }
        elif isinstance(context.get("governor"), dict) and spectral_memory.get("u"):
            context["governor"] = {
                **context["governor"],
                "uncertainty": spectral_memory["u"],
            }
    except Exception as exc:
        spectral_memory = {"error": f"{type(exc).__name__}: {exc}", "end_to_end": False}
        context["spectral_memory"] = spectral_memory
    # Seam: soft-bind fusion when CORTEX_FUSE_AUTO=1; always measure coherence
    fusion_bind: dict[str, Any] | None = None
    try:
        from .coherence import measure_coherence, soft_bind_fusion

        fusion_bind = soft_bind_fusion(home, store, governor, repo, task=task)
        context["fusion_bind"] = fusion_bind
        conf_for_c = conf
        if context.get("u") is not None:
            conf_for_c = max(0.0, min(1.0, 1.0 - float(context.get("u") or 0.5)))
        context["coherence"] = measure_coherence(
            store,
            repo,
            governor=governor,
            home=home,
            retrieval_confidence=conf_for_c,
        )
    except Exception as exc:
        context["coherence"] = {"error": f"{type(exc).__name__}: {exc}"}
        fusion_bind = None
    session = begin_session(home, store, repo, task)
    from . import __version__
    from .organism import (
        build_organism,
        load_prior_pulse,
        persist_organism_pulse,
        save_prior_pulse,
    )
    from .profiles import project_packet

    prior = load_prior_pulse(store, repo)
    organism = build_organism(
        repo=repo,
        repository_id=str(repository["repository_id"] or ""),
        task=task,
        session=session,
        context=context,
        surprise=surprise,
        prior_pulse=prior,
        cortex_version=__version__,
        phase="systole",
    )
    context["organism"] = organism
    # Re-hash packet including organism bond.
    import hashlib
    import json as _json

    to_hash = {k: v for k, v in context.items() if k not in {"packet_path", "packet_hash"}}
    context["packet_hash"] = hashlib.sha256(
        _json.dumps(to_hash, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    persist_organism_pulse(store, repo, organism, session_id=session.get("session_id"))
    save_prior_pulse(store, repo, organism["pulse"])

    # Consciousness stream 〰: rebind durable episodic thread; session bond is temporary.
    try:
        from .stream import append_stream_frame, stream_context_for_packet, stream_status

        stream_surface = stream_context_for_packet(
            store,
            repo,
            task=task,
            session_id=session.get("session_id"),
            control=context.get("control_error") or {},
            governor=context.get("governor") or {},
            aria=context.get("aria_materialization") or {},
        )
        append_stream_frame(
            store,
            repo,
            kind="activate" if refresh != "never" else "breathe",
            task=task,
            session_id=session.get("session_id"),
            surface="activate" if refresh != "never" else "breathe",
            payload={
                "activation": (
                    "ready" if certificate["status"] == "verified" else "degraded"
                ),
                "budget": budget,
                "profile": profile,
            },
            glyph_line=stream_surface.get("glyph_line"),
        )
        status = stream_status(store, repo)
        context["stream"] = {
            **stream_surface,
            "frame_count": status.get("frame_count"),
            "chain_tip": status.get("chain_tip"),
            "recent_frames": status.get("recent_frames"),
        }
        organism["stream"] = {
            "glyph": "〰",
            "stream_id": status.get("stream_id"),
            "frame_count": status.get("frame_count"),
            "alive": status.get("alive"),
            "continuity": stream_surface.get("continuity"),
        }
    except Exception as exc:
        context["stream"] = {
            "glyph": "〰",
            "alive": False,
            "error": f"{type(exc).__name__}: {exc}",
            "claim_boundary": "Stream optional; activation still valid without it.",
        }

    # Prefetch (v5): proactive evidence proposal — never ARIA surprise-wake.
    prediction: dict[str, Any] | None = None
    gov_mode = str((context.get("governor") or {}).get("mode") or "normal")
    do_prefetch = prefetch == "aggressive" or (
        prefetch == "auto" and gov_mode != "read_only"
    )
    if do_prefetch:
        try:
            from .predict import predict_context

            pref_budget = min(200, max(80, budget // 6))
            if prefetch == "aggressive":
                pref_budget = min(400, budget // 3)
            prediction = predict_context(
                store,
                repo,
                task,
                budget=pref_budget,
                session_id=session.get("session_id"),
                governor_mode=gov_mode,
            )
            context["prediction"] = {
                "trace_id": prediction.get("trace_id"),
                "predicted_paths": prediction.get("predicted_paths"),
                "scores": prediction.get("scores"),
            }
        except Exception:
            prediction = None

    # Connect pass: gather multi-surface metrics, expand metric graph, distill.
    from .connect_pass import record_connect_pass

    # Close prefetch→precision loop when prediction exists
    if prediction and prediction.get("trace_id"):
        try:
            from .predict import record_prediction_outcome

            used = [
                str(e.get("path") or "")
                for e in (context.get("evidence") or [])
                if e.get("path")
            ]
            pred_set = set(prediction.get("predicted_paths") or [])
            # Mark prefetch hits on evidence metadata for ranker features
            for item in context.get("evidence") or []:
                if isinstance(item, dict) and item.get("path") in pred_set:
                    meta = item.get("metadata") or {}
                    meta = {**meta, "prefetch_hit": True}
                    item["metadata"] = meta
            record_prediction_outcome(
                store, str(prediction["trace_id"]), used
            )
        except Exception:
            pass

    connect = record_connect_pass(
        store,
        home,
        repo=repo,
        task=task,
        session_id=session.get("session_id"),
        surface="breathe" if refresh == "never" else "activate",
        context=context,
        surprise=surprise,
        organism=organism,
        activation="ready" if certificate["status"] == "verified" else "read_only",
        block=bool((context.get("control_error") or {}).get("block")),
        auto_distill=True,
    )
    metrics_in = connect.get("metrics") or {}
    context["connect_pass"] = {
        "pass_id": connect.get("pass_id"),
        "pass_count": connect.get("pass_count"),
        "metric_graph": connect.get("metric_graph"),
        "distilled_count": len(connect.get("distilled") or []),
        "causal": connect.get("causal"),
        "decay": connect.get("decay"),
        "intel_pulse": connect.get("intel_pulse"),
        "spectral": connect.get("spectral"),
        # Pack interconnection on the connect pulse (enter→connect)
        "pack_top_domain": metrics_in.get("pack_top_domain")
        or (context.get("packs") or {}).get("top_domain"),
        "pack_expand": metrics_in.get("pack_expand")
        if "pack_expand" in metrics_in
        else (context.get("packs") or {}).get("expand"),
        "pack_evidence_paths": metrics_in.get("pack_evidence_paths"),
    }
    # Re-resonate organism nervous mesh with intel pulse (same frequency)
    if isinstance(organism.get("body"), dict):
        nervous = organism["body"].setdefault("nervous", {})
        mesh = nervous.setdefault("mesh", {})
        ip = connect.get("intel_pulse") or {}
        mesh["connect_pass_count"] = connect.get("pass_count")
        mesh["intel_beat"] = ip.get("beat")
        mesh["intel_intensity"] = (ip.get("resonance") or {}).get("intensity")
        mesh["intel_brightness"] = (ip.get("resonance") or {}).get("brightness")
        context["organism"] = organism

    full_context = context
    context = project_packet(full_context, profile)
    runtime_path = runtime_directory(root, config) / "context_latest.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(full_context, indent=2) + "\n", encoding="utf-8")

    control = full_context.get("control_error") or {}
    identity_report: dict[str, Any] | None = None
    try:
        from .identity import continuity_check

        identity_report = continuity_check(store, repo=repo)
    except Exception:
        identity_report = None
    # Envelope parity (v6.8): glyph_state + stream always on activate JSON root.
    glyph_state = full_context.get("glyph_state") or context.get("glyph_state")
    stream_env = full_context.get("stream") or context.get("stream")
    if isinstance(stream_env, dict):
        stream_env = {
            "glyph": stream_env.get("glyph") or "〰",
            "stream_id": stream_env.get("stream_id"),
            "alive": stream_env.get("alive"),
            "frame_count": stream_env.get("frame_count"),
            "last_task": stream_env.get("last_task"),
            "glyph_line": stream_env.get("glyph_line"),
            "continuity": stream_env.get("continuity"),
            "recent_frames": (stream_env.get("recent_frames") or [])[-4:],
        }
    aria_language: dict[str, Any] | None = None
    try:
        from .glyphs.canon import phrasebook, speak_line

        g_line = (
            (glyph_state or {}).get("line") if isinstance(glyph_state, dict) else None
        )
        aria_language = {
            "medium": "glyph_canon",
            "glyph": "◈",
            "line": g_line,
            "spoken": speak_line(g_line or "") if g_line else [],
            "phrasebook": phrasebook(),
            "automatic_execution": False,
            "claim_boundary": (
                "ARIA language here is reusable glyph phrases only; never opcodes "
                "or host mutation authority."
            ),
        }
    except Exception:
        aria_language = None
    return {
        "activation": "ready" if certificate["status"] == "verified" else "read_only",
        "repo": repo,
        "task": task,
        "profile": profile,
        "bootstrap_status": certificate["status"],
        "manifest_current": manifest_current,
        "refresh": refresh_result,
        "surprise": surprise,
        "read_first": True,
        "block": bool(control.get("block")),
        "immune_action": control.get("immune_action"),
        "control_error": control,
        "identity": identity_report,
        "glyph_state": glyph_state,
        "glyph_line": (
            (glyph_state or {}).get("line") if isinstance(glyph_state, dict) else None
        ),
        "stream": stream_env,
        "spectral_memory": full_context.get("spectral_memory") or spectral_memory,
        "u": full_context.get("u"),
        "coherence": full_context.get("coherence"),
        "emergence_log": full_context.get("emergence_log"),
        "fusion_bind": full_context.get("fusion_bind") or fusion_bind,
        "aria_language": aria_language,
        "packs": full_context.get("packs") or context.get("packs"),
        "connect_pass": connect,
        "prediction": prediction,
        "organism": organism,
        "environment": environment,
        "neural_interlink": neural,
        "session": session,
        "context": context,
        "context_full": full_context if profile != "debug" else None,
        "runtime_packet": str(runtime_path),
    }
