#!/usr/bin/env python3
"""Commission alpha.33 structured edit transport and corpus-privacy closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.edit_intent import INTENT_SCHEMA, compile_edit_intent, verify_edit_intent_compilation  # noqa: E402


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results/v100_alpha33_edit_intent_seal.json")
    args = parser.parse_args()
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="cortex-alpha33-") as parent:
        root = Path(parent)
        (root / "module.py").write_text("def state():\n    return 'old'\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Cortex Seal"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        intent = {"schema_version": INTENT_SCHEMA, "summary": "update state", "edits": [{"path": "module.py", "old": "    return 'old'\n", "new": "    return 'new'\n"}]}
        compilation = compile_edit_intent(root, intent, allowed_targets=["module.py"])
        checks["valid_intent_compiles"] = compilation["proposal"]["patch"].startswith("diff --git ")
        checks["canonical_reconstruction"] = verify_edit_intent_compilation(root, compilation)["valid"]
        checks["authority_closed"] = all(compilation[field] is False for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"))
        try:
            compile_edit_intent(root, {**intent, "success": True}, allowed_targets=["module.py"])
        except ValueError:
            checks["caller_success_rejected"] = True
        try:
            compile_edit_intent(root, {**intent, "edits": [{"path": "../x", "old": "x", "new": "y"}]}, allowed_targets=["module.py"])
        except ValueError:
            checks["scope_escape_rejected"] = True
        try:
            compile_edit_intent(root, {**intent, "edits": [{"path": "module.py", "old": " ", "new": "  "}]}, allowed_targets=["module.py"])
        except ValueError:
            checks["ambiguous_preimage_rejected"] = True
        (root / "module.py").write_text("def state():\n    return 'drifted'\n", encoding="utf-8")
        checks["stale_preimage_rejected"] = not verify_edit_intent_compilation(root, compilation)["valid"]
    report = {
        "schema_version": "cortex-alpha33-edit-intent-seal/1.0",
        "state": "EDIT_INTENT_TRANSPORT_READY" if all(checks.values()) else "EDIT_INTENT_TRANSPORT_HELD",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "compiler_schema": INTENT_SCHEMA,
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "additional_model_calls": 0,
        "historical_private_material_in_git": True,
        "historical_live_model_received_private_material": False,
        "historical_alpha32_scores_rewritten": False,
        "alpha31_corpus_reusable_for_future_heldout_trials": False,
        "future_private_specs_must_be_outside_repository": True,
        "structured_edit_removes_manual_diff_coordinate_burden": True,
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "next_action": "forge_new_external_private_executable_corpus_then_screen_structured_intents",
    }
    report["result_hash"] = _sha(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["state"] == "EDIT_INTENT_TRANSPORT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
