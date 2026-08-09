"""Interconnect mesh — fold v5/v6 organs into one read-only health surface.

Glyphic medium alignment: status only. Never mutation authority.
"""

from __future__ import annotations

import time
from typing import Any

from .agents.tokens import ALLOWED_SCOPES, FORBIDDEN_SCOPES
from .causal.ledger import causal_report
from .connect_pass import load_metric_graph
from .control_error import build_control_error
from .kernels import kernels_status
from .progress_glyphs import progress_glyph_registry
from .ranker.model import ranker_status
from .vectors.index import hnsw_status

SCHEMA = "cortex-interconnect/1.2"
GLYPH = "⧉"


def _binding_field_panel(store: Any, repo: str) -> dict[str, Any]:
    """v7.7 compact binding field (strictly observe; never persist)."""
    try:
        from .binding_field import observe_binding_field

        # The interconnect command is an inspection surface.  Persisting a
        # binding-field projection here made a status read change the state it
        # was reporting and broke the read-only contract.
        b = observe_binding_field(store, repo, persist=False)
        return {
            "classification": b.get("classification"),
            "reasons": b.get("reasons"),
            "buffer_ticks": (b.get("signals") or {}).get("live_buffer_ticks"),
            "field_frames_display": (b.get("signals") or {}).get("field_frames_display"),
            "sense_classification": (b.get("signals") or {}).get("sense_classification"),
            "advisory": (b.get("advisory") or {}).get("recommendations"),
            "advisory_only": True,
            "phase": "v7.7.0",
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}:{exc}", "advisory_only": True, "phase": "v7.7.0"}


def _cognitive_field_panel(store: Any, repo: str) -> dict[str, Any]:
    """v8.1 compact canonical predictive-observer surface."""
    try:
        from .cognitive import cognitive_status

        status = cognitive_status(store, repo)
        measured = status.get("measured_event_field") or {}
        model = status.get("predictive_self_model") or {}
        workspace = status.get("global_workspace") or {}
        autobiography = status.get("autobiography") or {}
        lesions = status.get("lesion_benchmarks") or {}
        return {
            "measurement_basis": measured.get("measurement_basis"),
            "changed_metrics": measured.get("changed_metrics"),
            "model_n": model.get("n_updates"),
            "prediction_error": model.get("ema_error"),
            "active_regime": model.get("last_regime"),
            "calibration": model.get("calibration"),
            "workspace_broadcasts": workspace.get("broadcast_count"),
            "workspace_latest": (workspace.get("latest") or {}).get("selected"),
            "autobiography_episodes": autobiography.get("episode_count"),
            "autobiography_chain_valid": autobiography.get("chain_valid"),
            "autobiography_lineage_anchored": autobiography.get("lineage_anchored"),
            "lesions_supported": lesions.get("supported_lesions"),
            "functional_self_model_only": True,
            "advisory_only": True,
            "phase": "v8.1.0",
        }
    except Exception as exc:
        return {
            "error": f"{type(exc).__name__}:{exc}",
            "functional_self_model_only": True,
            "advisory_only": True,
            "phase": "v8.1.0",
        }


def _continuity_slice(store: Any, repo: str) -> dict[str, Any]:
    """v7.1: body epoch + phase via observe-only (never seals).

    When no epoch is sealed yet, surface the live computed epoch_id (identity
    material only) so mesh diagnostics still report continuity without mutation.
    """
    try:
        from .epoch import observe_current_epoch
        from .phases import current_phase

        obs = observe_current_epoch(store, repo)
        ph = current_phase(store, repo)
        sealed = obs.get("sealed") or {}
        live = obs.get("live") or {}
        live_roots = obs.get("live_roots") or {}
        # Prefer sealed identity; else live compute (observe-only, not persisted)
        eid = (
            obs.get("epoch_id")
            or obs.get("live_epoch_id")
            or live.get("epoch_id")
        )
        return {
            "plane": "continuity",
            "body_epoch_id": eid,
            "live_epoch_id": obs.get("live_epoch_id") or live.get("epoch_id"),
            "epoch_verified": bool(obs.get("verified")),
            "epoch_present": bool(obs.get("present")),
            "epoch_sealed": bool(obs.get("present")),
            "epoch_mismatches": list(obs.get("mismatches") or []),
            "runtime_phase": ph.phase,
            "phase_epoch_id": ph.epoch_id,
            "phase_bound": (not eid)
            or ph.epoch_id in {eid, "unbound", ""}
            or ph.epoch_id == eid,
            "evidence_root_hash": str(
                sealed.get("evidence_root_hash")
                or live_roots.get("evidence_root_hash")
                or live.get("evidence_root_hash")
                or ""
            )[:16],
            "adaptive_root_hash": str(
                sealed.get("adaptive_root_hash")
                or live_roots.get("adaptive_root_hash")
                or live.get("adaptive_root_hash")
                or ""
            )[:16],
            "constitutional_config_hash": str(
                sealed.get("constitutional_config_hash")
                or live_roots.get("constitutional_config_hash")
                or live.get("constitutional_config_hash")
                or ""
            )[:16],
            "cortex_version": sealed.get("cortex_version")
            or live.get("cortex_version"),
            "repository_id": sealed.get("repository_id")
            or live.get("repository_id"),
            "receipt_hash": str(
                obs.get("receipt_hash") or live.get("receipt_hash") or ""
            )[:16],
            "observe_only": True,
        }
    except Exception as exc:
        return {"plane": "continuity", "error": f"{type(exc).__name__}: {exc}"}


