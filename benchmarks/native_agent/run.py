"""Structural v10 native-agent commissioning benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, NativeAgentRuntime, ScriptedAgentAdapter
from cortex.store import Store


def run_panel(runs: int) -> dict:
    samples = []
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        host = base / "host"
        host.mkdir()
        (host / "README.md").write_text("native benchmark\n", encoding="utf-8")
        home = ensure_home(base / "home")
        store = Store(home / "cortex.db")
        try:
            bootstrap_repository(home, store, host, "NativeBenchmark")
            for index in range(runs):
                started = time.perf_counter()
                result = NativeAgentRuntime(store, "NativeBenchmark").run(
                    f"structural benchmark {index}",
                    adapter=ScriptedAgentAdapter(
                        [{"public_output": "complete", "finish_reason": "stop"}],
                        model_id=f"fixture-{index}",
                    ),
                    grant=CapabilityGrant(workspace_root=str(host)),
                )
                samples.append(
                    {
                        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                        "event_count": result["event_count"],
                        "tool_call_count": result["tool_call_count"],
                        "trajectory_valid": result["verification"]["valid"],
                    }
                )
        finally:
            store.close()
    latencies = [item["elapsed_ms"] for item in samples]
    return {
        "schema_version": "cortex-native-agent-benchmark/1.0",
        "evidence_class": "synthetic_structural",
        "arm": "agent_plus_cortex_context",
        "runs": runs,
        "median_elapsed_ms": statistics.median(latencies),
        "min_elapsed_ms": min(latencies),
        "max_elapsed_ms": max(latencies),
        "all_trajectories_valid": all(item["trajectory_valid"] for item in samples),
        "samples": samples,
        "unmeasured_arms": ["agent_shell_only", "agent_plus_memory", "agent_plus_competence", "full_cortex"],
        "claim_boundary": "Structural runtime timing is not empirical model competence or causal Cortex benefit.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(run_panel(max(1, min(args.runs, 50))), indent=2))


if __name__ == "__main__":
    main()
