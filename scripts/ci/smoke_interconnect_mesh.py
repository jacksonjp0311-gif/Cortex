"""CI smoke: interconnect mesh + prune + gates (this repo only)."""

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
from cortex.governor import Governor  # noqa: E402
from cortex.interconnect import mesh_status  # noqa: E402
from cortex.neuron import compile_interlink  # noqa: E402
from cortex.prune import prune_graph  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.vectors import build_hnsw_index  # noqa: E402


def main() -> int:
    failures: list[str] = []
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-mesh-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexMeshCI", force=True)
        if (boot.get("certificate") or {}).get("status") not in {"verified", "degraded"}:
            failures.append("bootstrap")
        gov = Governor(home, store)
        compile_interlink(
            store, "CortexMeshCI", resolutions=("file", "symbol", "basic_block")
        )
        build_hnsw_index(store, "CortexMeshCI")
        for task in (
            "interconnect mesh gather first",
            "glyphic medium second pass",
            "seal gates third connect",
        ):
            activate_repository(
                home, store, gov, "CortexMeshCI", task, budget=500, prefetch="auto"
            )
        mesh = mesh_status(store, "CortexMeshCI", governor=gov, home=home)
        if mesh.get("connect", {}).get("pass_count", 0) < 3:
            failures.append(f"pass_count:{mesh.get('connect')}")
        if "host_mutate_forbidden" not in str(mesh.get("agents")):
            failures.append("agents_field")
        if not mesh.get("gates", {}).get("relevance_never_mutation"):
            failures.append("gates")
        dry = prune_graph(store, "CortexMeshCI", dry_run=True)
        if "candidates" not in dry:
            failures.append("prune")
        payload = {
            "passed": not failures,
            "failures": failures,
            "mesh_green": mesh.get("mesh_green"),
            "pass_count": mesh.get("connect", {}).get("pass_count"),
            "bottlenecks": mesh.get("bottlenecks"),
            "prune_candidates": dry.get("candidates"),
            "claim_boundary": "Self-host interconnect mesh regression only.",
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if not failures else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
