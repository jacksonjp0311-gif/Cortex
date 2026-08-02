"""v7.7 Binding Field — composite field from live interconnect + buffer + sense.

Named from live evidence:
  - Local spectral/graph coupling can be high while epoch binding lags (UNBOUND).
  - Resonant Frame live buffer can hold samples without closed frames (BUFFER_PENDING).
  - Until both binding and frames warm, self-sensing must not report healthy.

The Binding Field measures and classifies that gap. It does not close it silently.

May: measure, classify, recommend, optionally commit buffer (frame close only).
Never: host mutation, silent epoch seal, constitutional bits, capability, promote,
       consciousness claims.
"""

from __future__ import annotations

import hashlib
import json
import time
from enum import Enum
from typing import Any

from . import __version__

SCHEMA = "cortex-binding-field/1.0"
GLYPH = "◈⧉"
RECEIPT_SCHEMA = "cortex-binding-field-receipt/1.0"

CLAIM = (
    "Binding Field is a composite advisory field over constitutional binding, "
    "temporal buffer closure, spectral mass balance, and self-sensing residual. "
    "It explains the gap between local coupling and global readiness. "
    "It does not grant authority, seal epochs silently, mutate host source, "
    "or establish consciousness."
)

CANONICAL = (
    "Local coherence without epoch binding is not a verified regime. "
    "Open buffer samples without closed frames are not a warm temporal field. "
    "The Binding Field names that structure — it does not override constitutional gates."
)

# Live body taught us these regimes
class BindingClass(str, Enum):
    BINDING_GAP = "BINDING_GAP"  # epoch/phase unbound — primary live pattern
    BUFFER_PENDING = "BUFFER_PENDING"  # samples in buffer, no closed frames
    COLD_FIELD = "COLD_FIELD"  # closed frames / baselines short
    TRANSITION_REGIME = "TRANSITION_REGIME"  # warm+bound, temporal transition
    DRIFT_REGIME = "DRIFT_REGIME"  # warm+bound, observer drift/stress
    IMMUNE_HOLD = "IMMUNE_HOLD"  # immune block on mutation plane (expected)
    VERIFIED_REGIME = "VERIFIED_REGIME"  # warm + bound + replay-ok path
    INDETERMINATE = "INDETERMINATE"


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _latest_key(repo: str) -> str:
    return f"binding_field_latest:{repo}"


