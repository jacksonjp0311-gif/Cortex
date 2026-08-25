"""Build or score the provider-neutral v9.8.1 development task forge."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from cortex.discriminability import assess_task_panel
from cortex.discriminative_forge import build_discriminative_corpus


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="cortex-v981")
    parser.add_argument("--variants-per-family", type=int, default=4)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "v981_discriminative_forge.json")
    args = parser.parse_args()

    corpus = build_discriminative_corpus(seed=args.seed, variants_per_family=args.variants_per_family)
    cases = {str(case["case_id"]): case for case in corpus["cases"]}
    grouped: dict[str, list[bool]] = defaultdict(list)
    observation_state = "not_executed"
    if args.observations is not None:
        payload = json.loads(args.observations.read_text(encoding="utf-8"))
        rows = payload.get("observations") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("observations must be a list or an object containing observations")
        for row in rows:
            case_id = str(row.get("case_id") or "")
            if case_id not in cases:
                raise ValueError(f"unknown calibration case: {case_id}")
            grouped[str(cases[case_id]["family"])].append(bool(row.get("success")))
        observation_state = "scored"
    calibration = assess_task_panel(grouped, minimum_cases=args.variants_per_family) if grouped else None
    report = {
        "schema_version": "cortex-discriminative-forge-benchmark/1.0",
        "corpus": corpus,
        "observation_state": observation_state,
        "calibration": calibration,
        "empirical_trial_executed": False,
        "claim_boundary": "Development calibration only. Generated cases and observations are excluded from confirmatory evidence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"corpus_hash": corpus["corpus_hash"], "case_count": len(cases), "families": corpus["task_families"], "observation_state": observation_state}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
