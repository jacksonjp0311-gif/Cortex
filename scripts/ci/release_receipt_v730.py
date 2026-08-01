"""v7.3.0 Resonant Frames release receipt — hard CI gate."""

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
from cortex.field_channels import CHANNEL_FAMILIES, CLAIM_BOUNDARY as CH_CLAIM  # noqa: E402
from cortex.resonant_frame import (  # noqa: E402
    CANONICAL_STATEMENT,
    CLAIM_BOUNDARY,
    DEFAULT_THRESHOLDS,
    SCHEMA,
)


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
        "tests/test_field_channels.py",
        "tests/test_resonant_frame_math.py",
        "tests/test_field_comparator.py",
        "tests/test_field_policy.py",
        "tests/test_field_receipt.py",
        "tests/test_resonant_frame_integration.py",
        "tests/test_resonant_frame_nonmutation.py",
        "tests/test_attach_hermetic.py",
        "tests/test_observation_nonmutation.py",
        "tests/test_geometry_seal.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    summary_lines = [ln for ln in out.strip().splitlines() if ln.strip()][-12:]

    theory = ROOT / "docs/research/RESONANT_FRAME_THEORY_V0.1.md"
    math_doc = ROOT / "docs/research/RESONANT_FRAME_MATHEMATICS_V0.1.md"
    ledger = ROOT / "docs/research/RESONANT_FRAME_DISCOVERY_LEDGER.md"
    phase = ROOT / "docs/intelligence/PHASE_V7.3_RESONANT_FRAMES.md"

    modules = {
        "field_channels.py": _file_hash(ROOT / "cortex/field_channels.py"),
        "resonant_frame.py": _file_hash(ROOT / "cortex/resonant_frame.py"),
        "field_comparator.py": _file_hash(ROOT / "cortex/field_comparator.py"),
        "field_policy.py": _file_hash(ROOT / "cortex/field_policy.py"),
        "field_receipt.py": _file_hash(ROOT / "cortex/field_receipt.py"),
    }

    receipt = {
        "schema_version": "cortex-release-receipt/1.5",
        "release": "v7.3.0-resonant-frames",
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
        "frame_schema": SCHEMA,
        "frame_schema_hash": hashlib.sha256(SCHEMA.encode()).hexdigest(),
        "threshold_config": DEFAULT_THRESHOLDS.to_dict(),
        "threshold_config_hash": DEFAULT_THRESHOLDS.digest(),
        "channel_families": list(CHANNEL_FAMILIES),
        "channel_count": len(CHANNEL_FAMILIES),
        "modules": modules,
        "theory_hash": _file_hash(theory),
        "mathematics_hash": _file_hash(math_doc),
        "ledger_hash": _file_hash(ledger),
        "phase_doc_hash": _file_hash(phase),
        "canonical_statement": CANONICAL_STATEMENT,
        "claim_boundary": CLAIM_BOUNDARY,
        "channel_claim": CH_CLAIM,
        "source_note": {
            "author": "E. R. John",
            "title": "A Field Theory of Consciousness",
            "venue": "Consciousness and Cognition 10, 184–213 (2001)",
            "doi": "10.1006/ccog.2001.0508",
            "vendored_pdf": False,
        },
        "non_equivalences": [
            "not_a_brain",
            "tick_not_biological_ms",
            "frame_not_conscious_percept",
            "nonrandomness_not_thermodynamic_entropy",
            "coordination_not_em_zero_phase_lock",
            "field_score_not_subjective_experience",
            "no_quantum_or_microtubule_mechanism",
        ],
        "authority": {
            "temporal_moves_constitutional_bit": False,
            "frame_satisfies_evidence": False,
            "frame_satisfies_authority": False,
            "frame_satisfies_epoch": False,
            "frame_satisfies_witness": False,
            "host_mutation": False,
            "advisory_only": True,
        },
        "rollback_point": "disable CORTEX_FIELD=0 or field cleanup --apply",
    }
    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()

    out_dir = ROOT / "work"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "release_receipt_v730.json"
    path.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"path": str(path), "receipt_hash": receipt["receipt_hash"], "passed": r.returncode == 0}, indent=2))
    if r.returncode != 0:
        print(out[-4000:], file=sys.stderr)
    return 0 if r.returncode == 0 and __version__.startswith("7.3") else 1


if __name__ == "__main__":
    raise SystemExit(main())
