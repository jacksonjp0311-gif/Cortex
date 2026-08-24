"""Evaluate canonical transfer trials with the model-neutral v9.7 gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cortex.competence_differentiation import (
    evaluate_competence_differentiation,
    verify_differentiation_receipt,
)
from cortex.store import Store


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct paired competence effects from canonical transfer receipts. "
            "No model or provider selection is accepted by this command."
        )
    )
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--competence-id", required=True)
    parser.add_argument("--trial-id", action="append", required=True)
    parser.add_argument("--cohort-nonce", required=True)
    parser.add_argument("--minimum-cases", type=int, default=8)
    parser.add_argument("--minimum-effect", type=float, default=0.05)
    parser.add_argument(
        "--required-evidence-class",
        choices=("live_empirical", "empirically_attested", "structural"),
        default="live_empirical",
    )
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = _parser().parse_args()
    store = Store(args.home.resolve() / "cortex.db")
    try:
        receipt = evaluate_competence_differentiation(
            store,
            str(args.repo),
            competence_id=str(args.competence_id),
            trial_ids=[str(item) for item in args.trial_id],
            policy={
                "minimum_cases": int(args.minimum_cases),
                "minimum_effect": float(args.minimum_effect),
                "required_evidence_class": str(args.required_evidence_class),
            },
            cohort_nonce=str(args.cohort_nonce),
            persist=True,
        )
        checked = verify_differentiation_receipt(
            store, str(args.repo), str(receipt["cohort_id"])
        )
        output = {
            "status": receipt.get("status"),
            "cohort_id": receipt.get("cohort_id"),
            "receipt_hash": receipt.get("receipt_hash"),
            "receipt_valid": checked.get("valid") is True,
            "case_count": receipt.get("case_count"),
            "paired_effects": receipt.get("paired_effects"),
            "discriminability": receipt.get("discriminability"),
            "negative_transfer_rate": receipt.get("negative_transfer_rate"),
            "failed_gates": receipt.get("failed_gates"),
            "model_identity_used_in_scoring": False,
            "provider_identity_used_in_scoring": False,
            "distribution_authorized": False,
            "execution_authorized": False,
            "host_mutate_authorized": False,
            "claim_boundary": receipt.get("claim_boundary"),
        }
        print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if checked.get("valid") is True else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
