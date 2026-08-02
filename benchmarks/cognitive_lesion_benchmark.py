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
from cortex.cognitive.measured import METRICS, measured_delta  # noqa: E402
from cortex.cognitive.model import predict_next_delta, score_and_update  # noqa: E402
from cortex.cognitive.workspace import compete_and_broadcast  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.store import Store  # noqa: E402


def _delta(event_id: str) -> dict:
    before = {"state_hash": "b", "values": {name: 0.0 for name in METRICS}}
    after = {
        "state_hash": "a",
        "values": {name: 0.2 * METRICS[name][2] for name in METRICS},
    }
    return measured_delta(before, after, event_id=event_id)


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
