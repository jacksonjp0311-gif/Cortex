"""v7.3 Resonant Frames — bounded temporal field layer.

Two geometries + one temporal field layer:
  spectral geometry measures coupling quality;
  constitutional geometry governs participation rights;
  Resonant Frames measure bounded temporal coordination.
No temporal metric can move a constitutional bit.

Complexity O(K² W L) with K≤12, W≤32, L≤3.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .field_channels import (
    CHANNEL_FAMILIES,
    EVIDENCE_FAMILIES,
    MEMORY_FAMILIES,
    FieldSample,
    channel_truth_panel,
    clip01,
    is_verified_evidence_truth,
)
from .field_comparator import compare_evidence_memory
from .field_policy import policy_for_classification

EPS = 1e-12
SCHEMA = "cortex-resonant-frame/1.0"
GLYPH = "◈⟳"

W_MIN = 8
W_TARGET = 16
W_MAX = 32
L_MAX = 3
ACTIVITY_BINS = 8
MAX_EVENT_KEYS = 64
MIN_BASELINE_CHANNELS = 3
DEFAULT_Q95_DELTA_N = 0.12
FRAME_INDEX_CAP = 128
OBSERVATION_CURSOR_CAP = 256

CLAIM_BOUNDARY = (
    "Resonant Frames are bounded temporal telemetry for repository intelligence. "
    "They measure coordination, differentiation, evidence participation, comparator "
    "agreement, and transition across Cortex channels. They do not establish "
    "consciousness, biological equivalence, electromagnetic fields, quantum behavior, "
    "correctness, authority, witness, or host mutation permission."
)

CANONICAL_STATEMENT = (
    "Cortex has two geometries and one temporal field layer: "
    "spectral geometry measures coupling quality; "
    "constitutional geometry governs participation rights; "
    "Resonant Frames measure bounded temporal coordination. "
    "No temporal metric can move a constitutional bit."
)


class FrameClassification(str, Enum):
    QUIESCENT = "QUIESCENT"
    TRANSITION = "TRANSITION"
    FRAGMENTED = "FRAGMENTED"
    OVERBOUND = "OVERBOUND"
    STALE_ECHO = "STALE_ECHO"
    COHERENT_DIFFERENTIATED = "COHERENT_DIFFERENTIATED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class FrameThresholds:
    activity_low: float = 0.08
    nonrandomness_good: float = 0.35
    transition_high: float = 0.45
    integration_low: float = 0.25
    integration_good: float = 0.55
    integration_high: float = 0.78
    differentiation_low: float = 0.28
    differentiation_good: float = 0.50
    common_mode_high: float = 0.72
    participation_low: float = 0.35
    comparator_good: float = 0.60
    evidence_min: float = 0.20
    memory_dominant: float = 0.55
    edge_active: float = 0.45
    giant_min: float = 0.50
    w_min: int = W_MIN
    w_target: int = W_TARGET
    w_max: int = W_MAX
    l_max: int = L_MAX
    min_pair_overlap: int = 5
    q95_delta_n_default: float = DEFAULT_Q95_DELTA_N
    transition_weights: tuple[float, float, float, float] = (0.40, 0.30, 0.20, 0.10)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()


DEFAULT_THRESHOLDS = FrameThresholds()


@dataclass
class FrameMetrics:
    channel_count: int = 0
    eligible_channel_count: int = 0
    tick_count: int = 0
    mean_activity: float | None = None
    nonrandomness: float | None = None
    nonrandomness_rate: float | None = None
    integration: float | None = None
    same_frame_coordination: float | None = None
    lag_index: float | None = None
    differentiation: float | None = None
    common_mode: float | None = None
    participation_entropy: float | None = None
    giant_component_fraction: float | None = None
    comparator_available: bool = False
    comparator_agreement: float | None = None
    contradiction_mass: float | None = None
    comparator_quality: float | None = None
    evidence_participation: float | None = None
    memory_participation: float | None = None
    transition_pressure: float | None = None
    epoch_current: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def vector(self) -> dict[str, Any]:
        """Canonical R_F vector (nulls preserved — never invent middles)."""
        return {
            "N_F": self.nonrandomness,
            "Ndot_F": self.nonrandomness_rate,
            "I_F": self.integration,
            "S_F": self.same_frame_coordination,
            "L_F": self.lag_index,
            "D_F": self.differentiation,
            "M_F": self.common_mode,
            "H_P": self.participation_entropy,
            "G_F": self.giant_component_fraction,
            "Q_F": self.comparator_quality,
            "eta_E": self.evidence_participation,
            "eta_M": self.memory_participation,
            "T_F": self.transition_pressure,
        }


@dataclass
class ResonantFrame:
    frame_id: str
    repo: str
    body_epoch_id: str
    start_tick: int
    end_tick: int
    samples: list[FieldSample]
    sample_digest: str
    baseline_digest: str
    threshold_config_digest: str
    channel_truth_panel: dict[str, Any]
    metrics: FrameMetrics
    classification: str
    policy: dict[str, Any]
    measurement_basis: str = "direct_snapshot"
    policy_eligible: bool = True
    baseline_eligible: bool = True
    reasons: list[str] = field(default_factory=list)
    active_edges: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = SCHEMA
    cortex_version: str = ""
    issued_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "frame_id": self.frame_id,
            "repo": self.repo,
            "body_epoch_id": self.body_epoch_id,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "samples": [s.to_dict() for s in self.samples],
            "sample_digest": self.sample_digest,
            "baseline_digest": self.baseline_digest,
            "threshold_config_digest": self.threshold_config_digest,
            "channel_truth_panel": self.channel_truth_panel,
            "metrics": self.metrics.to_dict(),
            "frame_vector": self.metrics.vector(),
            "classification": self.classification,
            "reasons": list(self.reasons),
            "policy": dict(self.policy),
            "measurement_basis": self.measurement_basis,
            "policy_eligible": self.policy_eligible,
            "baseline_eligible": self.baseline_eligible,
            "active_edges": list(self.active_edges),
            "cortex_version": self.cortex_version,
            "issued_at": self.issued_at,
            "claim_boundary": CLAIM_BOUNDARY,
            "advisory_only": True,
        }

    def compact(self) -> dict[str, Any]:
        m = self.metrics
        return {
            "frame_id": self.frame_id,
            "classification": self.classification,
            "integration": m.integration,
            "differentiation": m.differentiation,
            "common_mode": m.common_mode,
            "comparator_quality": m.comparator_quality,
            "evidence_participation": m.evidence_participation,
            "transition_pressure": m.transition_pressure,
            "recommended_regime": (self.policy or {}).get("recommended_gcmt_regime"),
            "measurement_basis": self.measurement_basis,
            "policy_eligible": self.policy_eligible,
            "advisory_only": True,
        }


def measurement_contract(samples: list[FieldSample]) -> dict[str, Any]:
    """Aggregate sample measurement provenance without elevating truth."""
    bases = sorted(
        {
            str(s.metadata.get("measurement_basis") or "direct_snapshot")
            for s in samples
        }
    )
    return {
        "measurement_basis": bases[0] if len(bases) == 1 else "mixed",
        "measurement_bases": bases,
        "policy_eligible": all(
            bool(s.metadata.get("policy_eligible", True)) for s in samples
        ),
        "baseline_eligible": all(
            bool(s.metadata.get("baseline_eligible", True)) for s in samples
        ),
    }


# ── math primitives ──────────────────────────────────────────────


def _activity_bin(x: float) -> int:
    x = clip01(x)
    b = int(x * ACTIVITY_BINS)
    return min(ACTIVITY_BINS - 1, max(0, b))


def _kl(p: dict[str, float], q: dict[str, float]) -> float:
    s = 0.0
    for k, pk in p.items():
        if pk <= 0:
            continue
        qk = q.get(k, 0.0)
        s += pk * math.log((pk + EPS) / (qk + EPS))
    return s


def jsd_normalized(p: dict[str, float], q: dict[str, float]) -> float:
    """JSD / ln(2) ∈ [0,1] with natural log."""
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
    jsd = 0.5 * _kl(pp, m) + 0.5 * _kl(qq, m)
    return clip01(jsd / math.log(2.0))


def pearson(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a = a[:n]
    b = b[:n]
    ma = sum(a) / n
    mb = sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va < EPS or vb < EPS:
        return None
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def _is_constant(series: list[float]) -> bool:
    if len(series) < 2:
        return True
    m = sum(series) / len(series)
    return all(abs(x - m) < 1e-9 for x in series)


def build_series(
    samples: list[FieldSample],
) -> tuple[list[int], dict[str, list[float]], dict[str, float], dict[str, str]]:
    """Return sorted ticks, x[channel][tick_index], reliability, truth."""
    ticks = sorted({s.tick for s in samples})
    tick_index = {t: i for i, t in enumerate(ticks)}
    channels = sorted({s.channel_family for s in samples})
    series: dict[str, list[float]] = {
        c: [0.0] * len(ticks) for c in channels
    }
    rel: dict[str, list[float]] = {c: [] for c in channels}
    truth: dict[str, str] = {}
    for s in samples:
        i = tick_index[s.tick]
        series[s.channel_family][i] = s.activity
        rel[s.channel_family].append(s.reliability)
        truth[s.channel_family] = s.truth_source
    reliability = {
        c: (sum(rel[c]) / len(rel[c]) if rel[c] else 0.0) for c in channels
    }
    return ticks, series, reliability, truth


def frame_distributions(
    samples: list[FieldSample],
) -> dict[str, dict[str, float]]:
    """Per-channel categorical P over event_key × activity_bin."""
    counts: dict[str, dict[str, float]] = {}
    for s in samples:
        ch = s.channel_family
        ek = s.event_key or "default"
        # cap event keys: rare → OTHER (handled post)
        key = f"{ek}|{_activity_bin(s.activity)}"
        counts.setdefault(ch, {})
        counts[ch][key] = counts[ch].get(key, 0.0) + 1.0
    out: dict[str, dict[str, float]] = {}
    for ch, bag in counts.items():
        # keep top 64 event categories (by event stem), rest OTHER
        by_event: dict[str, float] = {}
        for k, v in bag.items():
            ev = k.rsplit("|", 1)[0]
            by_event[ev] = by_event.get(ev, 0.0) + v
        keep = set(
            sorted(by_event, key=lambda e: (-by_event[e], e))[:MAX_EVENT_KEYS]
        )
        slim: dict[str, float] = {}
        for k, v in bag.items():
            ev = k.rsplit("|", 1)[0]
            nk = k if ev in keep else f"OTHER|{k.rsplit('|', 1)[-1]}"
            slim[nk] = slim.get(nk, 0.0) + v
        total = sum(slim.values()) or 1.0
        out[ch] = {k: v / total for k, v in sorted(slim.items())}
    return out


def operational_nonrandomness(
    frame_dist: dict[str, dict[str, float]],
    baseline_dist: dict[str, dict[str, float]],
    reliability: dict[str, float],
) -> float | None:
    """N_F — weighted JSD / ln2 vs baseline; null if insufficient baselines."""
    num = 0.0
    den = 0.0
    used = 0
    for ch in sorted(frame_dist):
        base = baseline_dist.get(ch)
        if not base:
            continue
        nu = jsd_normalized(frame_dist[ch], base)
        r = float(reliability.get(ch, 0.0))
        num += r * nu
        den += r
        used += 1
    if used < MIN_BASELINE_CHANNELS or den <= EPS:
        return None
    return clip01(num / den)


def lagged_pair_stats(
    series: dict[str, list[float]],
    reliability: dict[str, float],
    *,
    l_max: int = L_MAX,
    min_overlap: int = 5,
) -> list[dict[str, Any]]:
    """Pairwise ρ, ℓ*, sign with deterministic tie-break."""
    channels = [c for c in sorted(series) if not _is_constant(series[c])]
    pairs: list[dict[str, Any]] = []
    for i, ci in enumerate(channels):
        for cj in channels[i + 1 :]:
            xi = series[ci]
            xj = series[cj]
            best_abs = -1.0
            best_c = 0.0
            best_l = 0
            # evaluate lags; collect candidates for tie-break
            candidates: list[tuple[float, int, float]] = []  # (-abs_c for sort, lag_key, c)
            for lag in range(-l_max, l_max + 1):
                a: list[float] = []
                b: list[float] = []
                w = len(xi)
                for t in range(w):
                    t2 = t - lag
                    if 0 <= t2 < w:
                        a.append(xi[t])
                        b.append(xj[t2])
                if len(a) < min_overlap:
                    continue
                c = pearson(a, b)
                if c is None:
                    continue
                candidates.append((abs(c), lag, c))
            if not candidates:
                continue
            # max |c|; ties: smallest |ℓ|, then negative lag before positive
            candidates.sort(key=lambda t: (-t[0], abs(t[1]), 0 if t[1] < 0 else 1, t[1]))
            best_abs, best_l, best_c = candidates[0]
            pairs.append(
                {
                    "i": ci,
                    "j": cj,
                    "rho": float(best_abs),
                    "lag": int(best_l),
                    "corr": float(best_c),
                    "sign": 0 if abs(best_c) < EPS else (1 if best_c > 0 else -1),
                    "w": float(reliability.get(ci, 0.0) * reliability.get(cj, 0.0)),
                    "c0": pearson(xi, xj),
                }
            )
    # stable order by channel lexical
    pairs.sort(key=lambda p: (p["i"], p["j"]))
    return pairs


def integration_metrics(
    pairs: list[dict[str, Any]], *, l_max: int = L_MAX
) -> tuple[float | None, float | None, float | None]:
    if not pairs:
        return None, None, None
    den = sum(p["w"] for p in pairs)
    if den <= EPS:
        return None, None, None
    i_f = sum(p["w"] * p["rho"] for p in pairs) / den
    s_num = 0.0
    for p in pairs:
        c0 = p.get("c0")
        if c0 is None:
            continue
        s_num += p["w"] * abs(float(c0))
    s_f = s_num / den
    l_f = sum(p["w"] * (abs(p["lag"]) / max(1, l_max)) for p in pairs) / den
    return clip01(i_f), clip01(s_f), clip01(l_f)


def _eigenvalues_symmetric(matrix: list[list[float]]) -> list[float]:
    """Jacobi eigenvalue algorithm for small K'×K' (K'≤12)."""
    n = len(matrix)
    if n == 0:
        return []
    if n == 1:
        return [max(0.0, matrix[0][0])]
    a = [row[:] for row in matrix]
    # Jacobi rotations
    for _ in range(40 * n * n):
        # find largest off-diagonal
        max_val = 0.0
        p = 0
        q = 1
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > max_val:
                    max_val = abs(a[i][j])
                    p, q = i, j
        if max_val < 1e-12:
            break
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        tau = (aqq - app) / (2.0 * apq) if abs(apq) > EPS else 0.0
        t = math.copysign(1.0, tau) / (abs(tau) + math.sqrt(1.0 + tau * tau)) if abs(apq) > EPS else 0.0
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        for k in range(n):
            if k == p or k == q:
                continue
            aik, aiq = a[k][p], a[k][q]
            a[k][p] = c * aik - s * aiq
            a[p][k] = a[k][p]
            a[k][q] = s * aik + c * aiq
            a[q][k] = a[k][q]
        a[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        a[p][q] = 0.0
        a[q][p] = 0.0
    eigs = [a[i][i] for i in range(n)]
    # clip tiny negatives
    eigs = [max(0.0, e) if e > -1e-10 else e for e in eigs]
    eigs = [max(0.0, e) for e in eigs]
    eigs.sort(reverse=True)
    return eigs


def differentiation_common_mode(
    series: dict[str, list[float]],
) -> tuple[float | None, float | None, int]:
    """D_F, M_F, K' from standardized covariance eigenvalues."""
    channels = [c for c in sorted(series) if not _is_constant(series[c])]
    k_prime = len(channels)
    if k_prime == 0:
        return None, None, 0
    if k_prime == 1:
        return 0.0, 1.0, 1
    w = len(next(iter(series.values())))
    if w < 2:
        return None, None, k_prime
    # standardize rows
    z: list[list[float]] = []
    for c in channels:
        row = series[c]
        m = sum(row) / w
        var = sum((x - m) ** 2 for x in row) / max(1, w - 1)
        sd = math.sqrt(var) if var > EPS else 1.0
        z.append([(x - m) / sd for x in row])
    # C = ZZ^T / (W-1)
    c_mat: list[list[float]] = [[0.0] * k_prime for _ in range(k_prime)]
    denom = max(1, w - 1)
    for i in range(k_prime):
        for j in range(k_prime):
            c_mat[i][j] = sum(z[i][t] * z[j][t] for t in range(w)) / denom
    eigs = _eigenvalues_symmetric(c_mat)
    total = sum(eigs)
    if total <= EPS:
        return 0.0, 1.0, k_prime
    p = [e / total for e in eigs]
    h_lambda = -sum(pj * math.log(pj + EPS) for pj in p if pj > 0)
    erank = math.exp(h_lambda)
    d_f = clip01((erank - 1.0) / (k_prime - 1.0))
    m_f = clip01(eigs[0] / total)
    return d_f, m_f, k_prime


def participation_entropy(
    series: dict[str, list[float]], reliability: dict[str, float]
) -> float | None:
    channels = sorted(series)
    k = len(channels)
    if k == 0:
        return None
    weights = []
    for c in channels:
        weights.append(reliability.get(c, 0.0) * sum(series[c]))
    z = sum(weights)
    if z <= EPS:
        return 0.0
    pi = [w / z for w in weights]
    h = -sum(p * math.log(p + EPS) for p in pi if p > 0)
    return clip01(h / math.log(max(2, k)))


def giant_component(
    channels: list[str],
    pairs: list[dict[str, Any]],
    *,
    tau_rho: float,
) -> tuple[float | None, list[dict[str, Any]]]:
    if not channels:
        return None, []
    adj: dict[str, set[str]] = {c: set() for c in channels}
    active = []
    for p in pairs:
        if p["rho"] >= tau_rho:
            adj[p["i"]].add(p["j"])
            adj[p["j"]].add(p["i"])
            active.append(
                {
                    "i": p["i"],
                    "j": p["j"],
                    "rho": p["rho"],
                    "lag": p["lag"],
                    "sign": p["sign"],
                }
            )
    seen: set[str] = set()
    best = 0
    for c in channels:
        if c in seen:
            continue
        stack = [c]
        comp = 0
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp += 1
            stack.extend(adj[u] - seen)
        best = max(best, comp)
    return clip01(best / len(channels)), active


def participation_etas(
    samples: list[FieldSample],
) -> tuple[float, float, float]:
    """η_E, η_M, Z_F — verified evidence never inflated by SIMULATED etc."""
    z = 0.0
    e = 0.0
    m = 0.0
    for s in samples:
        w = s.reliability * s.activity
        z += w
        if s.channel_family in EVIDENCE_FAMILIES and is_verified_evidence_truth(
            s.truth_source
        ):
            e += w
        if s.channel_family in MEMORY_FAMILIES:
            m += w
    if z <= EPS:
        return 0.0, 0.0, 0.0
    return clip01(e / z), clip01(m / z), z


def path_distribution(samples: list[FieldSample], half: str) -> dict[str, float]:
    ticks = sorted({s.tick for s in samples})
    if not ticks:
        return {}
    mid = ticks[len(ticks) // 2]
    bag: dict[str, float] = {}
    for s in samples:
        if half == "first" and s.tick > mid:
            continue
        if half == "second" and s.tick <= mid:
            continue
        for p in s.paths or ("∅",):
            bag[p] = bag.get(p, 0.0) + s.reliability * s.activity
    total = sum(bag.values()) or 1.0
    return {k: v / total for k, v in sorted(bag.items())}


def hamming_bits(a: tuple[int, ...] | list[int], b: tuple[int, ...] | list[int]) -> float:
    aa = list(a)[:4] + [0] * max(0, 4 - len(list(a)[:4]))
    bb = list(b)[:4] + [0] * max(0, 4 - len(list(b)[:4]))
    return sum(1 for i in range(4) if int(aa[i]) != int(bb[i])) / 4.0


def transition_pressure(
    samples: list[FieldSample],
    series: dict[str, list[float]],
    *,
    ndot: float | None,
    epoch_drift: bool,
    thresholds: FrameThresholds,
) -> float:
    if epoch_drift:
        return 1.0
    # Δ_A
    deltas = []
    for c, row in series.items():
        w = len(row)
        if w < 2:
            continue
        mid = w // 2
        first = sum(row[:mid]) / max(1, mid)
        second = sum(row[mid:]) / max(1, w - mid)
        deltas.append(abs(second - first))
    delta_a = clip01(sum(deltas) / len(deltas)) if deltas else 0.0
    delta_p = jsd_normalized(
        path_distribution(samples, "first"), path_distribution(samples, "second")
    )
    # constitutional bits first vs last tick
    by_tick: dict[int, tuple[int, ...]] = {}
    for s in samples:
        if s.constitutional_bits:
            by_tick[s.tick] = tuple(s.constitutional_bits)
    ticks = sorted(by_tick)
    if len(ticks) >= 2:
        delta_q = hamming_bits(by_tick[ticks[0]], by_tick[ticks[-1]])
    else:
        delta_q = 0.0
    delta_n = clip01(ndot if ndot is not None else 0.0)
    w0, w1, w2, w3 = thresholds.transition_weights
    return clip01(w0 * delta_a + w1 * delta_p + w2 * delta_n + w3 * delta_q)


def sample_digest(samples: list[FieldSample]) -> str:
    material = [
        {
            "t": s.tick,
            "c": s.channel_family,
            "a": round(s.activity, 6),
            "r": round(s.reliability, 6),
            "ts": s.truth_source,
            "ek": s.event_key,
        }
        for s in sorted(samples, key=lambda x: (x.tick, x.channel_family))
    ]
    return hashlib.sha256(
        json.dumps(material, sort_keys=True).encode()
    ).hexdigest()


def make_frame_id(
    *,
    repo: str,
    body_epoch_id: str,
    start_tick: int,
    end_tick: int,
    sample_digest_hex: str,
    baseline_digest: str,
    threshold_config_digest: str,
) -> str:
    material = {
        "repo": repo,
        "body_epoch_id": body_epoch_id,
        "start_tick": start_tick,
        "end_tick": end_tick,
        "sample_digest": sample_digest_hex,
        "baseline_digest": baseline_digest,
        "threshold_config_digest": threshold_config_digest,
    }
    h = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
    return f"frame_{h[:20]}"


def classify_frame(
    metrics: FrameMetrics,
    *,
    thresholds: FrameThresholds,
    baseline_warm: bool,
    epoch_drift: bool = False,
) -> tuple[str, list[str]]:
    """Deterministic classification in exact priority order."""
    reasons: list[str] = []
    w = metrics.tick_count
    # 0 INDETERMINATE
    if w < thresholds.w_min:
        return FrameClassification.INDETERMINATE.value, ["W < W_min"]
    if metrics.eligible_channel_count < 3:
        return FrameClassification.INDETERMINATE.value, ["eligible_channels < 3"]
    if not baseline_warm and metrics.nonrandomness is None:
        return FrameClassification.INDETERMINATE.value, ["baseline_warmup_incomplete"]
    required = [
        metrics.integration,
        metrics.differentiation,
        metrics.common_mode,
        metrics.participation_entropy,
        metrics.giant_component_fraction,
        metrics.evidence_participation,
        metrics.memory_participation,
        metrics.transition_pressure,
    ]
    if any(v is None for v in required):
        return FrameClassification.INDETERMINATE.value, ["required_metrics_unavailable"]

    n_f = metrics.nonrandomness
    t_f = float(metrics.transition_pressure or 0.0)
    mean_a = float(metrics.mean_activity or 0.0)
    i_f = float(metrics.integration or 0.0)
    d_f = float(metrics.differentiation or 0.0)
    m_f = float(metrics.common_mode or 0.0)
    h_p = float(metrics.participation_entropy or 0.0)
    g_f = float(metrics.giant_component_fraction or 0.0)
    q_f = metrics.comparator_quality
    eta_e = float(metrics.evidence_participation or 0.0)
    eta_m = float(metrics.memory_participation or 0.0)

    # 1 TRANSITION
    if epoch_drift or (
        t_f >= thresholds.transition_high
        and n_f is not None
        and n_f >= thresholds.nonrandomness_good
    ):
        reasons.append("epoch_drift" if epoch_drift else "T_F high with nonrandomness")
        return FrameClassification.TRANSITION.value, reasons

    # 2 QUIESCENT
    if mean_a < thresholds.activity_low and (
        n_f is None or n_f < thresholds.nonrandomness_good
    ):
        return FrameClassification.QUIESCENT.value, ["low_mean_activity"]

    # 3 STALE_ECHO
    if eta_m >= thresholds.memory_dominant and i_f >= thresholds.integration_good:
        if (
            eta_e < thresholds.evidence_min
            or q_f is None
            or q_f < thresholds.comparator_good
            or not metrics.epoch_current
        ):
            return FrameClassification.STALE_ECHO.value, ["memory_dominant_weak_evidence"]

    # 4 OVERBOUND
    if i_f >= thresholds.integration_high and (
        d_f < thresholds.differentiation_low
        or m_f > thresholds.common_mode_high
        or h_p < thresholds.participation_low
    ):
        return FrameClassification.OVERBOUND.value, ["high_integration_low_diversity"]

    # 5 FRAGMENTED
    if mean_a >= thresholds.activity_low and (
        i_f < thresholds.integration_low or g_f < thresholds.giant_min
    ):
        return FrameClassification.FRAGMENTED.value, ["low_integration_or_giant"]

    # 6 COHERENT_DIFFERENTIATED
    if (
        n_f is not None
        and n_f >= thresholds.nonrandomness_good
        and i_f >= thresholds.integration_good
        and d_f >= thresholds.differentiation_good
        and m_f <= thresholds.common_mode_high
        and h_p >= thresholds.participation_low
        and g_f >= thresholds.giant_min
        and metrics.comparator_available
        and q_f is not None
        and q_f >= thresholds.comparator_good
        and eta_e >= thresholds.evidence_min
        and metrics.epoch_current
    ):
        return FrameClassification.COHERENT_DIFFERENTIATED.value, ["all_coherent_criteria"]

    return FrameClassification.INDETERMINATE.value, ["no_rule_matched"]


def compute_frame_metrics(
    samples: list[FieldSample],
    *,
    baseline_dist: dict[str, dict[str, float]] | None = None,
    previous_n: float | None = None,
    q95_delta_n: float | None = None,
    thresholds: FrameThresholds | None = None,
    epoch_current: bool = False,
    epoch_drift: bool = False,
) -> tuple[FrameMetrics, list[dict[str, Any]], bool]:
    thr = thresholds or DEFAULT_THRESHOLDS
    baseline_dist = baseline_dist or {}
    ticks, series, reliability, _truth = build_series(samples)
    metrics = FrameMetrics(
        channel_count=len(series),
        tick_count=len(ticks),
        epoch_current=epoch_current,
    )
    if not samples or not ticks:
        return metrics, [], False

    # mean activity
    all_x = [x for row in series.values() for x in row]
    metrics.mean_activity = sum(all_x) / max(1, len(all_x))

    eligible = [c for c in series if not _is_constant(series[c])]
    metrics.eligible_channel_count = len(eligible)

    frame_dist = frame_distributions(samples)
    baseline_warm = (
        sum(1 for c in frame_dist if baseline_dist.get(c)) >= MIN_BASELINE_CHANNELS
    )
    n_f = operational_nonrandomness(frame_dist, baseline_dist, reliability)
    metrics.nonrandomness = n_f
    if n_f is not None and previous_n is not None:
        scale = (q95_delta_n if q95_delta_n is not None else thr.q95_delta_n_default) + EPS
        metrics.nonrandomness_rate = clip01(abs(n_f - previous_n) / scale)
    elif n_f is not None:
        metrics.nonrandomness_rate = 0.0
    else:
        metrics.nonrandomness_rate = None

    pairs = lagged_pair_stats(
        series, reliability, l_max=thr.l_max, min_overlap=thr.min_pair_overlap
    )
    i_f, s_f, l_f = integration_metrics(pairs, l_max=thr.l_max)
    metrics.integration = i_f
    metrics.same_frame_coordination = s_f
    metrics.lag_index = l_f

    d_f, m_f, _kp = differentiation_common_mode(series)
    metrics.differentiation = d_f
    metrics.common_mode = m_f
    metrics.participation_entropy = participation_entropy(series, reliability)

    g_f, active = giant_component(
        eligible or sorted(series), pairs, tau_rho=thr.edge_active
    )
    metrics.giant_component_fraction = g_f

    cmp = compare_evidence_memory(samples)
    metrics.comparator_available = bool(cmp.get("comparator_available"))
    metrics.comparator_agreement = cmp.get("agreement")
    metrics.contradiction_mass = cmp.get("contradiction_mass")
    metrics.comparator_quality = cmp.get("quality")

    eta_e, eta_m, _z = participation_etas(samples)
    metrics.evidence_participation = eta_e
    metrics.memory_participation = eta_m

    metrics.transition_pressure = transition_pressure(
        samples,
        series,
        ndot=metrics.nonrandomness_rate,
        epoch_drift=epoch_drift,
        thresholds=thr,
    )
    return metrics, active, baseline_warm


def close_resonant_frame(
    samples: list[FieldSample],
    *,
    repo: str,
    body_epoch_id: str = "",
    baseline_dist: dict[str, dict[str, float]] | None = None,
    baseline_digest: str = "",
    previous_n: float | None = None,
    q95_delta_n: float | None = None,
    thresholds: FrameThresholds | None = None,
    epoch_current: bool = False,
    epoch_drift: bool = False,
    cortex_version: str = "",
) -> ResonantFrame:
    thr = thresholds or DEFAULT_THRESHOLDS
    if not samples:
        raise ValueError("cannot close empty frame")
    ticks = sorted({s.tick for s in samples})
    start_tick, end_tick = ticks[0], ticks[-1]
    metrics, active, baseline_warm = compute_frame_metrics(
        samples,
        baseline_dist=baseline_dist,
        previous_n=previous_n,
        q95_delta_n=q95_delta_n,
        thresholds=thr,
        epoch_current=epoch_current,
        epoch_drift=epoch_drift,
    )
    classification, reasons = classify_frame(
        metrics,
        thresholds=thr,
        baseline_warm=baseline_warm,
        epoch_drift=epoch_drift,
    )
    contract = measurement_contract(samples)
    if contract["policy_eligible"]:
        pol = policy_for_classification(classification).to_dict()
    else:
        pol = policy_for_classification(
            FrameClassification.INDETERMINATE.value,
            reasons=["modeled_measurement_shadow_only"],
        ).to_dict()
        pol["mode"] = "shadow_modeled"
        pol["measurement_basis"] = contract["measurement_basis"]
        pol["policy_eligible"] = False
    sdig = sample_digest(samples)
    tdig = thr.digest()
    bdig = baseline_digest or hashlib.sha256(
        json.dumps(baseline_dist or {}, sort_keys=True).encode()
    ).hexdigest()
    fid = make_frame_id(
        repo=repo,
        body_epoch_id=body_epoch_id,
        start_tick=start_tick,
        end_tick=end_tick,
        sample_digest_hex=sdig,
        baseline_digest=bdig,
        threshold_config_digest=tdig,
    )
    if not cortex_version:
        try:
            from . import __version__ as cv

            cortex_version = cv
        except Exception:
            cortex_version = "unknown"
    return ResonantFrame(
        frame_id=fid,
        repo=repo,
        body_epoch_id=body_epoch_id,
        start_tick=start_tick,
        end_tick=end_tick,
        samples=list(samples),
        sample_digest=sdig,
        baseline_digest=bdig,
        threshold_config_digest=tdig,
        channel_truth_panel=channel_truth_panel(samples),
        metrics=metrics,
        classification=classification,
        policy=dict(pol),
        measurement_basis=str(contract["measurement_basis"]),
        policy_eligible=bool(contract["policy_eligible"]),
        baseline_eligible=bool(contract["baseline_eligible"]),
        reasons=reasons,
        active_edges=active,
        cortex_version=cortex_version,
        issued_at=time.time(),
    )


# ── live buffer / store persistence ──────────────────────────────


def _state_key(repo: str) -> str:
    return f"field_state:{repo}"


def _baseline_key(repo: str) -> str:
    return f"field_baseline:{repo}"


def _latest_key(repo: str) -> str:
    return f"field_frame_latest:{repo}"


def _frame_key(repo: str, frame_id: str) -> str:
    return f"field_frame:{repo}:{frame_id}"


def _index_key(repo: str) -> str:
    return f"field_frame_index:{repo}"


def _calibration_key(repo: str) -> str:
    return f"field_calibration:{repo}"


def load_field_state(store: Any, repo: str) -> dict[str, Any]:
    return dict(store.get_setting(_state_key(repo), {}) or {})


def save_field_state(store: Any, repo: str, state: dict[str, Any]) -> None:
    store.set_setting(_state_key(repo), state)


def load_baseline(store: Any, repo: str) -> dict[str, Any]:
    return dict(store.get_setting(_baseline_key(repo), {}) or {})


def field_enabled(store: Any | None = None) -> bool:
    import os

    flag = os.environ.get("CORTEX_FIELD", "1").strip().casefold()
    if flag in {"0", "off", "false", "no"}:
        return False
    if store is not None:
        st = store.get_setting("field_global", {}) or {}
        if st.get("enabled") is False:
            return False
    return True


def append_field_samples(
    store: Any,
    repo: str,
    samples: list[FieldSample],
    *,
    force_close: bool = False,
    reason: str = "",
) -> dict[str, Any]:
    """Append tick samples to rolling buffer; close frame if conditions met."""
    if not field_enabled(store) or not samples:
        return {"ok": True, "skipped": True, "reason": "field_disabled_or_empty"}

    thr = DEFAULT_THRESHOLDS
    state = load_field_state(store, repo)
    buffer = [FieldSample.from_dict(s) for s in (state.get("buffer") or [])]
    buffer.extend(samples)
    # bound live buffer
    max_keep = thr.w_max * (len(CHANNEL_FAMILIES) + 2)
    if len(buffer) > max_keep:
        buffer = buffer[-max_keep:]

    ticks = sorted({s.tick for s in buffer})
    body_epoch = samples[-1].body_epoch_id if samples else state.get("body_epoch_id", "")
    prev_epoch = state.get("body_epoch_id") or body_epoch
    epoch_drift = bool(prev_epoch and body_epoch and prev_epoch != body_epoch)

    close = force_close or reason in {
        "task_step",
        "fusion_close",
        "explicit_close",
        "constitutional_transition",
    }
    if len(ticks) >= thr.w_max:
        close = True
        reason = reason or "W_max"
    if epoch_drift:
        close = True
        reason = reason or "epoch_drift"

    # transition pressure after W_min
    closed_frame = None
    if not close and len(ticks) >= thr.w_min:
        bas = load_baseline(store, repo)
        metrics, _, _ = compute_frame_metrics(
            buffer,
            baseline_dist=bas.get("distributions") or {},
            previous_n=state.get("previous_n"),
            q95_delta_n=(bas.get("q95_delta_n")),
            epoch_current=bool(state.get("epoch_current")),
            epoch_drift=False,
        )
        if (metrics.transition_pressure or 0) >= thr.transition_high:
            close = True
            reason = reason or "transition_pressure"
        elif reason == "activation_observation":
            # Activation observations close at the first mathematically usable
            # window. Fusion keeps its existing transition/W_max cadence.
            close = True
            reason = "temporal_window_ready"

    state["buffer"] = [s.to_dict() for s in buffer]
    state["body_epoch_id"] = body_epoch
    state["tick"] = samples[-1].tick if samples else state.get("tick", 0)
    state["updated_at"] = time.time()

    if close and len(ticks) >= 1:
        bas = load_baseline(store, repo)
        epoch_current = False
        try:
            from .epoch import observe_current_epoch

            obs = observe_current_epoch(store, repo)
            epoch_current = bool(obs.get("verified") or obs.get("is_current"))
            body_epoch = str(obs.get("epoch_id") or obs.get("live_epoch_id") or body_epoch)
        except Exception:
            pass
        frame = close_resonant_frame(
            buffer,
            repo=repo,
            body_epoch_id=body_epoch,
            baseline_dist=bas.get("distributions") or {},
            baseline_digest=str(bas.get("digest") or ""),
            previous_n=state.get("previous_n"),
            q95_delta_n=bas.get("q95_delta_n"),
            epoch_current=epoch_current,
            epoch_drift=epoch_drift,
        )
        persist_closed_frame(store, repo, frame, baseline=bas)
        state["buffer"] = []
        state["previous_n"] = frame.metrics.nonrandomness
        state["last_frame_id"] = frame.frame_id
        state["last_classification"] = frame.classification
        closed_frame = frame.to_dict()
        reason = reason or "closed"

    save_field_state(store, repo, state)
    return {
        "ok": True,
        "closed": closed_frame is not None,
        "reason": reason,
        "buffer_ticks": len(sorted({s.tick for s in buffer})) if not closed_frame else 0,
        "frame": closed_frame,
        "latest_compact": (closed_frame or {}).get("frame_id")
        and {
            "frame_id": closed_frame["frame_id"],
            "classification": closed_frame["classification"],
            "advisory_only": True,
        },
    }


def persist_closed_frame(
    store: Any,
    repo: str,
    frame: ResonantFrame,
    *,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .field_receipt import issue_frame_receipt

    receipt = issue_frame_receipt(frame)
    store.set_setting(_frame_key(repo, frame.frame_id), receipt)
    store.set_setting(_latest_key(repo), receipt)
    idx = list(store.get_setting(_index_key(repo), []) or [])
    idx.append(frame.frame_id)
    idx = idx[-FRAME_INDEX_CAP:]
    store.set_setting(_index_key(repo), idx)

    # baseline update (strict conditions — capability assumed local observe store)
    bas = dict(baseline or load_baseline(store, repo))
    if _may_update_baseline(frame):
        dists = dict(bas.get("distributions") or {})
        frame_d = frame_distributions(frame.samples)
        for ch, dist in frame_d.items():
            old = dists.get(ch) or {}
            # exponential blend
            keys = sorted(set(old) | set(dist))
            blended = {}
            for k in keys:
                blended[k] = 0.85 * float(old.get(k, 0.0)) + 0.15 * float(dist.get(k, 0.0))
            s = sum(blended.values()) or 1.0
            dists[ch] = {k: v / s for k, v in blended.items()}
        bas["distributions"] = dists
        bas["digest"] = hashlib.sha256(
            json.dumps(dists, sort_keys=True).encode()
        ).hexdigest()
        bas["updated_at"] = time.time()
        bas["frames_seen"] = int(bas.get("frames_seen") or 0) + 1
        # track delta N for q95
        hist = list(bas.get("delta_n_history") or [])
        if frame.metrics.nonrandomness is not None:
            hist.append(float(frame.metrics.nonrandomness_rate or 0.0))
            hist = hist[-64:]
            bas["delta_n_history"] = hist
            if len(hist) >= 8:
                ordered = sorted(hist)
                bas["q95_delta_n"] = ordered[int(0.95 * (len(ordered) - 1))]
        store.set_setting(_baseline_key(repo), bas)
    return receipt


def _may_update_baseline(frame: ResonantFrame) -> bool:
    if not frame.baseline_eligible:
        return False
    if frame.classification in {
        FrameClassification.STALE_ECHO.value,
        FrameClassification.TRANSITION.value,
    }:
        return False
    if not frame.metrics.epoch_current:
        return False
    if (frame.metrics.contradiction_mass or 0) > 0.5:
        return False
    return True


def latest_frame(store: Any, repo: str) -> dict[str, Any] | None:
    return store.get_setting(_latest_key(repo))


def frame_trace(store: Any, repo: str, *, limit: int = 16) -> list[dict[str, Any]]:
    idx = list(store.get_setting(_index_key(repo), []) or [])
    out = []
    for fid in idx[-limit:]:
        rec = store.get_setting(_frame_key(repo, fid))
        if rec:
            out.append(rec)
    return out


def baseline_warmup_status(bas: dict[str, Any] | None = None) -> dict[str, Any]:
    """Human + machine warmup: '3/16' style, never silent null baselines."""
    bas = bas or {}
    seen = int(bas.get("frames_seen") or 0)
    need = 16  # calibration / solid baseline target
    min_ch = MIN_BASELINE_CHANNELS
    dist = bas.get("distributions") or {}
    channels_warm = sum(1 for _k, v in dist.items() if v)
    ready = seen >= need and channels_warm >= min_ch
    warming = not ready
    # display like "3/16"
    seen_display = f"{min(seen, need)}/{need}"
    return {
        "baseline_frames_seen": seen,
        "baseline_frames_target": need,
        "baseline_frames_display": seen_display,
        "baseline_channels_warm": channels_warm,
        "baseline_channels_min": min_ch,
        "baseline_ready": ready,
        "baseline_warming": warming,
        "baseline_message": (
            f"baseline ready ({seen_display} frames, {channels_warm} channels)"
            if ready
            else (
                f"baseline warming ({seen_display} frames; "
                f"need {need} epoch-current frames and ≥{min_ch} channel baselines)"
            )
        ),
        "n_f_note": (
            "N_F available when ≥3 channels have baselines"
            if channels_warm >= min_ch
            else "N_F is null until ≥3 channel baselines warm (not a middle value)"
        ),
    }


def field_report(store: Any, repo: str) -> dict[str, Any]:
    state = load_field_state(store, repo)
    latest = latest_frame(store, repo)
    bas = load_baseline(store, repo)
    warmup = baseline_warmup_status(bas)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "enabled": field_enabled(store),
        "live_buffer_samples": len(state.get("buffer") or []),
        "last_frame_id": state.get("last_frame_id"),
        "last_classification": state.get("last_classification"),
        "latest": latest,
        # numeric + "3/16" display (never hide warmup)
        "baseline_frames_seen": warmup["baseline_frames_seen"],
        "baseline_frames_target": warmup["baseline_frames_target"],
        "baseline_frames_display": warmup["baseline_frames_display"],
        "baseline_warmup": warmup,
        "baseline_ready": warmup["baseline_ready"],
        "baseline_digest": bas.get("digest"),
        "canonical_statement": CANONICAL_STATEMENT,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
    }


def field_close(store: Any, repo: str) -> dict[str, Any]:
    state = load_field_state(store, repo)
    buffer = [FieldSample.from_dict(s) for s in (state.get("buffer") or [])]
    if not buffer:
        return {"ok": True, "closed": False, "reason": "empty_buffer"}
    bas = load_baseline(store, repo)
    body_epoch = ""
    epoch_current = False
    try:
        from .epoch import observe_current_epoch

        obs = observe_current_epoch(store, repo)
        body_epoch = str(obs.get("epoch_id") or obs.get("live_epoch_id") or "")
        epoch_current = bool(obs.get("verified") or obs.get("is_current"))
    except Exception:
        body_epoch = buffer[-1].body_epoch_id if buffer else ""
    frame = close_resonant_frame(
        buffer,
        repo=repo,
        body_epoch_id=body_epoch,
        baseline_dist=bas.get("distributions") or {},
        baseline_digest=str(bas.get("digest") or ""),
        previous_n=state.get("previous_n"),
        epoch_current=epoch_current,
    )
    receipt = persist_closed_frame(store, repo, frame, baseline=bas)
    state["buffer"] = []
    state["previous_n"] = frame.metrics.nonrandomness
    state["last_frame_id"] = frame.frame_id
    state["last_classification"] = frame.classification
    save_field_state(store, repo, state)
    return {"ok": True, "closed": True, "reason": "explicit_close", "frame": receipt}


def seed_from_activation(
    store: Any,
    repo: str,
    activation: dict[str, Any] | None = None,
    *,
    task: str = "",
    governor_mode: str = "unknown",
    force_close: bool = False,
    reason: str = "activation",
) -> dict[str, Any]:
    from .field_channels import collect_activation_channels
    from .cognitive.measured import delta_field_samples

    state = load_field_state(store, repo)
    act = activation or {}
    ctx = act.get("context") if isinstance(act.get("context"), dict) else {}
    stream = ctx.get("stream") if isinstance(ctx.get("stream"), dict) else {}
    observations: list[tuple[str, str, float | None]] = []
    cognitive = act.get("cognitive_cycle") if isinstance(act.get("cognitive_cycle"), dict) else {}
    measured = (
        cognitive.get("measured_event_field")
        if isinstance(cognitive.get("measured_event_field"), dict)
        else act.get("measured_event_field")
    )
    if not isinstance(measured, dict):
        measured = {}
    is_measured = measured.get("measurement_basis") == "measured_delta"

    def add_observation(
        value: Any, kind: str, observed_at: Any = None
    ) -> None:
        observation_id = str(value or "")
        if not observation_id or any(item[0] == observation_id for item in observations):
            return
        try:
            at = float(observed_at) if observed_at is not None else None
        except (TypeError, ValueError):
            at = None
        observations.append((observation_id, kind[:128], at))

    neural = ctx.get("neural_interlink") if isinstance(ctx.get("neural_interlink"), dict) else {}
    organism = ctx.get("organism") if isinstance(ctx.get("organism"), dict) else {}
    prediction = ctx.get("prediction") if isinstance(ctx.get("prediction"), dict) else {}
    connect = ctx.get("connect_pass") if isinstance(ctx.get("connect_pass"), dict) else {}
    controller = (
        ctx.get("controller_execution")
        if isinstance(ctx.get("controller_execution"), dict)
        else {}
    )
    if is_measured:
        add_observation(
            measured.get("event_id") or measured.get("receipt_hash"),
            "activation_transaction",
            measured.get("measured_at"),
        )
    else:
        add_observation(neural.get("activation_id"), "neural_activation")
    organism_body = organism.get("body") if isinstance(organism.get("body"), dict) else {}
    organism_identity = (
        organism_body.get("identity")
        if isinstance(organism_body.get("identity"), dict)
        else {}
    )
    if not is_measured:
        add_observation(organism_identity.get("session_id"), "session_begin")
        add_observation(organism.get("pulse"), "organism_pulse", organism.get("issued_at"))
        add_observation(
            organism.get("pulse_chain"), "organism_pulse_chain", organism.get("issued_at")
        )
        add_observation(ctx.get("packet_hash"), "context_packet")
        for frame in list(stream.get("recent_frames") or []):
            if isinstance(frame, dict):
                add_observation(
                    frame.get("frame_id"),
                    f"stream_{str(frame.get('kind') or 'event')}",
                    frame.get("at"),
                )
        add_observation(prediction.get("trace_id"), "prediction_trace")
        add_observation(connect.get("pass_id"), "connect_pass")
        add_observation(controller.get("receipt_hash"), "controller_receipt")
    if not observations:
        add_observation(
            act.get("packet_hash") or stream.get("chain_tip"),
            "activation_boundary",
        )
    seen = list(state.get("activation_observation_ids") or [])
    pending = [item for item in observations if item[0] not in seen]
    if observations and not pending:
        return {
            "ok": True,
            "skipped": True,
            "reason": "duplicate_observation",
            "observation_id": observations[-1][0],
            "observation_ids": [item[0] for item in observations],
            "observation_count": 0,
            "buffer_ticks": len(
                {int(s.get("tick") or 0) for s in (state.get("buffer") or [])}
            ),
        }
    tick = int(state.get("tick") or 0)
    samples: list[FieldSample] = []
    for offset, (observation_id, observation_kind, observed_at) in enumerate(pending, start=1):
        if is_measured:
            samples.extend(
                delta_field_samples(
                    measured,
                    repo=repo,
                    body_epoch_id=str((act.get("body_epoch") or {}).get("epoch_id") or ""),
                    tick=tick + offset,
                    governor_mode=governor_mode,
                )
            )
        else:
            samples.extend(
                collect_activation_channels(
                    store,
                    repo,
                    tick=tick + offset,
                    task=task,
                    activation=activation,
                    governor_mode=governor_mode,
                    observation_id=observation_id,
                    observation_kind=observation_kind,
                    observed_at=observed_at,
                )
            )
    result = append_field_samples(
        store,
        repo,
        samples,
        force_close=force_close,
        reason=reason,
    )
    if pending:
        state = load_field_state(store, repo)
        seen = list(state.get("activation_observation_ids") or [])
        for observation_id, _, _ in pending:
            if observation_id not in seen:
                seen.append(observation_id)
        state["activation_observation_ids"] = seen[-OBSERVATION_CURSOR_CAP:]
        state["last_activation_observation_id"] = pending[-1][0]
        save_field_state(store, repo, state)
    result["observation_id"] = pending[-1][0] if pending else None
    result["observation_ids"] = [item[0] for item in pending]
    result["observation_count"] = len(pending)
    result["exactly_once"] = bool(pending)
    return result


def fuse_tick_field(
    store: Any,
    repo: str,
    *,
    tick: int,
    task: str = "",
    paths: list[str] | None = None,
    governor_mode: str = "unknown",
    close: bool = False,
) -> dict[str, Any]:
    """Cheap per-tick sample for fusion co-process (no full eigen every token)."""
    from .field_channels import sample_tick_channels
    from .epoch import observe_current_epoch

    body_epoch = ""
    try:
        obs = observe_current_epoch(store, repo)
        body_epoch = str(obs.get("epoch_id") or obs.get("live_epoch_id") or "")
    except Exception:
        pass
    # lightweight activities from tick dynamics
    base = 0.2 + 0.02 * (tick % 10)
    activities = {fam: clip01(base) for fam in CHANNEL_FAMILIES}
    activities["T_TASK"] = clip01(0.4 + (0.3 if task else 0.0))
    activities["O_OPERATIONS"] = clip01(0.35 + 0.01 * min(20, tick))
    if paths:
        activities["E_HOST"] = clip01(0.3 + 0.05 * min(8, len(paths)))
        activities["S_STRUCTURE"] = clip01(0.25 + 0.04 * min(8, len(paths)))
    samples = sample_tick_channels(
        repo=repo,
        body_epoch_id=body_epoch,
        tick=tick,
        activities=activities,
        paths_by_channel={"E_HOST": list(paths or [])[:12], "T_TASK": list(paths or [])[:4]},
        governor_mode=governor_mode,
        truth_sources={
            "E_HOST": "MEASURED" if paths else "INFERRED",
            "O_OPERATIONS": "MEASURED",
            "T_TASK": "OPERATOR_ASSERTED" if task else "UNKNOWN",
        },
    )
    result = append_field_samples(
        store, repo, samples, force_close=False, reason="fusion_close" if close else ""
    )
    if close:
        result = field_close(store, repo)
    latest = latest_frame(store, repo)
    compact = None
    if latest:
        compact = {
            "frame_id": latest.get("frame_id"),
            "classification": latest.get("classification"),
            "integration": (latest.get("metrics") or {}).get("integration"),
            "differentiation": (latest.get("metrics") or {}).get("differentiation"),
            "common_mode": (latest.get("metrics") or {}).get("common_mode"),
            "comparator_quality": (latest.get("metrics") or {}).get("comparator_quality"),
            "evidence_participation": (latest.get("metrics") or {}).get(
                "evidence_participation"
            ),
            "transition_pressure": (latest.get("metrics") or {}).get("transition_pressure"),
            "recommended_regime": (latest.get("policy") or {}).get(
                "recommended_gcmt_regime"
            ),
            "advisory_only": True,
        }
    result["resonant_frame"] = compact
    result["instruction"] = (
        "Use Resonant Frame state only as an advisory context-selection signal. "
        "It is not authority, witness, correctness, or host mutation permission."
    )
    return result


def cleanup_field_data(store: Any, repo: str, *, dry_run: bool = True) -> dict[str, Any]:
    """Remove field_* keys only — never host/evidence/epochs/claims."""
    keys = [
        _state_key(repo),
        _baseline_key(repo),
        _latest_key(repo),
        _index_key(repo),
        _calibration_key(repo),
    ]
    idx = list(store.get_setting(_index_key(repo), []) or [])
    for fid in idx:
        keys.append(_frame_key(repo, fid))
    removed = []
    if not dry_run:
        for k in keys:
            try:
                store.db.execute("DELETE FROM settings WHERE key=?", (k,))
                removed.append(k)
            except Exception:
                pass
        store.db.commit()
    return {
        "ok": True,
        "dry_run": dry_run,
        "keys": keys,
        "removed": removed,
        "claim": "field cleanup does not touch evidence, memory, epochs, capabilities, claims, or host registration",
    }


def calibrate_shadow(store: Any, repo: str) -> dict[str, Any]:
    """Shadow-only calibration candidate after ≥16 valid frames."""
    frames = frame_trace(store, repo, limit=64)
    valid = [
        f
        for f in frames
        if f.get("classification")
        not in {FrameClassification.INDETERMINATE.value}
        and (f.get("metrics") or {}).get("epoch_current")
    ]
    if len(valid) < 16:
        return {
            "ok": False,
            "shadow": True,
            "reason": "need_16_valid_epoch_current_frames",
            "have": len(valid),
        }
    # quantile candidates — never auto-promote
    def col(name: str) -> list[float]:
        vals = []
        for f in valid:
            v = (f.get("metrics") or {}).get(name)
            if v is not None:
                vals.append(float(v))
        return sorted(vals)

    def q(vals: list[float], p: float) -> float | None:
        if not vals:
            return None
        return vals[int(p * (len(vals) - 1))]

    candidate = {
        "integration_good": q(col("integration"), 0.4),
        "integration_low": q(col("integration"), 0.2),
        "differentiation_good": q(col("differentiation"), 0.4),
        "common_mode_high": q(col("common_mode"), 0.8),
        "defaults_preserved": DEFAULT_THRESHOLDS.to_dict(),
        "shadow": True,
        "promoted": False,
        "frames": len(valid),
        "issued_at": time.time(),
    }
    store.set_setting(_calibration_key(repo), candidate)
    return {"ok": True, "shadow": True, "calibration": candidate}
