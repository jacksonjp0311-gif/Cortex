"""v7.7.0 Binding Field release receipt."""

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
from cortex.binding_field import CANONICAL, CLAIM, SCHEMA  # noqa: E402


def _fh(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing"


def main() -> int:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    tests = [
        "tests/test_binding_field.py",
        "tests/test_warm_in.py",
        "tests/test_self_sensing.py",
        "tests/test_claim_receipt.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    receipt = {
        "schema_version": "cortex-release-receipt/1.9",
        "release": "v7.7.0-binding-field",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "test_totals": {
            "exit_code": r.returncode,
            "passed": r.returncode == 0,
            "summary": [ln for ln in out.strip().splitlines() if ln.strip()][-10:],
            "suite": tests,
        },
        "binding_schema": SCHEMA,
        "modules": {"binding_field.py": _fh(ROOT / "cortex/binding_field.py")},
        "phase_doc_hash": _fh(ROOT / "docs/intelligence/PHASE_V7.7_BINDING_FIELD.md"),
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "live_structure_named": [
            "BINDING_GAP",
            "BUFFER_PENDING",
            "COLD_FIELD",
            "VERIFIED_REGIME",
        ],
        "rollback_point": "v7.6.0",
    }
    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    outp = ROOT / "work"
    outp.mkdir(exist_ok=True)
    path = outp / "release_receipt_v770.json"
    path.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"path": str(path), "receipt_hash": receipt["receipt_hash"], "passed": r.returncode == 0, "version": __version__}, indent=2))
    if r.returncode != 0:
        print(out[-3000:], file=sys.stderr)
    return 0 if r.returncode == 0 and release_at_least(__version__, (7, 7, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
