"""Hash-chained operational autobiography derived from measured episodes."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

SCHEMA = "cortex-operational-autobiography/1.0"
HISTORY_CAP = 256


def _key(repo: str) -> str:
    return f"operational_autobiography:{repo}"


def _hash(material: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def append_episode(
    store: Any,
    repo: str,
    *,
    task: str,
    body_epoch_id: str,
    measured: dict[str, Any],
    prediction_score: dict[str, Any],
    workspace: dict[str, Any],
    self_sensing: dict[str, Any],
) -> dict[str, Any]:
    episodes = list(store.get_setting(_key(repo), []) or [])
    previous_hash = str((episodes[-1] if episodes else {}).get("episode_hash") or "GENESIS")
    material = {
        "repo": repo,
        "sequence": int((episodes[-1] if episodes else {}).get("sequence") or 0) + 1,
        "previous_hash": previous_hash,
        "task_hash": hashlib.sha256(task.encode()).hexdigest(),
        "body_epoch_id": body_epoch_id,
        "measured_receipt_hash": measured.get("receipt_hash"),
        "changed_metrics": measured.get("changed_metrics") or [],
        "forecast_id": prediction_score.get("forecast_id"),
        "prediction_error": prediction_score.get("normalized_mae"),
        "workspace_broadcast_hash": workspace.get("broadcast_hash"),
        "workspace_signals": [
            item.get("signal_id") for item in (workspace.get("selected") or [])
        ],
        "self_classification": self_sensing.get("classification"),
    }
    episode = {
        "schema_version": SCHEMA,
        **material,
        "episode_hash": _hash(material),
        "recorded_at": time.time(),
        "claim_boundary": (
            "This is a hash-chained operational history, not personal identity, "
            "subjective memory, ownership, or consciousness."
        ),
    }
    episodes.append(episode)
    store.set_setting(_key(repo), episodes[-HISTORY_CAP:])
    return episode


def verify_autobiography(store: Any, repo: str) -> dict[str, Any]:
    episodes = list(store.get_setting(_key(repo), []) or [])
    valid = True
    breaks: list[int] = []
    for index, episode in enumerate(episodes):
        expected_previous = (
            ("GENESIS" if int(episode.get("sequence") or 0) == 1 else episode.get("previous_hash"))
            if index == 0
            else episodes[index - 1].get("episode_hash")
        )
        material = {
            key: episode.get(key)
            for key in (
                "repo", "sequence", "previous_hash", "task_hash", "body_epoch_id",
                "measured_receipt_hash", "changed_metrics", "forecast_id",
                "prediction_error", "workspace_broadcast_hash", "workspace_signals",
                "self_classification",
            )
        }
        if episode.get("previous_hash") != expected_previous or episode.get("episode_hash") != _hash(material):
            valid = False
            breaks.append(index + 1)
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "episode_count": len(episodes),
        "chain_valid": valid,
        "breaks": breaks,
        "latest": episodes[-1] if episodes else None,
        "advisory_only": True,
    }
