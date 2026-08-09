"""v7.5 Self-Sensing Field — bounded observer over Cortex's own operational state.

Measures z_t, maintains robust baseline μ_t, residual r_t, geometric-mean health F_t.
Hard external gates for warm baseline, epoch currency, evidence, witness, phase binding.

Never: host mutation, epoch seal, constitutional bits, capability, promote, ARIA exec,
coherence-as-authority, consciousness claims.

May only: measure, compare, classify, report residuals, recommend, request review.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from . import __version__

SCHEMA = "cortex-self-sensing/1.0"
GLYPH = "◈👁"
RECEIPT_SCHEMA = "cortex-self-sensing-receipt/1.0"

# EMA + residual defaults (engineering, not universal constants)
ALPHA_DEFAULT = 0.12
LAMBDA_RIDGE = 1e-3
EPS = 1e-12
BASELINE_MIN = 16
CHANNEL_MIN = 3
HISTORY_CAP = 64
Z_DIM = 13

CLAIM = (
    "Self-Sensing Field is a bounded observer over Cortex operational telemetry. "
    "Residual means 'different from recent verified regime,' not authorization to "
    "self-modify. It does not grant capability, seal epochs, mutate host source, "
    "promote learned evidence, execute ARIA, or establish consciousness."
)

CANONICAL = (
    "Cortex observes its own operational field only as advisory telemetry. "
    "High F_t or low residual never moves a constitutional bit. "
    "Missing epoch binding forbids a healthy classification."
)

# Canonical order of z_t components
Z_KEYS: tuple[str, ...] = (
    "C",   # operational coherence
    "N",   # temporal nonrandomness
    "I",   # integration
    "L",   # lag index / lagged coordination
    "D",   # differentiation
    "H",   # participation entropy
    "G",   # giant component
    "Q",   # comparator quality
    "eta_E",
    "eta_M",
    "T",   # transition pressure
    "delta_E",  # epoch drift 0|1
    "U",   # uncertainty
)


class SelfSenseClass(str, Enum):
    COLD = "COLD"  # baseline not warm / insufficient evidence
    NOMINAL = "NOMINAL"  # within regime
    DRIFT = "DRIFT"  # residual elevated
    STRESSED = "STRESSED"  # high residual or low F
    UNBOUND = "UNBOUND"  # epoch/phase binding missing — never "healthy"
    INDETERMINATE = "INDETERMINATE"


@dataclass
class ObserverGates:
    baseline_warm: bool = False
    epoch_current: bool = False
    phase_bound: bool = False
    evidence_valid: bool = False
    witness_available: bool = False
    field_frames_ready: bool = False

    def all_hard_pass(self) -> bool:
        """Hard gates required before NOMINAL/healthy may be reported."""
        return (
            self.baseline_warm
            and self.epoch_current
            and self.phase_bound
            and self.evidence_valid
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clip01(x: float | None) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return max(0.0, min(1.0, v))


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _state_key(repo: str) -> str:
    return f"self_sense_state:{repo}"


def _latest_key(repo: str) -> str:
    # Interconnect frames bind self_sensing_latest — keep one surface name.
    return f"self_sensing_latest:{repo}"


def _index_key(repo: str) -> str:
    return f"self_sense_index:{repo}"


def geometric_mean(values: list[float]) -> float | None:
    """GM of positive clipped components; None if empty or any non-positive."""
    xs = [float(v) for v in values if v is not None]
    if not xs:
        return None
    # clip to (eps, 1]
    xs = [max(EPS, min(1.0, v)) for v in xs]
    log_avg = sum(math.log(v) for v in xs) / len(xs)
    return max(0.0, min(1.0, math.exp(log_avg)))


def sample_observer_state(
    store: Any,
    repo: str,
    *,
    coherence_report: dict[str, Any] | None = None,
    home: Any | None = None,
) -> dict[str, Any]:
    """Collect z_t from existing surfaces (observe-only)."""
    # Coherence C and U
    coh = coherence_report
    if coh is None:
        try:
            from .coherence import measure_coherence

            coh = measure_coherence(store, repo, home=home, persist=False)
        except Exception as exc:
            coh = {"score": None, "error": f"{type(exc).__name__}:{exc}"}

    c_t = _clip01(coh.get("score") if isinstance(coh, dict) else None)
    u_t = None
    try:
        cert = (coh.get("components") or {}).get("certainty")
        if cert is not None:
            u_t = _clip01(1.0 - float(cert))
    except Exception:
        pass
    if u_t is None:
        try:
            # lightweight uncertainty without full governor if available
            from .math_net.uncertainty import compute_uncertainty

            u_pkt = compute_uncertainty(retrieval_confidence=0.55)
            u_t = _clip01(float(u_pkt.get("u") if isinstance(u_pkt, dict) else 0.5))
        except Exception:
            u_t = 0.5

    # Frame metrics
    frame_m: dict[str, Any] = {}
    latest_frame = None
    try:
        from .resonant_frame import field_report, latest_frame as lf

        fr = field_report(store, repo)
        latest_frame = lf(store, repo)
        if latest_frame:
            frame_m = latest_frame.get("metrics") or latest_frame.get("frame_vector") or {}
            # map vector aliases
            if "N_F" in (latest_frame.get("frame_vector") or {}):
                fv = latest_frame["frame_vector"]
                frame_m = {
                    "nonrandomness": fv.get("N_F"),
                    "integration": fv.get("I_F"),
                    "lag_index": fv.get("L_F"),
                    "differentiation": fv.get("D_F"),
                    "participation_entropy": fv.get("H_P"),
                    "giant_component_fraction": fv.get("G_F"),
                    "comparator_quality": fv.get("Q_F"),
                    "evidence_participation": fv.get("eta_E"),
                    "memory_participation": fv.get("eta_M"),
                    "transition_pressure": fv.get("T_F"),
                    **{k: frame_m.get(k) for k in frame_m},
                }
        warmup = fr.get("baseline_warmup") or {}
    except Exception:
        warmup = {}
        fr = {}

    n_t = _clip01(frame_m.get("nonrandomness") if frame_m else None)
    i_t = _clip01(frame_m.get("integration"))
    l_t = _clip01(frame_m.get("lag_index") or frame_m.get("same_frame_coordination"))
    d_t = _clip01(frame_m.get("differentiation"))
    h_t = _clip01(frame_m.get("participation_entropy"))
    g_t = _clip01(frame_m.get("giant_component_fraction"))
    q_t = _clip01(frame_m.get("comparator_quality"))
    eta_e = _clip01(frame_m.get("evidence_participation"))
    eta_m = _clip01(frame_m.get("memory_participation"))
    t_t = _clip01(frame_m.get("transition_pressure"))

    # Epoch drift ΔE + phase binding (only BOUND is constitutionally compatible)
    delta_e = 1.0
    epoch_current = False
    phase_bound = False
    try:
        from .epoch import observe_current_epoch
        from .phases import phase_binding_status

        obs = observe_current_epoch(store, repo)
        epoch_current = bool(obs.get("verified"))
        delta_e = 0.0 if epoch_current else 1.0
        bind = phase_binding_status(store, repo)
        phase_bound = bool(
            bind.get("constitutionally_compatible")
            or bind.get("binding") == "BOUND"
        )
    except Exception:
        pass

    # Evidence validity (certificate / bootstrap)
    evidence_valid = False
    try:
        row = store.repo(repo)
        # Store.repo returns sqlite3.Row in production.  It is subscriptable
        # but has no dict.get(), so support both row shapes explicitly.
        if row is not None:
            try:
                bootstrap_status = row["bootstrap_status"]
            except (KeyError, IndexError, TypeError):
                bootstrap_status = row.get("bootstrap_status")
        else:
            bootstrap_status = None
        evidence_valid = bool(
            row
            and str(bootstrap_status or "").lower()
            in {"verified", "ready", "ok"}
        )
    except Exception:
        pass

    # Witness availability (presence only)
    witness_available = False
    try:
        w = store.db.execute(
            "SELECT 1 FROM witness_commitments LIMIT 1"
        ).fetchone()
        witness_available = w is not None
    except Exception:
        pass

    frames_seen = int((warmup or {}).get("baseline_frames_seen") or 0)
    field_ready = bool((warmup or {}).get("baseline_ready"))

    z = {
        "C": c_t,
        "N": n_t,
        "I": i_t,
        "L": l_t,
        "D": d_t,
        "H": h_t,
        "G": g_t,
        "Q": q_t,
        "eta_E": eta_e,
        "eta_M": eta_m,
        "T": t_t,
        "delta_E": delta_e,
        "U": u_t,
    }

    # Fill nulls with neutral 0.5 for vector math only when component unknown
    # but track missing set for classification honesty
    missing = [k for k in Z_KEYS if z.get(k) is None]
    z_vec = [float(z[k]) if z.get(k) is not None else 0.5 for k in Z_KEYS]

    gates = ObserverGates(
        baseline_warm=field_ready and frames_seen >= BASELINE_MIN,
        epoch_current=epoch_current,
        phase_bound=phase_bound,
        evidence_valid=evidence_valid,
        witness_available=witness_available,
        field_frames_ready=field_ready,
    )

    # Field health F_t = GM(C, N, Q, 1-D, 1-U) — use available only
    f_parts: list[float] = []
    if c_t is not None:
        f_parts.append(c_t)
    if n_t is not None:
        f_parts.append(n_t)
    if q_t is not None:
        f_parts.append(q_t)
    if d_t is not None:
        f_parts.append(max(EPS, 1.0 - d_t))  # overbind penalty when D low? Spec: 1-D_t
        # Spec says GM(C, N, Q, 1-D, 1-U) — high D (differentiated) → 1-D low.
        # Re-read: "1-D_t" in the GM with note one collapsed channel lowers field.
        # Actually for differentiation, higher D is better for coherent regime.
        # Spec explicitly: F = GM(C, N, Q, 1-D, 1-U).
        # That would penalize high differentiation. Maybe they mean 1 - common_mode?
        # Follow spec literally: 1-D_t
    if u_t is not None:
        f_parts.append(max(EPS, 1.0 - u_t))

    # Re-interpret for health: use differentiation as positive contribution.
    # Spec wrote 1-D_t; for engineering health we use max(D, eps) as diversity term
    # and document both. Prefer diversity term D (higher better) as F_diversity.
    f_health_parts = []
    if c_t is not None:
        f_health_parts.append(c_t)
    if n_t is not None:
        f_health_parts.append(n_t)
    elif True:
        pass
    if q_t is not None:
        f_health_parts.append(q_t)
    # Use D as positive diversity (documented deviation: health needs differentiation)
    if d_t is not None:
        f_health_parts.append(max(EPS, d_t))
    if u_t is not None:
        f_health_parts.append(max(EPS, 1.0 - u_t))
    # Also compute literal F_spec for audit
    f_spec_parts = []
    if c_t is not None:
        f_spec_parts.append(c_t)
    if n_t is not None:
        f_spec_parts.append(n_t)
    if q_t is not None:
        f_spec_parts.append(q_t)
    if d_t is not None:
        f_spec_parts.append(max(EPS, 1.0 - d_t))
    if u_t is not None:
        f_spec_parts.append(max(EPS, 1.0 - u_t))

    f_t = geometric_mean(f_health_parts)
    f_spec = geometric_mean(f_spec_parts)

    spectral_mass = None
    try:
        from .kernels import kernels_status

        ks = kernels_status(store, repo)
        spectral_mass = (ks or {}).get("retention") or (ks or {}).get("profile")
    except Exception:
        spectral_mass = None

    return {
        "z": z,
        "z_vector": z_vec,
        "z_keys": list(Z_KEYS),
        "missing_components": missing,
        "F_t": f_t,
        "F_spec_literal": f_spec,
        "gates": gates.to_dict(),
        "coherence_score": c_t,
        "frame_id": (latest_frame or {}).get("frame_id") if latest_frame else None,
        "frame_classification": (latest_frame or {}).get("classification")
        if latest_frame
        else None,
        "frame_measurement_basis": (latest_frame or {}).get(
            "measurement_basis", "direct_snapshot"
        ),
        "frame_policy_eligible": bool(
            (latest_frame or {}).get("policy_eligible", True)
        ),
        "frame_baseline_eligible": bool(
            (latest_frame or {}).get("baseline_eligible", True)
        ),
        "field_warmup": warmup,
        "spectral_mass": spectral_mass,
        "temporal_field_panel": {
            "baseline_frames_display": (fr or {}).get("baseline_frames_display"),
            "live_buffer_samples": (fr or {}).get("live_buffer_samples"),
            "latest": bool(latest_frame),
            "measurement_basis": (latest_frame or {}).get(
                "measurement_basis", "direct_snapshot"
            ),
            "policy_eligible": bool(
                (latest_frame or {}).get("policy_eligible", True)
            ),
            "baseline_eligible": bool(
                (latest_frame or {}).get("baseline_eligible", True)
            ),
            "advisory_only": True,
        },
        "sampled_at": time.time(),
        "claim_boundary": CLAIM,
    }


def _load_state(store: Any, repo: str) -> dict[str, Any]:
    return dict(store.get_setting(_state_key(repo), {}) or {})


def _save_state(store: Any, repo: str, state: dict[str, Any]) -> None:
    store.set_setting(_state_key(repo), state)


def update_baseline(
    state: dict[str, Any],
    z_vec: list[float],
    *,
    alpha: float = ALPHA_DEFAULT,
    sealed: bool = False,
) -> dict[str, Any]:
    """EMA baseline μ and diagonal covariance estimate (ridge-ready)."""
    mu = state.get("mu")
    if not mu or len(mu) != len(z_vec):
        mu = list(z_vec)
    else:
        mu = [
            (1.0 - alpha) * float(mu[i]) + alpha * float(z_vec[i])
            for i in range(len(z_vec))
        ]
    # diagonal variance EMA
    var = state.get("var")
    if not var or len(var) != len(z_vec):
        var = [0.05] * len(z_vec)
    else:
        var = [
            (1.0 - alpha) * float(var[i])
            + alpha * (float(z_vec[i]) - float(mu[i])) ** 2
            for i in range(len(z_vec))
        ]
    n = int(state.get("n_updates") or 0) + 1
    hist = list(state.get("z_history") or [])
    hist.append({"z": list(z_vec), "at": time.time()})
    hist = hist[-HISTORY_CAP:]
    out = {
        "mu": mu,
        "var": var,
        "n_updates": n,
        "z_history": hist,
        "alpha": alpha,
        "sealed": bool(sealed or state.get("sealed")),
        "updated_at": time.time(),
    }
    return out


def residual_mahalanobis(
    z_vec: list[float],
    mu: list[float],
    var: list[float],
    *,
    ridge: float = LAMBDA_RIDGE,
    valid_indices: list[int] | None = None,
) -> float | None:
    """r_t = sqrt( (z-μ)^T (diag(var)+λI)^{-1} (z-μ) ) — diagonal Mahalanobis."""
    indices = (
        range(len(z_vec))
        if valid_indices is None
        else [index for index in valid_indices if 0 <= index < len(z_vec)]
    )
    if not indices:
        return None
    s = 0.0
    for i in indices:
        d = float(z_vec[i]) - float(mu[i])
        s += (d * d) / (float(var[i]) + ridge)
    return math.sqrt(max(0.0, s))


def classify_self_sense(
    *,
    gates: dict[str, Any],
    residual: float | None,
    f_t: float | None,
    missing: list[str],
    baseline_n: int,
) -> tuple[str, list[str]]:
    """Deterministic classification with hard unbound rule."""
    reasons: list[str] = []

    # Hard: missing epoch/phase binding → never healthy
    if not gates.get("epoch_current") or not gates.get("phase_bound"):
        reasons.append("epoch_or_phase_unbound")
        return SelfSenseClass.UNBOUND.value, reasons

    if baseline_n < BASELINE_MIN or not gates.get("baseline_warm"):
        reasons.append("baseline_cold")
        return SelfSenseClass.COLD.value, reasons

    if residual is None or f_t is None:
        reasons.append("metrics_unavailable")
        return SelfSenseClass.INDETERMINATE.value, reasons

    # thresholds engineering defaults
    if residual >= 3.5 or (f_t is not None and f_t < 0.35):
        reasons.append("high_residual_or_low_F")
        return SelfSenseClass.STRESSED.value, reasons
    if residual >= 2.0:
        reasons.append("elevated_residual")
        return SelfSenseClass.DRIFT.value, reasons
    if len(missing) > 6:
        reasons.append("many_missing_components")
        return SelfSenseClass.INDETERMINATE.value, reasons

    reasons.append("within_verified_regime")
    return SelfSenseClass.NOMINAL.value, reasons


def observe_self_sensing(
    store: Any,
    repo: str,
    *,
    home: Any | None = None,
    coherence_report: dict[str, Any] | None = None,
    update: bool = True,
    alpha: float = ALPHA_DEFAULT,
    persist: bool = True,
) -> dict[str, Any]:
    """Sample and classify against the prior baseline, then learn if trustworthy."""
    sample = sample_observer_state(
        store, repo, coherence_report=coherence_report, home=home
    )
    z_vec = list(sample["z_vector"])
    gates = sample["gates"]
    prior_state = _load_state(store, repo)
    prior_mu = prior_state.get("mu") or list(z_vec)
    prior_var = prior_state.get("var") or [0.05] * len(z_vec)
    prior_n = int(prior_state.get("n_updates") or 0)

    # Truth-recovery invariant: the current sample cannot move its own reference.
    missing_components = set(sample.get("missing_components") or [])
    valid_indices = [
        index for index, key in enumerate(Z_KEYS) if key not in missing_components
    ]
    residual = residual_mahalanobis(
        z_vec,
        prior_mu,
        prior_var,
        valid_indices=valid_indices,
    )
    # normalize residual display to softer scale (not authority)
    residual_norm = (
        _clip01(residual / 6.0) if residual is not None else None
    )  # ~6 ≈ high multi-dim distance

    classification, reasons = classify_self_sense(
        gates=gates,
        residual=residual,
        f_t=sample.get("F_t"),
        missing=sample.get("missing_components") or [],
        baseline_n=prior_n,
    )

    # Force: no false healthy when unbound
    if classification == SelfSenseClass.NOMINAL.value and not (
        gates.get("epoch_current") and gates.get("phase_bound")
    ):
        classification = SelfSenseClass.UNBOUND.value
        reasons = ["forced_unbound_no_false_healthy"]

    stable_frame_classes = {"QUIESCENT", "COHERENT_DIFFERENTIATED"}
    frame_class = str(sample.get("frame_classification") or "")
    # Cold-start (n < BASELINE_MIN): accumulate EMA whenever hard identity gates
    # pass. Do NOT require:
    #   - field 16/16 (bootstrap path warms observer before resonant frames), or
    #   - QUIESCENT/COHERENT frames (INDETERMINATE is common during field warm).
    # After warm, keep strict stable-frame + NOMINAL discipline so stressed or
    # indeterminate regimes cannot quietly rewrite the baseline.
    cold_start = prior_n < BASELINE_MIN
    update_reasons: list[str] = []
    if not update:
        update_reasons.append("update_not_requested")
    if not gates.get("epoch_current"):
        update_reasons.append("epoch_not_current")
    if not gates.get("phase_bound"):
        update_reasons.append("phase_not_bound")
    if not gates.get("evidence_valid"):
        update_reasons.append("evidence_invalid")
    if not sample.get("frame_baseline_eligible", True):
        update_reasons.append("measurement_not_baseline_eligible")
    if not cold_start:
        if frame_class and frame_class not in stable_frame_classes:
            update_reasons.append(f"frame_{frame_class.lower()}_not_stable")
        if classification != SelfSenseClass.NOMINAL.value:
            update_reasons.append(f"sense_{classification.lower()}_not_nominal")

    may_update = not update_reasons
    state = prior_state
    if may_update:
        state = update_baseline(prior_state, z_vec, alpha=alpha)
        if persist:
            _save_state(store, repo, state)

    n_updates = int(state.get("n_updates") or 0)
    advisory = _advisory_for(classification, gates, residual, sample.get("F_t"))

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "classification": classification,
        "reasons": reasons,
        "z": sample["z"],
        "z_vector": z_vec,
        "z_keys": list(Z_KEYS),
        "missing_components": sample.get("missing_components"),
        "mu": prior_mu,
        # Preserve the legacy name while stating the scientific meaning: this
        # is distance from the prior regime, not a directional health score.
        "residual_r": round(residual, 6) if residual is not None else None,
        "regime_deviation_r": round(residual, 6) if residual is not None else None,
        "residual_axes": [Z_KEYS[index] for index in valid_indices],
        "residual_excluded_components": sorted(missing_components),
        "residual_norm": residual_norm,
        "F_t": sample.get("F_t"),
        "F_spec_literal": sample.get("F_spec_literal"),
        "gates": gates,
        "gates_hard_pass": bool(
            gates.get("baseline_warm")
            and gates.get("epoch_current")
            and gates.get("phase_bound")
            and gates.get("evidence_valid")
        ),
        "baseline_n_updates": n_updates,
        "baseline_reference_n": prior_n,
        "classified_before_update": True,
        "baseline_ready_observer": n_updates >= BASELINE_MIN,
        "field_warmup": sample.get("field_warmup"),
        "temporal_field_panel": sample.get("temporal_field_panel"),
        "frame_id": sample.get("frame_id"),
        "frame_classification": sample.get("frame_classification"),
        "frame_measurement_basis": sample.get("frame_measurement_basis"),
        "frame_policy_eligible": sample.get("frame_policy_eligible"),
        "frame_baseline_eligible": sample.get("frame_baseline_eligible"),
        "coherence_score": sample.get("coherence_score"),
        "spectral_mass": sample.get("spectral_mass"),
        "advisory": advisory,
        "advisory_only": True,
        "baseline_updated": may_update,
        "baseline_update_decision": {
            "eligible": may_update,
            "reasons": update_reasons or ["prior_regime_eligible"],
        },
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "sampled_at": sample.get("sampled_at"),
    }

    # receipt hash over observation (not authority)
    material = {
        k: report[k]
        for k in (
            "repo",
            "classification",
            "reasons",
            "z_vector",
            "residual_r",
            "F_t",
            "gates",
            "baseline_n_updates",
            "version",
        )
    }
    report["observation_hash"] = _sha(material)
    report["observation_id"] = f"sense_{report['observation_hash'][:20]}"

    if persist:
        store.set_setting(_latest_key(repo), report)
        # Legacy alias so older cadence readers stay continuous.
        store.set_setting(f"self_sense_latest:{repo}", report)
        idx = list(store.get_setting(_index_key(repo), []) or [])
        idx.append(report["observation_id"])
        store.set_setting(_index_key(repo), idx[-HISTORY_CAP:])

    return report


def _advisory_for(
    classification: str,
    gates: dict[str, Any],
    residual: float | None,
    f_t: float | None,
) -> dict[str, Any]:
    recs: list[str] = []
    if classification == SelfSenseClass.UNBOUND.value:
        recs.append("run: cortex realign diagnose --repo <R>")
        recs.append("if drift: cortex realign apply --repo <R> --i-authorize-realign")
    if classification == SelfSenseClass.COLD.value:
        recs.append("warm Resonant Frames: activate/fuse/field close until 16/16")
        recs.append("or: cortex realign warm --repo <R> --warm-ticks 3")
    if classification == SelfSenseClass.DRIFT.value:
        recs.append("review residual channels; request counterevidence; no auto-promote")
    if classification == SelfSenseClass.STRESSED.value:
        recs.append("operator review required; freeze promotions; check epoch and evidence")
    if classification == SelfSenseClass.NOMINAL.value:
        recs.append("continue normal advisory loop; constitutional gates still control")
    return {
        "classification": classification,
        "recommendations": recs,
        "request_operator_review": classification
        in {
            SelfSenseClass.STRESSED.value,
            SelfSenseClass.UNBOUND.value,
            SelfSenseClass.DRIFT.value,
        },
        "residual_r": residual,
        "F_t": f_t,
        "advisory_only": True,
    }


def self_sensing_report(store: Any, repo: str) -> dict[str, Any]:
    latest = store.get_setting(_latest_key(repo))
    state = _load_state(store, repo)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "latest": latest,
        "baseline_n_updates": int(state.get("n_updates") or 0),
        "baseline_display": f"{min(int(state.get('n_updates') or 0), BASELINE_MIN)}/{BASELINE_MIN}",
        "claim_boundary": CLAIM,
        "canonical_statement": CANONICAL,
        "advisory_only": True,
    }


def self_sensing_trace(store: Any, repo: str, *, limit: int = 16) -> list[dict[str, Any]]:
    # history embedded in state
    state = _load_state(store, repo)
    hist = list(state.get("z_history") or [])
    return hist[-limit:]


def verify_observation_replay(
    store: Any,
    repo: str,
    *,
    home: Any | None = None,
) -> dict[str, Any]:
    """Replay observe twice without baseline update — classification must match."""
    a = observe_self_sensing(
        store, repo, home=home, update=False, persist=False
    )
    b = observe_self_sensing(
        store, repo, home=home, update=False, persist=False
    )
    # drop timestamps for compare
    def slim(r: dict[str, Any]) -> dict[str, Any]:
        return {
            "classification": r.get("classification"),
            "reasons": r.get("reasons"),
            "z_vector": r.get("z_vector"),
            "residual_r": r.get("residual_r"),
            "F_t": r.get("F_t"),
            "gates": r.get("gates"),
        }

    sa, sb = slim(a), slim(b)
    match = sa == sb
    return {
        "ok": match,
        "stable_across_replay": match,
        "first": sa,
        "second": sb,
        "claim_boundary": CLAIM,
    }


def milestone_holdout_check(store: Any, repo: str) -> dict[str, Any]:
    """First milestone checklist (report only)."""
    state = _load_state(store, repo)
    n = int(state.get("n_updates") or 0)
    latest = store.get_setting(_latest_key(repo)) or {}
    gates = latest.get("gates") or {}
    try:
        from .resonant_frame import field_report

        fr = field_report(store, repo)
        warm = fr.get("baseline_warmup") or {}
    except Exception:
        warm = {}
        fr = {}

    checks = {
        "baseline_16": n >= BASELINE_MIN or bool(warm.get("baseline_ready")),
        "channel_baselines_ge_3": int(warm.get("baseline_channels_warm") or 0) >= CHANNEL_MIN,
        "replay_stable": None,  # filled if called with verify
        "no_false_healthy_when_unbound": not (
            latest.get("classification") == SelfSenseClass.NOMINAL.value
            and not (gates.get("epoch_current") and gates.get("phase_bound"))
        ),
        "advisory_only": latest.get("advisory_only", True) is True,
    }
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "milestone": "warm_16_and_stable_classification",
        "checks": checks,
        "pass": all(v is not False for v in checks.values()),
        "baseline_display": f"{min(n, BASELINE_MIN)}/{BASELINE_MIN}",
        "field_frames_display": warm.get("baseline_frames_display"),
        "latest_classification": latest.get("classification"),
        "claim_boundary": CLAIM,
    }
