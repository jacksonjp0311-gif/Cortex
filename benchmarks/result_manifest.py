"""Generate a hash-bound manifest for committed quantitative benchmark JSON."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402

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
            elif payload.get("schema_version") == "cortex-live-autonomy-pilot/1.0":
                metadata_state = (
                    "development_live_empirical_held"
                    if payload.get("empirical_advantage_established") is False
                    else "development_live_empirical"
                )
            elif payload.get("schema_version") == "cortex-semantic-transfer-readiness/1.0":
                metadata_state = (
                    "readiness_held_zero_call"
                    if payload.get("calls_executed") == 0
                    else "readiness_invalid_unexpected_calls"
                )
            elif payload.get("schema_version") == "cortex-alpha16-commissioning/1.0":
                metadata_state = (
                    "structural_mechanism_pass_zero_call"
                    if payload.get("state") == "EPISTEMIC_KERNEL_SEED_PASS"
                    and payload.get("paid_calls_executed") == 0
                    and payload.get("empirical_transfer_established") is False
                    else "structural_commissioning_held"
                )
            elif payload.get("schema_version") == "cortex-alpha17-commissioning/1.0":
                metadata_state = (
                    "live_screen_ready_zero_call"
                    if payload.get("state") == "LIVE_CALIBRATION_SCREEN_READY"
                    and payload.get("paid_calls_executed") == 0
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    else "semantic_calibration_preflight_held"
                )
            elif payload.get("schema_version") == "cortex-alpha18-live-screen/1.0":
                metadata_state = (
                    "development_live_empirical_geometry_exhausted"
                    if payload.get("state") == "LIVE_BASELINE_SCREEN_RECONSTRUCTED"
                    and payload.get("evidence_class") == "live_empirical"
                    and payload.get("calls_executed") == 4
                    and payload.get("screen_level") == 3
                    and payload.get("calibration_geometry_exhausted") is True
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    else "development_live_empirical_screening_ceiling"
                    if payload.get("state") == "LIVE_BASELINE_SCREEN_RECONSTRUCTED"
                    and payload.get("evidence_class") == "live_empirical"
                    and payload.get("calls_executed") == 4
                    and (payload.get("screen") or {}).get("state")
                    == "screening_ceiling"
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    else "development_live_empirical_screen_held"
                )
            elif payload.get("schema_version") == "cortex-alpha20-open-response-forge/1.0":
                metadata_state = (
                    "open_response_forge_ready_zero_call"
                    if payload.get("state") == "OPEN_RESPONSE_LATENT_FORGE_READY"
                    and payload.get("planned_live_calls") == 0
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "open_response_forge_held"
                )
            elif payload.get("schema_version") == "cortex-alpha21-live-open-response-screen/1.0":
                metadata_state = (
                    "development_live_open_response_screen"
                    if payload.get("state") == "LIVE_OPEN_RESPONSE_SCREEN_RECONSTRUCTED"
                    and payload.get("calls_executed") == 4
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "development_live_open_response_held"
                )
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
        "cortex_version": __version__,
        "source_commit": commit,
        "benchmark_suite_hash": suite_hash,
        "runtime_class": {"python": platform.python_version(), "system": platform.system()},
        "evidence_class": "committed_controlled_artifacts",
        "result_count": len(files),
        "results": files,
        "limitations": [
            "Artifacts span historical results, fresh controlled reruns, development-only frontier calibrations, and unexecuted task-forge and commissioning manifests.",
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
