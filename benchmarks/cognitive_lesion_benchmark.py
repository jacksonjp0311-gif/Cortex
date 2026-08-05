"""Deterministic v8.0 functional lesion benchmark."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.cognitive.autobiography import append_episode  # noqa: E402
from cortex.cognitive.lesion import run_lesion_benchmarks  # noqa: E402
from cortex.cognitive.measured import (  # noqa: E402
    COORDINATE_SCHEMA_VERSION,
    METRICS,
    STATE_SCHEMA,
    coordinate_schema_payload,
    measured_delta,
)
from cortex.cognitive.model import predict_next_delta, score_and_update  # noqa: E402
from cortex.cognitive.workspace import compete_and_broadcast  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.store import Store  # noqa: E402


def _snapshot(values: dict[str, float], *, repo: str, repository_id: str) -> dict:
    """Build a complete null-preserving measured snapshot for synthetic workloads."""
    import hashlib
    import json

    metadata = coordinate_schema_payload()
    ordered = list(metadata["ordered_coordinate_names"])
    material = {
        "repo": repo,
        "repository_id": repository_id,
        "coordinate_schema_digest": metadata["coordinate_schema_digest"],
        "values": {name: float(values[name]) for name in ordered},
        "validity_mask": {name: True for name in ordered},
        "failure_reasons": {name: None for name in ordered},
    }
    state_hash = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return {
        "schema_version": STATE_SCHEMA,
        **material,
        "coordinate_schema_version": COORDINATE_SCHEMA_VERSION,
        "ordered_coordinate_names": ordered,
        "ordered_shape_signature": list(metadata["ordered_shape_signature"]),
        "scale_digest": metadata["scale_digest"],
        "valid_count": len(ordered),
        "required_count": len(ordered),
        "valid_fraction": 1.0,
        "state_hash": state_hash,
    }


def _delta(event_id: str, *, repo: str = "CognitiveLesion", repository_id: str = "rid-lesion") -> dict:
    # Complete schema + validity masks so null-preserving metrology does not
    # collapse synthetic workloads into unmeasured zeros.
    before_values = {name: 0.0 for name in METRICS}
    after_values = {name: 0.2 * METRICS[name][2] for name in METRICS}
    return measured_delta(
        _snapshot(before_values, repo=repo, repository_id=repository_id),
        _snapshot(after_values, repo=repo, repository_id=repository_id),
        event_id=event_id,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        home = ensure_home(Path(temp) / "home")
        host = Path(temp) / "host"
        host.mkdir()
        store = Store(home / "cortex.db")
        repo = "CognitiveLesion"
        store.attach(repo, "rid-lesion", host)
        try:
            latest_delta = None
            latest_score = None
            for index in range(12):
                forecast = predict_next_delta(store, repo, action="activation")
                latest_delta = _delta(f"event-{index}")
                latest_score = score_and_update(store, repo, forecast, latest_delta)
            workspace = compete_and_broadcast(
                store,
                repo,
                measured=latest_delta or {},
                prediction_score=latest_score or {},
                self_sensing={"classification": "NOMINAL", "residual_r": 0.1},
                frame={"classification": "QUIESCENT", "measurement_basis": "measured_delta"},
                epoch_delta={"material_change": False},
            )
            for index in range(2):
                append_episode(
                    store,
                    repo,
                    task=f"lesion-{index}",
                    body_epoch_id="epoch",
                    measured=_delta(f"episode-{index}"),
                    prediction_score=latest_score or {},
                    workspace=workspace,
                    self_sensing={"classification": "NOMINAL"},
                )
            report = run_lesion_benchmarks(store, repo)
            print(json.dumps(report, indent=2))
            return 0 if report["all_supported"] else 1
        finally:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
