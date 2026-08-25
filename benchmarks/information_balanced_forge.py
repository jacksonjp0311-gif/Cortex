"""Build and optionally score the v9.8.2 difficulty-ladder calibration corpus.

This runner is model-neutral. External runtimes may return public case outcomes;
the runner never selects a provider or accepts model identity as a policy input.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from cortex.discriminative_forge import build_difficulty_ladder_corpus, build_held_out_bundle
from cortex.information_calibration import calibrate_difficulty_ladders


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-seed", default="cortex-v982-development")
    parser.add_argument("--maximum-level", type=int, default=4)
    parser.add_argument("--variants-per-level", type=int, default=4)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--heldout-seed-file", type=Path)
    parser.add_argument("--private-answer-key-output", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "v982_information_calibration.json")
    args = parser.parse_args()

    development = build_difficulty_ladder_corpus(
        seed=args.development_seed,
        maximum_level=args.maximum_level,
        variants_per_level=args.variants_per_level,
    )
    cases = {str(row["case_id"]): row for row in development["cases"]}
    ladders: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    calibration = None
    heldout_manifest = None
    state = "DEVELOPMENT_CORPUS_BUILT"
    if args.observations is not None:
        payload = json.loads(args.observations.read_text(encoding="utf-8"))
        rows = payload.get("observations") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("observations must be a list or an object containing observations")
        for observation in rows:
            case_id = str(observation.get("case_id") or "")
            if case_id not in cases:
                raise ValueError(f"unknown development case: {case_id}")
            case = cases[case_id]
            ladders[str(case["family"])][str(case["difficulty_level"])].append(bool(observation.get("success")))
        calibration = calibrate_difficulty_ladders(ladders, minimum_cases_per_level=args.variants_per_level)
        state = "CALIBRATION_SCORED"
        if calibration["overall_state"] == "pass" and args.heldout_seed_file is not None:
            if args.private_answer_key_output is None:
                raise ValueError("--private-answer-key-output is required when generating held-out cases")
            secret_seed = args.heldout_seed_file.read_text(encoding="utf-8").strip()
            if not secret_seed:
                raise ValueError("held-out seed file is empty")
            bundle = build_held_out_bundle(calibration, development, secret_seed=secret_seed)
            heldout_manifest = bundle["manifest"]
            args.private_answer_key_output.parent.mkdir(parents=True, exist_ok=True)
            args.private_answer_key_output.write_text(json.dumps(bundle["answer_key"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
            state = "HELDOUT_SEALED"

    report = {
        "schema_version": "cortex-information-balanced-forge-benchmark/1.0",
        "version": "9.8.2",
        "state": state,
        "development_corpus": development,
        "calibration": calibration,
        "heldout_public_manifest": heldout_manifest,
        "empirical_trial_executed": False,
        "model_selected_by_runner": False,
        "provider_selected_by_runner": False,
        "claim_boundary": "Development calibration and held-out design only; no competence effect is established.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "state": state,
        "development_corpus_hash": development["corpus_hash"],
        "case_count": len(development["cases"]),
        "calibration_state": calibration["overall_state"] if calibration else "NOT_EXECUTED",
        "heldout_state": "SEALED" if heldout_manifest else "NOT_GENERATED",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
