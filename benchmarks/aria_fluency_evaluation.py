from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.aria_meta.evaluation import (  # noqa: E402
    evaluate_aria_corpus,
    load_aria_corpus,
)


def main() -> None:
    corpus = ROOT / "benchmarks" / "corpora" / "aria_fluency.json"
    result = evaluate_aria_corpus(load_aria_corpus(corpus))
    print(json.dumps(result, indent=2))
    if (
        result["false_wakes"]
        or result["missed_wakes"]
        or result["purpose_misses"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
