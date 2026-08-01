"""v7.5.0 Self-Sensing Field release receipt — hard CI gate."""

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
from cortex.self_sensing import CANONICAL, CLAIM, SCHEMA, Z_KEYS  # noqa: E402


def _fh(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def main() -> int:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"

    tests = [
        "tests/test_self_sensing.py",
        "tests/test_realign.py",
        "tests/test_claim_receipt.py",
        "tests/test_resonant_frame_nonmutation.py",
        "tests/test_observation_nonmutation.py",
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
        "schema_version": "cortex-release-receipt/1.7",
        "release": "v7.5.0-self-sensing-field",
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
        "self_sensing_schema": SCHEMA,
        "z_dim": len(Z_KEYS),
        "z_keys": list(Z_KEYS),
        "modules": {
            "self_sensing.py": _fh(ROOT / "cortex/self_sensing.py"),
            "coherence.py": _fh(ROOT / "cortex/coherence.py"),
            "interconnect.py": _fh(ROOT / "cortex/interconnect.py"),
        },
        "phase_doc_hash": _fh(
            ROOT / "docs/intelligence/PHASE_V7.5_SELF_SENSING_FIELD.md"
        ),
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
        "forbidden": [
            "host_mutation",
            "silent_epoch_seal",
            "constitutional_bit_write",
            "capability_grant",
            "auto_promote",
            "auto_aria",
            "consciousness_claim",
        ],
        "rollback_point": "v7.4.0; disable sense CLI / ignore self_sensing panel",
    }
    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    outp = ROOT / "work"
    outp.mkdir(exist_ok=True)
    path = outp / "release_receipt_v750.json"
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
    return 0 if r.returncode == 0 and __version__.startswith("7.5") else 1


if __name__ == "__main__":
    raise SystemExit(main())
