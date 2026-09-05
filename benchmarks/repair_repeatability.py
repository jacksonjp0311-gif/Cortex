"""Freeze, then separately execute one four-call fixed-corpus replication.

No model/provider catalog or identity is hard-coded. Private evaluators remain
in the host vault. An interrupted/partial run cannot be silently retried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.harder_contract_aligned_forge import verify_harder_contract_aligned_forge  # noqa: E402
from cortex.harder_contract_aligned_screen import aligned_forge_view  # noqa: E402
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.structured_repair_screen import (  # noqa: E402
    execute_structured_repair_screen,
    freeze_structured_repair_screen,
    verify_structured_repair_screen,
)

RUNTIME_FILES = (
    "cortex/native_agent.py", "cortex/provider_fabric.py", "cortex/edit_intent.py",
    "cortex/executable_repair_forge.py", "cortex/coding_workspace.py", "cortex/source_improvement.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "execute"))
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--prior-report", type=Path, required=True)
    parser.add_argument("--preregistration-hash")
    parser.add_argument("--maximum-calls", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.maximum_calls != 4 or args.output.exists():
        raise ValueError("exactly four calls and a new output path are required")
    prior_report = json.loads(args.prior_report.read_text(encoding="utf-8"))
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    corpus_hash = forge["public_corpus"]["corpus_hash"]
    private = HostCalibrationContractVault().get(corpus_hash)
    if not private:
        raise ValueError("host-private evaluator unavailable; no calls made")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    # Compare inference/compilation/evaluation code, not documentation or the
    # repaired receipt checker. Git object bytes avoid Windows newline drift.
    runtime_hashes = {}
    for name in RUNTIME_FILES:
        current = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        previous = subprocess.check_output(["git", "show", f"{prior_report['source_commit']}:{name}"], cwd=ROOT)
        if current != previous:
            raise ValueError(f"comparison runtime changed since baseline: {name}")
        runtime_hashes[name] = hashlib.sha256(current).hexdigest()
    if subprocess.check_output(["git", "diff", "HEAD", "--", "cortex", "benchmarks/repair_repeatability.py"], cwd=ROOT):
        raise ValueError("commit runtime changes before freezing/executing")
    store = Store(cortex_home() / "cortex.db")
    try:
        if verify_harder_contract_aligned_forge(store, args.repo, forge, private_bundle=private)["valid"] is not True:
            raise ValueError("forge verification failed")
        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        prerequisite = {
            "purpose": "fixed_corpus_repeatability",
            "source_commit": source,
            "prior_source_commit": prior_report["source_commit"],
            "comparison_runtime_hashes": runtime_hashes,
            "model_configuration": "provider_defaults_unpinned",
            "provider_weight_revision_attested": False,
            "maximum_calls": 4,
        }
        if args.phase == "freeze":
            prereg = freeze_structured_repair_screen(
                store, args.repo, forge_artifact=aligned_forge_view(forge), private_bundle=private,
                adapter=adapter, repeat_of_result_receipt_hash=prior_report["result_receipt_hash"],
                governed_prerequisite=prerequisite,
            )
            report = {
                "schema_version": "cortex-repair-repeatability-report/1.0",
                "state": "FROZEN_NOT_EXECUTED", "source_commit": source,
                "preregistration_receipt_hash": prereg["receipt_hash"],
                "prior_result_receipt_hash": prior_report["result_receipt_hash"],
                "planned_calls": 4, "calls_executed": 0,
                "repeatability_policy": prereg["repeatability_binding"]["policy"],
                "model_identity": prereg["model_identity"],
                "runtime_boundary": prerequisite,
            }
        else:
            prereg = store.symbiotic_receipt(str(args.preregistration_hash or ""), repo=args.repo) or {}
            if (
                prereg.get("governed_prerequisite") != prerequisite
                or (prereg.get("repeatability_binding") or {}).get("prior_result_receipt_hash") != prior_report["result_receipt_hash"]
            ):
                raise ValueError("frozen source/prior/run binding changed; no calls made")
            now = time.time()
            print("Executing at most four fresh invocations; no automatic retry.", flush=True)
            result = execute_structured_repair_screen(
                store, args.repo, preregistration=prereg,
                private_bundle=private["executable_private_bundle"], adapter=adapter,
                tools=ToolRegistry(), grant=CapabilityGrant(
                    workspace_root=store.repo(args.repo)["path"], allowed_tools=(),
                    principal_id="repair-repeatability-operator", purpose="frozen four-call repeat",
                    issued_at=now, expires_at=now + 1800, max_tool_calls=0, max_total_tool_seconds=0,
                ),
            )
            audit = verify_structured_repair_screen(store, args.repo, result_receipt_hash=result["receipt_hash"])
            usage = {"input_tokens": 0, "output_tokens": 0}
            for case_hash in result["case_receipt_hashes"]:
                case = store.symbiotic_receipt(case_hash, repo=args.repo)
                trajectory = store.symbiotic_receipt(case["trajectory_receipt_hash"], repo=args.repo)
                for response in trajectory["responses"]:
                    for field in usage:
                        value = response.get("token_usage", {}).get(field)
                        usage[field] = usage[field] + value if usage[field] is not None and type(value) is int else None
            report = {
                "schema_version": "cortex-repair-repeatability-report/1.0",
                "state": "REPEATABILITY_RECONSTRUCTED" if audit["valid"] else "REPEATABILITY_HELD",
                "source_commit": source, "runtime_boundary": prerequisite,
                "preregistration_receipt_hash": prereg["receipt_hash"],
                "result_receipt_hash": result["receipt_hash"],
                "prior_result_receipt_hash": prior_report["result_receipt_hash"],
                "model_identity": result["model_identity"], "evidence_class": result["evidence_class"],
                "calls_executed": result["calls_executed"], "screen": result["screen"],
                "repeatability": result["repeatability"], "provider_reported_usage": usage,
                "canonical_reconstruction": audit, "baseline_calibrated": False,
                "semantic_transfer_established": False, "general_improvement_established": False,
                "private_bundle_persisted_in_artifact": False,
                "host_mutate_authorized": False, "execution_authorized": False,
                "memory_admission_authorized": False, "policy_effect": False,
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2 if report["state"] == "REPEATABILITY_HELD" else 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
