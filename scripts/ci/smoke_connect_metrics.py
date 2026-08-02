"""CI smoke: connect passes expand metric graph and distill (this repo only)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.activation import activate_repository  # noqa: E402
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.connect_pass import metric_graph_report  # noqa: E402
from cortex.governor import Governor  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-connect-")) / "home")
    store = Store(home / "cortex.db")
    failures: list[str] = []
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexConnectCI", force=True, external=True)
        cert = (boot.get("certificate") or {}).get("status")
        if cert not in {"verified", "degraded"}:
            failures.append(f"bootstrap:{cert}")
            print(json.dumps({"passed": False, "failures": failures}, default=str))
            return 1
        gov = Governor(home, store)
        counts: list[int] = []
        for i, task in enumerate(
            (
                "Map interconnect and immune first",
                "Gather connect metrics on second pass",
                "Distill ARIA memory into substrate graph",
            )
        ):
            result = activate_repository(
                home, store, gov, "CortexConnectCI", task, budget=600
            )
            cp = result.get("connect_pass") or {}
            if not cp.get("pass_id") and not cp.get("pass_count"):
                failures.append(f"pass_{i}_missing")
            counts.append(int(cp.get("pass_count") or 0))
        if len(counts) >= 2 and counts[-1] < counts[0]:
            failures.append(f"pass_count_not_growing:{counts}")
        if counts and counts[-1] < 3:
            failures.append(f"expected_3_passes:{counts}")
        report = metric_graph_report(store, "CortexConnectCI")
        graph = report.get("graph") or {}
        if int(graph.get("pass_count") or 0) < 3:
            failures.append("graph_pass_count")
        if not (graph.get("averages") or {}):
            failures.append("averages_missing")
        # Path coactivation may be empty on sparse evidence; not a hard fail.
        payload = {
            "passed": not failures,
            "failures": failures,
            "pass_counts": counts,
            "averages": graph.get("averages"),
            "totals": graph.get("totals"),
            "top_coactivations": dict(
                list((graph.get("path_coactivation") or {}).items())[:3]
            ),
            "recent": len(report.get("recent_connect_passes") or []),
            "claim_boundary": "Self-host connect metric growth only.",
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if not failures else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
