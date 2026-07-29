"""CI smoke: spectral kernels + mesh dashboard (this repo only)."""

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
from cortex.interconnect import mesh_dashboard  # noqa: E402
from cortex.kernels import annotate_synapses, kernels_status, rho_from_delta  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    failures: list[str] = []
    if abs(rho_from_delta(2.3) - 0.10) > 0.03:
        failures.append("rho_reset")
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-spectral-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexSpectralCI", force=True)
        if (boot.get("certificate") or {}).get("status") not in {"verified", "degraded"}:
            failures.append("bootstrap")
        annotate_synapses(store, "CortexSpectralCI")
        gov = Governor(home, store)
        act = activate_repository(
            home,
            store,
            gov,
            "CortexSpectralCI",
            "spectral kernels interconnect mesh",
            budget=500,
        )
        spectral = (act.get("connect_pass") or {}).get("spectral") or {}
        if not spectral.get("spectrum") and not spectral.get("dominant"):
            # connect may nest spectrum inside spectral from retention_by_class
            if "error" in spectral:
                failures.append(f"spectral:{spectral['error']}")
        ks = kernels_status(store, "CortexSpectralCI")
        if not (ks.get("retention") or {}).get("retain"):
            failures.append("retain_missing")
        dash = mesh_dashboard(store, "CortexSpectralCI", governor=gov, home=home)
        if not dash.get("xi_spectrum"):
            failures.append("dashboard_xi")
        payload = {
            "passed": not failures,
            "failures": failures,
            "dominant": ks.get("dominant"),
            "retention": ks.get("retention"),
            "mesh_green": dash.get("mesh_green"),
            "hnsw_boot": (boot.get("hnsw") or {}).get("built"),
            "claim_boundary": "Self-host spectral kernel regression only.",
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if not failures else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
