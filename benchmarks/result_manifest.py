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
            elif payload.get("schema_version") == "cortex-alpha21-open-response-evaluator-audit/1.0":
                metadata_state = (
                    "zero_call_evaluator_audit_held"
                    if payload.get("state") == "EVALUATOR_AUDIT_HELD"
                    and payload.get("raw_scores_rewritten") is False
                    and payload.get("baseline_difficulty_established") is False
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    else "evaluator_audit_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha22-semantic-causal-evaluator/1.0":
                metadata_state = (
                    "semantic_evaluator_v2_ready_zero_call"
                    if payload.get("state") == "SEMANTIC_CAUSAL_EVALUATOR_V2_READY"
                    and payload.get("planned_live_calls") == 0
                    and payload.get("baseline_difficulty_established") is False
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "semantic_evaluator_v2_held"
                )
            elif payload.get("schema_version") == "cortex-alpha23-live-semantic-causal-screen/1.0":
                metadata_state = (
                    "development_live_semantic_causal_screen"
                    if payload.get("state") == "LIVE_SEMANTIC_CAUSAL_SCREEN_RECONSTRUCTED"
                    and payload.get("calls_executed") == 4
                    and payload.get("calibration_established") is False
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "development_live_semantic_causal_held"
                )
            elif payload.get("schema_version") == "cortex-alpha24-harder-live-semantic-screen/1.0":
                metadata_state = (
                    "development_harder_live_semantic_screen"
                    if payload.get("state") == "LIVE_SEMANTIC_CAUSAL_SCREEN_RECONSTRUCTED"
                    and payload.get("difficulty_level") == 4
                    and payload.get("calls_executed") == 4
                    and (payload.get("canonical_reconstruction") or {}).get("valid") is True
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "development_harder_live_semantic_held"
                )
            elif payload.get("schema_version") == "cortex-alpha25-semantic-instrument-sufficiency-audit/1.0":
                metadata_state = (
                    "zero_call_semantic_instrument_audit_held"
                    if payload.get("state") == "DIFFICULTY_INTERPOLATION_HELD"
                    and payload.get("additional_model_calls") == 0
                    and payload.get("historical_scores_rewritten") is False
                    and payload.get("difficulty_interpolation_ready") is False
                    and payload.get("semantic_transfer_established") is False
                    else "semantic_instrument_audit_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha26-relational-causal-evaluator/1.0":
                metadata_state = (
                    "zero_call_relational_causal_evaluator_ready"
                    if payload.get("state") == "RELATIONAL_CAUSAL_EVALUATOR_V3_READY"
                    and payload.get("planned_live_calls") == 0
                    and (payload.get("self_test") or {}).get("passed") is True
                    and (payload.get("self_test") or {}).get("check_count") == 11
                    and payload.get("historical_scores_rewritten") is False
                    and payload.get("difficulty_interpolation_ready") is True
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "relational_causal_evaluator_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha27-intermediate-relational-forge/1.0":
                metadata_state = (
                    "zero_call_intermediate_relational_forge_ready"
                    if payload.get("state") == "INTERMEDIATE_RELATIONAL_FORGE_READY"
                    and payload.get("panel_count") == 3
                    and payload.get("cases_per_panel") == 4
                    and payload.get("planned_live_calls") == 0
                    and payload.get("maximum_future_calls_without_new_authority") == 0
                    and payload.get("historical_scores_rewritten") is False
                    and payload.get("evidence_policy_constant_across_bands") is True
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "intermediate_relational_forge_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha28-bridge-low-relational-screen/1.0":
                metadata_state = (
                    "development_bridge_low_relational_screen"
                    if payload.get("state") == "RELATIONAL_LIVE_SCREEN_RECONSTRUCTED"
                    and payload.get("planned_calls") == 4
                    and payload.get("maximum_calls") == 4
                    and payload.get("calls_executed") == 4
                    and (payload.get("canonical_reconstruction") or {}).get("valid") is True
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "bridge_low_relational_screen_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha28-bridge-low-instrument-audit/1.0":
                metadata_state = (
                    "zero_call_bridge_low_interpretation_held"
                    if payload.get("state") == "BRIDGE_LOW_INTERPRETATION_HELD"
                    and payload.get("additional_model_calls") == 0
                    and payload.get("historical_scores_rewritten") is False
                    and payload.get("difficulty_interpretation_confounded") is True
                    and payload.get("baseline_difficulty_established") is False
                    and payload.get("semantic_transfer_established") is False
                    else "bridge_low_instrument_audit_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha29-relational-equivalence/1.0":
                metadata_state = (
                    "zero_call_relational_equivalence_ready"
                    if payload.get("state") == "RELATIONAL_EQUIVALENCE_V4_READY"
                    and payload.get("additional_model_calls") == 0
                    and payload.get("historical_scores_rewritten") is False
                    and payload.get("ruler_building_closed") is True
                    and (payload.get("self_test") or {}).get("passed") is True
                    and payload.get("baseline_difficulty_established") is False
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "relational_equivalence_invalid"
                )
            elif payload.get("schema_version") == "cortex-alpha30-final-relational-screen/1.0":
                reconstruction = payload.get("canonical_reconstruction") or {}
                calibrated = payload.get("calibration_established") is True
                retired = payload.get("synthetic_semantic_benchmark_retired") is True
                disposition_valid = (calibrated and not retired) or (retired and not calibrated)
                metadata_state = (
                    "development_final_relational_screen"
                    if payload.get("state") == "FINAL_RELATIONAL_SCREEN_RECONSTRUCTED"
                    and payload.get("difficulty_band") == "bridge_mid"
                    and payload.get("planned_calls") == 4
                    and payload.get("maximum_calls") == 4
                    and payload.get("calls_executed") == 4
                    and reconstruction.get("valid") is True
                    and payload.get("ruler_building_closed") is True
                    and payload.get("ruler_revision_permitted") is False
                    and disposition_valid
                    and payload.get("semantic_transfer_established") is False
                    and payload.get("private_contract_persisted_in_artifact") is False
                    else "final_relational_screen_invalid"
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
