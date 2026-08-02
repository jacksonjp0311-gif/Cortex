from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .config import load_repo_config
from .constitutional import assess_context, memory_balance
from .control_error import build_control_error
from .environment import environment_summary
from .efficiency import efficiency_telemetry
from .graph import neighborhood
from .hippocampus import active_session
from .neuron import activate_interlink
from .glyphs.canon import encode_state, glyph_canon_registry, meta_instructions
from .progress_glyphs import progress_glyph_registry
from .resonance import clamp
from .retrieval import materialize_aria_for_task, query, support_hits
from thalamus import apply_feedback, inhibit, make_request, route


def _geometry_surface(
    *,
    governance: dict[str, Any],
    aria_materialization: dict[str, Any],
    neural_payload: dict[str, Any],
    deferred_remaining: int,
) -> dict[str, Any]:
    """Fold the five covenant axes into one packet-visible interlock map."""

    authority = governance.get("authority") or {}
    aria = (neural_payload.get("metrics") or {}).get("aria_substrate") or {}
    mode = aria.get("mode") or aria_materialization.get("mode") or "dormant"
    return {
        "schema_version": "cortex-geometry/1.0",
        "axes": {
            "authority": {
                "latched": authority.get("cortex_may_authorize_mutation") is not True,
                "mode": governance.get("mode"),
            },
            "evidence": {
                "latched": True,
                "rule": "source_and_tests_outrank_learned_memory",
            },
            "activation": {
                "latched": mode in {"dormant", "active"},
                "aria_mode": mode,
                "eligible_aria_nodes": aria.get("eligible_nodes", 0),
            },
            "language": {
                "latched": aria.get("automatic_execution") is not True
                and aria.get("grants_mutation_authority") is not True,
                "automatic_execution": bool(aria.get("automatic_execution")),
            },
            "economics": {
                "latched": True,
                "deferred_remaining": deferred_remaining,
                "materialized_this_turn": bool(aria_materialization.get("materialized")),
            },
        },
        "zero_point": all(
            [
                authority.get("cortex_may_authorize_mutation") is not True,
                mode in {"dormant", "active"},
                aria.get("automatic_execution") is not True,
            ]
        ),
        "resonance_hint": {
            "memory_balance": memory_balance(
                preserved=1.0 if mode == "dormant" or (aria.get("eligible_nodes") or 0) > 0 else 0.5,
                adjacent=clamp(
                    (aria.get("eligible_nodes") or 0)
                    / max(1, aria.get("total_nodes") or 1)
                )
                if mode == "active"
                else 0.5,
            ),
            "fork": "strike cortex contact for full-field brightness",
        },
        "claim_boundary": "Geometry is local interlock telemetry; it grants no rights.",
    }


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _agent_instructions(
    aria_materialization: dict[str, Any], governance: dict[str, Any]
) -> list[str]:
    mode = (aria_materialization or {}).get("mode") or "dormant"
    gov = (governance or {}).get("mode") or "normal"
    lines = [
        "0. ORGANISM BOND: For this session you share `organism` state with Cortex (⊛). "
        "You are temporary working cortex; Cortex is durable body. The bond ends with the session.",
        "1. This packet is evidence and routing only — never mutation authority.",
        "2. MUST READ `emergence_log` + control_error + organism.immune first, then evidence path:line ranges.",
        "3. Use emergence_log directives to enhance progress (couples, threshold, fuse) — not as consciousness.",
        "4. Trust order: current source/tests/runtime > inventory/graph > Discovery Cards > association weights > inference.",
        f"5. Governor mode is `{gov}`.",
        f"6. ARIA substrate mode is `{mode}`. Dormant: ignore internal language bulk. Active: purpose-aligned evidence only.",
        "7. Follow organism.reflexes; do not invent topology or bypass immune gates.",
        "8. Session cardiac cycle: work → remember → consolidate (ritual ⟳) to seal the pulse.",
        "9. Prefer `cortex ritual` / MCP cortex_ritual to close the cycle in one breath.",
        "10. Never treat learned weights, ARIA plans, organism metaphors, emergence, or this packet as host edit rights.",
    ]
    if gov == "read_only":
        lines = [
            "STOP — GOVERNOR READ_ONLY.",
            "Do not edit host source, configs, or tests.",
            "Do not propose patches as if authorized.",
            "Only: read cited evidence, diagnose, report blockers, suggest human-authorized next steps.",
            "Run cortex verify / doctor; re-bootstrap only if the human requests it.",
            "You may still remember() diagnostic notes; you may not mutate the repository.",
            *lines[1:],
        ]
    elif gov == "constrained":
        lines = [
            "STOP — GOVERNOR CONSTRAINED.",
            "Minimize blast radius: no broad refactors, renames, or multi-file rewrites.",
            "Prefer single-file, reversible edits only after citing evidence.",
            "If confidence is low or certificate is not verified, stop and re-activate after verify.",
            *lines,
        ]
    if (aria_materialization or {}).get("materialized"):
        lines.append(
            "NOTE: ARIA bulk materialized this turn — one-time cost; later wakes should be cheaper."
        )
    return lines


