"""v7.1.0 Constitutional Geometry release receipt."""

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
from cortex.constitutional_geometry import (  # noqa: E402
    CLAIM,
    enumerate_coordinates_hash,
)
from cortex.constitutional_requirements import requirements_hash  # noqa: E402


def _file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    commit = ""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"

    tests = [
        "tests/test_constitutional_geometry.py",
        "tests/test_constitutional_requirements.py",
        "tests/test_forbidden_diagonals.py",
        "tests/test_constitutional_path.py",
        "tests/test_observation_nonmutation.py",
        "tests/test_v71_integration.py",
        "tests/test_epoch.py",
        "tests/test_phases.py",
        "tests/test_continuity.py",
        "tests/test_activation_fail_closed.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    summary_lines = [ln for ln in out.strip().splitlines() if ln.strip()][-5:]

    research = {
        "CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md": _file_hash(
            ROOT / "docs/research/CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md"
        ),
        "CORTEX_CONSTITUTIONAL_TESSERACT_V0.1.md": _file_hash(
            ROOT / "docs/research/CORTEX_CONSTITUTIONAL_TESSERACT_V0.1.md"
        ),
        "CSG_DISCOVERY_LEDGER.md": _file_hash(
            ROOT / "docs/research/CSG_DISCOVERY_LEDGER.md"
        ),
    }

    receipt = {
        "schema_version": "cortex-release-receipt/1.3",
        "version": __version__,
        "commit": commit,
        "commit_hash": commit,
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "at": time.time(),
        "test_totals": {
            "exit_code": r.returncode,
            "passed": r.returncode == 0,
            "summary": summary_lines,
            "suite": tests,
        },
        "coordinate_enumeration_hash": enumerate_coordinates_hash(),
        "operation_requirements_hash": requirements_hash(),
        "illegal_diagonal_test_result": "pass" if r.returncode == 0 else "fail",
        "observation_nonmutation_result": "pass" if r.returncode == 0 else "fail",
        "research_document_hashes": research,
        "gates": {
            "four_axis_model": "test_constitutional_geometry",
            "operation_requirements": "test_constitutional_requirements",
            "illegal_diagonals": "test_forbidden_diagonals",
            "legal_path_no_mutation": "test_constitutional_path",
            "observation_nonmutation": "test_observation_nonmutation",
            "boundary_integration": "test_v71_integration",
        },
        "claim_boundary": CLAIM,
    }
    material = json.dumps(receipt, sort_keys=True, default=str)
    receipt["receipt_hash"] = hashlib.sha256(material.encode()).hexdigest()
    out_path = ROOT / "work" / "release_receipt_v710.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
