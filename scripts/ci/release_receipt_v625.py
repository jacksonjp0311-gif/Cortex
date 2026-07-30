"""v6.25 release receipt generator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402


def main() -> None:
    commit = ""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    # Run targeted tests
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_evidence_kernel.py",
            "tests/test_controller_firewall.py",
            "tests/test_activation_fail_closed.py",
            "tests/test_lineage_graph.py",
            "tests/test_immunity_scan.py",
            "tests/test_quarantine.py",
            "tests/test_causal_unlearning.py",
            "tests/test_ranker_rebuild.py",
            "tests/test_independent_witness.py",
            "tests/test_repair_readmission.py",
            "tests/test_promotion_independence.py",
            "tests/test_memory_simplex.py",
            "-q",
            "--tb=no",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    passed = r.returncode == 0
    # count dots roughly
    test_line = [ln for ln in out.splitlines() if "passed" in ln or "failed" in ln]
    receipt = {
        "schema_version": "cortex-release-receipt/1.1",
        "version": __version__,
        "commit_hash": commit,
        "at": time.time(),
        "tests_exit_code": r.returncode,
        "tests_passed": passed,
        "tests_summary": test_line[-1] if test_line else out[-500:],
        "schema_migrations": [
            "lineage_artifacts",
            "lineage_edges",
            "quarantine_envelopes",
            "memory_wounds",
            "unlearning_plans",
            "repair_snapshots",
            "repair_receipts",
        ],
        "features": [
            "evidence_kernel",
            "controller_scope",
            "activation_fail_closed",
            "lineage",
            "immunity_lifecycle",
            "independent_witness",
            "promote_coupling_safety_only",
        ],
        "claim_boundary": (
            "Cortex Immunology provides provenance-directed quarantine, selective "
            "unlearning, repair verification, and trusted evidence fallback for an "
            "adaptive repository-memory runtime. It does not establish biological life, "
            "consciousness, autonomous host authority, or perfect protection from "
            "adversarial memory."
        ),
    }
    material = json.dumps(receipt, sort_keys=True, default=str)
    receipt["receipt_hash"] = hashlib.sha256(material.encode()).hexdigest()
    out_path = ROOT / "work" / "release_receipt_v625.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