def sample_binding_field(store: Any, repo: str, *, home: Any | None = None) -> dict[str, Any]:
    """Compose binding field from existing surfaces (observe-heavy)."""
    from .realign import diagnose_realign
    from .resonant_frame import W_MIN, field_report, load_field_state
    from .self_sensing import observe_self_sensing

    diag = diagnose_realign(store, repo)
    field = field_report(store, repo)
    state = load_field_state(store, repo)
    buffer = list(state.get("buffer") or [])
    buffer_n = len(buffer)
    # unique ticks in buffer
    ticks = sorted({int(s.get("tick") or 0) for s in buffer if isinstance(s, dict)})
    buffer_ticks = len(ticks)

    sense = observe_self_sensing(
        store, repo, home=home, update=False, persist=False
    )

    warm = field.get("baseline_warmup") or {}
    frames_seen = int(warm.get("baseline_frames_seen") or 0)
    channels_warm = int(warm.get("baseline_channels_warm") or 0)
    field_ready = bool(warm.get("baseline_ready"))

    # Spectral mass (bimodal integrate/retain)
    spectral = {"dominant": None, "integrate_share": None, "retain_share": None, "reset_share": None}
    try:
        from .kernels import kernels_status

        ks = kernels_status(store, repo) or {}
        ret = ks.get("retention") or {}
        spectral["dominant"] = ks.get("dominant") or (ks.get("profile") or {}).get("dominant")
        for name in ("integrate", "retain", "reset"):
            block = ret.get(name) if isinstance(ret, dict) else None
            if isinstance(block, dict) and "share" in block:
                spectral[f"{name}_share"] = block.get("share")
    except Exception as exc:
        spectral["error"] = f"{type(exc).__name__}:{exc}"

    # Immune hold (mutation plane) — expected recommend-only posture
    immune_block = False
    immune_code = None
    try:
        from .immunity import immunity_status

        imm = immunity_status(store, repo) or {}
        immune_block = bool(imm.get("block") or imm.get("host_mutate_forbidden"))
        immune_code = imm.get("code") or (imm.get("action") or {}).get("code")
    except Exception:
        immune_block = True  # fail closed on mutation narrative
        immune_code = "unknown"

    # Graph mass (local coupling proxy)
    graph = {"nodes": 0, "synapses": 0}
    try:
        graph["nodes"] = store.db.execute(
            "SELECT COUNT(*) AS c FROM neural_nodes WHERE repo=?", (repo,)
        ).fetchone()["c"]
        graph["synapses"] = store.db.execute(
            "SELECT COUNT(*) AS c FROM neural_synapses WHERE repo=?", (repo,)
        ).fetchone()["c"]
    except Exception:
        pass

    epoch = diag.get("epoch") or {}
    needs_realign = bool(diag.get("needs_realign"))
    epoch_current = bool(epoch.get("verified")) and not needs_realign
    phase_bound = bool((sense.get("gates") or {}).get("phase_bound"))
    sense_class = sense.get("classification")
    coherence = sense.get("coherence_score")
    residual = sense.get("residual_r")
    f_t = sense.get("F_t")

    # Field vector components (all in [0,1] or null)
    def clip(x: Any) -> float | None:
        if x is None:
            return None
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(1.0, v))

    integrate_s = clip(spectral.get("integrate_share"))
    retain_s = clip(spectral.get("retain_share"))
    # bimodality score: both integrate and retain material, reset low
    bimodal = None
    if integrate_s is not None and retain_s is not None:
        # healthy live pattern ~0.5/0.5; score high when both present
        bimodal = min(integrate_s, retain_s) * 2.0  # peaks at 0.5/0.5 → 1.0
        bimodal = max(0.0, min(1.0, bimodal))

    buffer_fill = clip(buffer_ticks / max(1, W_MIN)) if buffer_ticks else 0.0
    frame_warm = clip(frames_seen / 16.0)
    binding_ok = 1.0 if (epoch_current and phase_bound) else 0.0
    sense_ok = 1.0 if sense_class == "NOMINAL" else (
        0.5 if sense_class in {"COLD", "INDETERMINATE", "DRIFT"} else 0.0
    )

    field_vec = {
        "binding_ok": binding_ok,
        "buffer_fill": buffer_fill,
        "frame_warm": frame_warm,
        "channels_warm_frac": clip(channels_warm / 3.0) if channels_warm else 0.0,
        "coherence": clip(coherence),
        "F_t": clip(f_t),
        "residual_norm": clip((residual or 0) / 6.0) if residual is not None else None,
        "spectral_bimodal": bimodal,
        "integrate_share": integrate_s,
        "retain_share": retain_s,
        "sense_ok": sense_ok,
        "delta_E": 0.0 if epoch_current else 1.0,
    }

    classification, reasons = classify_binding_field(
        needs_realign=needs_realign,
        epoch_current=epoch_current,
        phase_bound=phase_bound,
        buffer_ticks=buffer_ticks,
        frames_seen=frames_seen,
        field_ready=field_ready,
        sense_class=str(sense_class or ""),
        latest_frame_class=str(field.get("last_classification") or ""),
        immune_block=immune_block,
        w_min=W_MIN,
    )

    advisory = advisory_for_binding(
        classification,
        repo=repo,
        buffer_ticks=buffer_ticks,
        frames_seen=frames_seen,
        needs_realign=needs_realign,
    )

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "classification": classification,
        "reasons": reasons,
        "field_vector": field_vec,
        "signals": {
            "needs_realign": needs_realign,
            "epoch": {
                "verified": epoch.get("verified"),
                "stale": epoch.get("stale"),
                "sealed_cortex_version": epoch.get("sealed_cortex_version"),
                "mismatches": epoch.get("mismatches"),
            },
            "phase_bound": phase_bound,
            "live_buffer_samples": buffer_n,
            "live_buffer_ticks": buffer_ticks,
            "w_min": W_MIN,
            "field_frames_display": field.get("baseline_frames_display"),
            "channels_warm": channels_warm,
            "last_frame_classification": field.get("last_classification"),
            "sense_classification": sense_class,
            "coherence_score": coherence,
            "residual_r": residual,
            "F_t": f_t,
            "spectral": spectral,
            "graph": graph,
            "immune": {"block": immune_block, "code": immune_code},
        },
        "advisory": advisory,
        "advisory_only": True,
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "live_reading": (
            "Local coupling may be active while constitutional binding lags; "
            "buffer samples without closed frames leave the temporal field cold."
        ),
        "sampled_at": time.time(),
    }
    material = {
        k: report[k]
        for k in (
            "repo",
            "classification",
            "reasons",
            "field_vector",
            "version",
        )
    }
    report["observation_hash"] = _sha(material)
    report["observation_id"] = f"bind_{report['observation_hash'][:20]}"
    return report


