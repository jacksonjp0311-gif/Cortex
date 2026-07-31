"""Repository activation — v6.25.1 controller-first, sterile baseline path."""

from __future__ import annotations

import hashlib
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


def resolve_activation_controller(
    governor: Any,
    repo: str,
    *,
    memory_controller: str | None = None,
    force_evidence_baseline: bool = False,
    manifest_current: bool | None = None,
) -> dict[str, Any]:
    """Resolve controller before any side effect. Fail closed to evidence_baseline."""
    from .controller_scope import normalize_controller

    fail_closed = False
    reason = "advanced_allowed"
    gov_pre: dict[str, Any] = {}
    try:
        gov_pre = governor.evaluate(
            repo, retrieval_confidence=0.5, manifest_current=manifest_current
        )
    except Exception as exc:
        fail_closed = True
        reason = f"internal_control_failure:governor:{type(exc).__name__}"
        gov_pre = {
            "mode": "read_only",
            "reason": reason,
            "stability": 0.0,
        }

    try:
        from .memory_simplex import resolve_controller

        sx = resolve_controller(
            requested=memory_controller,
            governance_mode=str(gov_pre.get("mode") or "read_only"),
            force_baseline=bool(force_evidence_baseline) or fail_closed,
        )
        controller = normalize_controller(str(sx.get("controller") or "evidence_baseline"))
        if fail_closed:
            controller = "evidence_baseline"
            reason = reason if reason.startswith("internal") else str(sx.get("reason") or reason)
        else:
            reason = str(sx.get("reason") or reason)
            if force_evidence_baseline:
                controller = "evidence_baseline"
                reason = "force_baseline"
    except Exception as exc:
        fail_closed = True
        controller = "evidence_baseline"
        reason = f"internal_control_failure:simplex:{type(exc).__name__}"
        sx = {"error": f"{type(exc).__name__}: {exc}"}

    # capability issued after caller binds epoch (see activate_repository)
    return {
        "controller": controller,
        "fail_closed": fail_closed,
        "reason": reason,
        "governor": gov_pre,
        "simplex": sx if isinstance(sx, dict) else {},
        "transfer_to_baseline": controller == "evidence_baseline",
    }


