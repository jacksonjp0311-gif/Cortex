"""Deterministic v8.2.1 core/periphery bridge benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.math_net.info_interlock import bridge_deconcentration_report  # noqa: E402


class Graph:
    def __init__(self, edges: list[tuple[str, str]]) -> None:
        self.edges = edges

    def neural_synapses(self, repo: str):
        return [
            {
                "source_id": source,
                "target_id": target,
                "relation": "imports" if index % 2 else "tests",
            }
            for index, (source, target) in enumerate(self.edges)
        ]


def main() -> int:
    edges = [
        ("core1/a.py", "core1/b.py"),
        ("core1/a.py", "bridge/c.py"),
        ("core1/b.py", "bridge/c.py"),
        ("core2/e.py", "core2/f.py"),
        ("core2/e.py", "bridge/d.py"),
        ("core2/f.py", "bridge/d.py"),
        ("bridge/c.py", "bridge/d.py"),
    ]
    started = time.perf_counter()
    report = bridge_deconcentration_report(Graph(edges), "BridgeBench")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    top = {item["path"] for item in report["candidates"][:2]}
    receipt = {
        "schema_version": "cortex-geometric-bridge-benchmark/1.0",
        "top_candidates": sorted(top),
        "expected_connectors": ["bridge/c.py", "bridge/d.py"],
        "elapsed_ms": round(elapsed_ms, 6),
        "policy_effect": report["policy_effect"],
        "checks": {
            "connectors_found": top == {"bridge/c.py", "bridge/d.py"},
            "shadow_only": report["mode"] == "shadow",
            "policy_inert": report["policy_effect"] is False,
        },
        "claim_boundary": report["claim_boundary"],
    }
    receipt["passed"] = all(receipt["checks"].values())
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
