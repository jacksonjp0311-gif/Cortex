"""CI smoke: immune_action STOP codes and inspect_immune (this repo only)."""

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
from cortex.control_error import build_control_error  # noqa: E402
from cortex.governor import Governor  # noqa: E402
from cortex.immune import inspect_immune  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    failures: list[str] = []

    stop = build_control_error(
        certificate={"status": "verified"},
        governance={"mode": "read_only"},
        manifest_current=True,
        retrieval_confidence=0.9,
        aria_materialization={"mode": "dormant"},
    )
    if not stop.get("block") or stop["immune_action"]["code"] != "STOP_NO_HOST_MUTATION":
        failures.append("STOP_NO_HOST_MUTATION")

    reverify = build_control_error(
        certificate={"status": "failed"},
        governance={"mode": "normal"},
        manifest_current=False,
        retrieval_confidence=0.4,
        aria_materialization={"mode": "dormant"},
    )
    if not reverify.get("block"):
        failures.append("reverify_block")
    if reverify["immune_action"]["code"] not in {
        "STOP_REVERIFY_REQUIRED",
        "STOP_NO_HOST_MUTATION",
    }:
        failures.append(f"reverify_code:{reverify['immune_action']['code']}")

    open_gate = build_control_error(
        certificate={"status": "verified"},
        governance={"mode": "normal"},
        manifest_current=True,
        retrieval_confidence=0.9,
        aria_materialization={"mode": "dormant"},
    )
    if open_gate.get("block") or open_gate["immune_action"]["code"] != "PROCEED_UNDER_HOST_AUTHORITY":
        failures.append("PROCEED_UNDER_HOST_AUTHORITY")

    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-immune-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexImmuneCI", force=True, external=True)
        cert = (boot.get("certificate") or {}).get("status")
        if cert not in {"verified", "degraded"}:
            failures.append(f"bootstrap:{cert}")
        else:
            gate = inspect_immune(home, store, Governor(home, store), "CortexImmuneCI")
            if "block" not in gate or "immune_action" not in gate:
                failures.append("inspect_missing_fields")
            if not gate.get("read_first"):
                failures.append("read_first")
            if gate.get("schema_version") != "cortex-immune/1.0":
                failures.append("schema")
    finally:
        store.close()

    payload = {
        "passed": not failures,
        "failures": failures,
        "stop": stop.get("immune_action"),
        "reverify": reverify.get("immune_action"),
        "proceed": open_gate.get("immune_action"),
        "claim_boundary": "Self-host immune gate regression only.",
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
