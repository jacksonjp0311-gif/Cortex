"""v7.3 Evidence–memory comparator for Resonant Frames.

Unknown is not agreement. Simulated/inferred never inflate verified evidence.
Contradiction requires explicit measured conflict relations — not lexical diff alone.
"""

from __future__ import annotations

import math
from typing import Any

from .field_channels import (
    EVIDENCE_FAMILIES,
    MEMORY_FAMILIES,
    FieldSample,
    is_verified_evidence_truth,
)

EPS = 1e-12


def _jsd_norm(p: dict[str, float], q: dict[str, float]) -> float:
    keys = sorted(set(p) | set(q))
    if not keys:
        return 0.0
    pp = {k: float(p.get(k, 0.0)) for k in keys}
    qq = {k: float(q.get(k, 0.0)) for k in keys}
    sp = sum(pp.values()) or 1.0
    sq = sum(qq.values()) or 1.0
    pp = {k: v / sp for k, v in pp.items()}
    qq = {k: v / sq for k, v in qq.items()}
    m = {k: 0.5 * (pp[k] + qq[k]) for k in keys}

    def kl(a: dict[str, float], b: dict[str, float]) -> float:
        s = 0.0
        for k, ak in a.items():
            if ak <= 0:
                continue
            s += ak * math.log((ak + EPS) / (b.get(k, 0.0) + EPS))
        return s

    jsd = 0.5 * kl(pp, m) + 0.5 * kl(qq, m)
    return min(1.0, max(0.0, jsd / math.log(2.0)))


def _fingerprint_mass(
    samples: list[FieldSample],
    *,
    families: frozenset[str],
    verified_only: bool,
) -> dict[str, float]:
    bag: dict[str, float] = {}
    for s in samples:
        if s.channel_family not in families:
            continue
        if verified_only and not is_verified_evidence_truth(s.truth_source):
            continue
        fps = list(s.paths) if s.paths else list(s.source_ids)
        if not fps:
            fps = [f"ch:{s.channel_family}"]
        w = s.reliability * s.activity
        for fp in fps:
            key = str(fp)
            bag[key] = bag.get(key, 0.0) + w
    total = sum(bag.values())
    if total <= EPS:
        return {}
    return {k: v / total for k, v in sorted(bag.items())}


def _contradiction_mass(
    samples: list[FieldSample], p_e: dict[str, float], p_m: dict[str, float]
) -> float:
    """Explicit contradictions only: metadata markers, not lexical difference."""
    matched = set(p_e) & set(p_m)
    if not matched:
        return 0.0
    contradicted: set[str] = set()
    for s in samples:
        meta = s.metadata or {}
        # explicit flags only
        flags = meta.get("contradictions") or meta.get("conflicts") or []
        if isinstance(flags, (list, tuple)):
            for f in flags:
                contradicted.add(str(f))
        if meta.get("stale_evidence") or meta.get("failed_test") or meta.get("hash_changed"):
            for p in s.paths:
                contradicted.add(str(p))
        if meta.get("explicit_contradiction"):
            for p in s.paths:
                contradicted.add(str(p))
    matched_mass = sum(min(p_e[k], p_m[k]) for k in matched)
    contra_mass = sum(min(p_e.get(k, 0.0), p_m.get(k, 0.0)) for k in contradicted if k in matched)
    return min(1.0, max(0.0, contra_mass / (matched_mass + EPS)))


def compare_evidence_memory(samples: list[FieldSample]) -> dict[str, Any]:
    """A_F, C_F, Q_F with nulls when either side absent."""
    p_e = _fingerprint_mass(samples, families=EVIDENCE_FAMILIES, verified_only=True)
    p_m = _fingerprint_mass(samples, families=MEMORY_FAMILIES, verified_only=False)

    if not p_e or not p_m:
        return {
            "comparator_available": False,
            "agreement": None,
            "contradiction_mass": None,
            "quality": None,
            "p_e_keys": len(p_e),
            "p_m_keys": len(p_m),
            "note": "unknown_is_not_agreement",
        }

    agreement = 1.0 - _jsd_norm(p_e, p_m)
    c_mass = _contradiction_mass(samples, p_e, p_m)
    quality = agreement * (1.0 - c_mass)
    return {
        "comparator_available": True,
        "agreement": round(agreement, 6),
        "contradiction_mass": round(c_mass, 6),
        "quality": round(quality, 6),
        "p_e_keys": len(p_e),
        "p_m_keys": len(p_m),
        "note": "unknown_is_not_agreement",
    }
