"""Alpha.16 zero-paid-call epistemic-kernel commissioning pulse."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.epistemic_kernel import (  # noqa: E402
    compile_action_sufficient_context,
    list_epistemic_events,
    project_epistemic_state,
)
from cortex.source_experience import forge_structural_source_experience  # noqa: E402
from cortex.store import Store  # noqa: E402


def run_pulse() -> dict:
    with tempfile.TemporaryDirectory(prefix="cortex-alpha16-") as raw:
        root = Path(raw)
        home = ensure_home(root / "home")
        host = root / "host"
        host.mkdir()
        (host / "README.md").write_text(
            "Alpha.16 isolated structural source experience.\n", encoding="utf-8"
        )
        store = Store(home / "cortex.db")
        try:
            bootstrap_repository(home, store, host, "Alpha16Pulse")
            source = forge_structural_source_experience(store, "Alpha16Pulse")
            events = list_epistemic_events(store, "Alpha16Pulse")
            projection = project_epistemic_state(events)
            claim_ids = [item["claim_id"] for item in projection["claims"]]
            context = compile_action_sufficient_context(
                events, required_claim_ids=claim_ids, character_budget=2000
            )
        finally:
            store.close()
    return {
        "schema_version": "cortex-alpha16-commissioning/1.0",
        "state": (
            "EPISTEMIC_KERNEL_SEED_PASS"
            if source["state"] == "STRUCTURAL_SOURCE_EXPERIENCE_PASS"
            and context["state_preservation"] == "PASS"
            else "EPISTEMIC_KERNEL_SEED_HELD"
        ),
        "source_experience": source,
        "projection": projection,
        "compiled_context": context,
        "calls_executed": 0,
        "paid_calls_executed": 0,
        "empirical_transfer_established": False,
        "next_action": "calibrate_held_out_non_ceiling_semantic_transfer_tasks",
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_pulse()
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["state"] == "EPISTEMIC_KERNEL_SEED_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
