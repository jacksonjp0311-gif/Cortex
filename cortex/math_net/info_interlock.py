"""v8.2 typed informational interlocks and triadic alignment.

The measured triad is Evidence (E) -> Learned route (L) -> independently
verified Outcome (O).  All metrics are shadow telemetry.  They do not grant
authority, alter the ranker, or prove consciousness / subjective sensing.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from itertools import product
import json
import math
import random
from typing import Any, Iterable, Sequence

from ..epoch import current_body_epoch
from .ratio_lattice import build_undirected_adj, local_closure, triadic_metrics


SCHEMA = "cortex-information-interlock/1.0"
GLYPH = "⟁"
BRIDGE_GLYPH = "⟠"
READINESS_SCHEMA = "cortex-interlock-readiness/1.0"
TEMPORAL_FRAME_MIN = 16
OVERALL_VALID_MIN = 128
CLAIM = (
    "Informational interlocks are epoch-audited, cohort-scoped E-L-O outcome telemetry. "
    "Synergy is a conservative mutual-information proxy, not full PID; "
    "the field is advisory and is not consciousness or mutation authority."
)


def measurement_cohort_identity(
    *,
    repo: str,
    repository_id: str,
    evidence_root_hash: str,
    schema_hash: str,
    constitutional_config_hash: str,
    coordinate_schema_digest: str | None = None,
    prefix: str = "ico",
) -> str:
    """Derive one canonical compatible-measurement cohort identifier.

    Activation conformance passes its coordinate schema digest and uses the
    ``aco`` namespace.  Existing E-L-O cohorts omit it for backward-compatible
    information-interlock reporting.
    """
    material = {
        "repo": str(repo),
        "repository_id": str(repository_id),
        "evidence_root_hash": str(evidence_root_hash),
        "schema_hash": str(schema_hash),
        "constitutional_config_hash": str(constitutional_config_hash),
    }
    if coordinate_schema_digest is not None:
        material["coordinate_schema_digest"] = str(coordinate_schema_digest)
    if not all(material.values()):
        raise ValueError("measurement_cohort_identity_incomplete")
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_" + sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _task_family(task: str, thalamus: dict[str, Any]) -> str:
    routed = str(thalamus.get("primary_intent") or thalamus.get("intent") or "unknown")
    if routed not in {"", "unknown"}:
        return routed
    lowered = task.casefold()
    families = (
        ("code_change", ("implement", "fix", "add", "build", "refactor", "evolve", "change")),
        ("verification", ("test", "verify", "validate", "benchmark", "check")),
        ("analysis", ("analyze", "inspect", "study", "diagnose", "report")),
        ("documentation", ("document", "readme", "guide", "explain")),
        ("release", ("release", "publish", "push", "merge")),
    )
    for family, cues in families:
        if any(cue in lowered for cue in cues):
            return family
    return "unknown"


def observe_activation_interlock(
    store: Any,
    repo: str,
    activation: dict[str, Any],
    *,
    task: str,
) -> dict[str, Any]:
    """Extract and persist one unresolved typed observation from activation."""
    context = activation.get("context_full") or activation.get("context") or {}
    neural = context.get("neural_interlink") or {}
    activation_id = str(neural.get("activation_id") or "")
    if not activation_id:
        return {"observed": False, "reason": "neural_activation_missing"}
    evidence = [
        str(item.get("path") or "")
        for item in (context.get("evidence") or [])
        if isinstance(item, dict) and item.get("path")
    ]
    learned = list(neural.get("support_paths") or [])
    if not learned:
        seed_paths = set(neural.get("seed_paths") or [])
        learned = [p for p in (neural.get("fired_paths") or []) if p not in seed_paths]
    body_epoch = activation.get("body_epoch") or {}
    epoch_id = str(body_epoch.get("epoch_id") or "")
    cohort_material = {
        "repo": repo,
        "repository_id": body_epoch.get("repository_id"),
        "evidence_root_hash": body_epoch.get("evidence_root_hash"),
        "schema_hash": body_epoch.get("schema_hash"),
        "constitutional_config_hash": body_epoch.get("constitutional_config_hash"),
    }
    cohort_ready = all(cohort_material.values())
    cohort_id = (
        measurement_cohort_identity(**cohort_material)
        if cohort_ready
        else f"epoch:{epoch_id}"
    )
    thalamus = context.get("thalamus") or {}
    task_family = _task_family(task, thalamus)
    geometry = context.get("geometry") or {}
    axes = geometry.get("axes") or {}
    constitutional_valid = bool(
        epoch_id
        and (activation.get("activation_finalization") or {}).get("ok")
        and geometry.get("zero_point")
        and axes
        and all(
            isinstance(axis, dict) and bool(axis.get("latched"))
            for axis in axes.values()
        )
    )
    u_after = context.get("u")
    if u_after is None:
        u_after = ((context.get("governor") or {}).get("uncertainty") or {}).get("u")
    receipt = store.record_interlock_observation(
        repo,
        activation_id=activation_id,
        session_id=(activation.get("session") or {}).get("session_id"),
        body_epoch_id=epoch_id,
        task_family=task_family,
        evidence_paths=evidence,
        learned_paths=[str(p) for p in learned],
        constitutional_valid=constitutional_valid,
        u_after=float(u_after) if u_after is not None else None,
        metadata={
            "task_hash": neural.get("task_hash"),
            "task_text_hash": sha256(task.encode("utf-8")).hexdigest(),
            "controller": (activation.get("controller_execution") or {}).get("resolved"),
            "evidence_role": "E",
            "learned_role": "L",
            "outcome_role": "O_pending",
            "measurement_cohort_id": cohort_id,
            "cohort_basis": (
                "repo+repository_id+evidence_root+schema+constitutional_config"
            ),
            "shadow_only": True,
        },
    )
    return {
        "observed": True,
        **receipt,
        "task_family": task_family,
        "evidence_count": len(set(evidence)),
        "learned_count": len(set(learned)),
        "constitutional_valid": constitutional_valid,
        "measurement_cohort_id": cohort_id,
        "advisory_only": True,
    }


def _entropy(counts: Iterable[float]) -> float:
    values = [float(v) for v in counts if float(v) > 0.0]
    total = sum(values)
    if total <= 0.0:
        return 0.0
    return -sum((v / total) * math.log2(v / total) for v in values)


def mutual_information_bits(xs: Sequence[Any], ys: Sequence[Any], *, alpha: float = 0.5) -> float:
    """Discrete plug-in MI with Jeffreys smoothing, reported in bits."""
    if len(xs) != len(ys) or not xs:
        return 0.0
    x_states = sorted(set(xs), key=str)
    y_states = sorted(set(ys), key=str)
    joint = Counter(zip(xs, ys))
    nx = Counter(xs)
    ny = Counter(ys)
    cells = len(x_states) * len(y_states)
    denom = float(len(xs)) + alpha * cells
    mi = 0.0
    for x in x_states:
        for y in y_states:
            pxy = (joint[(x, y)] + alpha) / denom
            px = (nx[x] + alpha * len(y_states)) / denom
            py = (ny[y] + alpha * len(x_states)) / denom
            mi += pxy * math.log2(max(pxy, 1e-15) / max(px * py, 1e-15))
    return max(0.0, float(mi))


def synergy_proxy_bits(
    evidence_present: Sequence[int],
    learned_present: Sequence[int],
    outcomes: Sequence[int],
) -> dict[str, float]:
    """Conservative pair synergy: I(E,L;O) - max(I(E;O), I(L;O)).

    This intentionally avoids claiming a unique partial-information
    decomposition.  XOR is synergistic; duplicate predictors are redundant.
    """
    joint_predictor = list(zip(evidence_present, learned_present))
    i_e = mutual_information_bits(evidence_present, outcomes)
    i_l = mutual_information_bits(learned_present, outcomes)
    i_joint = mutual_information_bits(joint_predictor, outcomes)
    synergy = max(0.0, i_joint - max(i_e, i_l))
    redundancy = max(0.0, i_e + i_l - i_joint)
    h_outcome = _entropy(Counter(outcomes).values())
    return {
        "i_evidence_outcome_bits": round(i_e, 8),
        "i_learned_outcome_bits": round(i_l, 8),
        "i_joint_outcome_bits": round(i_joint, 8),
        "synergy_proxy_bits": round(synergy, 8),
        "redundancy_proxy_bits": round(redundancy, 8),
        "outcome_entropy_bits": round(h_outcome, 8),
    }


def _normalized_entropy(values: Sequence[float]) -> float:
    vals = [max(0.0, float(v)) for v in values]
    if not vals or sum(vals) <= 0.0:
        return 0.0
    if len(vals) == 1:
        return 1.0
    return max(0.0, min(1.0, _entropy(vals) / math.log2(len(vals))))


def triad_alignment_score(
    *,
    typed_closure: float,
    normalized_synergy: float,
    outcome_validity: float,
    redundancy_penalty: float,
    constitutional_gate: bool,
    sample_reliability: float = 1.0,
) -> dict[str, float | bool]:
    """A_tau = G*(C*S*V)^(1/3)*B*(1-D), with bounded inputs."""
    c = max(0.0, min(1.0, float(typed_closure)))
    s = max(0.0, min(1.0, float(normalized_synergy)))
    v = max(0.0, min(1.0, float(outcome_validity)))
    d = max(0.0, min(1.0, float(redundancy_penalty)))
    r = max(0.0, min(1.0, float(sample_reliability)))
    balance = _normalized_entropy((c, s, v))
    base = (c * s * v) ** (1.0 / 3.0) if c * s * v > 0 else 0.0
    score = base * balance * (1.0 - d) * r if constitutional_gate else 0.0
    return {
        "alignment": round(max(0.0, min(1.0, score)), 8),
        "typed_closure": round(c, 8),
        "normalized_synergy": round(s, 8),
        "outcome_validity": round(v, 8),
        "balance": round(balance, 8),
        "redundancy_penalty": round(d, 8),
        "sample_reliability": round(r, 8),
        "constitutional_gate": bool(constitutional_gate),
    }


def graph_sampling_audit(store: Any, repo: str, *, cap: int = 400) -> dict[str, Any]:
    """Compare the complete graph with the historical top-degree projection."""
    full = triadic_metrics(store, repo, max_nodes=0)
    projected = triadic_metrics(store, repo, max_nodes=max(1, int(cap)))
    full_nodes = int(full.get("n_nodes") or 0)
    full_triangles = int(full.get("triangles") or 0)
    projected_triangles = int(projected.get("triangles") or 0)
    closure_delta = float(projected.get("global_closure_T") or 0.0) - float(
        full.get("global_closure_T") or 0.0
    )
    local_ratio = float(projected.get("mean_local_closure") or 0.0) / max(
        1e-12, float(full.get("mean_local_closure") or 0.0)
    )
    return {
        "schema_version": "cortex-triadic-sampling-audit/1.0",
        "full": full,
        "top_degree_projection": projected,
        "node_coverage": round(int(projected.get("n_nodes") or 0) / max(1, full_nodes), 6),
        "triangle_concentration": round(projected_triangles / max(1, full_triangles), 6),
        "global_closure_delta": round(closure_delta, 6),
        "mean_local_ratio": round(local_ratio, 6),
        "sampling_agreement": abs(closure_delta) <= 0.02,
        "claim_boundary": (
            "This audit exposes top-degree truncation bias; the complete graph is the "
            "reference for release decisions."
        ),
    }


def _path_domain(node_id: str) -> str:
    path = str(node_id).replace("\\", "/")
    if path.startswith("symbol:"):
        return "symbol"
    return path.split("/", 1)[0] if "/" in path else "root"


def bridge_deconcentration_report(
    store: Any,
    repo: str,
    *,
    limit: int = 24,
) -> dict[str, Any]:
    """Rank non-hub connectors without changing retrieval or topology.

    B_v = (open_v * reach_v * diversity_v * nonhub_v)^(1/4).
    The score favors nodes with open wedges, enough reach to connect regions,
    diverse neighboring domains/relations, and distance from the dominant hub.
    """
    adj = build_undirected_adj(store, repo, max_nodes=0)
    rows = list(store.neural_synapses(repo) or [])
    relation_by_node: dict[str, list[str]] = {}
    for row in rows:
        source = str(row["source_id"] or "")
        target = str(row["target_id"] or "")
        relation = str(row["relation"] or "unknown")
        relation_by_node.setdefault(source, []).append(relation)
        relation_by_node.setdefault(target, []).append(relation)
    max_degree = max((len(neighbors) for neighbors in adj.values()), default=0)
    candidates: list[dict[str, Any]] = []
    degree_mass = sorted((len(v) for v in adj.values()), reverse=True)
    top_n = max(1, int(math.ceil(len(degree_mass) * 0.1))) if degree_mass else 1
    hub_degree_share = sum(degree_mass[:top_n]) / max(1, sum(degree_mass))

    for node_id, neighbors in adj.items():
        degree = len(neighbors)
        if degree < 2 or max_degree < 2:
            continue
        openness = 1.0 - local_closure(adj, node_id)
        reach = math.log1p(degree) / math.log1p(max_degree)
        nonhub = 1.0 - min(0.95, degree / max_degree)
        domain_diversity = _normalized_entropy(
            list(Counter(_path_domain(n) for n in neighbors).values())
        )
        relation_diversity = _normalized_entropy(
            list(Counter(relation_by_node.get(node_id) or ["unknown"]).values())
        )
        diversity = max(domain_diversity, relation_diversity)
        bridge = (
            openness * reach * diversity * nonhub
        ) ** 0.25 if openness * reach * diversity * nonhub > 0 else 0.0
        candidates.append(
            {
                "path": node_id,
                "degree": degree,
                "local_closure": round(1.0 - openness, 8),
                "open_wedge": round(openness, 8),
                "reach": round(reach, 8),
                "domain_diversity": round(domain_diversity, 8),
                "relation_diversity": round(relation_diversity, 8),
                "nonhub": round(nonhub, 8),
                "bridge_potential": round(bridge, 8),
                "shadow_only": True,
            }
        )
    candidates.sort(
        key=lambda item: (
            -float(item["bridge_potential"]),
            -float(item["domain_diversity"]),
            str(item["path"]),
        )
    )
    return {
        "schema_version": "cortex-geometric-bridge-field/1.0",
        "glyph": BRIDGE_GLYPH,
        "repo": repo,
        "mode": "shadow",
        "advisory_only": True,
        "n_nodes": len(adj),
        "n_edges": sum(len(v) for v in adj.values()) // 2,
        "max_degree": max_degree,
        "top_decile_degree_share": round(hub_degree_share, 8),
        "candidates": candidates[: max(1, int(limit))],
        "formula": "B_v=(open_wedge*log_reach*diversity*nonhub)^(1/4)",
        "policy_effect": False,
        "claim_boundary": (
            "Bridge potential is structural deconcentration telemetry. It does not "
            "change retrieval, invent edges, grant authority, or establish consciousness."
        ),
    }


def refresh_bridge_shadow(store: Any, repo: str) -> dict[str, Any]:
    report = bridge_deconcentration_report(store, repo)
    payload = {
        **report,
        "path_scores": {
            str(item["path"]): item for item in report.get("candidates", [])
        },
    }
    store.set_setting(f"bridge_shadow_latest:{repo}", payload)
    return payload


def _bootstrap_candidate_ci(
    rows: Sequence[dict[str, Any]],
    *,
    evidence_path: str,
    learned_path: str,
    min_samples: int,
    rounds: int = 400,
) -> tuple[float, float]:
    """Paired observation bootstrap for intact-vs-synergy-lesioned effect."""
    if not rows:
        return (0.0, 0.0)
    seed_material = "|".join(
        [evidence_path, learned_path]
        + [
            f"{r.get('activation_id')}:{float(r.get('reward') or 0.0):.4f}"
            for r in rows
        ]
    )
    seed = int(sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    effects: list[float] = []
    n = len(rows)
    for _ in range(max(100, int(rounds))):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        e = [int(evidence_path in r.get("evidence_paths", [])) for r in sample]
        learned = [int(learned_path in r.get("learned_paths", [])) for r in sample]
        y = [int(float(r.get("reward") or 0.0) > 0.0) for r in sample]
        opportunities = sum(1 for a, b in zip(e, learned) if a or b)
        joint = sum(1 for a, b in zip(e, learned) if a and b)
        info = synergy_proxy_bits(e, learned, y)
        h_y = float(info["outcome_entropy_bits"])
        synergy_n = float(info["synergy_proxy_bits"]) / max(h_y, 1e-12) if h_y else 0.0
        redundancy_n = float(info["redundancy_proxy_bits"]) / max(h_y, 1e-12) if h_y else 0.0
        hub = max(sum(e), sum(learned)) / max(1, n)
        penalty = min(
            1.0,
            0.5 * min(1.0, redundancy_n) + 0.5 * max(0.0, (hub - 0.5) * 2.0),
        )
        score = triad_alignment_score(
            typed_closure=joint / max(1, opportunities),
            normalized_synergy=min(1.0, synergy_n),
            outcome_validity=1.0,
            redundancy_penalty=penalty,
            constitutional_gate=True,
            sample_reliability=min(1.0, n / max(1, int(min_samples))),
        )
        effects.append(float(score["alignment"]))
    effects.sort()
    lo = effects[max(0, int(0.025 * len(effects)) - 1)]
    hi = effects[min(len(effects) - 1, int(0.975 * len(effects)))]
    return (float(lo), float(hi))


def _interlock_readiness(
    store: Any,
    repo: str,
    *,
    cohort_rows: Sequence[dict[str, Any]],
    resolved: Sequence[dict[str, Any]],
    valid: Sequence[dict[str, Any]],
    min_samples: int,
    data_ready: bool,
) -> dict[str, Any]:
    """Describe the smallest evidence runway needed for the next gate.

    This is deliberately a plan, not an executor. It converts the existing
    promotion gates into explicit deficits so operators can collect the right
    measurements instead of interpreting zero alignment as a signal to mutate
    routing or learning state.
    """
    resonance = store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}
    current_epoch = current_body_epoch(store, repo)
    current_epoch_id = str(current_epoch.epoch_id) if current_epoch else ""
    resonance_epoch_id = str(resonance.get("body_epoch_id") or "")
    resonance_current = bool(
        resonance_epoch_id
        and current_epoch_id
        and resonance_epoch_id == current_epoch_id
    )
    frame_count = (
        max(0, int(resonance.get("frame_count") or 0))
        if resonance_current
        else 0
    )
    outcome_classes = sorted(
        {
            "positive" if float(row.get("reward") or 0.0) > 0.0 else "non_positive"
            for row in valid
        }
    )
    families: dict[str, dict[str, Any]] = {}
    for family in sorted(
        {str(row.get("task_family") or "unknown") for row in cohort_rows}
    ):
        family_rows = [
            row
            for row in cohort_rows
            if str(row.get("task_family") or "unknown") == family
        ]
        family_resolved = [
            row
            for row in family_rows
            if row.get("outcome_id") and row.get("reward") is not None
        ]
        family_valid = [
            row
            for row in family_resolved
            if row.get("constitutional_valid") and row.get("witness_valid")
        ]
        family_classes = sorted(
            {
                "positive" if float(row.get("reward") or 0.0) > 0.0 else "non_positive"
                for row in family_valid
            }
        )
        families[family] = {
            "observations": len(family_rows),
            "resolved": len(family_resolved),
            "valid": len(family_valid),
            "valid_remaining": max(0, int(min_samples) - len(family_valid)),
            "outcome_classes": family_classes,
            "outcome_variation": len(family_classes) >= 2,
            "data_ready": (
                len(family_valid) >= int(min_samples)
                and len(family_classes) >= 2
            ),
        }

    actions: list[str] = []

    def add(action: str) -> None:
        if action not in actions:
            actions.append(action)

    if frame_count < TEMPORAL_FRAME_MIN:
        add("collect_same_epoch_frames")
    if not cohort_rows:
        add("collect_same_epoch_interlock_observations")
    if len(cohort_rows) > len(resolved):
        add("resolve_interlock_outcomes")
    if len(outcome_classes) < 2:
        add("collect_verified_outcome_variation")
    if len(valid) < int(min_samples):
        add("collect_valid_cohort_samples")
    if families and any(not family["data_ready"] for family in families.values()):
        add("collect_task_family_replicates")
    if data_ready:
        add("measure_recall_latency_holdout")

    return {
        "schema_version": READINESS_SCHEMA,
        "mode": "measurement_only",
        "current": {
            "cohort_observations": len(cohort_rows),
            "resolved_outcomes": len(resolved),
            "valid_outcomes": len(valid),
            "outcome_classes": outcome_classes,
            "same_epoch_frames": frame_count,
            "same_epoch_frame_status": (
                resonance.get("status") or "not_measured"
                if resonance_current
                else "stale_epoch"
                if resonance_epoch_id
                else "not_measured"
            ),
            "body_epoch_id": current_epoch_id or None,
            "frame_epoch_id": resonance_epoch_id or None,
        },
        "required": {
            "valid_samples_per_task_family": int(min_samples),
            "valid_samples_overall": OVERALL_VALID_MIN,
            "same_epoch_frames": TEMPORAL_FRAME_MIN,
            "outcome_classes": 2,
        },
        "remaining": {
            "valid_samples_in_cohort": max(0, int(min_samples) - len(valid)),
            "valid_samples_overall": max(0, OVERALL_VALID_MIN - len(valid)),
            "same_epoch_frames": max(0, TEMPORAL_FRAME_MIN - frame_count),
            "outcome_classes": max(0, 2 - len(outcome_classes)),
            "witness_repairs": max(0, len(resolved) - len(valid)),
        },
        "task_families": families,
        "next_actions": actions,
        "ready_for_shadow_analysis": bool(data_ready),
        "promotion_ready": False,
        "policy_effect": False,
        "advisory_only": True,
        "claim_boundary": (
            "Readiness is a deficit report over recorded measurements. It does not "
            "execute collection, resolve outcomes, grant authority, or establish "
            "consciousness or subjective sensing."
        ),
    }


def interlock_report(
    store: Any,
    repo: str,
    *,
    limit: int = 2048,
    top_paths: int = 16,
    min_samples: int = 32,
    include_lesion: bool = True,
) -> dict[str, Any]:
    """Measure E-L-O candidates in the newest constitutionally stable cohort.

    Exact body epochs remain in every row.  Adaptive successors may share a
    cohort only when repository identity, evidence, schema, and constitutional
    configuration are unchanged.
    """
    rows = list(store.interlock_observations(repo, limit=limit) or [])
    latest_epoch = next((str(r.get("body_epoch_id") or "") for r in rows if r.get("body_epoch_id")), "")
    live_epoch = current_body_epoch(store, repo)
    live_epoch_id = str(live_epoch.epoch_id) if live_epoch else ""

    def _cohort(row: dict[str, Any]) -> str:
        return str(
            (row.get("metadata") or {}).get("measurement_cohort_id")
            or f"epoch:{row.get('body_epoch_id') or ''}"
        )

    latest_cohort = _cohort(rows[0]) if rows else ""
    cohort_current = True
    if live_epoch:
        cohort_material = {
            "repo": repo,
            "repository_id": live_epoch.repository_id,
            "evidence_root_hash": live_epoch.evidence_root_hash,
            "schema_hash": live_epoch.schema_hash,
            "constitutional_config_hash": live_epoch.constitutional_config_hash,
        }
        expected_cohort = measurement_cohort_identity(**cohort_material)
        cohort_current = bool(latest_cohort and latest_cohort == expected_cohort)
        if not cohort_current:
            latest_cohort = ""
    cohort_rows = [r for r in rows if _cohort(r) == latest_cohort]
    if not cohort_current:
        cohort_rows = []
        latest_epoch = ""
    cohort_epochs = sorted({str(r.get("body_epoch_id") or "") for r in cohort_rows})
    resolved = [r for r in cohort_rows if r.get("outcome_id") and r.get("reward") is not None]
    valid = [r for r in resolved if r.get("constitutional_valid") and r.get("witness_valid")]
    e_freq = Counter(p for r in valid for p in r.get("evidence_paths", []))
    l_freq = Counter(p for r in valid for p in r.get("learned_paths", []))
    e_paths = [p for p, _ in e_freq.most_common(max(1, int(top_paths)))]
    l_paths = [p for p, _ in l_freq.most_common(max(1, int(top_paths)))]
    candidates: list[dict[str, Any]] = []

    for evidence_path, learned_path in product(e_paths, l_paths):
        e = [int(evidence_path in r.get("evidence_paths", [])) for r in valid]
        learned_presence = [
            int(learned_path in r.get("learned_paths", [])) for r in valid
        ]
        y = [int(float(r.get("reward") or 0.0) > 0.0) for r in valid]
        support = sum(1 for a, b in zip(e, learned_presence) if a and b)
        if support == 0:
            continue
        all_e = [int(evidence_path in r.get("evidence_paths", [])) for r in resolved]
        all_l = [int(learned_path in r.get("learned_paths", [])) for r in resolved]
        opportunities = sum(1 for a, b in zip(all_e, all_l) if a or b)
        joint_all = sum(1 for a, b in zip(all_e, all_l) if a and b)
        valid_joint = sum(
            1
            for r, a, b in zip(resolved, all_e, all_l)
            if a and b and r.get("constitutional_valid") and r.get("witness_valid")
        )
        info = synergy_proxy_bits(e, learned_presence, y)
        h_y = float(info["outcome_entropy_bits"])
        synergy_n = float(info["synergy_proxy_bits"]) / max(h_y, 1e-12) if h_y else 0.0
        redundancy_n = float(info["redundancy_proxy_bits"]) / max(h_y, 1e-12) if h_y else 0.0
        hub = max(sum(e), sum(learned_presence)) / max(1, len(valid))
        hub_penalty = max(0.0, (hub - 0.5) * 2.0)
        penalty = min(1.0, 0.5 * min(1.0, redundancy_n) + 0.5 * hub_penalty)
        score = triad_alignment_score(
            typed_closure=joint_all / max(1, opportunities),
            normalized_synergy=min(1.0, synergy_n),
            outcome_validity=valid_joint / max(1, joint_all),
            redundancy_penalty=penalty,
            constitutional_gate=bool(latest_cohort and valid_joint > 0),
            sample_reliability=min(1.0, len(valid) / max(1, int(min_samples))),
        )
        candidates.append(
            {
                "evidence_path": evidence_path,
                "learned_path": learned_path,
                "sample_n": len(valid),
                "joint_support": support,
                "hub_prevalence": round(hub, 6),
                **info,
                **score,
            }
        )

    candidates.sort(key=lambda x: (-float(x["alignment"]), -int(x["joint_support"]), x["evidence_path"], x["learned_path"]))
    alignments = [float(c["alignment"]) for c in candidates]
    mean_alignment = sum(alignments) / max(1, len(alignments))
    data_ready = len(valid) >= int(min_samples) and len(set(int(float(r.get("reward") or 0) > 0) for r in valid)) >= 2
    readiness = _interlock_readiness(
        store,
        repo,
        cohort_rows=cohort_rows,
        resolved=resolved,
        valid=valid,
        min_samples=int(min_samples),
        data_ready=data_ready,
    )
    if candidates and include_lesion:
        lesion_target = candidates[0]
        lesion_effect = float(lesion_target["alignment"])
        ci_low, ci_high = _bootstrap_candidate_ci(
            valid,
            evidence_path=str(lesion_target["evidence_path"]),
            learned_path=str(lesion_target["learned_path"]),
            min_samples=int(min_samples),
        )
    elif candidates:
        lesion_target = candidates[0]
        lesion_effect = float(lesion_target["alignment"])
        ci_low, ci_high = (0.0, 0.0)
    else:
        lesion_target = {}
        lesion_effect = 0.0
        ci_low, ci_high = (0.0, 0.0)
    lesion = {
        "lesion": "remove_outcome_synergy_leg",
        "target": {
            "evidence_path": lesion_target.get("evidence_path"),
            "learned_path": lesion_target.get("learned_path"),
        },
        "observed_effect": round(lesion_effect, 8),
        "ci95": [round(ci_low, 8), round(ci_high, 8)],
        "supported": bool(include_lesion and data_ready and ci_low > 0.0),
        "computed": bool(include_lesion),
        "method": (
            "deterministic paired observation bootstrap on top shadow candidate"
            if include_lesion
            else "deferred on compact/read-path report"
        ),
        "selection_note": "Exploratory top-candidate interval; promotion still requires sealed holdout replication.",
    }
    bridge_shadow = store.get_setting(f"bridge_shadow_latest:{repo}", {}) or {}
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "mode": "shadow",
        "advisory_only": True,
        "body_epoch_id": latest_epoch or None,
        "current_body_epoch_id": live_epoch_id or None,
        "cohort_current": cohort_current,
        "measurement_cohort_id": latest_cohort or None,
        "body_epochs_in_cohort": cohort_epochs,
        "counts": {
            "observations": len(rows),
            "cohort_observations": len(cohort_rows),
            "epoch_observations": sum(
                1 for r in cohort_rows if str(r.get("body_epoch_id") or "") == latest_epoch
            ),
            "resolved": len(resolved),
            "valid": len(valid),
            "unresolved": len(cohort_rows) - len(resolved),
            "excluded_cross_cohort": len(rows) - len(cohort_rows),
            "compatible_cross_epoch": sum(
                1 for r in cohort_rows if str(r.get("body_epoch_id") or "") != latest_epoch
            ),
            "excluded_cross_epoch": len(rows)
            - sum(1 for r in rows if str(r.get("body_epoch_id") or "") == latest_epoch),
            "candidates": len(candidates),
        },
        "data_ready": data_ready,
        "readiness": readiness,
        "mean_alignment": round(mean_alignment, 8),
        "top_interlocks": candidates[:12],
        "lesion": lesion,
        "geometric_bridges": {
            "available": bool(bridge_shadow),
            "glyph": bridge_shadow.get("glyph") or BRIDGE_GLYPH,
            "top_decile_degree_share": bridge_shadow.get("top_decile_degree_share"),
            "candidate_count": len(bridge_shadow.get("candidates") or []),
            "top_candidates": (bridge_shadow.get("candidates") or [])[:5],
            "policy_effect": False,
        },
        "promotion_gates": {
            "min_samples": int(min_samples),
            "sample_gate": len(valid) >= int(min_samples),
            "outcome_variation_gate": len(set(int(float(r.get("reward") or 0) > 0) for r in valid)) >= 2 if valid else False,
            "measurement_cohort_gate": bool(latest_cohort),
            "exact_epochs_audited": bool(cohort_epochs),
            "witness_gate": bool(resolved) and len(valid) == len(resolved),
            "lesion_gate": lesion["supported"],
            "recall_gate": "not_measured",
            "latency_gate": "not_measured",
            "eligible": False,
            "policy": "never auto-promote; release receipt must satisfy every gate",
        },
        "claim_boundary": CLAIM,
    }


def refresh_interlock_shadow(store: Any, repo: str) -> dict[str, Any]:
    """Refresh the bounded route stamp only after an outcome closes a triad."""
    report = interlock_report(
        store, repo, limit=2048, top_paths=16, include_lesion=False
    )
    path_scores: dict[str, dict[str, Any]] = {}
    eligible_candidates = (
        report.get("top_interlocks", []) if report.get("data_ready") else []
    )
    for candidate in eligible_candidates:
        if (
            float(candidate.get("alignment") or 0.0) <= 0.0
            or candidate.get("constitutional_gate") is not True
        ):
            continue
        for role, key in (("E", "evidence_path"), ("L", "learned_path")):
            path = str(candidate.get(key) or "")
            if not path:
                continue
            prior = path_scores.get(path) or {}
            if float(candidate.get("alignment") or 0.0) >= float(prior.get("alignment") or 0.0):
                path_scores[path] = {
                    "role": role,
                    "alignment": candidate.get("alignment"),
                    "sample_n": candidate.get("sample_n"),
                    "joint_support": candidate.get("joint_support"),
                    "constitutional_gate": candidate.get("constitutional_gate"),
                    "body_epoch_id": report.get("body_epoch_id"),
                    "measurement_cohort_id": report.get("measurement_cohort_id"),
                    "data_ready": report.get("data_ready"),
                    "shadow_only": True,
                }
    payload = {
        "schema_version": SCHEMA,
        "body_epoch_id": report.get("body_epoch_id"),
        "measurement_cohort_id": report.get("measurement_cohort_id"),
        "data_ready": report.get("data_ready"),
        "path_scores": path_scores,
        "policy_effect": False,
    }
    store.set_setting(f"interlock_shadow_latest:{repo}", payload)
    return payload


def stamp_hits_with_interlock_shadow(store: Any, repo: str, hits: list[Any]) -> int:
    """Attach cached interlock/bridge telemetry without changing score or order."""
    interlock = store.get_setting(f"interlock_shadow_latest:{repo}", {}) or {}
    interlock_scores = (
        interlock.get("path_scores") or {}
        if interlock.get("data_ready") is True
        else {}
    )
    bridge = store.get_setting(f"bridge_shadow_latest:{repo}", {}) or {}
    bridge_scores = bridge.get("path_scores") or {}
    stamped = 0
    for hit in hits:
        path = str(hit.get("path") if isinstance(hit, dict) else getattr(hit, "path", ""))
        interlock_shadow = interlock_scores.get(path)
        bridge_shadow = bridge_scores.get(path)
        if not interlock_shadow and not bridge_shadow:
            continue
        if isinstance(hit, dict):
            metadata = dict(hit.get("metadata") or {})
            if interlock_shadow:
                metadata["information_interlock_shadow"] = dict(interlock_shadow)
            if bridge_shadow:
                metadata["geometric_bridge_shadow"] = dict(bridge_shadow)
            hit["metadata"] = metadata
        else:
            try:
                metadata = dict(getattr(hit, "metadata", None) or {})
                if interlock_shadow:
                    metadata["information_interlock_shadow"] = dict(interlock_shadow)
                if bridge_shadow:
                    metadata["geometric_bridge_shadow"] = dict(bridge_shadow)
                hit.metadata = metadata
            except Exception:
                continue
        stamped += 1
    return stamped


__all__ = [
    "BRIDGE_GLYPH",
    "GLYPH",
    "READINESS_SCHEMA",
    "SCHEMA",
    "graph_sampling_audit",
    "bridge_deconcentration_report",
    "interlock_report",
    "measurement_cohort_identity",
    "mutual_information_bits",
    "observe_activation_interlock",
    "refresh_interlock_shadow",
    "refresh_bridge_shadow",
    "stamp_hits_with_interlock_shadow",
    "synergy_proxy_bits",
    "triad_alignment_score",
]
