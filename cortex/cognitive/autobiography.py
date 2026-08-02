"""Hash-chained operational autobiography derived from measured episodes."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

SCHEMA = "cortex-operational-autobiography/1.1"
HISTORY_CAP = 256


def _key(repo: str) -> str:
    return f"operational_autobiography:{repo}"


def _checkpoint_key(repo: str) -> str:
    return f"operational_autobiography_checkpoint:{repo}"


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
    if len(episodes) > HISTORY_CAP:
        discarded = episodes[:-HISTORY_CAP]
        prior = dict(store.get_setting(_checkpoint_key(repo), {}) or {})
        tip = discarded[-1]
        checkpoint_material = {
            "repo": repo,
            "prior_checkpoint_hash": prior.get("checkpoint_hash") or "GENESIS",
            "segment_tip_sequence": tip.get("sequence"),
            "segment_tip_hash": tip.get("episode_hash"),
            "retained_from_sequence": episodes[-HISTORY_CAP].get("sequence"),
        }
        checkpoint = {
            "schema_version": "cortex-autobiography-checkpoint/1.0",
            **checkpoint_material,
            "checkpoint_hash": _hash(checkpoint_material),
            "recorded_at": time.time(),
        }
        store.set_setting(_checkpoint_key(repo), checkpoint)
    store.set_setting(_key(repo), episodes[-HISTORY_CAP:])
    return episode


def verify_autobiography(store: Any, repo: str) -> dict[str, Any]:
    episodes = list(store.get_setting(_key(repo), []) or [])
    checkpoint = dict(store.get_setting(_checkpoint_key(repo), {}) or {})
    checkpoint_valid = True
    if checkpoint:
        checkpoint_material = {
            key: checkpoint.get(key)
            for key in (
                "repo", "prior_checkpoint_hash", "segment_tip_sequence",
                "segment_tip_hash", "retained_from_sequence",
            )
        }
        checkpoint_valid = checkpoint.get("checkpoint_hash") == _hash(checkpoint_material)
    valid = True
    breaks: list[int] = []
    for index, episode in enumerate(episodes):
        if index == 0:
            if int(episode.get("sequence") or 0) == 1:
                expected_previous = "GENESIS"
            elif checkpoint:
                expected_previous = checkpoint.get("segment_tip_hash")
            else:
                expected_previous = episode.get("previous_hash")
        else:
            expected_previous = episodes[index - 1].get("episode_hash")
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
    valid = valid and checkpoint_valid
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "episode_count": len(episodes),
        "chain_valid": valid,
        "checkpoint": checkpoint or None,
        "checkpoint_valid": checkpoint_valid,
        "lineage_anchored": bool(
            not episodes
            or int(episodes[0].get("sequence") or 0) == 1
            or (checkpoint and checkpoint_valid)
        ),
        "breaks": breaks,
        "latest": episodes[-1] if episodes else None,
        "advisory_only": True,
    }
