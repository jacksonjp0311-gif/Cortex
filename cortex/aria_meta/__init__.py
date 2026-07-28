"""Cortex-owned native ARIA semantic-language substrate."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .substrate import classify_aria_task, is_internal_aria_path


def bundle_root() -> Path:
    """Return the self-contained ARIA snapshot shipped with Cortex."""

    return Path(__file__).resolve().parent / "vendor"


def bundle_identity() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "INTERNAL_ARIA.json"
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bundle() -> dict[str, Any]:
    """Verify every file declared by ARIA's native manifest."""

    root = bundle_root()
    manifest_path = root / "MANIFEST.sha256"
    checked = 0
    failures: list[dict[str, str]] = []
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        expected, relative = line.split(maxsplit=1)
        path = root / relative
        if not path.is_file():
            failures.append({"path": relative, "reason": "missing"})
            continue
        actual = sha256(path.read_bytes()).hexdigest()
        checked += 1
        if actual != expected:
            failures.append(
                {
                    "path": relative,
                    "reason": "digest_mismatch",
                    "expected": expected,
                    "actual": actual,
                }
            )
    identity = bundle_identity()
    return {
        "schema_version": "cortex-internal-aria-verification/1.0",
        "valid": not failures and checked > 0,
        "checked_files": checked,
        "failures": failures,
        "source_commit": identity["source_commit"],
        "role": identity["role"],
        "external_runtime_dependency": False,
    }


__all__ = [
    "bundle_identity",
    "bundle_root",
    "classify_aria_task",
    "is_internal_aria_path",
    "verify_bundle",
]