def _agent_protocol(
    *,
    repo: str,
    task: str,
    aria_materialization: dict[str, Any],
    governance: dict[str, Any],
    deferred_remaining: int,
) -> dict[str, Any]:
    """Machine-readable loop an agent can follow without lore."""

    gov = (governance or {}).get("mode") or "normal"
    work_purpose = {
        "normal": "edit/test only under host and human authority",
        "constrained": "minimal reversible edits only; no broad refactors",
        "read_only": "NO repository mutation; diagnose and report only",
    }.get(gov, "edit/test only under host and human authority")
    allowed_actions = {
        "normal": ["read_evidence", "edit_with_host_authority", "test", "remember", "consolidate"],
        "constrained": ["read_evidence", "minimal_edit", "test", "remember", "consolidate", "verify"],
        "read_only": ["read_evidence", "diagnose", "remember", "verify", "report"],
    }.get(gov, ["read_evidence", "remember"])
    return {
        "schema_version": "cortex-agent-protocol/1.1",
        "repo": repo,
        "task": task,
        "entrypoints": {
            "cli_activate": f'cortex activate --repo {repo} --task "<task>" --json',
            "cli_ritual": (
                f'cortex ritual --repo {repo} --task "<task>" '
                f'--remember-kind discovery --remember-text "<fact>" --json'
            ),
            "mcp_context": "cortex_context",
            "mcp_ritual": "cortex_ritual",
            "wrapper_ps": ".\\.cortex\\bin\\cortex.ps1 activate -Task \"<task>\"",
            "wrapper_sh": "./.cortex/bin/cortex.sh activate --task \"<task>\"",
        },
        "steps": [
            {
                "id": "activate",
                "command": f'cortex activate --repo {repo} --task "<task>" --json',
                "purpose": "bounded evidence packet + session",
            },
            {
                "id": "obey_governor",
                "purpose": f"mode={gov}; allowed={','.join(allowed_actions)}",
            },
            {
                "id": "work",
                "purpose": work_purpose,
            },
            {
                "id": "remember",
                "command": (
                    f'cortex remember --repo {repo} --kind decision|discovery|failure|fix '
                    f'--text "<fact>" --json'
                ),
                "purpose": "append-only session events",
            },
            {
                "id": "consolidate",
                "command": f"cortex consolidate --repo {repo} --json",
                "purpose": "Discovery Card with provenance; source remains authoritative",
            },
            {
                "id": "ritual",
                "command": (
                    f'cortex ritual --repo {repo} --task "<task>" '
                    f'--remember-kind discovery --remember-text "<fact>" --json'
                ),
                "purpose": "single-command activate → remember → consolidate",
            },
        ],
        "state": {
            "governor_mode": gov,
            "aria_mode": (aria_materialization or {}).get("mode") or "dormant",
            "aria_materialized_this_turn": bool(
                (aria_materialization or {}).get("materialized")
            ),
            "deferred_substrate_remaining": deferred_remaining,
            "may_mutate_repository": False,
            "work_allowed": gov != "read_only",
            "broad_refactor_allowed": gov == "normal",
            "allowed_actions": allowed_actions,
        },
        "hard_stops": (
            ["repository_mutation", "broad_refactor", "ignore_certificate"]
            if gov == "read_only"
            else ["broad_refactor", "ignore_low_confidence"]
            if gov == "constrained"
            else ["treat_packet_as_authorization"]
        ),
        "organism_bond": {
            "glyph": "⊛",
            "role": "session_co_process",
            "agent": "temporary_working_cortex",
            "cortex": "durable_body",
            "separable": True,
        },
        "refuse": [
            "new_memory_database",
            "auto_execute_aria",
            "treat_packet_as_authorization",
            "new_neural_region_without_covenant_axis",
            "glow_chasing_without_quality_gate",
            "unsolicited_foreign_repo_scan",
            "claim_shared_consciousness",
        ],
    }


