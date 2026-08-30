"""Fixed subprocess entry point for one claimed Cortex improvement campaign.

The entry point accepts one private JSON payload over stdin. It never prints
the policy secret and exposes only a bounded terminal summary on stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .autonomous_improvement import resolve_canonical_storm_result
from .campaign_runtime import run_claimed_improvement_campaign
from .store import Store


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        store = Store(Path(str(payload["database_path"])))
        try:
            repo = str(payload["repo"])
            claim_hash = str(payload["claim_receipt_hash"])
            claim = store.symbiotic_receipt(claim_hash, repo=repo)
            if not claim or claim.get("kind") != "campaign_worker_claim":
                raise PermissionError("canonical campaign worker claim required")
            storm = resolve_canonical_storm_result(
                store, repo, str(claim.get("storm_summary_receipt_hash") or "")
            )
            result = run_claimed_improvement_campaign(
                store,
                repo,
                Path(str(payload["root"])),
                claim_receipt_hash=claim_hash,
                storm_result=storm,
                policy_receipt_hash=str(claim.get("policy_receipt_hash") or ""),
                policy_secret=str(payload["policy_secret"]),
                auto_promote=False,
            )
            terminal = result.get("terminal") or {}
            print(
                json.dumps(
                    {
                        "status": str(result.get("status") or "unknown"),
                        "terminal_receipt_hash": str(
                            terminal.get("receipt_hash") or ""
                        ),
                    },
                    sort_keys=True,
                )
            )
            return 0 if result.get("status") != "worker_failed" else 1
        finally:
            store.close()
    except Exception as exc:
        print(
            json.dumps(
                {"status": "worker_process_failed", "error_type": type(exc).__name__},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
