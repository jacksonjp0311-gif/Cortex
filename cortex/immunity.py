"""v6.25 Cortex Immunology — detect → trace → quarantine → plan → repair → verify → readmit."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__
from .lineage import (
    ensure_lineage_tables,
    lineage_integrity_check,
    propagation_trace,
    record_artifact,
)
from .quarantine import active_quarantined_ids, quarantine_artifacts
from .unlearning import (
    apply_unlearning,
    plan_unlearning,
    rollback_repair,
)

SCHEMA = "cortex-immunity/1.0"
GLYPH = "🛡"

CLAIM = (
    "Cortex Immunology provides provenance-directed quarantine, selective unlearning, "
    "repair verification, and trusted evidence fallback for an adaptive repository-memory "
    "runtime. It does not establish biological life, consciousness, autonomous host "
    "authority, or perfect protection from adversarial memory."
)

DDL = """
CREATE TABLE IF NOT EXISTS memory_wounds(
    wound_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    kind TEXT NOT NULL,
    origin_ids_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    created_at REAL NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
"""


def ensure_immunity_tables(store: Any) -> None:
    ensure_lineage_tables(store)
    store.db.executescript(DDL)
    store.db.commit()


def open_wound(
    store: Any,
    repo: str,
    *,
    kind: str,
    origin_ids: list[str],
    summary: str,
    severity: str = "medium",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_immunity_tables(store)
    now = time.time()
    wid = "mw_" + hashlib.sha256(f"{repo}|{kind}|{origin_ids}|{now}".encode()).hexdigest()[:18]
    store.db.execute(
        """
        INSERT INTO memory_wounds(wound_id, repo, kind, origin_ids_json, summary, severity, created_at, metadata_json)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            wid,
            repo,
            kind,
            json.dumps(list(origin_ids)),
            summary,
            severity,
            now,
            json.dumps(metadata or {}),
        ),
    )
    store.db.commit()
    return {
        "wound_id": wid,
        "repo": repo,
        "kind": kind,
        "origin_ids": list(origin_ids),
        "summary": summary,
        "severity": severity,
        "schema_version": SCHEMA,
        "claim_boundary": CLAIM,
    }


def scan_wounds(store: Any, repo: str) -> dict[str, Any]:
    """Detect wounds from lineage integrity + certificate + explicit markers."""
    ensure_immunity_tables(store)
    found: list[dict[str, Any]] = []
    # Lineage issues
    lin = lineage_integrity_check(store, repo)
    for issue in lin.get("issues") or []:
        w = open_wound(
            store,
            repo,
            kind="lineage_" + str(issue.get("kind") or "issue"),
            origin_ids=[str(issue.get("artifact_id") or "unresolved")],
            summary=json.dumps(issue, sort_keys=True),
            severity="high" if issue.get("kind") == "cycle" else "medium",
            metadata={"auto": True, "issue": issue},
        )
        found.append(w)
    # Certificate degraded
    try:
        row = store.latest_bootstrap(repo)
        if row:
            cert = json.loads(row["certificate"] or "{}")
            if cert.get("status") not in {"verified", None} and cert.get("status"):
                if cert.get("status") != "verified":
                    w = open_wound(
                        store,
                        repo,
                        kind="certificate_degraded",
                        origin_ids=["certificate"],
                        summary=f"certificate status={cert.get('status')}",
                        severity="high",
                        metadata={"auto": True},
                    )
                    found.append(w)
    except Exception:
        pass
    # Active wounds list
    open_rows = store.db.execute(
        "SELECT * FROM memory_wounds WHERE repo=? AND resolved=0 ORDER BY created_at DESC LIMIT 40",
        (repo,),
    ).fetchall()
    open_list = [dict(r) for r in open_rows]
    critical = any(str(r.get("severity") or "") == "critical" for r in open_list)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "new_wounds": found,
        "open_wounds": open_list,
        "lineage": lin,
        "has_critical_wound": critical,
        "quarantined_n": len(active_quarantined_ids(store, repo)),
        "claim_boundary": CLAIM,
    }


def trace_artifact(store: Any, repo: str, artifact_id: str) -> dict[str, Any]:
    from .lineage import ancestors_of, descendants_of

    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "artifact_id": artifact_id,
        "ancestors": ancestors_of(store, repo, artifact_id),
        "descendants": descendants_of(store, repo, artifact_id),
        "propagation": propagation_trace(store, repo, [artifact_id]),
        "claim_boundary": CLAIM,
    }


def quarantine_from_wound(
    store: Any,
    repo: str,
    *,
    wound_id: str | None = None,
    artifact_id: str | None = None,
    reason: str = "immunity_quarantine",
) -> dict[str, Any]:
    origins: list[str] = []
    if artifact_id:
        origins = [artifact_id]
    if wound_id:
        row = store.db.execute(
            "SELECT origin_ids_json FROM memory_wounds WHERE wound_id=? AND repo=?",
            (wound_id, repo),
        ).fetchone()
        if row:
            origins.extend(json.loads(row["origin_ids_json"] or "[]"))
    origins = list(dict.fromkeys(str(o) for o in origins))
    trace = propagation_trace(store, repo, origins)
    targets = origins + list(trace.get("descendants") or [])
    env = quarantine_artifacts(
        store, repo, targets, reason=reason, wound_id=wound_id
    )
    return {**env, "trace": trace, "claim_boundary": CLAIM}


