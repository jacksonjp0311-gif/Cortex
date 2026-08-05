"""CORTEX v8.3.3 independent activation-conformance release receipt."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402
from cortex.activation import activate_repository  # noqa: E402
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home, load_repo_config  # noqa: E402
from cortex.governor import Governor  # noqa: E402
from cortex.indexer import current_manifest_hash  # noqa: E402
from cortex.ostt.conformance import (  # noqa: E402
    activation_cohort_report,
    verify_activation_receipt,
)
from cortex.state_transition import logical_state_digest  # noqa: E402
from cortex.store import Store  # noqa: E402


# Receipt remains the v8.3.3 conformance probe; package may be newer.
MINIMUM_VERSION = "8.3.3"
OUTPUT = ROOT / "work" / "release_receipt_v833.json"


def _version_at_least(current: str, minimum: str) -> bool:
    def parts(value: str) -> tuple[int, ...]:
        core = value.split("+", 1)[0].split("-", 1)[0]
        return tuple(int(part) for part in core.split(".") if part.isdigit())

    left = parts(current)
    right = parts(minimum)
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return left >= right


def _sha(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _focused_tests() -> dict[str, Any]:
    suite = [
        "tests/test_ostt.py",
        "tests/test_ostt_residuals.py",
        "tests/test_activation_conformance.py",
        "tests/test_activation_conformance_integration.py",
    ]
    run = subprocess.run(
        [sys.executable, "-m", "pytest", *suite, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (run.stdout or "") + (run.stderr or "")
    return {
        "passed": run.returncode == 0,
        "exit_code": run.returncode,
        "suite": suite,
        "summary": [line for line in output.splitlines() if line.strip()][-12:],
        "output_hash": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }


def _activation_probe() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cortex-v833-") as temp_dir:
        base = Path(temp_dir)
        home = ensure_home(base / "home")
        host = base / "host"
        host.mkdir()
        (host / "README.md").write_text("# v8.3.3 conformance host\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        try:
            bootstrap_repository(home, store, host, "V833ReleaseHost")
            config = load_repo_config(host, home)
            host_before = current_manifest_hash(host, config)
            adaptive_before = logical_state_digest(store, "V833ReleaseHost")
            predictor_before = store.get_setting(
                "predictive_self_model:V833ReleaseHost", None
            )
            route_before = _sha(
                {
                    "ranker": [
                        dict(row)
                        for row in store.db.execute(
                            "SELECT * FROM ranker_models WHERE repo=? ORDER BY model_id",
                            ("V833ReleaseHost",),
                        ).fetchall()
                    ],
                    "synapses": [
                        dict(row)
                        for row in store.db.execute(
                            "SELECT * FROM neural_synapses WHERE repo=? ORDER BY synapse_id",
                            ("V833ReleaseHost",),
                        ).fetchall()
                    ],
                }
            )
            activation = activate_repository(
                home,
                store,
                Governor(home, store),
                "V833ReleaseHost",
                "produce one independent activation conformance receipt",
                budget=400,
                refresh="never",
                force_evidence_baseline=True,
            )
            receipt = dict(activation.get("ostt_residual_receipt") or {})
            receipt_hash = str(receipt.get("receipt_hash") or "")
            verification = verify_activation_receipt(
                store, "V833ReleaseHost", receipt_hash
            )
            cohort = activation_cohort_report(store, "V833ReleaseHost")
            count_before_duplicate = len(
                store.activation_conformance_receipts("V833ReleaseHost", limit=4096)
            )
            duplicate = store.append_activation_conformance_receipt(
                "V833ReleaseHost", dict(receipt.get("receipt_body") or {})
            )
            count_after_duplicate = len(
                store.activation_conformance_receipts("V833ReleaseHost", limit=4096)
            )
            host_after = current_manifest_hash(host, config)
            adaptive_after = logical_state_digest(store, "V833ReleaseHost")
            predictor_after = store.get_setting(
                "predictive_self_model:V833ReleaseHost", None
            )
            route_after = _sha(
                {
                    "ranker": [
                        dict(row)
                        for row in store.db.execute(
                            "SELECT * FROM ranker_models WHERE repo=? ORDER BY model_id",
                            ("V833ReleaseHost",),
                        ).fetchall()
                    ],
                    "synapses": [
                        dict(row)
                        for row in store.db.execute(
                            "SELECT * FROM neural_synapses WHERE repo=? ORDER BY synapse_id",
                            ("V833ReleaseHost",),
                        ).fetchall()
                    ],
                }
            )
            invariant_results = receipt.get("invariant_results") or []
            invariants = {
                str(item.get("invariant_id")): bool(item.get("passed"))
                for item in invariant_results
                if isinstance(item, dict)
            }
            gates = {
                "production_activation_path": bool(
                    activation.get("sterile_baseline")
                    and (activation.get("controller_execution") or {}).get("resolved")
                    == "evidence_baseline"
                ),
                "coordinate_schema": bool(
                    receipt.get("coordinate_schema_digest")
                    and receipt.get("ordered_coordinate_names")
                    and receipt.get("scale_digest")
                ),
                "all_required_coordinates_valid": float(
                    receipt.get("valid_fraction") or 0.0
                )
                == 1.0,
                "independent_recomputation": bool(
                    verification.get("independent_recomputation_matches")
                ),
                "B_rms_tolerance": float(receipt.get("B_rms") or 0.0) <= 1e-12,
                "B_max_tolerance": float(receipt.get("B_max") or 0.0) <= 1e-12,
                "B_invalid_zero": float(receipt.get("B_invalid") or 0.0) == 0.0,
                "epoch_current": bool(verification.get("epoch_current")),
                "cohort_current": bool(verification.get("cohort_current")),
                "host_immutable": bool(invariants.get("host_immutable"))
                and host_before == host_after,
                "structured_measurement_witness": bool(
                    verification.get("measurement_witness_valid")
                ),
                "structured_invariants": bool(
                    verification.get("invariant_panel_valid")
                ),
                "receipt_hash": bool(verification.get("receipt_hash_valid")),
                "receipt_chain": bool(verification.get("chain_valid")),
                "duplicate_event_rejected": bool(
                    duplicate.get("duplicate")
                    and not duplicate.get("inserted")
                    and count_before_duplicate == count_after_duplicate == 1
                ),
                "routing_unchanged": route_before == route_after,
                "learning_unchanged": adaptive_before == adaptive_after
                and predictor_before == predictor_after,
                "policy_effect_false": receipt.get("policy_effect") is False,
                "update_authorized_false": receipt.get("update_authorized") is False,
                "host_source_unchanged": host_before == host_after,
                "measurement_conformance": bool(
                    verification.get("measurement_conformance_valid")
                ),
                "cohort_gate_c_cold": cohort.get("status") == "cold"
                and int(cohort.get("receipt_count") or 0) == 1,
            }
            sanitized = {
                "schema_version": receipt.get("schema_version"),
                "status": receipt.get("status"),
                "receipt_hash": receipt_hash,
                "subject_receipt_hash": receipt.get("subject_receipt_hash"),
                "measurement_subject_hash": receipt.get(
                    "measurement_subject_hash"
                ),
                "event_id": receipt.get("event_id"),
                "case_id": receipt.get("case_id"),
                "comparison_arm": receipt.get("comparison_arm"),
                "body_epoch_id": receipt.get("body_epoch_id"),
                "measurement_cohort_id": receipt.get("measurement_cohort_id"),
                "coordinate_schema_digest": receipt.get(
                    "coordinate_schema_digest"
                ),
                "valid_fraction": receipt.get("valid_fraction"),
                "B_rms": receipt.get("B_rms"),
                "B_max": receipt.get("B_max"),
                "B_invalid": receipt.get("B_invalid"),
                "channel_burdens": receipt.get("channel_burdens"),
                "invariant_results": invariant_results,
                "measurement_witness": receipt.get("measurement_witness"),
                "chain_sequence": receipt.get("chain_sequence"),
                "previous_receipt_hash": receipt.get("previous_receipt_hash"),
                "chain_valid": receipt.get("chain_valid"),
                "policy_effect": receipt.get("policy_effect"),
                "update_authorized": receipt.get("update_authorized"),
                "advisory_only": receipt.get("advisory_only"),
                "claim_boundary": receipt.get("claim_boundary"),
            }
            return {
                "gates": gates,
                "activation_receipt_hash": receipt_hash,
                "sanitized_production_receipt": sanitized,
                "cohort": {
                    "status": cohort.get("status"),
                    "receipt_count": cohort.get("receipt_count"),
                    "remaining": cohort.get("remaining"),
                    "required_count": cohort.get("required_count"),
                },
            }
        finally:
            store.close()


def main() -> int:
    OUTPUT.parent.mkdir(exist_ok=True)
    focused = _focused_tests()
    error: str | None = None
    try:
        probe = _activation_probe()
    except Exception as exc:
        probe = {"gates": {}, "activation_receipt_hash": None}
        error = f"{type(exc).__name__}:{exc}"
    gates = {
        "version_at_least_8_3_3": _version_at_least(__version__, MINIMUM_VERSION),
        "focused_tests": bool(focused.get("passed")),
        **dict(probe.get("gates") or {}),
    }
    passed = bool(gates) and all(gates.values()) and error is None
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.3.3-independent-activation-conformance",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "classification": "CONFORMANCE_MEASURED" if passed else "HELD",
        "passed": passed,
        "gates": gates,
        "failed_gates": [name for name, value in gates.items() if not value],
        "focused_tests": focused,
        "activation_receipt_hash": probe.get("activation_receipt_hash"),
        "sanitized_production_receipt": probe.get(
            "sanitized_production_receipt"
        ),
        "cohort": probe.get("cohort"),
        "error": error,
        "claim_boundary": (
            "v8.3.3 verifies activation-measurement conformance. It does not "
            "establish task utility, prediction accuracy, cognition, consciousness, "
            "agency, or authority."
        ),
    }
    receipt["release_receipt_hash"] = _sha(receipt)
    OUTPUT.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "passed": passed,
                "classification": receipt["classification"],
                "activation_receipt_hash": receipt["activation_receipt_hash"],
                "release_receipt_hash": receipt["release_receipt_hash"],
                "failed_gates": receipt["failed_gates"],
                "error": error,
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
