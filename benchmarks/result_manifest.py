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
    for path in sorted(RESULTS.rglob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        metadata_state = "legacy_partial"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("evidence_class") == "live_external_calibration" and payload.get("confirmatory_eligible") is False:
                metadata_state = "development_calibration"
            elif payload.get("schema_version") == "cortex-discriminative-forge-benchmark/1.0" and payload.get("observation_state") == "not_executed":
                metadata_state = "structural_unexecuted"
            elif payload.get("schema_version") == "cortex-information-balanced-forge-benchmark/1.0" and payload.get("empirical_trial_executed") is False:
                metadata_state = "structural_unexecuted"
            elif payload.get("schema_version") == "cortex-calibration-commissioning/1.0" and payload.get("empirical_trial_executed") is False:
                metadata_state = "structural_unexecuted"
            elif payload.get("schema_version") == "cortex-frontier-calibration-commissioning/1.0":
                metadata_state = "development_live_empirical"
            elif path.parent.name == "v980_rerun":
                metadata_state = "fresh_controlled_rerun_partial_metadata"
        except (json.JSONDecodeError, OSError):
            metadata_state = "unreadable"
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "metadata_state": metadata_state,
            }
        )
    suite_files = sorted((ROOT / "benchmarks").glob("*.py"))
    suite_hash = hashlib.sha256(
        "".join(f"{path.name}:{sha256(path)}\n" for path in suite_files).encode()
    ).hexdigest()
    manifest = {
        "schema_version": "cortex-benchmark-result-manifest/1.0",
        "cortex_version": "9.8.3",
        "source_commit": commit,
        "benchmark_suite_hash": suite_hash,
        "runtime_class": {"python": platform.python_version(), "system": platform.system()},
        "evidence_class": "committed_controlled_artifacts",
        "result_count": len(files),
        "results": files,
        "limitations": [
            "Artifacts span historical results, fresh controlled reruns, one development-only frontier calibration, and unexecuted task-forge and commissioning manifests.",
            "Manifest generation is not a benchmark rerun.",
            "legacy_partial artifacts cannot establish current-head empirical effects.",
            "Development calibration and structural manifests cannot establish confirmatory competence effects.",
        ],
    }
    (RESULTS / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
