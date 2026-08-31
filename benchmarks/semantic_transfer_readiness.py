"""Zero-call alpha.15 semantic-transfer readiness pulse."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.epoch import observe_current_epoch  # noqa: E402
from cortex.semantic_transfer import assess_semantic_transfer_readiness  # noqa: E402
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--task-family", action="append", default=[])
    parser.add_argument("--maximum-next-run-calls", type=int, default=6)
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    store = Store(cortex_home() / "cortex.db")
    try:
        epoch = observe_current_epoch(store, args.repo)
        report = assess_semantic_transfer_readiness(
            store,
            args.repo,
            task_families=args.task_family,
            body_epoch_id=str(epoch.get("live_epoch_id") or epoch.get("epoch_id") or ""),
            maximum_next_run_calls=args.maximum_next_run_calls,
            persist=args.persist,
        )
    finally:
        store.close()
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
