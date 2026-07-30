"""CI release receipt — version + tests + holdout + OCI snapshot (v6.20).

Run from repo root after unit tests. Exit 0 always if receipt written;
exit 1 only on hard import failures.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from cortex import __version__
    from cortex.coherence import measure_coherence
    from cortex.config import ensure_home
    from cortex.eval_coupling import HOLDOUT_CORPUS, HOLDOUT_FREEZE_ID, run_eval_coupling
    from cortex.governor import Governor
    from cortex.promote_gate import evaluate_promotion
    from cortex.store import Store

    home = ensure_home()
    store = Store(home / "cortex.db")
    gov = Governor(home, store)

    # Prefer CortexTeach if present, else first repo
    names = [r["name"] for r in store.repos()]
    body = "CortexTeach" if "CortexTeach" in names else (names[0] if names else None)

    receipt: dict = {
        "schema_version": "cortex-release-receipt/1.0",
        "version": __version__,
        "at": time.time(),
        "holdout_freeze_id": HOLDOUT_FREEZE_ID,
        "holdout_case_count": len(HOLDOUT_CORPUS),
        "body_repo": body,
    }

    # Test count from pytest --collect-only if available
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=str(root),
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        # last line often "N tests collected"
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        receipt["pytest_collect_tail"] = lines[-3:]
    except Exception as exc:
        receipt["pytest_collect_error"] = f"{type(exc).__name__}: {exc}"

    if body and store.repo(body):
        coh = measure_coherence(store, body, governor=gov, home=home, persist=False)
        receipt["oci"] = coh.get("operational_coupling_index")
        receipt["emergent_coupling"] = coh.get("emergent_coupling")
        receipt["lyapunov"] = (coh.get("lyapunov") or {}).get("V")
        receipt["couple_percolation"] = {
            "occupied_bonds": (coh.get("couple_percolation") or {}).get(
                "occupied_bonds"
            ),
            "phase_emergent": (coh.get("couple_percolation") or {}).get(
                "phase_emergent"
            ),
        }
        try:
            ho = run_eval_coupling(
                home, store, gov, body, suite="holdout", persist=False
            )
            receipt["holdout"] = {
                "recall": (ho.get("ablations") or {})
                .get("baseline", {})
                .get("recall_at_k"),
                "winner": ho.get("winner"),
                "freeze_id": ho.get("holdout_freeze_id"),
            }
        except Exception as exc:
            receipt["holdout_error"] = f"{type(exc).__name__}: {exc}"

        foreign = None
        if "PulseFlow" in names:
            try:
                foreign = run_eval_coupling(
                    home, store, gov, "PulseFlow", suite="foreign", persist=False
                )
                receipt["foreign"] = {
                    "repo": "PulseFlow",
                    "recall": (foreign.get("ablations") or {})
                    .get("baseline", {})
                    .get("recall_at_k"),
                }
            except Exception as exc:
                receipt["foreign_error"] = f"{type(exc).__name__}: {exc}"

        receipt["promotion"] = evaluate_promotion(
            holdout_report=receipt.get("holdout")
            and {
                "winner": (receipt.get("holdout") or {}).get("winner"),
                "gate": {"baseline_is_winner": True},
                "ablations": {
                    "baseline": {
                        "recall_at_k": (receipt.get("holdout") or {}).get("recall")
                    }
                },
                "repo": body,
            },
            foreign_report=foreign,
            emergent_coupling=bool(receipt.get("emergent_coupling")),
            require_foreign=bool(foreign),
        )

    out_dir = home / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"release-receipt-{__version__}-{int(time.time())}.json"
    path.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    # Also write to repo work/ if present
    work = root / "work"
    if work.is_dir():
        (work / "release-receipt-latest.json").write_text(
            json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8"
        )
    print(json.dumps(receipt, indent=2, default=str))
    print("receipt_path", path, file=sys.stderr)
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
