"""Deterministic v8.2.3 source-admission triad benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.source_admission import source_admission_score  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    aligned = source_admission_score(
        query_text="source admission candidate field",
        path="cortex/source_admission.py",
        semantic_similarity=0.86,
        lexical_rank=1,
    )
    semantic_lesion = source_admission_score(
        query_text="source admission candidate field",
        path="cortex/source_admission.py",
        semantic_similarity=-0.90,
        lexical_rank=1,
    )
    evidence_lesion = source_admission_score(
        query_text="source admission candidate field",
        path="docs/source_admission.md",
        semantic_similarity=0.99,
        lexical_rank=1,
    )
    checks = {
        "aligned_source_admitted": aligned["eligible"] is True,
        "semantic_floor_blocks": semantic_lesion["eligible"] is False,
        "evidence_floor_blocks": evidence_lesion["eligible"] is False,
        "triad_is_monotone": aligned["triadic_alignment"] > semantic_lesion["triadic_alignment"],
        "shadow_only": all(item["shadow_only"] for item in (aligned, semantic_lesion, evidence_lesion)),
    }
    receipt = {
        "schema_version": "cortex-source-admission-benchmark/1.0",
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": "Candidate admission telemetry is counterfactual and policy-inert.",
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
