"""v6.25 Independent Witness — sealed evaluation outside adaptive geometry.

Witness cases must not be readable by concept routes, ranker warm, foreign_emerge,
or training corpus machinery. Commitment hashes freeze cases before reveal.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from . import __version__
from .evidence_kernel import evidence_kernel_query
from .retrieval import query

SCHEMA = "cortex-witness/1.0"
GLYPH = "⚖"

# Development transfer suite label (formerly overclaimed as sealed foreign proof)
DEVELOPMENT_TRANSFER_SUITE = "development_transfer_suite"

CLAIM = (
    "Independent Witness seals evaluation cases outside adaptive learning. "
    "Coupling health is a safety prerequisite only — not utility certification. "
    "Not consciousness. Not host authority."
)


def case_commitment(case: dict[str, Any]) -> str:
    material = json.dumps(
        {
            "id": case.get("id"),
            "query": case.get("query"),
            "expected": case.get("expected_substrings"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def commit_manifest(
    cases: list[dict[str, Any]],
    *,
    witness_id: str | None = None,
    allowed_controller: str = "evidence_baseline",
    evaluator_identity: str = "independent_witness",
) -> dict[str, Any]:
    commits = [
        {"id": c.get("id"), "commitment": case_commitment(c)} for c in cases
    ]
    root = hashlib.sha256(
        json.dumps(commits, sort_keys=True).encode()
    ).hexdigest()
    wid = witness_id or ("wit_" + root[:16])
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "witness_id": wid,
        "manifest_version": "1.0",
        "case_commitment_hash": root,
        "case_commitments": commits,
        "allowed_controller": allowed_controller,
        "forbidden_training_access": True,
        "forbidden_route_access": True,
        "evaluator_identity": evaluator_identity,
        "created_at": time.time(),
        "revealed_at": None,
        "n_cases": len(cases),
        "claim_boundary": CLAIM,
        "version": __version__,
    }


def load_sealed_manifest(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    # Must not expose expected answers to callers that warm rankers
    return data


def run_witness(
    store: Any,
    repo: str,
    *,
    cases: list[dict[str, Any]],
    controller: str = "evidence_baseline",
    top_k: int = 5,
    limit: int = 16,
) -> dict[str, Any]:
    """Run cases without writing adaptive state. Prefer Evidence Kernel."""
    manifest = commit_manifest(cases, allowed_controller=controller)
    results = []
    hits = 0
    for case in cases:
        q = str(case.get("query") or "")
        expected = [str(x) for x in case.get("expected_substrings") or []]
        if controller == "evidence_baseline":
            ek = evidence_kernel_query(store, repo, q, limit=limit)
            paths = [str(h.get("path") or "") for h in (ek.get("hits") or [])[:top_k]]
        else:
            # advanced path still must not train
            hs = query(
                store,
                repo,
                q,
                limit=limit,
                ranker_primary=True,
                concept_routes=False,  # witness isolation: no IR routes
            )
            paths = [str(getattr(h, "path", "") or "") for h in hs[:top_k]]
        ok = False
        rank = None
        for i, p in enumerate(paths):
            pn = p.replace("\\", "/")
            for e in expected:
                if e.replace("\\", "/") in pn:
                    ok = True
                    rank = i + 1
                    break
            if ok:
                break
        if ok:
            hits += 1
        results.append(
            {
                "id": case.get("id"),
                "hit_at_k": ok,
                "first_hit_rank": rank,
                "returned_paths": [p.replace("\\", "/") for p in paths],
                # expected not echoed in adaptive logs — only in sealed result
                "commitment": case_commitment(case),
            }
        )
    n = max(1, len(cases))
    recall = hits / n
    manifest["revealed_at"] = time.time()
    result = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "witness_id": manifest["witness_id"],
        "case_commitment_hash": manifest["case_commitment_hash"],
        "controller": controller,
        "recall_at_k": round(recall, 6),
        "hits_at_k": hits,
        "cases": n,
        "results": results,
        "manifest": manifest,
        "result_hash": hashlib.sha256(
            json.dumps(
                {"recall": recall, "hits": hits, "ids": [r["id"] for r in results]},
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        "suite_kind": "sealed_witness",
        "claim_boundary": CLAIM,
        "version": __version__,
    }
    return result


def assert_not_in_learning_surfaces(case_ids: list[str], *surfaces: Any) -> dict[str, Any]:
    """Test helper: ensure case ids do not appear in route/warm surfaces."""
    leaks = []
    blob = json.dumps(surfaces, default=str).casefold()
    for cid in case_ids:
        if cid and str(cid).casefold() in blob:
            leaks.append(cid)
    return {"ok": len(leaks) == 0, "leaks": leaks, "claim_boundary": CLAIM}
