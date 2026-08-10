"""Canonical independent witness commit-before-reveal evidence.

The commitment ledger records only a pre-reveal promise. The immutable
``witness_results`` ledger records the independently evaluated result. A
commitment is therefore never, by itself, a passing witness gate.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__
from .evidence_kernel import evidence_kernel_query

SCHEMA = "cortex-witness/1.2"
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

CREATE TABLE IF NOT EXISTS witness_results(
    witness_result_hash TEXT PRIMARY KEY CHECK(length(witness_result_hash) = 64),
    witness_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    repository_id TEXT,
    body_epoch_id TEXT,
    session_id TEXT,
    task_family TEXT,
    commitment_root TEXT NOT NULL,
    evaluator_identity TEXT NOT NULL,
    controller TEXT NOT NULL,
    cases INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    score REAL,
    recall REAL,
    success INTEGER NOT NULL,
    chronology_ok INTEGER NOT NULL,
    repository_snapshot_hash TEXT,
    cortex_commit_hash TEXT,
    result_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repo, witness_id, witness_result_hash)
);
CREATE INDEX IF NOT EXISTS idx_witness_results_repo_created
ON witness_results(repo, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_witness_results_witness
ON witness_results(repo, witness_id, created_at DESC);

DROP TRIGGER IF EXISTS witness_results_no_update;
CREATE TRIGGER witness_results_no_update
BEFORE UPDATE ON witness_results
BEGIN
    SELECT RAISE(ABORT, 'canonical witness results cannot be updated');
END;
DROP TRIGGER IF EXISTS witness_results_no_delete;
CREATE TRIGGER witness_results_no_delete
BEFORE DELETE ON witness_results
BEGIN
    SELECT RAISE(ABORT, 'canonical witness results cannot be deleted');
END;
"""


def ensure_witness_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _result_material(result: dict[str, Any]) -> dict[str, Any]:
    """Return the explicit, non-circular witness-result hash material."""
    return {
        str(key): value
        for key, value in result.items()
        if str(key) not in {"result_hash", "witness_result_hash"}
    }


def _result_hash(result: dict[str, Any]) -> str:
    return _sha(_result_material(result))


def _repository_id(store: Any, repo: str) -> str:
    try:
        row = store.repo(repo)
        return str(row["repository_id"] or "") if row is not None else ""
    except Exception:
        return ""


