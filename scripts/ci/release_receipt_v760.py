"""v7.6.0 Verified Operating Regime release receipt — hard CI gate."""

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
from cortex.warm_in import CANONICAL, CLAIM, SCHEMA  # noqa: E402


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
        "tests/test_warm_in.py",
        "tests/test_self_sensing.py",
        "tests/test_realign.py",
        "tests/test_claim_receipt.py",
        "tests/test_resonant_frame_nonmutation.py",
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
        "schema_version": "cortex-release-receipt/1.8",
        "release": "v7.6.0-verified-operating-regime",
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
        "warm_in_schema": SCHEMA,
        "modules": {
            "warm_in.py": _fh(ROOT / "cortex/warm_in.py"),
            "self_sensing.py": _fh(ROOT / "cortex/self_sensing.py"),
            "realign.py": _fh(ROOT / "cortex/realign.py"),
        },
        "phase_doc_hash": _fh(
            ROOT / "docs/intelligence/PHASE_V7.6_VERIFIED_OPERATING_REGIME.md"
        ),
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "forbidden": [
            "host_mutation",
            "silent_epoch_seal",
            "constitutional_bit_write",
            "capability_grant",
            "auto_promote",
            "consciousness_claim",
        ],
        "rollback_point": "v7.5.0; ignore warm-in CLI",
    }
    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    outp = ROOT / "work"
    outp.mkdir(exist_ok=True)
    path = outp / "release_receipt_v760.json"
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
    return 0 if r.returncode == 0 and release_at_least(__version__, (7, 6, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
