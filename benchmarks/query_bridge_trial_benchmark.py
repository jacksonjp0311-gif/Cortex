"""Deterministic v8.2.2 paired bridge-reserve benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.bridge_trials import query_conditioned_bridge_trial  # noqa: E402


def main() -> int:
    hits = [
        {"path": "core1/a.py", "score": 1.0},
        {"path": "core2/b.py", "score": 0.8},
        {"path": "bridge/c.py", "score": 0.75},
        {"path": "noise/z.py", "score": 0.7},
    ]
    before = [(hit["path"], hit["score"]) for hit in hits]
    started = time.perf_counter()
    report = query_conditioned_bridge_trial(
        "cross region connector",
        hits,
        bridge_scores={
            "bridge/c.py": {"bridge_potential": 0.9, "domain_diversity": 0.8},
            "noise/z.py": {"bridge_potential": 0.2, "domain_diversity": 0.2},
        },
        adjacency={"bridge/c.py": {"other/x.py", "other/y.py"}},
        top_k=2,
        triadic_floor=0.65,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    checks = {
        "bridge_selected": (report.get("selected") or {}).get("path") == "bridge/c.py",
        "fixed_cardinality": report.get("fixed_cardinality") is True,
        "annotation_inert": report["arms"]["annotation_only"] == report["arms"]["baseline"],
        "input_unchanged": before == [(hit["path"], hit["score"]) for hit in hits],
        "policy_inert": report.get("policy_effect") is False,
    }
    receipt = {
        "schema_version": "cortex-query-bridge-benchmark/1.0",
        "elapsed_ms": round(elapsed_ms, 6),
        "checks": checks,
        "selected": report.get("selected"),
        "passed": all(checks.values()),
        "claim_boundary": report.get("claim_boundary"),
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
