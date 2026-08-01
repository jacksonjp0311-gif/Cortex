"""v7.3 Resonant Frames — typed channel set and FieldSample contracts.

Bounded K (6–12). Paths/nodes are metadata contributors, not channels.
Reliability never elevates unverified truth into evidence gates.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any


class ChannelTruthSource(str, Enum):
    MEASURED = "MEASURED"
    RECEIPT_VERIFIED = "RECEIPT_VERIFIED"
    OPERATOR_ASSERTED = "OPERATOR_ASSERTED"
    SIMULATED = "SIMULATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


VERIFIED_EVIDENCE_TRUTH = frozenset(
    {
        ChannelTruthSource.MEASURED,
        ChannelTruthSource.RECEIPT_VERIFIED,
        "MEASURED",
        "RECEIPT_VERIFIED",
    }
)

# Canonical families (K default = 11, within 6–12)
CHANNEL_FAMILIES: tuple[str, ...] = (
    "E_HOST",
    "E_RUNTIME",
    "S_STRUCTURE",
    "M_CONSOLIDATED",
    "M_LEARNED",
    "M_FEDERATED",
    "T_TASK",
    "G_GOVERNOR",
    "C_CONSTITUTIONAL",
    "W_WITNESS",
    "O_OPERATIONS",
)

EVIDENCE_FAMILIES = frozenset({"E_HOST", "E_RUNTIME"})
MEMORY_FAMILIES = frozenset({"M_CONSOLIDATED", "M_LEARNED", "M_FEDERATED"})

K_MIN = 6
K_MAX = 12
K_DEFAULT = len(CHANNEL_FAMILIES)

CLAIM_BOUNDARY = (
    "Field channels are typed activity traces for Resonant Frame telemetry. "
    "They do not grant authority, witness, epoch seal, or host mutation rights. "
    "Only MEASURED and RECEIPT_VERIFIED may count as verified external evidence."
)


def is_verified_evidence_truth(source: Any) -> bool:
    if isinstance(source, ChannelTruthSource):
        return source in (
            ChannelTruthSource.MEASURED,
            ChannelTruthSource.RECEIPT_VERIFIED,
        )
    return str(source or "").upper() in {"MEASURED", "RECEIPT_VERIFIED"}


def clip01(x: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def normalize_truth(source: Any) -> str:
    if isinstance(source, ChannelTruthSource):
        return source.value
    s = str(source or "UNKNOWN").upper().strip()
    try:
        return ChannelTruthSource[s].value
    except KeyError:
        for member in ChannelTruthSource:
            if member.value == s:
                return member.value
        return ChannelTruthSource.UNKNOWN.value


@dataclass(frozen=True)
class FieldSample:
    repo: str
    body_epoch_id: str
    tick: int
    timestamp: float
    channel_id: str
    channel_family: str
    activity: float
    reliability: float
    truth_source: str
    event_key: str = "default"
    source_ids: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    constitutional_bits: tuple[int, ...] = ()
    governor_mode: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "activity", clip01(self.activity))
        object.__setattr__(self, "reliability", clip01(self.reliability))
        object.__setattr__(self, "truth_source", normalize_truth(self.truth_source))
        object.__setattr__(self, "channel_family", str(self.channel_family or self.channel_id))
        object.__setattr__(self, "event_key", str(self.event_key or "default")[:128])

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_ids"] = list(self.source_ids)
        d["paths"] = list(self.paths)
        d["constitutional_bits"] = list(self.constitutional_bits)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldSample:
        return cls(
            repo=str(data.get("repo") or ""),
            body_epoch_id=str(data.get("body_epoch_id") or ""),
            tick=int(data.get("tick") or 0),
            timestamp=float(data.get("timestamp") or 0.0),
            channel_id=str(data.get("channel_id") or data.get("channel_family") or ""),
            channel_family=str(data.get("channel_family") or data.get("channel_id") or ""),
            activity=clip01(data.get("activity", 0.0)),
            reliability=clip01(data.get("reliability", 0.0)),
            truth_source=normalize_truth(data.get("truth_source")),
            event_key=str(data.get("event_key") or "default"),
            source_ids=tuple(data.get("source_ids") or ()),
            paths=tuple(data.get("paths") or ()),
            constitutional_bits=tuple(int(x) for x in (data.get("constitutional_bits") or ())),
            governor_mode=str(data.get("governor_mode") or "unknown"),
            metadata=dict(data.get("metadata") or {}),
        )

    @property
    def is_verified_evidence(self) -> bool:
        return (
            self.channel_family in EVIDENCE_FAMILIES
            and is_verified_evidence_truth(self.truth_source)
        )

    @property
    def is_memory(self) -> bool:
        return self.channel_family in MEMORY_FAMILIES


def default_channel_ids() -> list[str]:
    return list(CHANNEL_FAMILIES)


def assert_k_bounds(channel_ids: list[str] | tuple[str, ...]) -> None:
    k = len(channel_ids)
    if k < K_MIN or k > K_MAX:
        raise ValueError(f"channel count K={k} outside bounds [{K_MIN},{K_MAX}]")


def sample_tick_channels(
    *,
    repo: str,
    body_epoch_id: str,
    tick: int,
    activities: dict[str, float],
    reliabilities: dict[str, float] | None = None,
    truth_sources: dict[str, str] | None = None,
    event_keys: dict[str, str] | None = None,
    paths_by_channel: dict[str, list[str]] | None = None,
    constitutional_bits: tuple[int, ...] | list[int] = (),
    governor_mode: str = "unknown",
    timestamp: float | None = None,
    families: tuple[str, ...] | None = None,
) -> list[FieldSample]:
    """Build one tick of FieldSamples for the canonical (or provided) channel set."""
    fams = list(families or CHANNEL_FAMILIES)
    assert_k_bounds(fams)
    reliabilities = reliabilities or {}
    truth_sources = truth_sources or {}
    event_keys = event_keys or {}
    paths_by_channel = paths_by_channel or {}
    ts = float(timestamp if timestamp is not None else time.time())
    bits = tuple(int(b) for b in constitutional_bits)
    out: list[FieldSample] = []
    for fam in sorted(fams):  # deterministic order
        act = clip01(activities.get(fam, 0.0))
        rel = clip01(reliabilities.get(fam, 0.5 if act > 0 else 0.1))
        truth = normalize_truth(truth_sources.get(fam, ChannelTruthSource.UNKNOWN))
        out.append(
            FieldSample(
                repo=repo,
                body_epoch_id=body_epoch_id,
                tick=tick,
                timestamp=ts,
                channel_id=fam,
                channel_family=fam,
                activity=act,
                reliability=rel,
                truth_source=truth,
                event_key=str(event_keys.get(fam) or fam),
                paths=tuple(paths_by_channel.get(fam) or ()),
                constitutional_bits=bits,
                governor_mode=governor_mode,
            )
        )
    return out


def collect_activation_channels(
    store: Any,
    repo: str,
    *,
    tick: int = 0,
    task: str = "",
    activation: dict[str, Any] | None = None,
    governor_mode: str = "unknown",
    observation_id: str = "",
    observation_kind: str = "activation_boundary",
    observed_at: float | None = None,
) -> list[FieldSample]:
    """Cheap bounded sample from live Cortex surfaces (observation-only epoch)."""
    body_epoch_id = ""
    epoch_current = False
    bits: tuple[int, ...] = ()
    try:
        from .epoch import observe_current_epoch

        obs = observe_current_epoch(store, repo)
        body_epoch_id = str(obs.get("epoch_id") or obs.get("live_epoch_id") or "")
        epoch_current = bool(obs.get("verified") or obs.get("is_current"))
    except Exception:
        pass

    act = activation or {}
    ctx = act.get("context") if isinstance(act.get("context"), dict) else {}
    evidence = ctx.get("evidence") or act.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    e_paths = [
        str(e.get("path") or "")
        for e in evidence[:24]
        if isinstance(e, dict) and e.get("path")
    ]

    # Certificate / bootstrap
    cert_status = str(
        act.get("bootstrap_status")
        or (act.get("certificate") or {}).get("status")
        or ""
    ).lower()
    e_runtime = 0.7 if cert_status in {"verified", "ready"} else 0.25
    e_host = clip01(0.2 + 0.08 * min(10, len(e_paths)))

    # Structure / memory rough signals
    try:
        n_files = len(store.files(repo) or []) if hasattr(store, "files") else 0
    except Exception:
        n_files = 0
    s_struct = clip01(0.15 + min(0.7, n_files / 200.0))

    m_cons = 0.4
    m_learn = 0.25
    m_fed = 0.1
    try:
        from .memory_simplex import simplex_state

        sx = simplex_state(store, repo) if callable(simplex_state) else {}
        if isinstance(sx, dict):
            m_cons = clip01(float(sx.get("consolidated") or sx.get("score") or m_cons))
    except Exception:
        pass

    t_task = clip01(0.35 + (0.4 if task else 0.0))
    g_gov = 0.55
    if governor_mode == "normal":
        g_gov = 0.75
    elif governor_mode == "constrained":
        g_gov = 0.45
    elif governor_mode in {"locked", "blocked"}:
        g_gov = 0.2

    c_const = 0.5 if epoch_current else 0.2
    w_wit = 0.4
    o_ops = clip01(0.3 + 0.05 * min(10, int(tick)))

    activities = {
        "E_HOST": e_host,
        "E_RUNTIME": e_runtime,
        "S_STRUCTURE": s_struct,
        "M_CONSOLIDATED": m_cons,
        "M_LEARNED": m_learn,
        "M_FEDERATED": m_fed,
        "T_TASK": t_task,
        "G_GOVERNOR": g_gov,
        "C_CONSTITUTIONAL": c_const,
        "W_WITNESS": w_wit,
        "O_OPERATIONS": o_ops,
    }
    if observation_id:
        # Encode which measured subsystem produced the receipt. This is a
        # bounded event-participation mask over the live channel snapshot, not
        # a synthetic event or a claim that inactive channels disappeared.
        salience_by_kind = {
            "neural_activation": {"M_LEARNED", "S_STRUCTURE"},
            "session_begin": {"T_TASK", "O_OPERATIONS"},
            "organism_pulse": {
                "M_CONSOLIDATED",
                "G_GOVERNOR",
                "O_OPERATIONS",
            },
            "organism_pulse_chain": {
                "M_CONSOLIDATED",
                "G_GOVERNOR",
                "O_OPERATIONS",
            },
            "context_packet": {"E_HOST", "E_RUNTIME", "T_TASK"},
            "prediction_trace": {"M_LEARNED", "M_FEDERATED", "T_TASK"},
            "connect_pass": {
                "E_RUNTIME",
                "S_STRUCTURE",
                "M_FEDERATED",
                "O_OPERATIONS",
            },
            "controller_receipt": {
                "G_GOVERNOR",
                "C_CONSTITUTIONAL",
                "W_WITNESS",
            },
            "activation_boundary": {"E_RUNTIME", "T_TASK", "O_OPERATIONS"},
        }
        salience = (
            {"M_CONSOLIDATED", "T_TASK", "O_OPERATIONS"}
            if observation_kind.startswith("stream_")
            else salience_by_kind.get(
                observation_kind, salience_by_kind["activation_boundary"]
            )
        )
        activities = {
            family: clip01(0.75 * value + (0.25 if family in salience else 0.0))
            for family, value in activities.items()
        }
    truths = {
        "E_HOST": ChannelTruthSource.MEASURED.value if e_paths else ChannelTruthSource.INFERRED.value,
        "E_RUNTIME": (
            ChannelTruthSource.RECEIPT_VERIFIED.value
            if cert_status in {"verified", "ready"}
            else ChannelTruthSource.INFERRED.value
        ),
        "S_STRUCTURE": ChannelTruthSource.MEASURED.value if n_files else ChannelTruthSource.UNKNOWN.value,
        "M_CONSOLIDATED": ChannelTruthSource.INFERRED.value,
        "M_LEARNED": ChannelTruthSource.INFERRED.value,
        "M_FEDERATED": ChannelTruthSource.INFERRED.value,
        "T_TASK": ChannelTruthSource.OPERATOR_ASSERTED.value if task else ChannelTruthSource.UNKNOWN.value,
        "G_GOVERNOR": ChannelTruthSource.MEASURED.value,
        "C_CONSTITUTIONAL": ChannelTruthSource.MEASURED.value if body_epoch_id else ChannelTruthSource.UNKNOWN.value,
        "W_WITNESS": ChannelTruthSource.UNKNOWN.value,
        "O_OPERATIONS": ChannelTruthSource.MEASURED.value,
    }
    paths = {
        "E_HOST": e_paths[:12],
        "E_RUNTIME": e_paths[:4],
        "S_STRUCTURE": e_paths[:8],
        "M_CONSOLIDATED": e_paths[:6],
        "T_TASK": e_paths[:4],
    }
    samples = sample_tick_channels(
        repo=repo,
        body_epoch_id=body_epoch_id,
        tick=tick,
        activities=activities,
        truth_sources=truths,
        paths_by_channel=paths,
        constitutional_bits=bits,
        governor_mode=governor_mode,
        timestamp=observed_at,
    )
    if not observation_id:
        return samples
    # The event category stays bounded while source_ids preserves exact event
    # identity. Unique IDs must not become unbounded categorical dimensions.
    return [
        replace(
            sample,
            event_key=observation_kind,
            source_ids=(observation_id,),
            metadata={
                **sample.metadata,
                "observation_id": observation_id,
                "observation_kind": observation_kind,
            },
        )
        for sample in samples
    ]


def channel_truth_panel(samples: list[FieldSample]) -> dict[str, dict[str, Any]]:
    """Per-channel truth summary for receipts (deterministic key order)."""
    panel: dict[str, dict[str, Any]] = {}
    by_ch: dict[str, list[FieldSample]] = {}
    for s in samples:
        by_ch.setdefault(s.channel_family, []).append(s)
    for fam in sorted(by_ch):
        items = by_ch[fam]
        sources = sorted({s.truth_source for s in items})
        mean_act = sum(s.activity for s in items) / max(1, len(items))
        mean_rel = sum(s.reliability for s in items) / max(1, len(items))
        verified = any(s.is_verified_evidence for s in items)
        panel[fam] = {
            "truth_sources": sources,
            "mean_activity": round(mean_act, 6),
            "mean_reliability": round(mean_rel, 6),
            "verified_evidence_eligible": verified,
            "sample_count": len(items),
        }
    return panel
