"""v7.1.1 Geometry Seal release receipt — hard CI gate."""

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
    GATE_ELIGIBLE_TRUTH,
    AxisTruthSource,
    enumerate_coordinates_hash,
)
from cortex.constitutional_requirements import requirements_hash  # noqa: E402
from cortex.phases import PHASE_BINDING_STATES  # noqa: E402


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
        "tests/test_geometry_seal.py",
        "tests/test_epoch.py",
        "tests/test_phases.py",
        "tests/test_continuity.py",
        "tests/test_activation_fail_closed.py",
        "tests/test_interconnect_continuity.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    summary_lines = [ln for ln in out.strip().splitlines() if ln.strip()][-8:]

    research = {
        "CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md": _file_hash(
            ROOT / "docs/research/CONSTITUTIONAL_SYSTEMS_GEOMETRY_V0.1.md"
        ),
        "EMERGENT_MATH_AND_COMPOSITION_V0.1.md": _file_hash(
            ROOT / "docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md"
        ),
        "CSG_DISCOVERY_LEDGER.md": _file_hash(
            ROOT / "docs/research/CSG_DISCOVERY_LEDGER.md"
        ),
        "PHASE_V7.1.1_GEOMETRY_SEAL.md": _file_hash(
            ROOT / "docs/intelligence/PHASE_V7.1.1_GEOMETRY_SEAL.md"
        ),
    }

    truth_sources = sorted(s.value for s in AxisTruthSource)
    gate_eligible = sorted(s.value for s in GATE_ELIGIBLE_TRUTH)
    phase_bindings = sorted(PHASE_BINDING_STATES)

    receipt = {
        "schema_version": "cortex-release-receipt/1.4",
        "release": "v7.1.1-geometry-seal",
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
        "axis_truth_sources": truth_sources,
        "gate_eligible_truth_sources": gate_eligible,
        "phase_binding_states": phase_bindings,
        "illegal_diagonal_test_result": "pass" if r.returncode == 0 else "fail",
        "observation_nonmutation_result": "pass" if r.returncode == 0 else "fail",
        "geometry_seal_test_result": "pass" if r.returncode == 0 else "fail",
        "research_document_hashes": research,
        "gates": {
            "hard_ci_receipt": "release_receipt_v711.py",
            "truth_source_split": "MEASURED|RECEIPT_VERIFIED vs OPERATOR_ASSERTED|SIMULATED|UNKNOWN",
            "phase_binding": "only BOUND satisfies constitutional compatibility",
            "evidence_refresh_edge": "observe→authorize→refresh E→recompute→select_path",
            "foreign_prediction": "test_foreign_prediction_detects_unencoded_failures",
            "four_axis_model": "test_constitutional_geometry",
            "boundary_integration": "test_v71_integration",
        },
        "claim_boundary": CLAIM,
    }
    material = json.dumps(receipt, sort_keys=True, default=str)
    receipt["receipt_hash"] = hashlib.sha256(material.encode()).hexdigest()
    out_path = ROOT / "work" / "release_receipt_v711.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
