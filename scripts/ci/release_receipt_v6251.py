"""v6.25.1 Constitutional Seal release receipt."""

from __future__ import annotations

import hashlib
import json
import os
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
    tests = [
        "tests/test_evidence_kernel.py",
        "tests/test_controller_firewall.py",
        "tests/test_activation_fail_closed.py",
        "tests/test_ranker_rebuild.py",
        "tests/test_independent_witness.py",
        "tests/test_causal_unlearning.py",
        "tests/test_promotion_independence.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    receipt = {
        "schema_version": "cortex-release-receipt/1.2",
        "version": __version__,
        "commit_hash": commit,
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "at": time.time(),
        "tests_exit_code": r.returncode,
        "tests_passed": r.returncode == 0,
        "tests_summary": out.strip().splitlines()[-3:] if out.strip() else [],
        "gates": {
            "baseline_sterility": "test_activation_fail_closed",
            "firewall_denial": "test_controller_firewall",
            "ranker_rebuild": "test_ranker_rebuild",
            "witness_chronology": "test_independent_witness",
            "transactional_repair": "test_causal_unlearning",
        },
        "schema_migrations": [
            "controller_audit_events",
            "state_transitions",
            "ranker_training_events",
            "witness_commitments",
            "repair_snapshots_full_db",
        ],
        "claim_boundary": (
            "Cortex v6.25.1 enforces capability-scoped adaptive writes, sterile "
            "evidence-only activation, runtime quarantine exclusion, atomic repair "
            "transactions, deterministic ranker reconstruction, exact database recovery, "
            "and commit-before-reveal witness verification. These mechanisms provide "
            "bounded computational continuity; they do not establish biological life, "
            "consciousness, autonomous host authority, or perfect adversarial security."
        ),
    }
    material = json.dumps(receipt, sort_keys=True, default=str)
    receipt["receipt_hash"] = hashlib.sha256(material.encode()).hexdigest()
    out_path = ROOT / "work" / "release_receipt_v6251.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    sys.exit(0 if r.returncode == 0 else 1)


if __name__ == "__main__":
    main()
