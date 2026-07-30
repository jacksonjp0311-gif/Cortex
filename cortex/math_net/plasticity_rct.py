"""M8 — Plasticity RCT: compare Hebbian on vs off against recall/causal metrics."""

from __future__ import annotations

import time
from typing import Any

SCHEMA = "cortex-plasticity-rct/1.0"


def rct_status(store: Any, repo: str) -> dict[str, Any]:
    raw = store.get_setting(f"plasticity_rct:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("schema_version") == SCHEMA:
        return raw
    return {
        "schema_version": SCHEMA,
        "enabled_arm": "on",  # default production arm
        "arms": {
            "on": {"n": 0, "reward_sum": 0.0, "recall_sum": 0.0},
            "off": {"n": 0, "reward_sum": 0.0, "recall_sum": 0.0},
        },
        "updated_at": 0.0,
    }


def assign_arm(store: Any, repo: str, *, force: str | None = None) -> str:
    """Alternate arms by pulse count for a crude RCT (not crypto RNG)."""
    st = rct_status(store, repo)
    if force in {"on", "off"}:
        arm = force
    else:
        total = int(st["arms"]["on"]["n"]) + int(st["arms"]["off"]["n"])
        arm = "off" if total % 2 == 0 else "on"
    st["enabled_arm"] = arm
    st["updated_at"] = time.time()
    try:
        store.set_setting(f"plasticity_rct:{repo}", st)
    except Exception:
        pass
    return arm


def record_rct_outcome(
    store: Any,
    repo: str,
    *,
    arm: str,
    reward: float,
    recall_at_k: float | None = None,
) -> dict[str, Any]:
    st = rct_status(store, repo)
    if arm not in st["arms"]:
        arm = "on"
    bucket = st["arms"][arm]
    bucket["n"] = int(bucket.get("n") or 0) + 1
    bucket["reward_sum"] = float(bucket.get("reward_sum") or 0.0) + float(reward)
    if recall_at_k is not None:
        bucket["recall_sum"] = float(bucket.get("recall_sum") or 0.0) + float(recall_at_k)
        bucket["recall_n"] = int(bucket.get("recall_n") or 0) + 1
    st["arms"][arm] = bucket
    st["updated_at"] = time.time()
    # summary lift
    def mean(arm_name: str, key_sum: str, key_n: str = "n") -> float | None:
        b = st["arms"][arm_name]
        n = int(b.get(key_n) or 0)
        if n <= 0:
            return None
        return float(b.get(key_sum) or 0.0) / n

    st["summary"] = {
        "reward_on": mean("on", "reward_sum"),
        "reward_off": mean("off", "reward_sum"),
        "recall_on": mean("on", "recall_sum", "recall_n") if st["arms"]["on"].get("recall_n") else None,
        "recall_off": mean("off", "recall_sum", "recall_n") if st["arms"]["off"].get("recall_n") else None,
    }
    on_r = st["summary"]["reward_on"]
    off_r = st["summary"]["reward_off"]
    if on_r is not None and off_r is not None:
        st["summary"]["reward_lift_on_minus_off"] = round(on_r - off_r, 6)
        st["summary"]["keep_plasticity"] = on_r >= off_r - 0.02
    try:
        store.set_setting(f"plasticity_rct:{repo}", st)
    except Exception:
        pass
    return st
