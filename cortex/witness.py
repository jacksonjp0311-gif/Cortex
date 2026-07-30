"""v6.25.1 Independent Witness — commit-before-reveal chronology."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from . import __version__
from .evidence_kernel import evidence_kernel_query

SCHEMA = "cortex-witness/1.1"
GLYPH = "⚖"
DEVELOPMENT_TRANSFER_SUITE = "development_transfer_suite"

CLAIM = (
    "Independent Witness seals evaluation cases outside adaptive learning. "
    "Commitment predates reveal. Coupling is a safety prerequisite only. "
    "Not consciousness. Not host authority."
)

DDL = """
CREATE TABLE IF NOT EXISTS witness_commitments(
    witness_id TEXT PRIMARY KEY,
    commitment_root TEXT NOT NULL,
    case_commitments_json TEXT NOT NULL,
    evaluator_identity TEXT NOT NULL,
    created_at REAL NOT NULL,
    allowed_controller TEXT NOT NULL,
    repository_snapshot_hash TEXT,
    cortex_commit_hash TEXT,
    revealed_at REAL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
"""


def ensure_witness_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


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
    repository_snapshot_hash: str | None = None,
    cortex_commit_hash: str | None = None,
    store: Any = None,
) -> dict[str, Any]:
    """Commitment phase — stores hashes only, no plaintext answers in adaptive surfaces."""
    commits = [{"id": c.get("id"), "commitment": case_commitment(c)} for c in cases]
    # Public commitment object strips queries/expected
    public_commits = [{"id": c["id"], "commitment": c["commitment"]} for c in commits]
    root = hashlib.sha256(json.dumps(public_commits, sort_keys=True).encode()).hexdigest()
    wid = witness_id or ("wit_" + root[:16])
    created = time.time()
    commitment = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "witness_id": wid,
        "manifest_version": "1.1",
        "case_commitment_hash": root,
        "case_commitments": public_commits,
        "allowed_controller": allowed_controller,
        "forbidden_training_access": True,
        "forbidden_route_access": True,
        "evaluator_identity": evaluator_identity,
        "created_at": created,
        "revealed_at": None,
        "repository_snapshot_hash": repository_snapshot_hash,
        "cortex_commit_hash": cortex_commit_hash or __version__,
        "n_cases": len(cases),
        "claim_boundary": CLAIM,
        "version": __version__,
    }
    if store is not None:
        ensure_witness_tables(store)
        # store commitments only — not plaintext cases
        store.db.execute(
            """
            INSERT OR REPLACE INTO witness_commitments(
              witness_id, commitment_root, case_commitments_json, evaluator_identity,
              created_at, allowed_controller, repository_snapshot_hash, cortex_commit_hash, metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                wid,
                root,
                json.dumps(public_commits),
                evaluator_identity,
                created,
                allowed_controller,
                repository_snapshot_hash,
                cortex_commit_hash or __version__,
                json.dumps({"n_cases": len(cases)}),
            ),
        )
        store.db.commit()
    return commitment


def verify_reveal(
    commitment: dict[str, Any],
    revealed_cases: list[dict[str, Any]],
    *,
    repository_snapshot_hash: str | None = None,
    cortex_commit_hash: str | None = None,
) -> dict[str, Any]:
    """Reveal phase — verify hashes match commitment; reject snapshot/commit drift."""
    if not commitment or not commitment.get("case_commitment_hash"):
        return {"ok": False, "error": "missing_preexisting_commitment"}
    if commitment.get("revealed_at"):
        # allow re-verify
        pass
    expected = {
        str(c.get("id")): str(c.get("commitment"))
        for c in (commitment.get("case_commitments") or [])
    }
    for case in revealed_cases:
        cid = str(case.get("id"))
        h = case_commitment(case)
        if cid not in expected:
            return {"ok": False, "error": "unknown_case_id", "id": cid}
        if h != expected[cid]:
            return {"ok": False, "error": "case_hash_mismatch", "id": cid}
    # recompute root
    public = [{"id": k, "commitment": expected[k]} for k in sorted(expected.keys())]
    # preserve original order from commitment
    public = list(commitment.get("case_commitments") or [])
    root = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
    if root != commitment.get("case_commitment_hash"):
        # order-sensitive — use list as stored
        root2 = hashlib.sha256(
            json.dumps(commitment.get("case_commitments") or [], sort_keys=True).encode()
        ).hexdigest()
        if root2 != commitment.get("case_commitment_hash"):
            return {"ok": False, "error": "commitment_root_mismatch"}
    if (
        commitment.get("repository_snapshot_hash")
        and repository_snapshot_hash
        and commitment["repository_snapshot_hash"] != repository_snapshot_hash
    ):
        return {"ok": False, "error": "repository_snapshot_changed"}
    if (
        commitment.get("cortex_commit_hash")
        and cortex_commit_hash
        and commitment["cortex_commit_hash"] != cortex_commit_hash
    ):
        return {"ok": False, "error": "cortex_commit_changed"}
    return {
        "ok": True,
        "witness_id": commitment.get("witness_id"),
        "created_at": commitment.get("created_at"),
        "revealed_at": time.time(),
    }


