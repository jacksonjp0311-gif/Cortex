"""Alpha.17 zero-call sham-controlled semantic calibration preflight."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.semantic_calibration import (  # noqa: E402
    build_semantic_calibration_bundle,
    build_semantic_calibration_preflight,
    verify_semantic_calibration_bundle,
)
from cortex.source_experience import forge_structural_source_experience_pair  # noqa: E402
from cortex.store import Store  # noqa: E402


def run_preflight() -> dict:
    with tempfile.TemporaryDirectory(prefix="cortex-alpha17-") as raw:
        root = Path(raw)
        home = ensure_home(root / "home")
        host = root / "host"
        host.mkdir()
        (host / "README.md").write_text("Alpha.17 isolated preflight.\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        try:
            bootstrap_repository(home, store, host, "Alpha17Preflight")
            pair = forge_structural_source_experience_pair(store, "Alpha17Preflight")
            bundle = build_semantic_calibration_bundle(
                secret_seed=secrets.token_hex(32)
            )
            bundle_check = verify_semantic_calibration_bundle(bundle)
            preflight = build_semantic_calibration_preflight(pair, bundle)
        finally:
            store.close()
    return {
        "schema_version": "cortex-alpha17-commissioning/1.0",
        "state": preflight["state"],
        "lesson_pair": pair,
        "public_corpus_manifest": bundle["manifest"],
        "answer_key_commitment": bundle["manifest"]["answer_key_commitment"],
        "answer_key_persisted_in_artifact": False,
        "bundle_verification": bundle_check,
        "preflight": preflight,
        "calls_executed": 0,
        "paid_calls_executed": 0,
        "calibration_established": False,
        "semantic_transfer_established": False,
        "next_action": "execute_four_call_live_baseline_screen",
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_preflight()
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["state"] == "LIVE_CALIBRATION_SCREEN_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