def attach_agent_surfaces(context: dict[str, Any]) -> dict[str, Any]:
    """Ensure every derived packet carries the same agent-facing protocol."""

    if "agent_protocol" not in context and context.get("repository"):
        # Rebuild minimal protocol if a partial packet is passed.
        context = {
            **context,
            "agent_protocol": _agent_protocol(
                repo=str((context.get("repository") or {}).get("name") or ""),
                task=str(context.get("task") or ""),
                aria_materialization=context.get("aria_materialization") or {},
                governance=context.get("governor") or {},
                deferred_remaining=int(
                    ((context.get("efficiency") or {}).get("aria_substrate") or {}).get(
                        "deferred_remaining"
                    )
                    or 0
                ),
            ),
        }
    if "instructions" not in context:
        context = {
            **context,
            "instructions": _agent_instructions(
                context.get("aria_materialization") or {},
                context.get("governor") or {},
            ),
        }
    return context


def _merge_candidates(
    direct_hits: list[Any],
    support: list[Any],
    neural_packet: dict[str, Any] | None,
) -> list[Any]:
    scored: dict[int, tuple[float, Any]] = {}
    direct_count = max(1, len(direct_hits))
    for rank, hit in enumerate(direct_hits):
        hit.metadata["selection_source"] = "hybrid_retrieval"
        priority = 1.0 - (0.35 * rank / direct_count)
        scored[hit.memory_id] = (priority, hit)

    potential_by_path: dict[str, float] = {}
    if neural_packet:
        for record in neural_packet.get("records", []):
            if record.get("fired"):
                potential_by_path[record["path"]] = float(record["potential"])
    for hit in support:
        priority = 0.76 + 0.20 * potential_by_path.get(hit.path, 0.0)
        current = scored.get(hit.memory_id)
        if current is None or priority > current[0]:
            scored[hit.memory_id] = (priority, hit)
    return [
        hit
        for _, hit in sorted(
            scored.values(),
            key=lambda item: (-item[0], item[1].path, item[1].start_line),
        )
    ]