def activate_evidence_baseline(
    home: Path,
    store: Any,
    repo: str,
    task: str,
    *,
    budget: int = 1200,
    profile: str = "agent",
    resolution: dict[str, Any],
    repository: Any,
    root: Path,
    config: Any,
    manifest_current: bool,
    certificate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Sterile baseline: resolve already done → Evidence Kernel → audit → return.

    Does NOT index, invent, fuse, train, organism-persist adaptive, connect_pass, etc.
    """
    from . import __version__
    from .capabilities import ExecutionCapability
    from .evidence_kernel import evidence_kernel_context
    from .profiles import project_packet
    from .state_transition import append_controller_audit

    controller = "evidence_baseline"
    cap: ExecutionCapability = resolution["capability"]
    gov_pre = resolution.get("governor") or {}

    append_controller_audit(
        store,
        repo,
        "controller_resolved",
        controller=controller,
        payload={"reason": resolution.get("reason"), "capability_id": cap.capability_id},
    )
    append_controller_audit(
        store,
        repo,
        "manifest_observed",
        controller=controller,
        payload={"manifest_current": manifest_current},
    )
    cert_status = (certificate or {}).get("status") if certificate else "unknown"
    append_controller_audit(
        store,
        repo,
        "certificate_observed",
        controller=controller,
        payload={"status": cert_status},
    )

    ek_ctx = evidence_kernel_context(
        store, repo, task, budget=budget, certificate=certificate if isinstance(certificate, dict) else None
    )
    append_controller_audit(
        store,
        repo,
        "evidence_kernel_queried",
        controller=controller,
        payload={
            "n_hits": len(ek_ctx.get("evidence") or []),
            "receipt": (ek_ctx.get("receipt") or {}).get("receipt_hash"),
        },
    )

    blocked = [
        "index_repository",
        "learn_environment",
        "ingest_git",
        "compile_interlink",
        "begin_session",
        "build_organism",
        "persist_organism_pulse",
        "append_stream_frame",
        "record_connect_pass",
        "spectral_memory_pulse",
        "soft_bind_fusion",
        "predict_context",
        "train_from_outcome",
        "invent_from_coactivation",
        "foreign_emerge",
        "decay_unused_weights",
    ]
    exec_receipt = {
        "requested": resolution.get("simplex", {}).get("requested") or "advanced",
        "resolved": controller,
        "fail_closed": bool(resolution.get("fail_closed")),
        "reason": resolution.get("reason"),
        "allowed_write_classes": list(cap.allowed_write_classes),
        "blocked_operations": blocked,
        "capability_id": cap.capability_id,
        "sterile_baseline": True,
    }
    exec_receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(exec_receipt, sort_keys=True, default=str).encode()
    ).hexdigest()

    full_context: dict[str, Any] = {
        "schema_version": "1.5",
        "task": task,
        "repository": {
            "name": repo,
            "path": str(root),
            "manifest_current": manifest_current,
            "repository_id": str(repository["repository_id"] or ""),
        },
        "governor": gov_pre,
        "governance": gov_pre,
        "context_budget": budget,
        "estimated_tokens": ek_ctx.get("estimated_tokens"),
        "budget_partition": ek_ctx.get("budget_partition"),
        "evidence": ek_ctx.get("evidence") or [],
        "structural_neighborhood": ek_ctx.get("structural_neighborhood") or [],
        "evidence_kernel": ek_ctx,
        "memory_simplex": {
            "controller": controller,
            "budget_scheme": "flat",
            "transfer_to_baseline": True,
            "reason": resolution.get("reason"),
        },
        "controller_execution": exec_receipt,
        "capability": cap.to_dict(),
        "control_error": {"block": False, "immune_action": None, "errors": []},
        "claim_boundary": (
            "EVIDENCE_BASELINE sterile activation — Evidence Kernel + audit only."
        ),
        "version": __version__,
    }
    append_controller_audit(
        store,
        repo,
        "activation_completed",
        controller=controller,
        payload={"receipt_hash": exec_receipt["receipt_hash"]},
    )

    projected = project_packet(full_context, profile)
    runtime_path = runtime_directory(root, config) / "context_latest.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(full_context, indent=2, default=str) + "\n", encoding="utf-8")

    cert_status = (certificate or {}).get("status") if isinstance(certificate, dict) else None
    bootstrap_status = str(
        repository["bootstrap_status"]
        if repository is not None and repository["bootstrap_status"]
        else (cert_status or "unknown")
    )
    return {
        "profile": profile,
        "context": projected,
        "context_full": full_context,
        "controller_execution": exec_receipt,
        "memory_simplex": full_context["memory_simplex"],
        "evidence_kernel": ek_ctx,
        "certificate": certificate,
        "manifest_current": manifest_current,
        "sterile_baseline": True,
        "capability": cap.to_dict(),
        "packet_path": str(runtime_path),
        "bootstrap_status": bootstrap_status,
        "activation": "ready" if bootstrap_status == "verified" or cert_status == "verified" else "read_only",
        "block": False,
        "control_error": full_context.get("control_error") or {"block": False},
        "claim_boundary": full_context["claim_boundary"],
    }


def activate_advanced(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    task: str,
    *,
    budget: int,
    refresh: str,
    profile: str,
    prefetch: str,
    budget_scheme: str,
    resolution: dict[str, Any],
    repository: Any,
    root: Path,
    config: Any,
    manifest_current: bool,
    certificate: dict[str, Any] | None,
    surprise: dict[str, Any],
    refresh_result: dict[str, Any] | None,
    environment: Any,
    neural: Any,
) -> dict[str, Any]:
    """Full adaptive activation under advanced capability."""
    from . import __version__
    from .capabilities import ExecutionCapability
    from .organism import (
        build_organism,
        load_prior_pulse,
        persist_organism_pulse,
        save_prior_pulse,
    )
    from .profiles import project_packet
    from .state_transition import append_controller_audit

    cap: ExecutionCapability = resolution["capability"]
    controller = "advanced"
    scheme = budget_scheme or "fib"
    try:
        from .memory_simplex import budget_scheme_for_controller

        scheme = budget_scheme_for_controller(controller, default=scheme)
    except Exception:
        pass

    append_controller_audit(
        store,
        repo,
        "controller_resolved",
        controller=controller,
        payload={"capability_id": cap.capability_id, "reason": resolution.get("reason")},
    )

    context = build_context(
        home,
        store,
        governor,
        repo,
        task,
        budget,
        manifest_current=manifest_current,
        certificate=certificate,
        budget_scheme=scheme,
        memory_controller=controller,
    )
    context["memory_simplex"] = {
        **(resolution.get("simplex") or {}),
        "controller": controller,
        "budget_scheme": scheme,
    }
    context["capability"] = cap.to_dict()
    if isinstance(context.get("efficiency"), dict):
        context["efficiency"]["surprise"] = surprise

    conf = float(
        ((context.get("governance") or {}).get("components") or {}).get(
            "retrieval_confidence"
        )
        or 0.5
    )
    try:
        from .math_net.spectral_memory import spectral_memory_pulse

        spectral_memory = spectral_memory_pulse(
            store,
            repo,
            retrieval_confidence=conf,
            certificate_status=str((certificate or {}).get("status") or "unknown"),
            manifest_current=manifest_current,
            budget_tokens=budget,
            auto_promote=True,
            capability=cap,
        )
        context["spectral_memory"] = spectral_memory
        context["u"] = (spectral_memory.get("u") or {}).get("u")
    except TypeError:
        # older signature without capability
        try:
            from .math_net.spectral_memory import spectral_memory_pulse

            spectral_memory = spectral_memory_pulse(
                store,
                repo,
                retrieval_confidence=conf,
                certificate_status=str((certificate or {}).get("status") or "unknown"),
                manifest_current=manifest_current,
                budget_tokens=budget,
                auto_promote=True,
            )
            context["spectral_memory"] = spectral_memory
        except Exception as exc:
            context["spectral_memory"] = {"error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:
        context["spectral_memory"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        from .coherence import measure_coherence, soft_bind_fusion

        context["fusion_bind"] = soft_bind_fusion(
            home, store, governor, repo, task=task, capability=cap
        )
    except TypeError:
        try:
            from .coherence import measure_coherence, soft_bind_fusion

            context["fusion_bind"] = soft_bind_fusion(home, store, governor, repo, task=task)
            conf_for_c = conf
            if context.get("u") is not None:
                conf_for_c = max(0.0, min(1.0, 1.0 - float(context.get("u") or 0.5)))
            context["coherence"] = measure_coherence(
                store, repo, governor=governor, home=home, retrieval_confidence=conf_for_c
            )
        except Exception as exc:
            context["coherence"] = {"error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:
        context["fusion_bind"] = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        from .coherence import measure_coherence

        conf_for_c = conf
        if context.get("u") is not None:
            conf_for_c = max(0.0, min(1.0, 1.0 - float(context.get("u") or 0.5)))
        if "coherence" not in context:
            context["coherence"] = measure_coherence(
                store, repo, governor=governor, home=home, retrieval_confidence=conf_for_c
            )
    except Exception as exc:
        context.setdefault("coherence", {"error": f"{type(exc).__name__}: {exc}"})

    session = begin_session(home, store, repo, task)
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
    to_hash = {k: v for k, v in context.items() if k not in {"packet_path", "packet_hash"}}
    context["packet_hash"] = hashlib.sha256(
        json.dumps(to_hash, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    persist_organism_pulse(store, repo, organism, session_id=session.get("session_id"))
    save_prior_pulse(store, repo, organism["pulse"])

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
                    "ready" if (certificate or {}).get("status") == "verified" else "degraded"
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
    except Exception as exc:
        context["stream"] = {"glyph": "〰", "alive": False, "error": f"{type(exc).__name__}: {exc}"}

    prediction = None
    gov_mode = str((context.get("governor") or {}).get("mode") or "normal")
    do_prefetch = prefetch == "aggressive" or (
        prefetch == "auto" and gov_mode != "read_only"
    )
    if do_prefetch:
        try:
            from .predict import predict_context

            prediction = predict_context(
                store,
                repo,
                task,
                budget=min(200, max(80, budget // 6)),
                session_id=session.get("session_id"),
                governor_mode=gov_mode,
            )
            context["prediction"] = {
                "trace_id": prediction.get("trace_id"),
                "predicted_paths": prediction.get("predicted_paths"),
            }
        except Exception:
            prediction = None

    from .connect_pass import record_connect_pass

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
        activation="ready" if (certificate or {}).get("status") == "verified" else "read_only",
        block=bool((context.get("control_error") or {}).get("block")),
        auto_distill=True,
    )
    # Keep connect_pass surface rich for mesh/pulse tests (pass_id + intel_pulse)
    context["connect_pass"] = {
        "pass_id": connect.get("pass_id"),
        "pass_count": connect.get("pass_count"),
        "intel_pulse": connect.get("intel_pulse"),
        "metric_graph": connect.get("metric_graph"),
        "spectral": connect.get("spectral"),
        "surface": connect.get("surface"),
    }

    exec_receipt = {
        "requested": "advanced",
        "resolved": controller,
        "fail_closed": False,
        "reason": resolution.get("reason"),
        "allowed_write_classes": list(cap.allowed_write_classes),
        "blocked_operations": [],
        "capability_id": cap.capability_id,
        "sterile_baseline": False,
    }
    exec_receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(exec_receipt, sort_keys=True, default=str).encode()
    ).hexdigest()
    context["controller_execution"] = exec_receipt

    full_context = context
    projected = project_packet(full_context, profile)
    runtime_path = runtime_directory(root, config) / "context_latest.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(full_context, indent=2, default=str) + "\n", encoding="utf-8")

    cert_status = (certificate or {}).get("status") if isinstance(certificate, dict) else None
    bootstrap_status = str(
        repository["bootstrap_status"]
        if repository is not None and repository["bootstrap_status"]
        else (cert_status or "unknown")
    )
    activation_state = "ready" if cert_status == "verified" or bootstrap_status == "verified" else "read_only"
    control = full_context.get("control_error") or {}
    glyph_state = full_context.get("glyph_state") or {}
    out = {
        "profile": profile,
        "context": projected,
        "context_full": full_context,
        "controller_execution": exec_receipt,
        "memory_simplex": full_context.get("memory_simplex"),
        "certificate": certificate,
        "manifest_current": manifest_current,
        "sterile_baseline": False,
        "capability": cap.to_dict(),
        "session": session,
        "organism": organism,
        "packet_path": str(runtime_path),
        "neural": neural,
        "environment": environment,
        "refresh": refresh_result,
        "surprise": surprise,
        "bootstrap_status": bootstrap_status,
        "activation": activation_state,
        "block": bool(control.get("block")),
        "control_error": control,
        "connect_pass": full_context.get("connect_pass"),
        "stream": full_context.get("stream"),
        "glyph_state": glyph_state,
        "glyph_line": full_context.get("glyph_line")
        or (glyph_state.get("line") if isinstance(glyph_state, dict) else None),
        "aria_language": full_context.get("aria_language")
        or full_context.get("aria_materialization")
        or full_context.get("glyph_canon"),
        "prediction": full_context.get("prediction"),
        "spectral_memory": full_context.get("spectral_memory"),
        "u": full_context.get("u"),
        "claim_boundary": "Advanced activation under capability-scoped adaptive writes.",
    }
    # Envelope parity: aria_language + phrasebook for agents/signal harness
    try:
        from .glyphs.canon import phrasebook as _phrasebook

        pb = _phrasebook()
    except Exception:
        pb = {"phrases": {}}
    al = out.get("aria_language")
    if not isinstance(al, dict) or not al.get("phrasebook"):
        out["aria_language"] = {
            "glyph": "◈",
            "phrasebook": pb,
            "automatic_execution": False,
            "aria_role": "meta_medium",
            "schema_version": "cortex-aria-language/1.0",
        }
    else:
        al.setdefault("glyph", "◈")
        al.setdefault("automatic_execution", False)
        al.setdefault("phrasebook", pb)
    if not out.get("glyph_state"):
        out["glyph_state"] = {"line": "◈", "expand": []}
    if not out.get("glyph_line"):
        out["glyph_line"] = (out.get("glyph_state") or {}).get("line") or "◈"
    return out


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
    budget_scheme: str = "fib",
    memory_controller: str | None = None,
    force_evidence_baseline: bool = False,
) -> dict[str, Any]:
    repository = store.repo(repo)
    if not repository:
        raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
    root = Path(repository["path"])
    config = load_repo_config(root)
    observed_manifest = current_manifest_hash(root, config)
    manifest_current = observed_manifest == (repository["manifest_hash"] or "")

    # Phase 1: resolve controller BEFORE any adaptive side effect
    resolution = resolve_activation_controller(
        governor,
        repo,
        memory_controller=memory_controller,
        force_evidence_baseline=force_evidence_baseline,
        manifest_current=manifest_current,
    )
    controller = resolution["controller"]

    # v7.0: bind body epoch + issue epoch-scoped capability
    from .capabilities import CapabilityIssuer
    from .epoch import ensure_current_epoch
    from .phases import transition_phase

    epoch = ensure_current_epoch(store, repo, reason="activation")
    cap = CapabilityIssuer("activation").issue(
        repo=repo,
        controller=controller,
        reason=resolution.get("reason") or "activation",
        ttl_s=7200.0,
        body_epoch_id=epoch.epoch_id,
        evidence_root_hash=epoch.evidence_root_hash,
        constitutional_config_hash=epoch.constitutional_config_hash,
    )
    resolution["capability"] = cap
    resolution["body_epoch"] = epoch.to_dict()
    # phase: baseline → OBSERVE/EVIDENCE_FREEZE; advanced → OBSERVE then ADAPT
    try:
        if controller == "evidence_baseline":
            transition_phase(store, repo, "OBSERVE", reason="baseline_activation")
            transition_phase(store, repo, "EVIDENCE_FREEZE", reason="baseline_activation")
        else:
            transition_phase(store, repo, "OBSERVE", reason="advanced_activation")
            transition_phase(store, repo, "ADAPT", reason="advanced_activation")
    except Exception:
        pass

    # Evidence refresh edge (v7.1.1): observe → authorize → refresh E only → recompute → path
    refresh_result: dict[str, Any] | None = None
    evidence_refresh_audit: dict[str, Any] | None = None
    if refresh == "always" or (refresh == "auto" and not manifest_current):
        try:
            from .evidence_refresh import run_evidence_refresh_edge

            evidence_refresh_audit = run_evidence_refresh_edge(
                home,
                store,
                repo,
                root=root,
                config=config,
                refresh_mode=refresh,
                governor=governor,
                memory_controller=memory_controller,
                force_evidence_baseline=force_evidence_baseline,
            )
            if evidence_refresh_audit.get("refreshed"):
                refresh_result = evidence_refresh_audit.get("refresh_result") or {
                    "refreshed": True
                }
                repository = store.repo(repo) or repository
                observed_manifest = current_manifest_hash(root, config)
                manifest_current = bool(
                    evidence_refresh_audit.get("manifest_current", False)
                ) or (
                    observed_manifest == (repository["manifest_hash"] or "")
                )
                # Re-issue capability under post-refresh epoch/controller
                from .epoch import ensure_current_epoch as _ensure_ep

                epoch = _ensure_ep(store, repo, reason="activation_post_evidence_refresh")
                cr = evidence_refresh_audit.get("controller_resolution") or {}
                if cr.get("controller") and not force_evidence_baseline:
                    controller = str(cr["controller"])
                    resolution = {
                        **resolution,
                        **{k: cr.get(k) for k in ("controller", "reason", "fail_closed") if k in cr},
                        "governor": cr.get("governor") or resolution.get("governor"),
                    }
                cap = CapabilityIssuer("activation").issue(
                    repo=repo,
                    controller=controller,
                    reason=resolution.get("reason") or "activation_post_refresh",
                    ttl_s=7200.0,
                    body_epoch_id=epoch.epoch_id,
                    evidence_root_hash=epoch.evidence_root_hash,
                    constitutional_config_hash=epoch.constitutional_config_hash,
                )
                resolution["capability"] = cap
                resolution["body_epoch"] = epoch.to_dict()
            else:
                refresh_result = {
                    "refreshed": False,
                    "reason": (evidence_refresh_audit.get("authorize") or {}).get(
                        "reason"
                    ),
                }
        except Exception as exc:
            refresh_result = {
                "error": f"{type(exc).__name__}:{exc}",
                "refreshed": False,
            }
            evidence_refresh_audit = {
                "ok": False,
                "error": f"{type(exc).__name__}:{exc}",
            }

    # Phase 2a: sterile baseline — no adaptive machinery after optional evidence refresh
    if controller == "evidence_baseline":
        certificate = verify_repository(
            home,
            store,
            repo,
            config,
            write_certificate=bool(refresh_result),
        )
        if isinstance(certificate, dict) and certificate.get("status") == "verified":
            try:
                store.update_repo_state(repo, bootstrap_status="verified")
                repository = store.repo(repo) or repository
            except Exception:
                pass
        out = activate_evidence_baseline(
            home,
            store,
            repo,
            task,
            budget=budget,
            profile=profile,
            resolution=resolution,
            repository=repository,
            root=root,
            config=config,
            manifest_current=manifest_current,
            certificate=certificate,
        )
        out["body_epoch"] = epoch.to_dict()
        out["refresh"] = refresh_result
        out["evidence_refresh_edge"] = evidence_refresh_audit
        out["manifest_current"] = manifest_current
        cert_status = (certificate or {}).get("status") if isinstance(certificate, dict) else None
        out["bootstrap_status"] = str(
            (repository["bootstrap_status"] if repository is not None else None)
            or cert_status
            or out.get("bootstrap_status")
            or "unknown"
        )
        if cert_status == "verified" or out["bootstrap_status"] == "verified":
            out["activation"] = "ready"
        return out

    # Phase 2b: advanced — may still refresh if not already done above
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
    if refresh_result is not None and not refresh_result.get("error"):
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
    elif refresh == "always" or (refresh == "auto" and not manifest_current):
        # Fallback if early refresh was skipped
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

    out = activate_advanced(
        home,
        store,
        governor,
        repo,
        task,
        budget=budget,
        refresh=refresh,
        profile=profile,
        prefetch=prefetch,
        budget_scheme=budget_scheme,
        resolution=resolution,
        repository=repository,
        root=root,
        config=config,
        manifest_current=manifest_current,
        certificate=certificate,
        surprise=surprise,
        refresh_result=refresh_result,
        environment=environment,
        neural=neural,
    )
    out["body_epoch"] = epoch.to_dict()
    out["refresh"] = refresh_result
    if evidence_refresh_audit is not None:
        out["evidence_refresh_edge"] = evidence_refresh_audit
    # seal epoch if adaptive roots changed during advanced activation
    try:
        from .epoch import seal_epoch_transition

        sealed = seal_epoch_transition(
            store, repo, reason="post_advanced_activation", parent=epoch
        )
        out["body_epoch"] = sealed.to_dict()
        if sealed.epoch_id != epoch.epoch_id:
            from .capabilities import revoke_epoch_capabilities

            revoke_epoch_capabilities(store, repo, epoch.epoch_id)
    except Exception:
        pass
    return out