def mesh_status(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Any | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Single-pane mesh health. Telemetry only; never authorization.

    compact=True (default) omits full glyph registry to save tokens.
    """

    graph = load_metric_graph(store, repo)
    ranker = ranker_status(store, repo)
    hnsw = hnsw_status(store, repo)
    causal = causal_report(store, repo, limit=10)
    frozen = bool((store.get_setting(f"ranker_frozen:{repo}", {}) or {}).get("frozen"))
    multi_agent = bool(
        (store.get_setting(f"multi_agent:{repo}", {}) or {}).get("enabled")
    )
    last_prune = store.get_setting(f"prune:{repo}", {}) or {}
    try:
        kernels = kernels_status(store, repo)
    except Exception as exc:
        kernels = {"error": f"{type(exc).__name__}: {exc}"}
    intel_pulse = store.get_setting(f"intel_pulse:{repo}", {}) or {}
    continuity = _continuity_slice(store, repo)

    control: dict[str, Any] = {}
    control_snapshot: dict[str, Any] = {
        "captured_at": round(time.time(), 3),
        "verification": "not_requested",
    }
    if governor is not None and home is not None:
        try:
            from .config import load_repo_config
            from .verify import verify_repository
            from pathlib import Path

            repository = store.repo(repo)
            if repository:
                root = Path(repository["path"])
                config = load_repo_config(root, home)
                cert = verify_repository(
                    home, store, repo, config, write_certificate=False
                )
                current = bool((cert.get("manifest") or {}).get("current"))
                gov = governor.evaluate(
                    repo, manifest_current=current, certificate=cert
                )
                control = build_control_error(
                    certificate=cert,
                    governance=gov,
                    manifest_current=current,
                    retrieval_confidence=0.0,
                    aria_materialization={},
                )
                control_snapshot = {
                    "captured_at": round(time.time(), 3),
                    "verification": "live_single_pass",
                    "certificate_hash": cert.get("certificate_hash"),
                    "manifest_stored": (cert.get("manifest") or {}).get("stored_hash"),
                    "manifest_observed": (cert.get("manifest") or {}).get("observed_hash"),
                    "manifest_current": current,
                    "certificate_status": cert.get("status"),
                }
        except Exception as exc:
            control = {"error": f"{type(exc).__name__}: {exc}"}
            control_snapshot = {
                "captured_at": round(time.time(), 3),
                "verification": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    block = bool(control.get("block"))
    # Bottleneck signals: high scan, low sparse fire, blocked immune
    averages = graph.get("averages") or {}
    bottlenecks: list[str] = []
    if block:
        bottlenecks.append("immune_block")
    if float(averages.get("block_rate") or 0) > 0.3:
        bottlenecks.append("high_historical_block_rate")
    if frozen:
        bottlenecks.append("ranker_frozen")
    if not hnsw.get("available"):
        bottlenecks.append("hnsw_absent")
    if int(graph.get("pass_count") or 0) == 0:
        bottlenecks.append("no_connect_passes_yet")
    # v7.0 continuity bottlenecks (executable stale-state signals)
    if continuity.get("error"):
        bottlenecks.append("continuity_unavailable")
    else:
        if continuity.get("epoch_verified") is False:
            bottlenecks.append("epoch_stale_or_mismatched")
        if continuity.get("phase_bound") is False:
            bottlenecks.append("phase_epoch_unbound")
        if not continuity.get("body_epoch_id"):
            bottlenecks.append("body_epoch_missing")

    nodes = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_nodes WHERE repo=?", (repo,)
    ).fetchone()["c"]
    synapses = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_synapses WHERE repo=?", (repo,)
    ).fetchone()["c"]
    file_nodes = store.db.execute(
        """
        SELECT COUNT(*) AS c FROM neural_nodes
        WHERE repo=? AND (resolution='file' OR resolution IS NULL OR resolution='')
        """,
        (repo,),
    ).fetchone()["c"]

    # Legacy mesh_green = constitutional/continuity path open only.
    # It is NOT overall cognitive–symbiotic readiness.
    mesh_green = (
        not block
        and "host.mutate" not in ALLOWED_SCOPES
        and "host.mutate" in FORBIDDEN_SCOPES
        and continuity.get("epoch_verified") is not False
        and continuity.get("phase_bound") is not False
        and not continuity.get("error")
    )
    pulse_at = intel_pulse.get("at")
    pulse_age_s = (
        max(0.0, time.time() - float(pulse_at))
        if isinstance(pulse_at, (int, float))
        else None
    )
    pulse_observation = intel_pulse.get("observation") or {}
    pulse_mesh = pulse_observation.get("mesh_green")
    pulse_matches_current = (
        bool(pulse_mesh) == bool(mesh_green) if pulse_mesh is not None else None
    )

    # v7.4 Continuity Realignment — advisory next step when seal lags live tree
    realign_advice: dict[str, Any] | None = None
    if "epoch_stale_or_mismatched" in bottlenecks or "body_epoch_missing" in bottlenecks:
        realign_advice = {
            "needed": True,
            "command": f"python -m cortex realign apply --repo {repo} --i-authorize-realign",
            "diagnose": f"python -m cortex realign diagnose --repo {repo} --json",
            "note": (
                "Seal lags living tree or version/config drift. "
                "Realign is operator-authorized only — never silent."
            ),
            "phase": "v7.4.0",
        }
    else:
        realign_advice = {
            "needed": False,
            "command": None,
            "note": "epoch continuity current for mesh path",
            "phase": "v7.4.0",
        }

    # v7.5 self-sensing compact (observe, no baseline force)
    self_sense_panel: dict[str, Any] | None = None
    try:
        from .self_sensing import observe_self_sensing, self_sensing_report

        # read-only snapshot preferred if exists; else light observe without update
        existing = self_sensing_report(store, repo)
        if existing.get("latest"):
            self_sense_panel = {
                "classification": (existing.get("latest") or {}).get("classification"),
                "residual_r": (existing.get("latest") or {}).get("residual_r"),
                "F_t": (existing.get("latest") or {}).get("F_t"),
                "baseline_display": existing.get("baseline_display"),
                "advisory_only": True,
            }
        else:
            snap = observe_self_sensing(store, repo, update=False, persist=False)
            self_sense_panel = {
                "classification": snap.get("classification"),
                "residual_r": snap.get("residual_r"),
                "F_t": snap.get("F_t"),
                "baseline_display": f"{snap.get('baseline_n_updates', 0)}/16",
                "advisory_only": True,
            }
    except Exception as exc:
        self_sense_panel = {"error": f"{type(exc).__name__}:{exc}", "advisory_only": True}

    try:
        from .math_net.info_interlock import interlock_report

        interlock_panel = interlock_report(
            store, repo, limit=512, top_paths=12, include_lesion=False
        )
    except Exception as exc:
        interlock_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
        }
    bridge_shadow = store.get_setting(f"bridge_shadow_latest:{repo}", {}) or {}
    bridge_panel = {
        "available": bool(bridge_shadow),
        "glyph": bridge_shadow.get("glyph") or "⟠",
        "top_decile_degree_share": bridge_shadow.get("top_decile_degree_share"),
        "candidate_count": len(bridge_shadow.get("candidates") or []),
        "top_candidates": (bridge_shadow.get("candidates") or [])[:5],
        "policy_effect": False,
        "advisory_only": True,
    }
    bridge_trial = store.get_setting(f"bridge_trial_latest:{repo}", {}) or {}
    bridge_trial_panel = {
        "available": bool(bridge_trial),
        "glyph": bridge_trial.get("glyph") or "⟐",
        "suite": bridge_trial.get("suite"),
        "case_count": bridge_trial.get("case_count"),
        "arms": bridge_trial.get("arms"),
        "promotion": bridge_trial.get("promotion"),
        "policy_effect": False,
        "advisory_only": True,
    }
    source_admission = store.get_setting(f"source_admission_latest:{repo}", {}) or {}
    source_admission_panel = {
        "available": bool(source_admission),
        "glyph": source_admission.get("glyph") or "⟢",
        "suite": source_admission.get("suite"),
        "case_count": source_admission.get("case_count"),
        "candidate_stage": source_admission.get("candidate_stage"),
        "final_stage": source_admission.get("final_stage"),
        "promotion": source_admission.get("promotion"),
        "policy_effect": False,
        "advisory_only": True,
    }
    try:
        from .resonance_sweep import run_frequency_sweep

        resonance_sweep_panel = run_frequency_sweep(store, repo, persist=False)
    except Exception as exc:
        resonance_sweep_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
        }
    try:
        from .geometric_echo import run_geometric_echo

        geometric_echo_panel = run_geometric_echo(store, repo, persist=False)
    except Exception as exc:
        geometric_echo_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
        }
    try:
        from .rotated_echo import run_rotated_echo

        rotated_echo_panel = run_rotated_echo(store, repo, persist=False)
    except Exception as exc:
        rotated_echo_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
        }
    binding_panel = _binding_field_panel(store, repo)

    # A mesh report can combine live probes with cached advisory surfaces. Make
    # that temporal boundary explicit and quarantine any cached panel whose
    # body epoch is not the one used for this report.
    live_body_epoch = str(continuity.get("body_epoch_id") or "")
    epoch_alignment: dict[str, dict[str, Any]] = {}
    for name, panel in (
        ("resonance_sweep", resonance_sweep_panel),
        ("geometric_echo", geometric_echo_panel),
        ("rotated_echo", rotated_echo_panel),
        ("informational_interlock", interlock_panel),
    ):
        if not isinstance(panel, dict):
            epoch_alignment[name] = {"status": "unavailable", "current": False}
            continue
        declared = str(
            panel.get("body_epoch_id")
            or panel.get("current_body_epoch_id")
            or ""
        )
        current = bool(live_body_epoch and declared and declared == live_body_epoch)
        status = "current" if current else "stale" if declared else "unbound"
        epoch_alignment[name] = {
            "status": status,
            "current": current,
            "declared_body_epoch_id": declared or None,
            "current_body_epoch_id": live_body_epoch or None,
        }
        if declared and not current:
            panel["epoch_current"] = False
            panel["stale_reason"] = "declared_body_epoch_not_current"
    try:
        from .symbiosis import symbiotic_status

        symbiosis_panel = symbiotic_status(store, repo)
    except Exception as exc:
        symbiosis_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
            "policy_effect": False,
        }
    latest_frame = None
    try:
        session = store.get_setting(f"symbiosis_latest:{repo}", None) or {}
        receipts = dict(session.get("receipts") or {})
        latest_frame = receipts.get("interconnect_frame")
        if not latest_frame:
            turns = dict(session.get("turns") or {})
            if turns:
                last_key = sorted(turns, key=lambda k: int(k) if str(k).isdigit() else 0)[
                    -1
                ]
                latest_frame = (turns.get(last_key) or {}).get("interconnect_frame")
    except Exception:
        latest_frame = None
    try:
        latest_ostt_receipt = store.latest_activation_conformance_receipt(repo)
        if latest_ostt_receipt:
            from .ostt.conformance import verify_activation_receipt

            latest_ostt_receipt = dict(latest_ostt_receipt)
            latest_ostt_receipt["canonical_verification"] = (
                verify_activation_receipt(
                    store,
                    repo,
                    str(latest_ostt_receipt.get("receipt_hash") or ""),
                )
            )
    except Exception:
        latest_ostt_receipt = None
    if not latest_ostt_receipt:
        latest_ostt_receipt = store.get_setting(
            f"ostt_residual_latest:{repo}", None
        )
    try:
        from .ostt import audit_runtime

        ostt_panel = audit_runtime(
            {
                "manifest_current": control_snapshot.get("manifest_current"),
                "certificate_status": control_snapshot.get("certificate_status"),
                "epoch_verified": continuity.get("epoch_verified"),
                "phase_bound": continuity.get("phase_bound"),
                "immune_block": block,
                "evidence_valid": bool(interlock_panel.get("cohort_current"))
                and bool(
                    (interlock_panel.get("promotion_gates") or {}).get(
                        "measurement_cohort_gate"
                    )
                ),
                "same_epoch_frames": resonance_sweep_panel.get("frame_count"),
                "resonance_status": resonance_sweep_panel.get("status"),
                "self_sensing_classification": (
                    self_sense_panel or {}
                ).get("classification"),
                "binding_classification": (binding_panel or {}).get("classification"),
                "interlock": interlock_panel,
                "operator_residuals": [latest_ostt_receipt]
                if latest_ostt_receipt
                else [],
            }
        )
    except Exception as exc:
        ostt_panel = {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "advisory_only": True,
            "policy_effect": False,
        }

    try:
        from .interconnect_frame import readiness_panel

        readiness = readiness_panel(
            mesh_green_constitutional=mesh_green,
            continuity=continuity,
            symbiosis=symbiosis_panel,
            self_sensing=self_sense_panel or {},
            binding=binding_panel or {},
            resonance=resonance_sweep_panel or {},
            interlock=interlock_panel or {},
            ostt=ostt_panel if isinstance(ostt_panel, dict) else {},
            frame=latest_frame or {},
        )
    except Exception as exc:
        readiness = {
            "error": f"{type(exc).__name__}:{exc}",
            "overall_ready": False,
            "mesh_green_legacy": mesh_green,
            "advisory_only": True,
        }

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "spoken": "interconnect mesh",
        "repo": repo,
        "ts": round(time.time(), 3),
        "observation_snapshot": {
            **control_snapshot,
            "body_epoch_id": continuity.get("body_epoch_id"),
            "runtime_phase": continuity.get("runtime_phase"),
            "mesh_green": mesh_green,
            "atomic_control_read": control_snapshot.get("verification")
            == "live_single_pass",
            "epoch_alignment": epoch_alignment,
        },
        "mesh_green": mesh_green,
        "mesh_green_meaning": (
            "constitutional_and_continuity_path_open — not overall symbiotic readiness"
        ),
        "readiness": readiness,
        "overall_ready": bool(readiness.get("overall_ready")),
        "interconnect_frame_latest": latest_frame,
        "bottlenecks": bottlenecks,
        "realign": realign_advice,
        "self_sensing": self_sense_panel,
        "informational_interlock": interlock_panel,
        "geometric_bridges": bridge_panel,
        "query_bridge_trials": bridge_trial_panel,
        "source_admission_trials": source_admission_panel,
        "resonance_sweep": resonance_sweep_panel,
        "geometric_echo": geometric_echo_panel,
        "rotated_echo": rotated_echo_panel,
        "ostt": ostt_panel,
        "symbiosis": symbiosis_panel,
        "warm_in": {
            "command": f"python -m cortex warm-in status --repo {repo}",
            "run": f"python -m cortex warm-in run --repo {repo}",
            "note": "v7.6 Verified Operating Regime — warm field+sense to milestone",
            "phase": "v7.6.0",
        },
        "binding_field": binding_panel,
        "cognitive_field": _cognitive_field_panel(store, repo),
        "continuity": continuity,
        "epoch_alignment": epoch_alignment,
        "planes": {
            "E": "evidence",
            "A": "adaptation",
            "I": "immunity",
            "C": "constitutional",
            "W": "witness",
        },
        "immune": {
            "block": block,
            "code": (control.get("immune_action") or {}).get("code"),
            "severity": control.get("severity"),
        },
        "connect": {
            "pass_count": graph.get("pass_count"),
            "averages": averages,
            "totals": {
                "distill_count": (graph.get("totals") or {}).get("distill_count"),
                "aria_materialize_count": (graph.get("totals") or {}).get(
                    "aria_materialize_count"
                ),
                "block_count": (graph.get("totals") or {}).get("block_count"),
            },
            "top_coactivations": dict(
                sorted(
                    (graph.get("path_coactivation") or {}).items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
            ),
        },
        "ranker": {
            "train_count": ranker.get("train_count"),
            "model_id": ranker.get("model_id"),
            "frozen": frozen,
        },
        "hnsw": {
            "available": hnsw.get("available"),
            "nodes": hnsw.get("nodes"),
            "algorithm": hnsw.get("algorithm"),
        },
        "graph": {
            "nodes": int(nodes),
            "file_nodes": int(file_nodes),
            "synapses": int(synapses),
            "last_prune": last_prune,
        },
        "causal": causal.get("counts"),
        "spectral": {
            "glyph": "≋",
            "dominant": kernels.get("dominant"),
            "retention": kernels.get("retention")
            or (graph.get("retention_by_class")),
            "profile": kernels.get("profile"),
            "clock_neq_memory_neq_decision": True,
        },
        "intelligence": {
            "glyph": "☰",
            "last_pulse": intel_pulse.get("at"),
            "resonance": intel_pulse.get("resonance"),
            "observation": pulse_observation,
            "freshness": {
                "age_s": round(pulse_age_s, 3) if pulse_age_s is not None else None,
                "stale": pulse_age_s is None or pulse_age_s > 120.0,
                "mesh_matches_current": pulse_matches_current,
                "current_snapshot_required_for_control": True,
            },
            "pass_count": intel_pulse.get("pass_count"),
            "version": intel_pulse.get("version"),
            "pulse_every": 2,
            "seal_every": 7,
        },
        "agents": {
            "multi_agent_mode": multi_agent,
            "host_mutate_forbidden": "host.mutate" in FORBIDDEN_SCOPES,
        },
        "aria": {
            "medium": "glyphic_progress_labels",
            "automatic_execution": False,
            "glyphs": {
                k: v.get("symbol")
                for k, v in (progress_glyph_registry().get("glyphs") or {}).items()
            },
        },
        "gates": {
            "immune_blocks_train": True,
            "immune_blocks_seal": True,
            "contract_constrains_only": True,
            "relevance_never_mutation": True,
        },
        "progress_glyphs": (
            {
                "symbols": {
                    k: v.get("symbol")
                    for k, v in (progress_glyph_registry().get("glyphs") or {}).items()
                },
                "automatic_execution": False,
            }
            if compact
            else progress_glyph_registry()
        ),
        "claim_boundary": (
            "Interconnect mesh is local operational health; not consciousness "
            "and not host mutation authority."
        ),
    }


def mesh_dashboard(store: Any, repo: str, *, governor: Any | None = None, home: Any | None = None) -> dict[str, Any]:
    """One-screen mesh + spectral field + continuity for operators."""

    mesh = mesh_status(store, repo, governor=governor, home=home)
    spectrum = (mesh.get("spectral") or {}).get("retention") or {}
    cont = mesh.get("continuity") or {}
    return {
        "schema_version": "cortex-mesh-dashboard/1.1",
        "glyph": "⧉",
        "repo": repo,
        "mesh_green": mesh.get("mesh_green"),
        "bottlenecks": mesh.get("bottlenecks"),
        "xi_spectrum": spectrum,
        "dominant_kernel": (mesh.get("spectral") or {}).get("dominant"),
        "connect_pass_count": (mesh.get("connect") or {}).get("pass_count"),
        "ranker": mesh.get("ranker"),
        "hnsw": mesh.get("hnsw"),
        "graph": mesh.get("graph"),
        "causal": mesh.get("causal"),
        "gates": mesh.get("gates"),
        "immune": mesh.get("immune"),
        "intelligence": mesh.get("intelligence"),
        "continuity": cont,
        "body_epoch_id": cont.get("body_epoch_id"),
        "runtime_phase": cont.get("runtime_phase"),
        "resonance": (mesh.get("intelligence") or {}).get("resonance"),
        "observation_snapshot": mesh.get("observation_snapshot"),
        "informational_interlock": mesh.get("informational_interlock"),
        "geometric_bridges": mesh.get("geometric_bridges"),
        "query_bridge_trials": mesh.get("query_bridge_trials"),
        "source_admission_trials": mesh.get("source_admission_trials"),
        "resonance_sweep": mesh.get("resonance_sweep"),
        "geometric_echo": mesh.get("geometric_echo"),
        "rotated_echo": mesh.get("rotated_echo"),
        "ostt": mesh.get("ostt"),
        "law": "common_pulse_through_kernel_spectrum_and_body_epoch",
        "claim_boundary": mesh.get("claim_boundary"),
    }
