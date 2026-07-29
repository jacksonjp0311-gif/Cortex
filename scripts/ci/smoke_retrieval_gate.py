"""CI smoke: bootstrap this repo and run path-recall corpus."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.evaluation import evaluate_retrieval_corpus, load_corpus  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-retrieval-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexCI", force=True)
        if (boot.get("certificate") or {}).get("status") not in {"verified", "degraded"}:
            print(json.dumps({"error": "bootstrap_failed", "boot": boot}, default=str))
            return 1
        corpus = load_corpus(ROOT / "benchmarks" / "corpora" / "cortex_retrieval.json")
        # After teach mass exists in tree, allow lower threshold for CI cold bootstrap
        corpus = {**corpus, "minimum_recall_at_k": corpus.get("minimum_recall_at_k", 0.375)}
        result = evaluate_retrieval_corpus(store, corpus, default_repo="CortexCI", top_k=5)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("passed") else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
