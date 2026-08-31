"""Synthetic mechanism check for the alpha.12 autonomy differential.

This runner deliberately uses ScriptedAgentAdapter.  It can prove pairing,
randomization, independent evaluation, accounting, and fail-closed evidence
typing.  It cannot prove empirical Cortex advantage.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from cortex.autonomy_differential import (
    create_autonomy_differential_preregistration,
    evaluate_autonomy_differential,
    randomization_seed_commitment,
    run_autonomy_differential_case,
)
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter, ToolRegistry
from cortex.store import Store


def _adapter(text: str) -> ScriptedAgentAdapter:
    return ScriptedAgentAdapter(
        [
            {
                "public_output": text,
                "finish_reason": "stop",
                "token_usage": {
                    "input_tokens": 16,
                    "output_tokens": 2,
                    "total_tokens": 18,
                },
                "cost": {"total": 0.0},
            }
        ],
        model_id="paired-fixture",
    )


def run_panel(cases: int = 8) -> dict[str, Any]:
    count = max(2, min(int(cases), 64))
    with tempfile.TemporaryDirectory(prefix="cortex-autonomy-differential-") as temporary:
        base = Path(temporary)
        root = base / "host"
        root.mkdir()
        (root / "README.md").write_text("alpha12 fixture\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "benchmark@example.invalid"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Cortex Benchmark"],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        home = ensure_home(base / "home")
        store = Store(home / "cortex.db")
        try:
            repo = "AutonomyDifferentialBenchmark"
            bootstrap_repository(home, store, root, repo)
            tools = ToolRegistry()
            now = time.time()
            grant = CapabilityGrant(
                workspace_root=str(root),
                allowed_tools=(),
                max_tool_calls=0,
                issued_at=now - 1,
                expires_at=now + 300,
            )
            panel = [
                {
                    "case_id": f"case-{index:03d}",
                    "task": f"Return the declared result for case {index}",
                    "task_family": "synthetic_protocol_check",
                    "evaluation_contract": {
                        "contract_id": f"case-{index:03d}-evaluator",
                        "task_type": "text_contains",
                        "target_field": "text",
                        "expected_value": "PASS",
                    },
                }
                for index in range(1, count + 1)
            ]
            seed = "alpha12-structural-benchmark-seed"
            prereg = create_autonomy_differential_preregistration(
                store,
                repo,
                root,
                adapter=_adapter("template"),
                tools=tools,
                grant=grant,
                cases=panel,
                randomization_seed_commitment=randomization_seed_commitment(seed),
                minimum_effect=0.10,
                maximum_regression_rate=0.10,
                maximum_total_tokens=100,
                maximum_latency_ms=60_000,
                maximum_cost=1.0,
            )
            for index, case in enumerate(panel, 1):
                # Deterministic contrast exercises both concordant and benefit
                # pairs.  It is intentionally not evidence of model capability.
                control = "PASS" if index % 2 == 0 else "CONTROL_FAIL"
                treatment = "PASS"
                run_autonomy_differential_case(
                    store,
                    repo,
                    root,
                    preregistration_id=prereg["preregistration_id"],
                    case_id=case["case_id"],
                    randomization_seed=seed,
                    control_adapter=_adapter(control),
                    cortex_adapter=_adapter(treatment),
                    tools=tools,
                    grant=grant,
                )
            result = evaluate_autonomy_differential(
                store,
                repo,
                preregistration_id=prereg["preregistration_id"],
            )
            return {
                "schema_version": "cortex-autonomy-differential-benchmark/1.0",
                "version": "10.0.0-alpha.12",
                "evidence_class": "synthetic",
                "cases": count,
                "status": result["status"],
                "paired_effect": result["exact_matched_binary"][
                    "paired_risk_difference"
                ],
                "discordant_pairs": result["exact_matched_binary"][
                    "discordant_pairs"
                ],
                "exact_two_sided_p": result["exact_matched_binary"][
                    "exact_two_sided_p"
                ],
                "empirical_advantage_established": result[
                    "empirical_advantage_established"
                ],
                "authority": {
                    "host_mutate_authorized": result["host_mutate_authorized"],
                    "execution_authorized": result["execution_authorized"],
                    "memory_admission_authorized": result[
                        "memory_admission_authorized"
                    ],
                    "policy_effect": result["policy_effect"],
                },
                "claim_boundary": (
                    "Synthetic scripted contrast verifies mechanism only. "
                    "It is not empirical evidence that Cortex improves a model."
                ),
            }
        finally:
            store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(run_panel(args.cases), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
