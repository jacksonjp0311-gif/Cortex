"""v7.3 Resonant Frame advisory policy — never authority.

Policy is ephemeral and advisory. Constitutional gates remain controlling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class FramePolicy:
    mode: str
    reasons: tuple[str, ...] = ()
    retrieval_width_delta: int = 0
    prefer_evidence: bool = False
    request_counterevidence: bool = False
    disable_learned_rerank_once: bool = False
    recommended_gcmt_regime: str = "abstain"
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["reasons"] = list(self.reasons)
        d["advisory_only"] = True
        return d


# GCMT regime mapping (recommendation only)
GCMT_MAP = {
    "QUIESCENT": "local",
    "TRANSITION": "re-anchor",
    "STALE_ECHO": "evidence",
    "OVERBOUND": "evidence",
    "FRAGMENTED": "evidence",
    "COHERENT_DIFFERENTIATED": "local",
    "INDETERMINATE": "abstain",
}


def policy_for_classification(classification: str, *, reasons: list[str] | None = None) -> FramePolicy:
    c = str(classification or "INDETERMINATE").upper()
    r = tuple(reasons or ())
    regime = GCMT_MAP.get(c, "abstain")

    if c == "QUIESCENT":
        return FramePolicy(
            mode="quiescent",
            reasons=r or ("preserve_mode", "avoid_unnecessary_graph_work"),
            retrieval_width_delta=0,
            recommended_gcmt_regime=regime,
        )
    if c == "TRANSITION":
        return FramePolicy(
            mode="transition",
            reasons=r or ("re_anchor", "prevent_immediate_promotion"),
            retrieval_width_delta=1,
            prefer_evidence=True,
            recommended_gcmt_regime=regime,
        )
    if c == "STALE_ECHO":
        return FramePolicy(
            mode="stale_echo",
            reasons=r or ("prefer_evidence_baseline", "disable_learned_rerank_once"),
            retrieval_width_delta=1,
            prefer_evidence=True,
            request_counterevidence=True,
            disable_learned_rerank_once=True,
            recommended_gcmt_regime=regime,
        )
    if c == "OVERBOUND":
        return FramePolicy(
            mode="overbound",
            reasons=r or ("diversify_retrieval", "request_disconfirming_evidence"),
            retrieval_width_delta=2,
            prefer_evidence=True,
            request_counterevidence=True,
            recommended_gcmt_regime=regime,
        )
    if c == "FRAGMENTED":
        return FramePolicy(
            mode="fragmented",
            reasons=r or ("widen_retrieval", "increase_structural_neighborhood"),
            retrieval_width_delta=2,
            prefer_evidence=True,
            recommended_gcmt_regime=regime,
        )
    if c == "COHERENT_DIFFERENTIATED":
        return FramePolicy(
            mode="coherent_differentiated",
            reasons=r or ("narrower_context_ok", "still_constitutional_gates"),
            retrieval_width_delta=-1,
            recommended_gcmt_regime=regime,
        )
    # INDETERMINATE / default — no policy effect
    return FramePolicy(
        mode="indeterminate",
        reasons=r or ("no_policy_effect", "report_missing_requirements"),
        retrieval_width_delta=0,
        recommended_gcmt_regime="abstain",
    )


def apply_field_policy_advisory(
    base_context: dict[str, Any] | None,
    policy: FramePolicy | dict[str, Any] | None,
    *,
    advisory_mode: bool = False,
) -> dict[str, Any]:
    """Optionally annotate context with field policy. Never grants authority."""
    ctx = dict(base_context or {})
    if not policy:
        return ctx
    p = policy.to_dict() if isinstance(policy, FramePolicy) else dict(policy)
    p["advisory_only"] = True
    ctx["resonant_frame_policy"] = p
    if not advisory_mode:
        ctx["field_policy_applied"] = False
        ctx["field_policy_note"] = "shadow — not applied to retrieval (set advisory mode to apply)"
        return ctx
    # advisory application: width hint only
    delta = int(p.get("retrieval_width_delta") or 0)
    if delta:
        ctx["retrieval_width_delta"] = delta
    if p.get("prefer_evidence"):
        ctx["prefer_evidence"] = True
    if p.get("request_counterevidence"):
        ctx["request_counterevidence"] = True
    if p.get("disable_learned_rerank_once"):
        ctx["disable_learned_rerank_once"] = True
    ctx["field_policy_applied"] = True
    ctx["field_policy_note"] = (
        "advisory context-selection only; constitutional gates remain controlling"
    )
    return ctx
