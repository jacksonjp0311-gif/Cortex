from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.neuron import activate_interlink  # noqa: E402
from cortex.retrieval import query  # noqa: E402
from cortex.store import Store  # noqa: E402


TASKS = {
    "generic_python": "Fix Python retrieval ranking and run unit tests",
    "aria_semantic": "ARIA semantic replay cooperative mesh session handoff",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    args = parser.parse_args()
    repo = args.repo.resolve()

    with tempfile.TemporaryDirectory() as temp:
        home = ensure_home(Path(temp) / "home")
        store = Store(home / "cortex.db")
        try:
            started = time.perf_counter()
            bootstrap = bootstrap_repository(
                home,
                store,
                repo,
                "AriaSubstrateBenchmark",
                force=True,
                preserve_agents=True,
                external=True,
            )
            results: dict[str, object] = {}
            for name, task in TASKS.items():
                retrieval_started = time.perf_counter()
                hits = query(store, "AriaSubstrateBenchmark", task, limit=24)
                retrieval_seconds = time.perf_counter() - retrieval_started
                activation_started = time.perf_counter()
                packet = activate_interlink(
                    store,
                    "AriaSubstrateBenchmark",
                    task,
                    hits,
                    max_depth=2,
                    max_nodes=64,
                    plasticity_enabled=False,
                    governance_mode="read_only",
                    record=False,
                )
                results[name] = {
                    "task": task,
                    "retrieval_seconds": round(retrieval_seconds, 6),
                    "seconds": round(time.perf_counter() - activation_started, 6),
                    "state_hash": packet.state_hash,
                    "metrics": packet.metrics,
                }
            print(
                json.dumps(
                    {
                        "schema_version": "cortex-aria-substrate-benchmark/1.0",
                        "repository": str(repo),
                        "bootstrap_seconds": round(time.perf_counter() - started, 6),
                        "graph": bootstrap["neural_interlink"],
                        "tasks": results,
                        "claim_boundary": (
                            "This measures deterministic routing on the declared local "
                            "tasks, not universal intent understanding."
                        ),
                    },
                    indent=2,
                )
            )
        finally:
            store.close()


if __name__ == "__main__":
    main()