def classify_binding_field(
    *,
    needs_realign: bool,
    epoch_current: bool,
    phase_bound: bool,
    buffer_ticks: int,
    frames_seen: int,
    field_ready: bool,
    sense_class: str,
    latest_frame_class: str = "",
    immune_block: bool,
    w_min: int = 8,
) -> tuple[str, list[str]]:
    """Priority order from live interconnect lessons."""
    reasons: list[str] = []

    # 1) Binding gap dominates — never call verified
    if needs_realign or not epoch_current or not phase_bound:
        reasons.append("epoch_or_phase_unbound")
        if needs_realign:
            reasons.append("needs_realign")
        return BindingClass.BINDING_GAP.value, reasons

    # 2) Buffer has enough ticks but no closed frames yet
    if buffer_ticks >= w_min and frames_seen == 0 and not field_ready:
        reasons.append("live_buffer_ge_W_min_no_closed_frames")
        return BindingClass.BUFFER_PENDING.value, reasons

    if buffer_ticks > 0 and frames_seen == 0 and not field_ready:
        reasons.append("open_buffer_without_closed_frames")
        return BindingClass.BUFFER_PENDING.value, reasons

    # 3) Cold field / cold observer
    if frames_seen < 16 and not field_ready:
        reasons.append("field_baseline_cold")
        return BindingClass.COLD_FIELD.value, reasons

    if sense_class in {"COLD", "UNBOUND"}:
        reasons.append(f"sense_{sense_class.lower()}")
        if sense_class == "UNBOUND":
            return BindingClass.BINDING_GAP.value, reasons
        return BindingClass.COLD_FIELD.value, reasons

    # 4) Warm and bound is necessary but not sufficient for verified.
    if latest_frame_class == "TRANSITION":
        reasons.append("latest_frame_transition")
        return BindingClass.TRANSITION_REGIME.value, reasons

    if sense_class in {"DRIFT", "STRESSED"}:
        reasons.append(f"sense_{sense_class.lower()}")
        return BindingClass.DRIFT_REGIME.value, reasons

    # 5) Verified path requires both a nominal observer and a stable frame.
    if (
        epoch_current
        and phase_bound
        and (field_ready or frames_seen >= 16)
        and sense_class == "NOMINAL"
        and latest_frame_class in {"QUIESCENT", "COHERENT_DIFFERENTIATED"}
    ):
        reasons.append("bound_and_warm")
        return BindingClass.VERIFIED_REGIME.value, reasons

    # Immune hold is informational, not a primary class if bound+warm
    if immune_block:
        reasons.append("immune_mutation_plane_held")  # expected

    return BindingClass.INDETERMINATE.value, reasons or ["no_rule_matched"]


def advisory_for_binding(
    classification: str,
    *,
    repo: str,
    buffer_ticks: int,
    frames_seen: int,
    needs_realign: bool,
) -> dict[str, Any]:
    recs: list[str] = []
    if classification == BindingClass.BINDING_GAP.value:
        recs.append(f"python -m cortex realign diagnose --repo {repo}")
        recs.append(
            f"python -m cortex warm-in run --repo {repo} --i-authorize-realign"
        )
    if classification == BindingClass.BUFFER_PENDING.value:
        recs.append(f"python -m cortex binding-field commit --repo {repo}")
        recs.append(
            f"# closes live buffer ({buffer_ticks} ticks) into a Resonant Frame — no epoch seal"
        )
    if classification == BindingClass.COLD_FIELD.value:
        recs.append(f"python -m cortex warm-in run --repo {repo} --rounds 4")
        recs.append(f"python -m cortex sense observe --repo {repo}")
    if classification == BindingClass.VERIFIED_REGIME.value:
        recs.append("continue advisory loop; constitutional gates still control")
    if classification == BindingClass.TRANSITION_REGIME.value:
        recs.append("hold baseline learning and observe the next measured frame")
    if classification == BindingClass.DRIFT_REGIME.value:
        recs.append("inspect residual contributors before accepting a new regime")
    if classification == BindingClass.IMMUNE_HOLD.value:
        recs.append("immune hold is expected (recommend-only); not a defect")

    return {
        "classification": classification,
        "recommendations": recs,
        "request_operator_review": classification
        in {
            BindingClass.BINDING_GAP.value,
            BindingClass.BUFFER_PENDING.value,
            BindingClass.TRANSITION_REGIME.value,
            BindingClass.DRIFT_REGIME.value,
        },
        "frames_seen": frames_seen,
        "buffer_ticks": buffer_ticks,
        "needs_realign": needs_realign,
        "advisory_only": True,
    }


def observe_binding_field(
    store: Any,
    repo: str,
    *,
    home: Any | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    report = sample_binding_field(store, repo, home=home)
    if persist:
        store.set_setting(_latest_key(repo), report)
    return report


def commit_live_buffer(store: Any, repo: str) -> dict[str, Any]:
    """Close Resonant Frame buffer only — never seals epoch."""
    from .resonant_frame import field_close, field_report, load_field_state

    state = load_field_state(store, repo)
    buffer = state.get("buffer") or []
    if not buffer:
        return {
            "ok": True,
            "closed": False,
            "reason": "empty_buffer",
            "claim_boundary": CLAIM,
        }
    result = field_close(store, repo)
    # re-observe binding field after close
    after = observe_binding_field(store, repo, persist=True)
    fr = field_report(store, repo)
    return {
        "ok": bool(result.get("ok", True)),
        "closed": bool(result.get("closed")),
        "field_close": {
            "reason": result.get("reason"),
            "frame_id": (result.get("frame") or {}).get("frame_id")
            if isinstance(result.get("frame"), dict)
            else None,
        },
        "binding_after": {
            "classification": after.get("classification"),
            "field_frames_display": fr.get("baseline_frames_display"),
            "last_classification": fr.get("last_classification"),
        },
        "note": "Buffer commit closes a frame only; does not seal body epoch.",
        "claim_boundary": CLAIM,
    }


def latest_binding_field(store: Any, repo: str) -> dict[str, Any] | None:
    return store.get_setting(_latest_key(repo))