def build_context(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    task: str,
    budget: int = 1200,
    manifest_current: bool | None = None,
    certificate: dict[str, Any] | None = None,
    budget_scheme: str = "fib",
    memory_controller: str | None = None,
) -> dict[str, Any]:
    repository = store.repo(repo)
    if not repository:
        raise ValueError(f"Unknown repository: {repo}")
    root = Path(repository["path"])
    # External attachments live under home/attachments — pass home for resolve
    config = load_repo_config(root, home)
    # Certificate-deferred ARIA bulk materializes only on intentional activation,
    # never as a side effect of verify/probe queries.
    aria_materialization = materialize_aria_for_task(store, repo, task)
    active = active_session(home, repo)
    if config.thalamus_enabled:
        request = make_request(
            repository,
            task,
            budget,
            active_files=tuple((active or {}).get("files", [])),
        )
        route_plan = route(request, manifest_current=manifest_current)
    else:
        route_plan = None

    # Every standard context retrieval is planned by Thalamus before candidates are read.
    # If ARIA just materialized (or is active/ready), query with substrate included.
    aria_mode_pre = (aria_materialization.get("mode") or "dormant")
    # Memory Simplex controller (v6.24)
    mc = memory_controller
    use_baseline = bool(mc and str(mc).casefold().startswith("evidence"))
    direct_hits = query(
        store,
        repo,
        task,
        limit=24,
        semantic_scan_limit=config.semantic_scan_limit,
        materialize_substrate=False,
        prove_implementation=(aria_mode_pre == "active") and not use_baseline,
        ranker_primary=not use_baseline,
        enrich_spectral=not use_baseline,
        concept_routes=not use_baseline,
        memory_controller=mc,
    )
    # Second chance: active but sparse ARIA evidence → force materialize once more
    # then re-query (evidence selection gap: cards without substrate proof).
    aria_paths = sum(
        1
        for h in direct_hits
        if str(getattr(h, "path", "")).replace("\\", "/").startswith(
            "cortex/aria_meta/"
        )
    )
    if aria_mode_pre == "active" and aria_paths < 2:
        from .indexer import ensure_aria_substrate_materialized

        retry = ensure_aria_substrate_materialized(store, repo, config, task)
        if retry.get("materialized") or retry.get("already_ready"):
            if retry.get("materialized"):
                from .graph import resolve_graph
                from .neuron import compile_interlink

                resolve_graph(store, repo)
                if config.neural_interlink_enabled:
                    compile_interlink(store, repo)
            aria_materialization = {**aria_materialization, **retry, "evidence_retry": True}
            direct_hits = query(
                store,
                repo,
                task,
                limit=24,
                semantic_scan_limit=config.semantic_scan_limit,
                materialize_substrate=False,
                prove_implementation=(not use_baseline),
                ranker_primary=not use_baseline,
                enrich_spectral=not use_baseline,
                concept_routes=not use_baseline,
                memory_controller=mc,
            )
    if route_plan:
        direct_hits = apply_feedback(store, repo, direct_hits)
        direct_hits = inhibit(
            direct_hits,
            route_plan.lane_weights,
            min_lane_relevance=config.thalamus_min_lane_relevance,
        )
    semantic_confidences = [
        hit.metadata.get("semantic_similarity", 0.0) for hit in direct_hits[:5]
    ]
    confidence = sum(max(0.0, value) for value in semantic_confidences) / max(
        1, len(semantic_confidences)
    )
    governance = governor.evaluate(
        repo, retrieval_confidence=confidence, manifest_current=manifest_current, certificate=certificate
    )

    effective_budget = budget
    if governance["mode"] == "constrained":
        effective_budget = min(budget, 800)
    elif governance["mode"] == "read_only":
        effective_budget = min(budget, 600)

    neural_payload: dict[str, Any]
    support: list[Any] = []
    if config.neural_interlink_enabled and store.neural_nodes(repo):
        neural = activate_interlink(
            store,
            repo,
            task,
            direct_hits,
            max_depth=config.neural_activation_depth,
            max_nodes=config.neural_max_nodes,
            learning_rate=config.neural_learning_rate,
            plasticity_enabled=config.neural_plasticity_enabled,
            governance_mode=governance["mode"],
            session_id=(active or {}).get("session_id"),
        )
        neural_payload = neural.to_dict()
        support = support_hits(
            store,
            repo,
            task,
            list(neural.support_paths),
            limit=max(6, min(16, config.neural_max_nodes // 4)),
        )
    else:
        neural_payload = {
            "available": False,
            "reason": "neural interlink disabled or not compiled",
            "records": [],
            "support_paths": [],
            "metrics": {},
        }

    # Binary-intel packs: domain zero-in / expand surface (Cortex memory branch).
    pack_surface: dict[str, Any] = {}
    try:
        from .packs.memory import pack_surface_for_packet

        pack_surface = pack_surface_for_packet(home, store, repo, task)
        if pack_surface.get("expand") and pack_surface.get("expanded_cards"):
            # Inject expanded pack card texts as synthetic high-signal candidates
            from .models import Hit

            extra_hits: list[Any] = []
            for i, card in enumerate(pack_surface.get("expanded_cards") or []):
                extra_hits.append(
                    Hit(
                        memory_id=-(i + 1),
                        repo=repo,
                        path=str(card.get("path") or f"cortex-packs/expand/{i}"),
                        start_line=1,
                        end_line=max(1, str(card.get("text") or "").count("\n") + 1),
                        text=str(card.get("text") or ""),
                        kind="intelligence_pack",
                        score=0.92 - 0.01 * i,
                        content_hash=str(i),
                        metadata={
                            "selection_source": "binary_intel_expand",
                            "pack_id": card.get("pack_id"),
                            "domain": card.get("domain"),
                            "prove_implementation": False,
                        },
                    )
                )
            if extra_hits:
                direct_hits = list(extra_hits) + list(direct_hits)
    except Exception as exc:
        pack_surface = {
            "glyph": "▣",
            "error": f"{type(exc).__name__}: {exc}",
            "expand": False,
        }

    candidates = _merge_candidates(direct_hits, support, neural_payload)
    aria_mode = (aria_materialization.get("mode") or "dormant")
    # When ARIA is awake, cap per-chunk spend so one vendored doc cannot monopolize
    # the packet and erase the multi-path evidence floor.
    per_hit_token_cap = max(120, effective_budget // (4 if aria_mode == "active" else 1))
    # v6 bottleneck reduction: diversify paths (organism-like fan-out, not monopoly)
    # v6.2 efficiency: tighter path fan-out → fewer tokens, more diversity
    max_chunks_per_path = 1 if aria_mode == "active" else 2

    # v6.21 ratio lattice: multi-res budget pools (fib default; flat = pre-6.21)
    from .math_net.ratio_lattice import hit_resolution, partition_budgets

    part = partition_budgets(
        effective_budget,
        ("symbol", "file", "module"),
        scheme=budget_scheme or "fib",
    )
    pools = dict(part.get("pools") or {})
    used_by_level: dict[str, int] = {k: 0 for k in pools}
    spillover_by_level: dict[str, int] = {k: 0 for k in pools}
    envelope_stress = 0
    # flat scheme: single shared pool on first key
    if (part.get("scheme") or "fib") == "flat":
        pools = {"all": effective_budget}
        used_by_level = {"all": 0}

    selected: list[dict[str, Any]] = []
    used_tokens = 0
    aria_paths_selected = 0
    path_chunk_counts: dict[str, int] = {}
    for hit in candidates:
        path_key = str(hit.path or "").replace("\\", "/")
        if path_chunk_counts.get(path_key, 0) >= max_chunks_per_path:
            continue
        meta_hit = getattr(hit, "metadata", None) or {}
        if isinstance(hit, dict):
            meta_hit = hit.get("metadata") or {}
        level = hit_resolution(path_key, meta_hit if isinstance(meta_hit, dict) else {})
        if (part.get("scheme") or "fib") == "flat":
            level = "all"
        elif level not in pools:
            level = "file" if "file" in pools else next(iter(pools), "file")

        preferred_level = level
        prefix = f"[{hit.path}:{hit.start_line}-{hit.end_line}]\n"
        remaining_budget = effective_budget - used_tokens
        pool_remaining = int(pools.get(level, 0)) - int(used_by_level.get(level, 0))
        # First spill toward coarser envelopes, then reclaim unused finer pools.
        # This keeps the hierarchy but prevents an empty symbol lane from
        # stranding half of an otherwise useful packet.
        if pool_remaining < 20 and (part.get("scheme") or "") != "flat":
            ordered_levels = list(pools)
            try:
                at = ordered_levels.index(level)
            except ValueError:
                at = 0
            spill_order = ordered_levels[at + 1 :] + list(
                reversed(ordered_levels[:at])
            )
            for alternate in spill_order:
                available = int(pools.get(alternate, 0)) - int(
                    used_by_level.get(alternate, 0)
                )
                if available >= 20:
                    level = alternate
                    pool_remaining = available
                    break
        if pool_remaining <= 0:
            envelope_stress += 1
            continue

        # Reserve tokens for a second ARIA path when substrate is active.
        reserve = 0
        if (
            aria_mode == "active"
            and aria_paths_selected < 2
            and not path_key.startswith("cortex/aria_meta/vendor/")
        ):
            reserve = min(180, max(0, remaining_budget // 3))
        available_chars = max(
            0, (min(remaining_budget, pool_remaining) - reserve) * 4 - len(prefix)
        )
        if available_chars <= 80:
            continue
        max_chars = min(available_chars, per_hit_token_cap * 4)
        text = hit.text[:max_chars]
        token_cost = estimate_tokens(prefix + text)
        if token_cost <= 0:
            continue
        if used_tokens + token_cost > effective_budget:
            continue
        if token_cost > pool_remaining:
            # try truncate to pool remainder
            if pool_remaining < 20:
                envelope_stress += 1
                continue
            max_chars = min(max_chars, pool_remaining * 4)
            text = hit.text[:max_chars]
            token_cost = estimate_tokens(prefix + text)
            if token_cost > pool_remaining or token_cost <= 0:
                envelope_stress += 1
                continue
        selected.append(
            {
                "memory_id": hit.memory_id,
                "path": hit.path,
                "line_range": [hit.start_line, hit.end_line],
                "kind": hit.kind,
                "score": hit.score,
                "content_hash": hit.content_hash,
                "text": text,
                "metadata": hit.metadata,
                "resolution_level": preferred_level,
                "budget_level": level,
                "budget_spillover": level != preferred_level,
            }
        )
        used_tokens += token_cost
        used_by_level[level] = int(used_by_level.get(level, 0)) + token_cost
        if level != preferred_level:
            spillover_by_level[level] = int(spillover_by_level.get(level, 0)) + token_cost
        path_chunk_counts[path_key] = path_chunk_counts.get(path_key, 0) + 1
        if path_key.startswith("cortex/aria_meta/vendor/"):
            aria_paths_selected += 1
        if used_tokens >= effective_budget:
            break

    graph_context = neighborhood(
        store, repo, [item["path"] for item in selected[:8]], limit=30
    )
    environment = environment_summary(store.environment_profile(repo))
    deferred_remaining = sum(
        1
        for row in store.files(repo)
        if row["status"] == "substrate_deferred"
    )
    control_error = build_control_error(
        certificate=certificate,
        governance=governance,
        manifest_current=manifest_current,
        retrieval_confidence=confidence,
        aria_materialization=aria_materialization,
        task=task,
    )
    instructions = _agent_instructions(aria_materialization, governance)
    if control_error.get("errors"):
        instructions = [
            f"CONTROL_ERROR ({control_error['severity']}): {control_error['summary']}",
            "Read control_error first. Obey must_reverify and work_allowed.",
            *instructions,
        ]
    protocol = _agent_protocol(
        repo=repo,
        task=task,
        aria_materialization=aria_materialization,
        governance=governance,
        deferred_remaining=deferred_remaining,
    )
    protocol["state"]["must_reverify"] = bool(control_error.get("must_reverify"))
    protocol["state"]["control_severity"] = control_error.get("severity")
    protocol["state"]["block"] = bool(control_error.get("block"))
    protocol["state"]["immune_action"] = control_error.get("immune_action")
    if control_error.get("block") or control_error.get("must_reverify"):
        protocol["hard_stops"] = list(
            dict.fromkeys(
                [
                    *(protocol.get("hard_stops") or []),
                    "ignore_control_error",
                    "ignore_immune_block",
                ]
            )
        )
    if control_error.get("errors"):
        instructions = [
            f"IMMUNE_ACTION: {control_error.get('immune_action', {}).get('code')} — "
            f"{control_error.get('immune_action', {}).get('message')}",
            *instructions,
        ]
    # MUST READ: emergence log (progress enhancement) — before work
    emergence_surface: dict[str, Any] = {}
    try:
        from .coherence import measure_coherence
        from .emergence_log import read_emergence_log

        # Refresh coherence so log captures this turn's field
        measure_coherence(
            store,
            repo,
            governor=governor,
            home=home,
            retrieval_confidence=confidence,
        )
        emergence_surface = read_emergence_log(home, store, repo, limit=12)
        if emergence_surface.get("instruction_lines"):
            instructions = [
                *list(emergence_surface["instruction_lines"]),
                *instructions,
            ]
        protocol["steps"] = [
            {
                "id": "read_emergence_log",
                "purpose": "MUST READ — enhance progress from coupling history",
                "command": f"cortex emergence-log --repo {repo} --json",
                "must_read": True,
            },
            *(protocol.get("steps") or []),
        ]
        protocol["state"]["emergence_log_events"] = emergence_surface.get("event_count")
        protocol["state"]["emergent_coupling"] = (
            (emergence_surface.get("coherence_snapshot") or {}).get("emergent_coupling")
        )
        protocol["refuse"] = list(
            dict.fromkeys(
                [
                    *(protocol.get("refuse") or []),
                    "ignore_emergence_log",
                    "claim_emergence_as_consciousness",
                ]
            )
        )
    except Exception as exc:
        emergence_surface = {"must_read": True, "error": f"{type(exc).__name__}: {exc}"}
        instructions = [
            "EMERGENCE LOG unavailable this turn — still obey control_error and governor.",
            *instructions,
        ]
    payload: dict[str, Any] = {
        "schema_version": "1.5",
        "generated_at": time.time(),
        "read_first": True,
        "must_read": ["control_error", "emergence_log", "agent_protocol"],
        "block": bool(control_error.get("block")),
        "immune_action": control_error.get("immune_action"),
        "control_error": control_error,
        "emergence_log": emergence_surface,
        "repository": {
            "name": repo,
            "repository_id": repository["repository_id"],
            "path": repository["path"],
            "manifest_hash": repository["manifest_hash"],
            "manifest_current": manifest_current,
            "bootstrap_status": repository["bootstrap_status"],
        },
        "task": task,
        "active_focus": active,
        "governor": governance,
        "context_budget": effective_budget,
        "estimated_tokens": used_tokens,
        "budget_partition": {
            "scheme": part.get("scheme"),
            "pools": pools,
            "used_by_level": used_by_level,
            "spillover_by_level": spillover_by_level,
            "spillover_tokens": sum(spillover_by_level.values()),
            "envelope_stress": envelope_stress,
            "sum_check": part.get("sum_check"),
            "claim_boundary": part.get("claim_boundary")
            or (
                "Budget heuristic from self-similar / rational partition — "
                "not golden-ratio activation or sacred geometry."
            ),
        },
        "memory_simplex": {
            "controller": mc or "advanced",
            "claim_boundary": (
                "Memory Simplex controller for this packet — advanced adaptive vs "
                "EVIDENCE_BASELINE trusted path. Not host authority."
            ),
        },
        "environment": environment,
        "thalamus": route_plan.to_dict() if route_plan else {"available": False, "reason": "disabled"},
        "neural_interlink": neural_payload,
        "aria_materialization": aria_materialization,
        "evidence": selected,
        "structural_neighborhood": graph_context,
        "instructions": instructions,
        "agent_protocol": protocol,
        "progress_glyphs": progress_glyph_registry(),
        "packs": {
            "glyph": "▣",
            "top_domain": pack_surface.get("top_domain"),
            "top_score": pack_surface.get("top_score"),
            "expand": pack_surface.get("expand"),
            "domains": (pack_surface.get("domains") or [])[:6],
            "expanded_count": len(pack_surface.get("expanded_cards") or []),
            "indexed": pack_surface.get("indexed"),
            "doctrine": pack_surface.get("doctrine"),
            "claim_boundary": pack_surface.get("claim_boundary"),
        }
        if pack_surface
        else {"glyph": "▣", "expand": False, "indexed": False},
    }
    # Keep full pack surface for debug / domain expand consumers
    if pack_surface:
        payload["pack_surface"] = pack_surface
    payload["efficiency"] = efficiency_telemetry(
        direct_candidates=len(direct_hits),
        context_tokens=used_tokens,
        context_budget=effective_budget,
        neural=neural_payload,
        aria_materialization=aria_materialization,
        deferred_substrate_remaining=deferred_remaining,
    )
    payload["geometry"] = _geometry_surface(
        governance=governance,
        aria_materialization=aria_materialization,
        neural_payload=neural_payload,
        deferred_remaining=deferred_remaining,
    )
    payload["constitutional_supervision"] = assess_context(payload)
    # Glyph Canon meta-medium: compress routing into ◈ line (ARIA-addressable).
    try:
        xi = ((payload.get("connect_pass") or {}).get("xi_spectrum") or {})
        dominant = None
        if isinstance(xi, dict) and xi:
            dominant = max(
                ((k, (v or {}).get("share") or 0) for k, v in xi.items() if isinstance(v, dict)),
                key=lambda item: item[1],
                default=(None, 0),
            )[0]
        resonance = (
            ((payload.get("connect_pass") or {}).get("intel_pulse") or {}).get("resonance")
            or {}
        )
        glyph_state = encode_state(
            control=control_error,
            governor=governance,
            aria=aria_materialization,
            resonance=resonance if isinstance(resonance, dict) else {},
            kernels={"dominant": dominant} if dominant else {},
        )
        payload["glyph_state"] = glyph_state
        payload["glyph_canon"] = {
            "schema_version": glyph_canon_registry()["schema_version"],
            "glyph": "◈",
            "count": glyph_canon_registry()["count"],
            "aria_role": "meta_medium",
        }
        # Prefer glyph meta-instructions when not emergency blocked (token thrift).
        if not control_error.get("block"):
            payload["instructions"] = meta_instructions(
                glyph_state,
                governor_mode=str((governance or {}).get("mode") or "normal"),
            )
            if control_error.get("errors"):
                payload["instructions"] = [
                    f"⚠ {control_error.get('severity')}: {control_error.get('summary')}",
                    *payload["instructions"],
                ]
    except Exception:
        payload["glyph_state"] = {"line": "◈", "error": "encode_failed"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["packet_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    packet_path = home / "packets" / f"{repo}-context-latest.json".replace("/", "_")
    packet_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["packet_path"] = str(packet_path)
    return payload


def nexus_packet(context: dict[str, Any]) -> dict[str, Any]:
    context = attach_agent_surfaces(context)
    return {
        "schema_version": "1.2",
        "intent": {
            "task": context["task"],
            "active_focus": context["active_focus"],
        },
        "evidence": context["evidence"],
        "authority": {
            "mode": "recommend_only",
            "human_authorized_only": True,
            "cortex_may_mutate": False,
            "governor_mode": context["governor"]["mode"],
        },
        "instructions": context.get("instructions"),
        "agent_protocol": context.get("agent_protocol"),
        "aria_materialization": context.get("aria_materialization"),
        "geometry": context.get("geometry"),
        "context": {
            "repository": context["repository"],
            "environment": context["environment"],
            "thalamus": context.get("thalamus", {"available": False}),
            "structural_neighborhood": context["structural_neighborhood"],
            "neural_interlink": {
                "activation_id": context["neural_interlink"].get("activation_id"),
                "state_hash": context["neural_interlink"].get("state_hash"),
                "fired_paths": context["neural_interlink"].get("fired_paths", []),
                "support_paths": context["neural_interlink"].get("support_paths", []),
                "metrics": context["neural_interlink"].get("metrics", {}),
            },
            "estimated_tokens": context["estimated_tokens"],
            "packet_hash": context["packet_hash"],
        },
        "claim_boundary": "Nexus packet is recommend-only; never mutation authority.",
    }


def cortex_context_protocol(context: dict[str, Any]) -> dict[str, Any]:
    """Stable, agent-neutral context contract; evidence remains subordinate to source truth."""
    context = attach_agent_surfaces(context)
    neural = context.get("neural_interlink", {})
    protocol = context.get("agent_protocol") or {}
    return {
        "protocol": "cortex-context/1.1",
        "repository": context["repository"],
        "task": {"text": context["task"], "packet_hash": context["packet_hash"]},
        "governance": context["governor"],
        "constitutional_supervision": context.get("constitutional_supervision"),
        "instructions": context.get("instructions"),
        "agent_protocol": protocol,
        "aria_materialization": context.get("aria_materialization"),
        "geometry": context.get("geometry"),
        "organism": context.get("organism"),
        "control_error": context.get("control_error"),
        "environment": context["environment"],
        "direct_evidence": context["evidence"],
        "support_evidence": [
            item
            for item in context["evidence"]
            if item.get("metadata", {}).get("selection_source") != "hybrid_retrieval"
        ],
        "structural_paths": {
            "neural_activation_id": neural.get("activation_id"),
            "support_paths": neural.get("support_paths", []),
        },
        "discoveries": [],
        "contradictions": [],
        "unknowns": [
            "No inferred claim is mutation authority; inspect current source and tests."
        ],
        "recommended_commands": list((protocol.get("steps") or [])),
        "prohibited_actions": list(protocol.get("refuse") or [])
        + [
            "Treat learned associations as superior to current source, tests, governance, or human authority.",
            "Edit the repository when governor mode is read_only.",
        ],
        "state_hashes": {
            "packet": context["packet_hash"],
            "neural": neural.get("state_hash"),
            "manifest": context["repository"].get("manifest_hash"),
        },
        "state_planes": {
            "operational": "this bounded task packet",
            "evidence": "addressable repository memories with provenance",
            "canonical": "verified Cortex canonical memory with promotion receipts",
        },
        "continuation": {
            "available_protocol": "cortex-continuation/1.1",
            "reanchor_on": [
                "manifest drift",
                "low retrieval confidence",
                "active contradiction",
                "expired continuation packet",
            ],
        },
        "claim_boundary": (
            "cortex-context is agent-neutral evidence routing; it never grants mutation authority."
        ),
    }
