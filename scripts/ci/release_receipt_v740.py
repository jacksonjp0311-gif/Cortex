"""v7.4.0 Continuity Realignment release receipt — hard CI gate."""

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
from version_gate import release_at_least  # noqa: E402
from cortex.realign import CANONICAL, CLAIM, SCHEMA  # noqa: E402


def _file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    commit = ""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"

    tests = [
        "tests/test_realign.py",
        "tests/test_epoch.py",
        "tests/test_continuity.py",
        "tests/test_observation_nonmutation.py",
        "tests/test_resonant_frame_nonmutation.py",
        "tests/test_attach_hermetic.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    summary = [ln for ln in out.strip().splitlines() if ln.strip()][-12:]

    receipt = {
        "schema_version": "cortex-release-receipt/1.6",
        "release": "v7.4.0-continuity-realignment",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "test_totals": {
            "exit_code": r.returncode,
            "passed": r.returncode == 0,
            "summary": summary,
            "suite": tests,
        },
        "realign_schema": SCHEMA,
        "modules": {
            "realign.py": _file_hash(ROOT / "cortex/realign.py"),
            "interconnect.py": _file_hash(ROOT / "cortex/interconnect.py"),
            "cli.py": _file_hash(ROOT / "cortex/cli.py"),
        },
        "phase_doc_hash": _file_hash(
            ROOT / "docs/intelligence/PHASE_V7.4_CONTINUITY_REALIGNMENT.md"
        ),
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "rules": {
            "silent_seal_forbidden": True,
            "authorize_flag_required": "--i-authorize-realign",
            "host_mutation": False,
            "observation_diagnose_only": True,
        },
        "rollback_point": "stay on v7.3.0; ignore realign CLI",
    }
    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()

    out_dir = ROOT / "work"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "release_receipt_v740.json"
    path.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(path),
                "receipt_hash": receipt["receipt_hash"],
                "passed": r.returncode == 0,
                "version": __version__,
            },
            indent=2,
        )
    )
    if r.returncode != 0:
        print(out[-4000:], file=sys.stderr)
    return 0 if r.returncode == 0 and release_at_least(__version__, (7, 4, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