def run_witness(
    store: Any,
    repo: str,
    *,
    commitment: dict[str, Any] | None = None,
    revealed_cases: list[dict[str, Any]] | None = None,
    cases: list[dict[str, Any]] | None = None,  # legacy — rejected if no commitment
    controller: str = "evidence_baseline",
    top_k: int = 5,
    limit: int = 16,
    repository_snapshot_hash: str | None = None,
    cortex_commit_hash: str | None = None,
) -> dict[str, Any]:
    """Run revealed cases against preexisting commitment. Does not train."""
    # Reject legacy path that commits during evaluation
    if cases is not None and commitment is None:
        return {
            "ok": False,
            "error": "commitment_required_before_reveal",
            "hint": "Call commit_manifest first, then run_witness(commitment=..., revealed_cases=...)",
            "claim_boundary": CLAIM,
        }
    if commitment is None or revealed_cases is None:
        return {
            "ok": False,
            "error": "commitment_and_revealed_cases_required",
            "claim_boundary": CLAIM,
        }
    v = verify_reveal(
        commitment,
        revealed_cases,
        repository_snapshot_hash=repository_snapshot_hash,
        cortex_commit_hash=cortex_commit_hash or __version__,
    )
    if not v.get("ok"):
        return {**v, "claim_boundary": CLAIM}

    results = []
    hits = 0
    for case in revealed_cases:
        q = str(case.get("query") or "")
        expected = [str(x) for x in case.get("expected_substrings") or []]
        if controller == "evidence_baseline":
            ek = evidence_kernel_query(store, repo, q, limit=limit)
            paths = [str(h.get("path") or "") for h in (ek.get("hits") or [])[:top_k]]
        else:
            from .retrieval import query

            hs = query(
                store,
                repo,
                q,
                limit=limit,
                ranker_primary=True,
                concept_routes=False,
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
                "commitment": case_commitment(case),
            }
        )
    n = max(1, len(revealed_cases))
    recall = hits / n
    revealed_at = float(v.get("revealed_at") or time.time())
    created_at = float(commitment.get("created_at") or 0)
    result = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "ok": True,
        "repo": repo,
        "witness_id": commitment["witness_id"],
        "case_commitment_hash": commitment["case_commitment_hash"],
        "controller": controller,
        "recall_at_k": round(recall, 6),
        "hits_at_k": hits,
        "cases": n,
        "results": results,
        "created_at": created_at,
        "revealed_at": revealed_at,
        "chronology_ok": created_at <= revealed_at,
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
    # Do not store plaintext cases — only aggregate
    try:
        ensure_witness_tables(store)
        store.db.execute(
            "UPDATE witness_commitments SET revealed_at=? WHERE witness_id=?",
            (revealed_at, commitment["witness_id"]),
        )
        store.db.commit()
    except Exception:
        pass
    return result


def assert_not_in_learning_surfaces(case_ids: list[str], *surfaces: Any) -> dict[str, Any]:
    leaks = []
    blob = json.dumps(surfaces, default=str).casefold()
    for cid in case_ids:
        if cid and str(cid).casefold() in blob:
            leaks.append(cid)
    return {"ok": len(leaks) == 0, "leaks": leaks, "claim_boundary": CLAIM}