def plan_repair(store: Any, repo: str, wound_id: str) -> dict[str, Any]:
    row = store.db.execute(
        "SELECT * FROM memory_wounds WHERE wound_id=? AND repo=?",
        (wound_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "wound_not_found"}
    origins = json.loads(row["origin_ids_json"] or "[]")
    plan = plan_unlearning(
        store, repo, wound_id=wound_id, origin_ids=origins, reason=str(row["kind"])
    )
    return plan


def apply_repair(
    store: Any,
    repo: str,
    plan_id: str,
    *,
    authorize: bool = False,
    governance_mode: str = "normal",
) -> dict[str, Any]:
    return apply_unlearning(
        store, repo, plan_id, authorize=authorize, governance_mode=governance_mode
    )


def verify_repair(
    store: Any,
    repo: str,
    repair_id: str,
    *,
    governor: Any = None,
    home: Any = None,
) -> dict[str, Any]:
    """Post-repair checks: lineage, quarantine completeness, evidence kernel smoke."""
    from .evidence_kernel import evidence_kernel_query
    from .unlearning import ensure_unlearning_tables

    ensure_unlearning_tables(store)
    row = store.db.execute(
        "SELECT * FROM repair_receipts WHERE repair_id=? AND repo=?",
        (repair_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "repair_not_found"}
    lin = lineage_integrity_check(store, repo)
    ek = evidence_kernel_query(store, repo, "authority evidence source", limit=5)
    checks = {
        "lineage_ok": bool(lin.get("ok")),
        "evidence_kernel_ok": bool(ek.get("ok")),
        "receipt_present": True,
        "repair_marked_ok": bool(row["ok"]),
    }
    ok = all(checks.values())
    decision = {
        "schema_version": SCHEMA,
        "repair_id": repair_id,
        "repo": repo,
        "checks": checks,
        "ok": ok,
        "readmit_allowed": ok,
        "claim_boundary": CLAIM,
    }
    try:
        store.set_setting(f"repair_verify:{repo}:{repair_id}", decision)
    except Exception:
        pass
    return decision


def readmit(
    store: Any,
    repo: str,
    repair_id: str,
    *,
    authorize: bool = False,
    verify_result: dict[str, Any] | None = None,
    skip_geometry: bool = False,
) -> dict[str, Any]:
    if not authorize:
        return {"ok": False, "error": "authorize_required", "claim_boundary": CLAIM}
    # v7.1 constitutional geometry boundary (repair_readmit requires e,a,t,w)
    try:
        from .epoch import ensure_current_epoch

        ensure_current_epoch(store, repo, reason="repair_readmit")
    except Exception:
        pass
    v = verify_result or verify_repair(store, repo, repair_id)
    if not skip_geometry:
        try:
            from .constitutional_path import assess_operation_at_boundary

            geometry = assess_operation_at_boundary(
                store,
                repo,
                "repair_readmit",
                authority_ok=True,
                witness_ok=bool(v.get("ok") and v.get("readmit_allowed")),
                require_witness=True,
            )
            if not geometry.get("allowed"):
                return {
                    "ok": False,
                    "readmitted": False,
                    "error": "constitutional_geometry_denied",
                    "geometry": geometry,
                    "coordinate": geometry.get("coordinate"),
                    "missing_axes": geometry.get("missing_axes"),
                    "reasons": geometry.get("reasons"),
                    "required_legal_path": geometry.get("required_legal_path"),
                    "verify": v,
                    "claim_boundary": CLAIM,
                }
        except Exception as exc:
            return {
                "ok": False,
                "readmitted": False,
                "error": f"geometry_error:{type(exc).__name__}",
                "detail": str(exc),
                "verify": v,
                "claim_boundary": CLAIM,
            }
    if not v.get("readmit_allowed"):
        # rollback if snapshot known
        row = store.db.execute(
            "SELECT snapshot_id FROM repair_receipts WHERE repair_id=? AND repo=?",
            (repair_id, repo),
        ).fetchone()
        rb = None
        if row:
            rb = rollback_repair(store, repo, str(row["snapshot_id"]))
        return {
            "ok": False,
            "readmitted": False,
            "error": "verify_failed",
            "verify": v,
            "rollback": rb,
            "claim_boundary": CLAIM,
        }
    # Mark related wounds resolved when possible
    store.db.execute(
        """
        UPDATE memory_wounds SET resolved=1 WHERE repo=? AND wound_id IN (
          SELECT wound_id FROM unlearning_plans WHERE repair_id=?
        )
        """,
        (repo, repair_id),
    )
    store.db.commit()
    return {
        "ok": True,
        "readmitted": True,
        "repair_id": repair_id,
        "verify": v,
        "claim_boundary": CLAIM,
    }


def immunity_status(store: Any, repo: str) -> dict[str, Any]:
    ensure_immunity_tables(store)
    open_n = store.db.execute(
        "SELECT COUNT(1) AS c FROM memory_wounds WHERE repo=? AND resolved=0",
        (repo,),
    ).fetchone()
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "open_wounds": int(open_n["c"] if open_n else 0),
        "quarantined_n": len(active_quarantined_ids(store, repo)),
        "lineage": lineage_integrity_check(store, repo),
        "claim_boundary": CLAIM,
        "version": __version__,
    }
