"""Generate a hash-bound manifest for committed quantitative benchmark JSON."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    files = []
    for path in sorted(RESULTS.glob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "metadata_state": "legacy_partial",
            }
        )
    suite_files = sorted((ROOT / "benchmarks").glob("*.py"))
    suite_hash = hashlib.sha256(
        "".join(f"{path.name}:{sha256(path)}\n" for path in suite_files).encode()
    ).hexdigest()
    manifest = {
        "schema_version": "cortex-benchmark-result-manifest/1.0",
        "cortex_version": "9.8.1",
        "source_commit": commit,
        "benchmark_suite_hash": suite_hash,
        "runtime_class": {"python": platform.python_version(), "system": platform.system()},
        "evidence_class": "committed_controlled_artifacts",
        "result_count": len(files),
        "results": files,
        "limitations": [
            "Artifacts predate this manifest and lack a unified original run identity.",
            "Manifest generation is not a benchmark rerun.",
            "legacy_partial artifacts cannot establish current-head empirical effects.",
        ],
    }
    (RESULTS / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
