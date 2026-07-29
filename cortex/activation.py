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
    context["connect_pass"] = {
        "pass_id": connect.get("pass_id"),
        "pass_count": connect.get("pass_count"),
        "metric_graph": connect.get("metric_graph"),
        "distilled_count": len(connect.get("distilled") or []),
        "causal": connect.get("causal"),
        "decay": connect.get("decay"),
    }

    full_context = context
    context = project_packet(full_context, profile)
    runtime_path = runtime_directory(root, config) / "context_latest.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(full_context, indent=2) + "\n", encoding="utf-8")

    control = full_context.get("control_error") or {}
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