def get_witness_result(
    store: Any, repo: str, witness_result_hash: str
) -> dict[str, Any] | None:
    """Resolve one immutable witness result without crossing repository scope."""
    # Resolution is observational.  Store construction owns schema setup;
    # reading a result must not run DDL, commit, or rewrite a trigger.
    try:
        row = store.db.execute(
            """SELECT * FROM witness_results
               WHERE repo=? AND witness_result_hash=?""",
            (str(repo), str(witness_result_hash)),
        ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    try:
        body = json.loads(str(row["result_json"] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict):
        return None
    # Indexed identity is canonical; do not let a body field replace it.
    body["witness_result_hash"] = str(row["witness_result_hash"])
    body["repo"] = str(row["repo"])
    body["repository_id"] = str(row["repository_id"] or "")
    return body


def verify_witness_result(
    store: Any,
    repo: str,
    witness_result_hash: str,
    *,
    expected_controller: str | None = None,
    expected_witness_id: str | None = None,
    expected_outcome_id: str | None = None,
    expected_activation_id: str | None = None,
    expected_transition_hash: str | None = None,
    expected_body_epoch_id: str | None = None,
    expected_session_id: str | None = None,
    expected_repository_snapshot_hash: str | None = None,
    expected_cortex_commit_hash: str | None = None,
) -> dict[str, Any]:
    """Independently verify the immutable result and commitment binding."""
    result = get_witness_result(store, repo, witness_result_hash)
    errors: list[str] = []
    if result is None:
        return {
            "verified": False,
            "witness_result_present": False,
            "identity_valid": False,
            "content_valid": False,
            "binding_valid": False,
            "chronology_valid": False,
            "result_state": "unknown",
            "errors": ["witness_result_not_in_ledger"],
        }

    stored_hash = str(result.get("witness_result_hash") or "")
    recomputed_hash = _result_hash(result)
    identity_valid = (
        len(stored_hash) == 64
        and stored_hash == str(witness_result_hash)
        and recomputed_hash == stored_hash
        and str(result.get("repo") or "") == str(repo)
    )
    if not identity_valid:
        errors.append("witness_result_hash_mismatch")

    witness_id = str(result.get("witness_id") or "")
    commitment = None
    try:
        row = store.db.execute(
            "SELECT * FROM witness_commitments WHERE witness_id=?",
            (witness_id,),
        ).fetchone()
        commitment = dict(row) if row is not None else None
    except Exception:
        commitment = None
    commitment_present = commitment is not None
    if not commitment_present:
        errors.append("witness_commitment_missing")

    evaluator_identity = str(result.get("evaluator_identity") or "")
    controller = str(result.get("controller") or "")
    content_valid = bool(
        evaluator_identity
        and controller
        and isinstance(result.get("cases"), int)
        and isinstance(result.get("hits"), int)
        and isinstance(result.get("success"), bool)
        and bool(result.get("chronology_ok"))
    )
    if not content_valid:
        errors.append("witness_result_content_invalid")
    if expected_controller and controller != str(expected_controller):
        errors.append("witness_controller_mismatch")
    if expected_witness_id and witness_id != str(expected_witness_id):
        errors.append("witness_id_mismatch")

    chronology_valid = False
    binding_valid = False
    if commitment is not None:
        committed_at = float(commitment.get("created_at") or 0.0)
        reveal = float(result.get("revealed_at") or 0.0)
        chronology_valid = (
            committed_at > 0
            and reveal >= committed_at
            and bool(result.get("chronology_ok"))
        )
        if not chronology_valid:
            errors.append("witness_chronology_invalid")
        binding_valid = (
            str(commitment.get("witness_id") or "") == witness_id
            and str(commitment.get("commitment_root") or "")
            == str(result.get("case_commitment_hash") or "")
            and str(commitment.get("evaluator_identity") or "") == evaluator_identity
            and str(commitment.get("allowed_controller") or "") == controller
            and str(commitment.get("cortex_commit_hash") or "")
            == str(result.get("cortex_commit_hash") or "")
        )
        snapshot = str(commitment.get("repository_snapshot_hash") or "")
        if snapshot and snapshot != str(result.get("repository_snapshot_hash") or ""):
            binding_valid = False
            errors.append("witness_repository_snapshot_mismatch")
        if not binding_valid:
            errors.append("witness_commitment_binding_invalid")

    if expected_body_epoch_id is not None:
        if not result.get("body_epoch_id"):
            errors.append("witness_epoch_missing")
        elif str(result.get("body_epoch_id")) != str(expected_body_epoch_id):
            errors.append("witness_epoch_mismatch")
    if expected_session_id is not None:
        if not result.get("session_id"):
            errors.append("witness_session_missing")
        elif str(result.get("session_id")) != str(expected_session_id):
            errors.append("witness_session_mismatch")
    if expected_repository_snapshot_hash and str(result.get("repository_snapshot_hash") or "") != str(expected_repository_snapshot_hash):
        errors.append("witness_repository_snapshot_binding_mismatch")
    if expected_cortex_commit_hash and str(result.get("cortex_commit_hash") or "") != str(expected_cortex_commit_hash):
        errors.append("witness_cortex_commit_binding_mismatch")
    if expected_outcome_id is not None and str(result.get("outcome_id") or "") != str(expected_outcome_id):
        errors.append("witness_outcome_binding_mismatch")
    if expected_activation_id is not None and str(result.get("activation_id") or "") != str(expected_activation_id):
        errors.append("witness_activation_binding_mismatch")
    if expected_transition_hash is not None and str(result.get("transition_hash") or "") != str(expected_transition_hash):
        errors.append("witness_transition_binding_mismatch")

    # The sealed suite's semantic criterion is full case coverage.  A stored
    # ``success`` bit cannot override the independently recomputed criterion.
    cases = int(result.get("cases") or 0)
    hits = int(result.get("hits") or 0)
    semantic_success = cases > 0 and hits == cases
    semantic_valid = bool(result.get("success") is True and semantic_success)
    if not semantic_valid:
        errors.append("witness_success_criterion_not_met")

    verified = bool(
        identity_valid
        and content_valid
        and commitment_present
        and chronology_valid
        and binding_valid
        and semantic_valid
        and not errors
    )
    return {
        "verified": verified,
        "witness_result_present": True,
        "witness_id": witness_id,
        "witness_result_hash": stored_hash,
        "identity_valid": identity_valid,
        "content_valid": content_valid,
        "binding_valid": binding_valid,
        "chronology_valid": chronology_valid,
        "commitment_present": commitment_present,
        "result_state": "pass" if verified else "fail",
        "success_criterion": "all_cases_hit_at_k",
        "errors": sorted(set(errors)),
        "result": result,
    }


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
    body_epoch_id: str | None = None,
    session_id: str | None = None,
    task_family: str | None = None,
    outcome_id: str | None = None,
    activation_id: str | None = None,
    transition_hash: str | None = None,
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
    commitment_created_at = float(commitment.get("created_at") or 0)
    # The result is materialized at reveal; keep the public chronology field
    # monotonic for compatibility while retaining commitment_created_at.
    result_created_at = revealed_at
    repository_id = _repository_id(store, repo)
    result = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "ok": True,
        "repo": repo,
        "witness_id": commitment["witness_id"],
        "case_commitment_hash": commitment["case_commitment_hash"],
        "commitment_created_at": commitment_created_at,
        "evaluator_identity": commitment.get("evaluator_identity") or "",
        "repository_id": repository_id,
        "repository_snapshot_hash": repository_snapshot_hash
        or commitment.get("repository_snapshot_hash"),
        "cortex_commit_hash": cortex_commit_hash
        or commitment.get("cortex_commit_hash")
        or __version__,
        "body_epoch_id": body_epoch_id,
        "session_id": session_id,
        "task_family": task_family,
        "outcome_id": outcome_id,
        "activation_id": activation_id,
        "transition_hash": transition_hash,
        "controller": controller,
        "recall_at_k": round(recall, 6),
        # Canonical indexed names are deliberately present in the immutable
        # result body as well as the compatibility aliases.  Verification
        # must be able to recompute the semantic criterion from the stored
        # result without trusting a caller-provided Boolean.
        "score": round(recall, 6),
        "hits": hits,
        "hits_at_k": hits,
        "cases": n,
        "results": results,
        "created_at": result_created_at,
        "revealed_at": revealed_at,
        "chronology_ok": commitment_created_at <= revealed_at,
        "success": bool(len(revealed_cases) > 0 and hits == len(revealed_cases)),
        "suite_kind": "sealed_witness",
        "claim_boundary": CLAIM,
        "version": __version__,
    }
    result["result_state"] = "success" if result["success"] else "failure"
    result_hash = _result_hash(result)
    result["result_hash"] = result_hash
    result["witness_result_hash"] = result_hash
    # Do not store plaintext cases — only the immutable aggregate result.
    try:
        ensure_witness_tables(store)
        store.db.execute(
            "UPDATE witness_commitments SET revealed_at=? WHERE witness_id=?",
            (revealed_at, commitment["witness_id"]),
        )
        existing = store.db.execute(
            "SELECT result_json FROM witness_results WHERE repo=? AND witness_result_hash=?",
            (repo, result_hash),
        ).fetchone()
        if existing is None:
            store.db.execute(
                """INSERT INTO witness_results(
                     witness_result_hash, witness_id, repo, repository_id,
                     body_epoch_id, session_id, task_family, commitment_root,
                     evaluator_identity, controller, cases, hits, score, recall,
                     success, chronology_ok, repository_snapshot_hash,
                     cortex_commit_hash, result_json, created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result_hash,
                    result["witness_id"],
                    repo,
                    repository_id,
                    result.get("body_epoch_id"),
                    result.get("session_id"),
                    result.get("task_family"),
                    result["case_commitment_hash"],
                    result["evaluator_identity"],
                    result["controller"],
                    int(result["cases"]),
                    int(result["hits_at_k"]),
                    float(result["recall_at_k"]),
                    float(result["recall_at_k"]),
                    1 if result["success"] else 0,
                    1 if result["chronology_ok"] else 0,
                    result.get("repository_snapshot_hash"),
                    result.get("cortex_commit_hash"),
                    _canonical(result),
                    result_created_at,
                ),
            )
            result["canonical_persistence"] = "committed"
            result["canonical_persistence_duplicate"] = False
        else:
            result["canonical_persistence"] = "duplicate"
            result["canonical_persistence_duplicate"] = True
        store.db.commit()
    except Exception as exc:
        result["canonical_persistence"] = "failed"
        result["canonical_persistence_error"] = f"{type(exc).__name__}:{exc}"
    return result


def assert_not_in_learning_surfaces(case_ids: list[str], *surfaces: Any) -> dict[str, Any]:
    leaks = []
    blob = json.dumps(surfaces, default=str).casefold()
    for cid in case_ids:
        if cid and str(cid).casefold() in blob:
            leaks.append(cid)
    return {"ok": len(leaks) == 0, "leaks": leaks, "claim_boundary": CLAIM}


__all__ = [
    "SCHEMA",
    "assert_not_in_learning_surfaces",
    "case_commitment",
    "commit_manifest",
    "ensure_witness_tables",
    "get_witness_result",
    "run_witness",
    "verify_reveal",
    "verify_witness_result",
]
