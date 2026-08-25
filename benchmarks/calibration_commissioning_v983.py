"""Build or verify the v9.8.3 development calibration commissioning panel.

This command does not select or invoke a model. A host may supply observations
previously resolved from canonical live Cortex circulations. With no observation
file it emits the honest CALIBRATION_NOT_EXECUTED commissioning plan.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.calibration_commissioning import commission_calibration_panel
from cortex.discriminative_forge import build_difficulty_ladder_corpus


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "v983_calibration_commissioning.json")
    parser.add_argument("--seed", default="cortex-v982-development")
    args = parser.parse_args()
    corpus = build_difficulty_ladder_corpus(seed=args.seed, maximum_level=4, variants_per_level=4)
    receipt = commission_calibration_panel(corpus=corpus, observations=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "commissioning_hash": receipt["commissioning_hash"],
        "accepted_observations": len(receipt["accepted_observation_hashes"]),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
