"""Focused alpha.10 control/runtime verification without the full suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(argv: list[str]) -> None:
    print("+", " ".join(argv), flush=True)
    completed = subprocess.run(argv, cwd=ROOT, check=False, shell=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_v100_alpha10_campaign_control.py",
            "tests/test_v100_alpha10_campaign_runtime.py",
            "tests/test_v100_alpha10_campaign_integration.py::V100Alpha10CampaignIntegrationTests::test_candidate_commit_is_off_tree_then_fast_forward_integrated",
            "--tb=short",
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "cortex/campaign_control.py",
            "cortex/campaign_runtime.py",
            "cortex/campaign_integration.py",
            "cortex/chat_service.py",
            "tests/test_v100_alpha10_campaign_control.py",
            "tests/test_v100_alpha10_campaign_runtime.py",
            "tests/test_v100_alpha10_campaign_integration.py",
        ]
    )
    print("ALPHA10_CONTROL_RUNTIME_SMOKE=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
