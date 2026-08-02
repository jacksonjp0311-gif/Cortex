"""Integrated v8.1 canonical predictive-observer cycle."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from .autobiography import append_episode, verify_autobiography
from .counterfactual import simulate_counterfactuals
from .lesion import run_lesion_benchmarks
from .measured import capture_measured_state, measured_delta
from .model import model_status, predict_next_delta, score_and_update
from .workspace import compete_and_broadcast, workspace_status

SCHEMA = "cortex-cognitive-cycle/1.0"


def begin_cognitive_cycle(store: Any, repo: str) -> dict[str, Any]:
    """Capture the pre-state and issue a prediction before activation effects."""
    return {
        "schema_version": SCHEMA,
        "before": capture_measured_state(store, repo),
        "forecast": predict_next_delta(store, repo, action="activation"),
        "opened_at": time.time(),
    }


def _event_id(activation: dict[str, Any], before_hash: str, after_hash: str) -> str:
    ctx = activation.get("context") if isinstance(activation.get("context"), dict) else {}
    neural = ctx.get("neural_interlink") if isinstance(ctx.get("neural_interlink"), dict) else {}
    native = str(
        neural.get("activation_id")
        or ctx.get("packet_hash")
        or activation.get("packet_hash")
        or ""
    )
    material = f"{native}|{before_hash}|{after_hash}"
    return "mevent_" + hashlib.sha256(material.encode()).hexdigest()[:20]


def close_cognitive_cycle(
    store: Any,
    repo: str,
    cycle: dict[str, Any],
    activation: dict[str, Any],
    *,
    realized_action: str,
) -> dict[str, Any]:
    """Capture post-state, score the prior forecast, and simulate alternatives."""
    after = capture_measured_state(store, repo)
    before = dict(cycle.get("before") or {})
    event_id = _event_id(
        activation, str(before.get("state_hash") or ""), str(after.get("state_hash") or "")
    )
    measured = measured_delta(
        before, after, event_id=event_id, event_kind="activation_transaction"
    )
    forecast = dict(cycle.get("forecast") or {})
    prediction_score = score_and_update(store, repo, forecast, measured)
    counterfactuals = simulate_counterfactuals(
        forecast, realized_action=realized_action
    )
    store.set_setting(f"measured_event_latest:{repo}", measured)
    store.set_setting(f"counterfactual_latest:{repo}", counterfactuals)
    return {
        "schema_version": SCHEMA,
        "order": [
            "capture_pre_state",
            "issue_prior_forecast",
            "execute_existing_bounded_activation",
            "capture_post_state",
            "score_forecast_before_learning",
            "simulate_nonexecuting_counterfactuals",
            "broadcast_capacity_bounded_workspace",
            "append_hash_chained_episode",
            "run_functional_lesions",
        ],
        "measured_event_field": measured,
        "self_model_forecast": forecast,
        "prediction_score": prediction_score,
        "counterfactuals": counterfactuals,
        "closed_at": time.time(),
        "advisory_only": True,
    }


def finalize_cognitive_cycle(
    store: Any,
    repo: str,
    cycle: dict[str, Any],
    *,
    task: str,
    body_epoch_id: str,
    self_sensing: dict[str, Any],
    frame: dict[str, Any] | None,
    epoch_delta: dict[str, Any] | None,
) -> dict[str, Any]:
    measured = dict(cycle.get("measured_event_field") or {})
    score = dict(cycle.get("prediction_score") or {})
    workspace = compete_and_broadcast(
        store,
        repo,
        measured=measured,
        prediction_score=score,
        self_sensing=self_sensing,
        frame=frame,
        epoch_delta=epoch_delta,
    )
    episode = append_episode(
        store,
        repo,
        task=task,
        body_epoch_id=body_epoch_id,
        measured=measured,
        prediction_score=score,
        workspace=workspace,
        self_sensing=self_sensing,
    )
    return {
        **cycle,
        "global_workspace": workspace,
        "autobiographical_episode": episode,
        "lesion_benchmarks": run_lesion_benchmarks(store, repo),
        "functional_self_model_only": True,
        "advisory_only": True,
        "claim_boundary": (
            "The cognitive cycle implements measured self-prediction, simulation, "
            "bounded global availability, and operational continuity. It does not "
            "establish consciousness or subjective sensing."
        ),
    }


def cognitive_status(store: Any, repo: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "measured_event_field": store.get_setting(f"measured_event_latest:{repo}", None),
        "predictive_self_model": model_status(store, repo),
        "counterfactuals": store.get_setting(f"counterfactual_latest:{repo}", None),
        "global_workspace": workspace_status(store, repo),
        "autobiography": verify_autobiography(store, repo),
        "lesion_benchmarks": run_lesion_benchmarks(store, repo),
        "functional_self_model_only": True,
        "advisory_only": True,
    }
