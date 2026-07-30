"""v6.24 Memory Simplex — advanced adaptive controller vs trusted evidence baseline.

Runtime-assurance pattern for memory (not host control, not consciousness):

  Advanced: ranker + spectral + concept routes + multi-res budget + invent/fusion
  Trusted:  EVIDENCE_BASELINE — lexical/structural hybrid only, no learned influence
  Decision: Governor modes + measure lift + optional force_baseline transfer

Authority inequality (topology law):
  Authority(G_learned) < Authority(G_evidence)

Claim boundary: cognitive runtime assurance for retrieval/adaptation only.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-memory-simplex/1.0"
GLYPH = "simplex"

# Controllers
CONTROLLER_ADVANCED = "advanced"
CONTROLLER_EVIDENCE_BASELINE = "evidence_baseline"

EVIDENCE_BASELINE_LAW = {
    "id": CONTROLLER_EVIDENCE_BASELINE,
    "lexical": True,
    "structural_neighborhood": True,
    "learned_rerank": False,
    "spectral_enrich": False,
    "concept_routes": False,  # hand/IR routes excluded from trusted path
    "invented_edge_boost": False,
    "fusion_influence": False,
    "adaptive_budget_partition": False,  # use flat budget scheme
    "budget_scheme": "flat",
    "provenance_required": True,
    "description": (
        "Trusted Simplex controller: hybrid lexical retrieval without ranker, "
        "spectral features, concept routes, or adaptive multi-res budgets."
    ),
}

ADVANCED_LAW = {
    "id": CONTROLLER_ADVANCED,
    "lexical": True,
    "structural_neighborhood": True,
    "learned_rerank": True,
    "spectral_enrich": True,
    "concept_routes": True,
    "invented_edge_boost": True,
    "fusion_influence": True,
    "adaptive_budget_partition": True,
    "budget_scheme": "fib",
    "provenance_required": True,
    "description": (
        "Advanced adaptive controller: ranker-primary + spectral + concept routes "
        "+ multi-res budgets under Governor gates."
    ),
}

CLAIM = (
    "Memory Simplex is runtime assurance for adaptive retrieval — advanced path "
    "vs trusted evidence baseline. Not consciousness, not host mutation authority."
)


def controller_law(name: str) -> dict[str, Any]:
    n = (name or CONTROLLER_ADVANCED).casefold().strip()
    if n in {
        CONTROLLER_EVIDENCE_BASELINE,
        "evidence",
        "trusted",
        "baseline_controller",
        "simplex_safe",
    }:
        return dict(EVIDENCE_BASELINE_LAW)
    return dict(ADVANCED_LAW)


def is_evidence_baseline(name: str | None) -> bool:
    if not name:
        return False
    n = name.casefold().strip()
    return n in {
        CONTROLLER_EVIDENCE_BASELINE,
        "evidence",
        "trusted",
        "baseline_controller",
        "simplex_safe",
    }


def resolve_controller(
    *,
    requested: str | None = None,
    governance_mode: str | None = None,
    force_baseline: bool = False,
) -> dict[str, Any]:
    """Pick advanced vs evidence_baseline under Governor / explicit force.

    Transfer rule (v6.24):
      force_baseline OR governance_mode == read_only → evidence_baseline
      constrained → still advanced by default (narrow scope, not full drop)
      normal → advanced
    """
    mode = (governance_mode or "normal").casefold().strip()
    if force_baseline or mode == "read_only" or is_evidence_baseline(requested):
        law = controller_law(CONTROLLER_EVIDENCE_BASELINE)
        reason = (
            "force_baseline"
            if force_baseline
            else (
                "governor_read_only"
                if mode == "read_only"
                else "explicit_evidence_baseline"
            )
        )
        transfer = True
    else:
        law = controller_law(requested or CONTROLLER_ADVANCED)
        reason = "advanced_allowed"
        transfer = False
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "controller": law["id"],
        "transfer_to_baseline": transfer,
        "reason": reason,
        "governance_mode": mode,
        "law": law,
        "claim_boundary": CLAIM,
    }


def query_kwargs_for_controller(controller: str | None) -> dict[str, Any]:
    """Keyword args for retrieval.query under a Simplex controller."""
    law = controller_law(controller or CONTROLLER_ADVANCED)
    if law["id"] == CONTROLLER_EVIDENCE_BASELINE:
        return {
            "ranker_primary": False,
            "enrich_spectral": False,
            "concept_routes": False,
            "memory_controller": CONTROLLER_EVIDENCE_BASELINE,
        }
    return {
        "ranker_primary": True,
        "enrich_spectral": True,
        "concept_routes": True,
        "memory_controller": CONTROLLER_ADVANCED,
    }


def budget_scheme_for_controller(controller: str | None, default: str = "fib") -> str:
    law = controller_law(controller or CONTROLLER_ADVANCED)
    if law["id"] == CONTROLLER_EVIDENCE_BASELINE:
        return "flat"
    return default or "fib"


def simplex_lift_report(
    advanced: dict[str, Any] | None,
    trusted: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare advanced (eval mode 'baseline') vs evidence_baseline metrics."""
    adv = advanced or {}
    tru = trusted or {}
    ar = float(adv.get("recall_at_k") or 0.0)
    am = float(adv.get("mrr") or 0.0)
    tr = float(tru.get("recall_at_k") or 0.0)
    tm = float(tru.get("mrr") or 0.0)
    beats = (ar, am) >= (tr, tm)
    return {
        "schema_version": SCHEMA,
        "advanced_mode": "baseline",  # historical eval name = advanced path
        "trusted_mode": CONTROLLER_EVIDENCE_BASELINE,
        "advanced_recall": ar,
        "advanced_mrr": am,
        "trusted_recall": tr,
        "trusted_mrr": tm,
        "lift_recall": round(ar - tr, 6),
        "lift_mrr": round(am - tm, 6),
        "advanced_beats_trusted": beats,
        "law": (
            "Advanced (learned) path should not systematically lose to "
            "EVIDENCE_BASELINE on sealed suites; ties allowed under ceiling."
        ),
        "claim_boundary": CLAIM,
    }


def memory_simplex_status(
    store: Any,
    repo: str,
    *,
    governance_mode: str | None = None,
) -> dict[str, Any]:
    """Telemetry packet for interconnect / activate."""
    resolved = resolve_controller(governance_mode=governance_mode)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "controllers": {
            CONTROLLER_ADVANCED: ADVANCED_LAW,
            CONTROLLER_EVIDENCE_BASELINE: EVIDENCE_BASELINE_LAW,
        },
        "active": resolved,
        "topology": {
            "G_evidence_authority": "higher",
            "G_learned_authority": "lower",
            "inequality": "Authority(G_learned) < Authority(G_evidence)",
        },
        "claim_boundary": CLAIM,
    }
