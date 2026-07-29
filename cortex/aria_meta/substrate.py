"""Typed, bounded routing for Cortex's native ARIA semantic substrate."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable


INTERNAL_ARIA_PREFIX = "cortex/aria_meta/vendor/"
INTERNAL_ARIA_REGION = "internal_aria_substrate"
REPOSITORY_REGION = "repository"
ARIA_CUE_THRESHOLD = 0.65
ARIA_MAX_LEARNED_CUES = 32
# Bootstrap indexes only anchors; the remaining substrate is certificate-deferred
# until an ARIA-active task materializes it. Work proxy:
#   W_bootstrap ≈ |repo ∪ anchors| · c_index + |aria \ anchors| · c_inventory
#   W_wake_once  ≈ |aria \ anchors| · c_index   (amortized over later runs as 0)
ARIA_SUBSTRATE_DEFERRED_STATUS = "substrate_deferred"
ARIA_INDEXING_DEFERRED = "deferred"
ARIA_INDEXING_EAGER = "eager"
ARIA_PURPOSES = (
    "language",
    "intent",
    "continuity",
    "consent",
    "governance",
    "coordination",
    "symbolic",
)

# Always fully indexed on bootstrap: identity, policy, and cue registry.
ARIA_SUBSTRATE_ANCHORS: tuple[str, ...] = (
    "cortex/aria_meta/vendor/ARIA-RUNTIME.json",
    "cortex/aria_meta/vendor/ARIA-CONNECT.json",
    "cortex/aria_meta/vendor/AGENTS.md",
    "cortex/aria_meta/vendor/README.md",
    "cortex/aria_meta/vendor/VERSION",
    "cortex/aria_meta/vendor/MANIFEST.sha256",
    "cortex/aria_meta/vendor/aria.policy.json",
    "cortex/aria_meta/vendor/aria.lock.json",
    "cortex/aria_meta/vendor/grammar/semantic-cues.json",
    "cortex/aria_meta/vendor/grammar/glyphs.json",
    "cortex/aria_meta/vendor/grammar/glyph-cards.json",
    "cortex/aria_meta/vendor/grammar/opcodes.json",
)

# Immutable core cues. Single-token common English is avoided to cut false wakes;
# "aria" is the only intentional single-token language wake.
CORE_CUES: tuple[dict[str, str], ...] = (
    {"phrase": "aria", "purpose": "language"},
    {"phrase": "meta-language", "purpose": "language"},
    {"phrase": "meta language", "purpose": "language"},
    {"phrase": "semantic plan", "purpose": "intent"},
    {"phrase": "semantic planning", "purpose": "intent"},
    {"phrase": "intent verification", "purpose": "intent"},
    {"phrase": "intent proof", "purpose": "intent"},
    {"phrase": "semantic replay", "purpose": "continuity"},
    {"phrase": "semantic handoff", "purpose": "continuity"},
    {"phrase": "session handoff", "purpose": "continuity"},
    {"phrase": "consent admission", "purpose": "consent"},
    {"phrase": "admission receipt", "purpose": "consent"},
    {"phrase": "capability authority", "purpose": "governance"},
    {"phrase": "governed evolution", "purpose": "governance"},
    {"phrase": "governance contract", "purpose": "governance"},
    {"phrase": "constitutional homeostasis", "purpose": "governance"},
    {"phrase": "authority monotonicity", "purpose": "governance"},
    {"phrase": "reversibility burden", "purpose": "governance"},
    {"phrase": "verified recovery", "purpose": "governance"},
    {"phrase": "provider bridge", "purpose": "coordination"},
    {"phrase": "cooperative mesh", "purpose": "coordination"},
    {"phrase": "agent mesh", "purpose": "coordination"},
    {"phrase": "verified glyph", "purpose": "symbolic"},
    {"phrase": "glyph card", "purpose": "symbolic"},
    {"phrase": "glyph memory", "purpose": "symbolic"},
    {"phrase": "context weave", "purpose": "symbolic"},
    {"phrase": "transcend check", "purpose": "governance"},
    {"phrase": "packet profile", "purpose": "language"},
    {"phrase": "control error", "purpose": "governance"},
    {"phrase": "retrieval gate", "purpose": "language"},
    {"phrase": "ritual idempotent", "purpose": "continuity"},
    {"phrase": "incremental surprise", "purpose": "language"},
    {"phrase": "teach surface", "purpose": "language"},
    {"phrase": "memory packet", "purpose": "continuity"},
    {"phrase": "interconnect intelligence", "purpose": "coordination"},
    {"phrase": "teach seed", "purpose": "language"},
    {"phrase": "co-process", "purpose": "continuity"},
    # Connect pass / metric graph / immune gate (multi-word; avoid common singles)
    {"phrase": "connect pass", "purpose": "coordination"},
    {"phrase": "metric graph", "purpose": "coordination"},
    {"phrase": "path coactivation", "purpose": "coordination"},
    {"phrase": "immune gate", "purpose": "governance"},
    {"phrase": "control error vector", "purpose": "governance"},
    {"phrase": "semantic memory packet", "purpose": "continuity"},
    {"phrase": "distill connect", "purpose": "continuity"},
    {"phrase": "organism pulse", "purpose": "continuity"},
    {"phrase": "semantic continuity", "purpose": "continuity"},
    # Glyphic medium + mesh (v6) — multi-word; reduce false wakes
    {"phrase": "interconnect mesh", "purpose": "coordination"},
    {"phrase": "glyphic medium", "purpose": "symbolic"},
    {"phrase": "progress glyph", "purpose": "symbolic"},
    {"phrase": "graph prune", "purpose": "coordination"},
    {"phrase": "weight decay", "purpose": "coordination"},
    {"phrase": "mesh bottleneck", "purpose": "coordination"},
    {"phrase": "seal the gate", "purpose": "governance"},
    {"phrase": "gates sealed", "purpose": "governance"},
    {"phrase": "hnsw vector", "purpose": "language"},
    {"phrase": "ranker freeze", "purpose": "governance"},
    {"phrase": "causal episode", "purpose": "continuity"},
    {"phrase": "aria glyph card", "purpose": "symbolic"},
    # v6.2 fold/heal + efficiency (multi-word)
    {"phrase": "lattice fold", "purpose": "coordination"},
    {"phrase": "heal the mesh", "purpose": "continuity"},
    {"phrase": "token efficiency", "purpose": "language"},
    {"phrase": "lean packet", "purpose": "language"},
    {"phrase": "multi agent mode", "purpose": "coordination"},
    {"phrase": "capability token", "purpose": "governance"},
    {"phrase": "distill intelligence", "purpose": "continuity"},
    {"phrase": "steady state cadence", "purpose": "coordination"},
)


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9_-]+", value.casefold()))


def _setting_key(repo: str) -> str:
    return f"aria_cue_profile:{repo}"


def is_internal_aria_path(path: str) -> bool:
    return path.replace("\\", "/").startswith(INTERNAL_ARIA_PREFIX)


def is_aria_anchor_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized in ARIA_SUBSTRATE_ANCHORS


def should_defer_aria_indexing(path: str, indexing_mode: str = ARIA_INDEXING_DEFERRED) -> bool:
    """Return True when path belongs to the deferred ARIA indexing tier."""

    mode = (indexing_mode or ARIA_INDEXING_DEFERRED).casefold()
    if mode == ARIA_INDEXING_EAGER:
        return False
    return is_internal_aria_path(path) and not is_aria_anchor_path(path)


def substrate_work_proxy(
    *,
    repository_indexed: int,
    aria_anchors_indexed: int,
    aria_deferred: int,
    aria_materialized: int = 0,
) -> dict[str, Any]:
    """Expose the bootstrap/wake work split as measurable counters.

    Cost units are file-ops (inventory vs full index). Absolute times vary by
    machine; ratios are the portable engineering signal.
    """

    bootstrap_index_ops = repository_indexed + aria_anchors_indexed
    bootstrap_inventory_ops = aria_deferred
    wake_materialize_ops = max(0, aria_deferred - aria_materialized)
    aria_total = aria_anchors_indexed + aria_deferred
    deferred_fraction = (
        round(aria_deferred / aria_total, 8) if aria_total else 0.0
    )
    # Relative bootstrap work vs eager full ARIA index:
    # eager ≈ repo + aria_total; deferred ≈ repo + anchors + inventory(aria_deferred)
    # inventory is treated as ~0.05 of a full index op for the ratio signal.
    eager_units = float(repository_indexed + aria_total)
    deferred_units = float(bootstrap_index_ops) + 0.05 * float(bootstrap_inventory_ops)
    savings_ratio = (
        round(max(0.0, 1.0 - (deferred_units / eager_units)), 8)
        if eager_units
        else 0.0
    )
    return {
        "schema_version": "cortex-aria-work-proxy/1.0",
        "bootstrap_index_ops": bootstrap_index_ops,
        "bootstrap_inventory_ops": bootstrap_inventory_ops,
        "wake_materialize_ops_remaining": wake_materialize_ops,
        "aria_deferred_fraction": deferred_fraction,
        "estimated_bootstrap_savings_ratio": savings_ratio,
        "formula": (
            "W_bootstrap ≈ |repo∪anchors|·c_index + |aria\\anchors|·c_inventory; "
            "W_wake_once ≈ remaining_deferred·c_index"
        ),
    }


def aria_purposes_for_path(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/").casefold()
    purposes: set[str] = set()
    keyword_map = {
        "intent": ("intent", "proposal"),
        "continuity": ("replay", "handoff", "semanticcontinuity"),
        "consent": ("consent", "admission", "receipt"),
        "governance": (
            "authority",
            "evolution",
            "policy",
            "capability",
            "gate",
            "execution-evidence",
            "homeostasis",
            "recovery",
            "reversibility",
        ),
        "coordination": (
            "bridge",
            "mesh",
            "handshake",
            "connection",
            "transmission",
        ),
        "symbolic": ("glyph", "alchemy", "semantic-cues", "context-weave"),
    }
    for purpose, keywords in keyword_map.items():
        if any(keyword in normalized for keyword in keywords):
            purposes.add(purpose)
    if not purposes:
        purposes.add("language")
    return tuple(
        purpose for purpose in ARIA_PURPOSES if purpose in purposes
    )


def aria_routing_purposes(classification: dict[str, Any]) -> tuple[str, ...]:
    purposes = tuple(classification.get("purposes", []))
    specialized = tuple(purpose for purpose in purposes if purpose != "language")
    return specialized or purposes


def aria_path_supports(path: str, purposes: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.endswith(
        ("ARIA-CONNECT.json", "ARIA-RUNTIME.json", "AGENTS.md")
    ):
        return True
    requested = set(purposes)
    return bool(requested.intersection(aria_purposes_for_path(path)))


def native_semantic_registry() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "vendor" / "grammar" / "semantic-cues.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "path": "bundled://grammar/semantic-cues.json",
        "format": payload.get("format"),
        "version": payload.get("version"),
        "digest": payload.get("digest"),
        "cue_count": len(payload.get("cues", [])),
        "cue_ids": [cue.get("id") for cue in payload.get("cues", [])],
        "engagement_contract": payload.get("engagementContract", {}),
        "routing_boundary": (
            "ARIA display semantics inform typed runtime meaning; "
            "they do not independently wake Cortex or grant authority."
        ),
    }


def load_aria_cue_profile(store: Any, repo: str) -> dict[str, Any]:
    profile = store.get_setting(
        _setting_key(repo),
        {
            "schema_version": "cortex-aria-cue-profile/1.0",
            "repo": repo,
            "threshold": ARIA_CUE_THRESHOLD,
            "max_learned_cues": ARIA_MAX_LEARNED_CUES,
            "cues": [],
        },
    )
    cues = [
        cue
        for cue in profile.get("cues", [])
        if cue.get("purpose") in ARIA_PURPOSES
        and isinstance(cue.get("phrase"), str)
        and isinstance(cue.get("confidence"), (int, float))
    ][:ARIA_MAX_LEARNED_CUES]
    return {
        "schema_version": "cortex-aria-cue-profile/1.0",
        "repo": repo,
        "threshold": ARIA_CUE_THRESHOLD,
        "max_learned_cues": ARIA_MAX_LEARNED_CUES,
        "cues": cues,
        "authority": "verification_tunes_relevance_only",
    }


def _cue_is_admissible_phrase(phrase: str) -> bool:
    """Reject under-specified learned cues that would reintroduce false wakes."""

    tokens = phrase.split()
    if not tokens or len(tokens) > 6:
        return False
    # Single-token learned cues are high false-wake risk unless they are "aria".
    if len(tokens) == 1:
        return tokens[0] == "aria"
    return 2 <= len(tokens) <= 6


def classify_aria_task(
    task: str, learned_cues: Iterable[dict[str, Any]] = ()
) -> dict[str, Any]:
    """Decide which typed ARIA purposes a task should wake."""

    normalized = _normalize(task)
    padded = f" {normalized} "
    evidence: list[dict[str, Any]] = []
    for cue in CORE_CUES:
        if f" {cue['phrase']} " in padded:
            evidence.append(
                {
                    **cue,
                    "source": "core",
                    "confidence": 1.0,
                    "immutable": True,
                }
            )
    for cue in learned_cues:
        phrase = _normalize(str(cue.get("phrase", "")))
        confidence = max(0.0, min(1.0, float(cue.get("confidence", 0.0))))
        purpose = str(cue.get("purpose", ""))
        if (
            phrase
            and _cue_is_admissible_phrase(phrase)
            and purpose in ARIA_PURPOSES
            and confidence >= ARIA_CUE_THRESHOLD
            and f" {phrase} " in padded
        ):
            evidence.append(
                {
                    "phrase": phrase,
                    "purpose": purpose,
                    "source": "learned",
                    "confidence": round(confidence, 6),
                    "immutable": False,
                }
            )
    active = bool(evidence)
    purposes = [
        purpose
        for purpose in ARIA_PURPOSES
        if any(item["purpose"] == purpose for item in evidence)
    ]
    confidence = max(
        (float(item["confidence"]) for item in evidence), default=0.0
    )
    return {
        "schema_version": "cortex-aria-activation/2.0",
        "known": True,
        "namespace": INTERNAL_ARIA_REGION,
        "mode": "active" if active else "dormant",
        "purposes": purposes,
        "confidence": round(confidence, 6),
        "cue_evidence": evidence,
        "matched_signals": [item["phrase"] for item in evidence],
        "decision_rule": (
            "immutable_core_match"
            if any(item["source"] == "core" for item in evidence)
            else "verified_learned_cue_at_or_above_threshold"
            if active
            else "deterministic_dormant_fallback"
        ),
        "reason": (
            f"task requests typed ARIA purposes: {', '.join(purposes)}"
            if active
            else "native ARIA remains known but no admitted cue crossed the wake threshold"
        ),
        "automatic_execution": False,
        "grants_mutation_authority": False,
    }


def adapt_aria_cues(
    store: Any,
    repo: str,
    activation: dict[str, Any],
    *,
    status: str,
    reward: float,
    verification_type: str,
    verification_payload: dict[str, Any],
    governance_mode: str,
) -> dict[str, Any]:
    """Tune learned cue relevance after explicit verification; never authority."""

    profile = load_aria_cue_profile(store, repo)
    cues = [dict(cue) for cue in profile["cues"]]
    aria = activation.get("metrics", {}).get("aria_substrate", {})
    admitted = governance_mode in {"normal", "constrained"}
    verified = bool(verification_type.strip()) and status in {
        "verified",
        "irrelevant",
        "failed",
        "unsafe",
    }
    updates: list[dict[str, Any]] = []
    if admitted and verified:
        matched_learned = {
            item["phrase"]
            for item in aria.get("cue_evidence", [])
            if item.get("source") == "learned"
        }
        for cue in cues:
            if cue["phrase"] not in matched_learned:
                continue
            old = float(cue["confidence"])
            directional_reward = (
                max(0.0, reward)
                if status == "verified"
                else min(0.0, reward)
            )
            delta = 0.05 * directional_reward
            cue["confidence"] = round(max(0.35, min(0.90, old + delta)), 6)
            cue["reviewed_outcomes"] = int(cue.get("reviewed_outcomes", 0)) + 1
            cue["last_verification"] = verification_type
            updates.append(
                {
                    "action": "confidence_adjusted",
                    "phrase": cue["phrase"],
                    "purpose": cue["purpose"],
                    "old_confidence": old,
                    "new_confidence": cue["confidence"],
                }
            )

        proposals = (
            verification_payload.get("aria_cue_proposals", [])
            if status == "verified"
            and reward > 0
            and verification_payload.get("aria_cue_reviewed") is True
            else []
        )
        core_phrases = {cue["phrase"] for cue in CORE_CUES}
        existing = {cue["phrase"] for cue in cues}
        for proposal in proposals:
            phrase = _normalize(str(proposal.get("phrase", "")))
            purpose = str(proposal.get("purpose", ""))
            if (
                phrase in core_phrases
                or phrase in existing
                or purpose not in ARIA_PURPOSES
                or not _cue_is_admissible_phrase(phrase)
                or len(cues) >= ARIA_MAX_LEARNED_CUES
            ):
                continue
            cue = {
                "phrase": phrase,
                "purpose": purpose,
                "confidence": ARIA_CUE_THRESHOLD,
                "reviewed_outcomes": 1,
                "last_verification": verification_type,
                "source": "human_reviewed_verified_outcome",
            }
            cues.append(cue)
            existing.add(phrase)
            updates.append({"action": "cue_admitted", **cue})

    updated_profile = {**profile, "cues": cues[:ARIA_MAX_LEARNED_CUES]}
    if updates:
        store.set_setting(_setting_key(repo), updated_profile)
        store.append_neural_event(
            repo,
            event_type="aria_cue_adapted",
            entity_id=activation["activation_id"],
            payload={
                "verification_type": verification_type,
                "status": status,
                "updates": updates,
                "authority_changed": False,
            },
        )
    return {
        "admitted": admitted and verified,
        "updates": updates,
        "profile": updated_profile,
        "authority_changed": False,
    }


def aria_runtime_status(
    store: Any, repo: str, task: str = ""
) -> dict[str, Any]:
    profile = load_aria_cue_profile(store, repo)
    return {
        "schema_version": "cortex-aria-runtime/1.0",
        "native": True,
        "core_cues": len(CORE_CUES),
        "native_semantic_registry": native_semantic_registry(),
        "purposes": list(ARIA_PURPOSES),
        "learned_profile": profile,
        "classification": (
            classify_aria_task(task, profile["cues"]) if task else None
        ),
        "fallback": "deterministic_dormant",
        "automatic_execution": False,
        "grants_mutation_authority": False,
    }


__all__ = [
    "ARIA_CUE_THRESHOLD",
    "ARIA_INDEXING_DEFERRED",
    "ARIA_INDEXING_EAGER",
    "ARIA_MAX_LEARNED_CUES",
    "ARIA_PURPOSES",
    "ARIA_SUBSTRATE_ANCHORS",
    "ARIA_SUBSTRATE_DEFERRED_STATUS",
    "CORE_CUES",
    "INTERNAL_ARIA_PREFIX",
    "INTERNAL_ARIA_REGION",
    "REPOSITORY_REGION",
    "adapt_aria_cues",
    "aria_path_supports",
    "aria_purposes_for_path",
    "aria_routing_purposes",
    "aria_runtime_status",
    "classify_aria_task",
    "is_aria_anchor_path",
    "is_internal_aria_path",
    "load_aria_cue_profile",
    "native_semantic_registry",
    "should_defer_aria_indexing",
    "substrate_work_proxy",
]
