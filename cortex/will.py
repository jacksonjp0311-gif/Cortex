"""v8.5 — Authenticated principal will (direction without invention).

Will supplies origin-authenticated *direction*: prioritize, deprioritize,
admit, or forbid distillation candidates. It never invents facts, never
mutates the host, and never auto-executes. Evidence remains authoritative
for what happened; will only ranks what may be retained under open gates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-will/1.0"
VERSION = "8.5.0"
GLYPH = "⚖⟹"
CLAIM_BOUNDARY = (
    "Authenticated will supplies direction only. It cannot invent facts, "
    "alter measured evidence, mutate host source, auto-execute tools, or "
    "open durable memory alone. Membrane admission still requires verified "
    "candidates and open ΓΞWOS gates."
)

WILL_SCOPES = frozenset(
    {
        "will.direct",
        "will.prioritize",
        "will.admit",
    }
)
FORBIDDEN_SCOPES = frozenset(
    {
        "host.mutate",
        "source.edit",
        "deploy",
        "execute",
        "invent_fact",
        "token.mint_self",
    }
)
CLAUSE_KINDS = frozenset(
    {
        "prioritize_type",
        "deprioritize_type",
        "admit_type",
        "forbid_type",
        "admit_candidate",
        "cap_retain",
        "prefer_support_min",
    }
)
SUPPORT_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def register_will_principal(
    store: Any,
    repo: str,
    principal_id: str,
    display_name: str,
    *,
    secret: str = "",
) -> dict[str, Any]:
    """Register a local will principal. Secret is shown once; not re-readable."""
    principal_id = str(principal_id or "").strip()
    if not principal_id:
        raise ValueError("principal_id required")
    secret = secret or _sha(f"{repo}|{principal_id}|{time.time()}|{uuid.uuid4().hex}")
    secret_hash = _secret_hash(secret)
    store.db.execute(
        """
        INSERT INTO will_principals(repo, principal_id, display_name, secret_hash, created_at)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(repo, principal_id) DO UPDATE SET
            display_name=excluded.display_name,
            secret_hash=excluded.secret_hash
        """,
        (repo, principal_id, display_name, secret_hash, time.time()),
    )
    store.db.commit()
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "registered": True,
        "repo": repo,
        "principal_id": principal_id,
        "display_name": display_name,
        "secret": secret,
        "secret_shown_once": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "policy_effect": False,
        "execution_authorized": False,
        "memory_write_authorized": False,
        "host_mutate_authorized": False,
    }


def _load_principal(store: Any, repo: str, principal_id: str) -> Mapping[str, Any] | None:
    row = store.db.execute(
        "SELECT * FROM will_principals WHERE repo=? AND principal_id=?",
        (repo, principal_id),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def _normalize_clauses(clauses: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(clauses or ()):
        if not isinstance(raw, Mapping):
            continue
        kind = str(raw.get("kind") or raw.get("clause_kind") or "").strip()
        if kind not in CLAUSE_KINDS:
            raise ValueError(f"unknown will clause kind: {kind}")
        clause = {
            "clause_id": str(raw.get("clause_id") or f"cl_{index}_{kind}"),
            "kind": kind,
            "candidate_types": [
                str(t) for t in (raw.get("candidate_types") or ()) if str(t).strip()
            ],
            "candidate_ids": [
                str(t) for t in (raw.get("candidate_ids") or ()) if str(t).strip()
            ],
            "transition_classes": [
                str(t) for t in (raw.get("transition_classes") or ()) if str(t).strip()
            ],
            "max_retain": raw.get("max_retain"),
            "min_support": raw.get("min_support"),
            "priority": int(raw.get("priority") or 0),
            "notes": str(raw.get("notes") or ""),
        }
        out.append(clause)
    return out


def _normalize_scopes(scopes: Sequence[str] | None) -> list[str]:
    clean: list[str] = []
    for scope in scopes or ("will.direct", "will.prioritize", "will.admit"):
        s = str(scope).strip()
        if s in FORBIDDEN_SCOPES:
            raise ValueError(f"forbidden will scope: {s}")
        if s not in WILL_SCOPES:
            raise ValueError(f"unknown will scope: {s}")
        if s not in clean:
            clean.append(s)
    if not clean:
        raise ValueError("will requires at least one scope")
    return sorted(clean)


def issue_will(
    store: Any,
    repo: str,
    *,
    principal_id: str,
    secret: str,
    clauses: Sequence[Mapping[str, Any]] | None = None,
    scopes: Sequence[str] | None = None,
    session_id: str | None = None,
    body_epoch_id: str | None = None,
    repository_id: str | None = None,
    ttl_seconds: int = 86_400,
    intent_summary: str = "",
    persist: bool = True,
) -> dict[str, Any]:
    """Mint a signed WillRoot. Secret must match the registered principal."""
    principal = _load_principal(store, repo, principal_id)
    if principal is None:
        return {
            "issued": False,
            "reason": "principal_not_registered",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    if _secret_hash(secret) != str(principal["secret_hash"]):
        return {
            "issued": False,
            "reason": "secret_mismatch",
            "claim_boundary": CLAIM_BOUNDARY,
        }

    if not repository_id:
        repository = store.repo(repo)
        if repository is not None:
            try:
                repository_id = str(repository["repository_id"] or "")
            except (KeyError, TypeError, IndexError):
                repository_id = str(getattr(repository, "repository_id", "") or "")
        else:
            repository_id = ""
    repository_id = str(repository_id or "")
    now = time.time()
    not_after = now + max(60, int(ttl_seconds))
    clause_list = _normalize_clauses(clauses)
    scope_list = _normalize_scopes(scopes)
    will_id = "will_" + _sha(
        {
            "repo": repo,
            "principal_id": principal_id,
            "now": now,
            "clauses": clause_list,
            "nonce": uuid.uuid4().hex,
        }
    )[:24]

    payload = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "will_root",
        "repo": repo,
        "repository_id": repository_id,
        "principal_id": principal_id,
        "display_name": principal.get("display_name"),
        "will_id": will_id,
        "session_id": session_id,
        "body_epoch_id": body_epoch_id or "",
        "scopes": scope_list,
        "clauses": clause_list,
        "intent_summary": str(intent_summary or ""),
        "issued_at": now,
        "not_before": now,
        "not_after": not_after,
        "signature_alg": "hmac-sha256",
        "invents_facts": False,
        "alters_evidence": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "memory_write_authorized": False,
        "durable_write_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    payload_hash = _sha(payload)
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    event_id = "evt_" + _sha({"will_id": will_id, "payload_hash": payload_hash})[:24]
    material = {
        **payload,
        "payload_hash": payload_hash,
        "signature": signature,
        "event_id": event_id,
    }
    receipt_hash = _sha(material)
    receipt = {
        **material,
        "receipt_hash": receipt_hash,
        "issued": True,
        "created_at": now,
    }
    if persist:
        try:
            store.append_will_receipt(repo, receipt)
        except Exception:
            store.set_setting(f"will_latest:{repo}", receipt)
        else:
            store.set_setting(f"will_latest:{repo}", receipt)
    return receipt


def verify_will(
    store: Any,
    repo: str,
    will: Mapping[str, Any],
    *,
    secret: str | None = None,
    now: float | None = None,
    require_session_id: str | None = None,
    require_body_epoch_id: str | None = None,
) -> dict[str, Any]:
    """Verify structural integrity, optional HMAC, time window, and bindings."""
    now = time.time() if now is None else float(now)
    checks: dict[str, bool] = {}
    errors: list[str] = []

    checks["kind"] = str(will.get("kind") or "") == "will_root"
    checks["repo"] = str(will.get("repo") or "") == str(repo)
    checks["will_id"] = bool(will.get("will_id"))
    checks["principal_id"] = bool(will.get("principal_id"))
    checks["scopes_present"] = bool(will.get("scopes"))
    checks["signature_present"] = bool(will.get("signature") and will.get("payload_hash"))
    checks["no_host_mutate"] = not bool(will.get("host_mutate_authorized"))
    checks["no_execution"] = not bool(will.get("execution_authorized"))
    checks["no_invent"] = will.get("invents_facts") is False
    checks["no_alter_evidence"] = will.get("alters_evidence") is False

    scopes = [str(s) for s in (will.get("scopes") or ())]
    checks["scopes_legal"] = all(s in WILL_SCOPES for s in scopes) and not any(
        s in FORBIDDEN_SCOPES for s in scopes
    )
    for clause in will.get("clauses") or ():
        if not isinstance(clause, Mapping):
            checks["clauses_legal"] = False
            errors.append("malformed_clause")
            break
        if str(clause.get("kind") or "") not in CLAUSE_KINDS:
            checks["clauses_legal"] = False
            errors.append(f"bad_clause_kind:{clause.get('kind')}")
            break
    else:
        checks["clauses_legal"] = True

    not_before = float(will.get("not_before") or 0)
    not_after = float(will.get("not_after") or 0)
    checks["time_window"] = not_before <= now <= not_after if not_after else False

    if require_session_id is not None and will.get("session_id"):
        checks["session_bound"] = str(will.get("session_id")) == str(require_session_id)
    else:
        checks["session_bound"] = True
    if require_body_epoch_id is not None and will.get("body_epoch_id"):
        checks["epoch_bound"] = str(will.get("body_epoch_id")) == str(
            require_body_epoch_id
        )
    else:
        checks["epoch_bound"] = True

    # Reconstruct payload hash without signature fields.
    payload = {
        k: will.get(k)
        for k in (
            "schema_version",
            "version",
            "glyph",
            "kind",
            "repo",
            "repository_id",
            "principal_id",
            "display_name",
            "will_id",
            "session_id",
            "body_epoch_id",
            "scopes",
            "clauses",
            "intent_summary",
            "issued_at",
            "not_before",
            "not_after",
            "signature_alg",
            "invents_facts",
            "alters_evidence",
            "execution_authorized",
            "host_mutate_authorized",
            "memory_write_authorized",
            "durable_write_authorized",
            "policy_effect",
            "update_authorized",
            "advisory_only",
            "claim_boundary",
            "cortex_version",
        )
    }
    expected_hash = _sha(payload)
    checks["payload_hash"] = str(will.get("payload_hash") or "") == expected_hash

    signature_ok = False
    principal = _load_principal(store, repo, str(will.get("principal_id") or ""))
    checks["principal_registered"] = principal is not None
    if secret is not None and checks["payload_hash"]:
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            expected_hash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signature_ok = hmac.compare_digest(
            expected_sig, str(will.get("signature") or "")
        )
        checks["signature"] = signature_ok
    elif principal is not None and checks["payload_hash"] and will.get("signature"):
        # Without secret we can only check structural hash, not HMAC.
        checks["signature"] = False
        checks["signature_deferred"] = True
        signature_ok = False
    else:
        checks["signature"] = False

    # verified requires secret proof when available; structure-only is not enough
    # for membrane admission.
    verified = all(
        checks.get(k)
        for k in (
            "kind",
            "repo",
            "will_id",
            "principal_id",
            "scopes_present",
            "scopes_legal",
            "clauses_legal",
            "signature_present",
            "payload_hash",
            "time_window",
            "session_bound",
            "epoch_bound",
            "principal_registered",
            "no_host_mutate",
            "no_execution",
            "no_invent",
            "no_alter_evidence",
            "signature",
        )
    )
    for key, ok in checks.items():
        if key == "signature_deferred":
            continue
        if not ok:
            errors.append(key)

    return {
        "schema_version": "cortex-will-verify/1.0",
        "version": VERSION,
        "repo": repo,
        "will_id": will.get("will_id"),
        "principal_id": will.get("principal_id"),
        "verified": verified,
        "checks": checks,
        "errors": errors,
        "scopes": scopes,
        "has_admit_scope": "will.admit" in scopes,
        "has_prioritize_scope": "will.prioritize" in scopes,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "policy_effect": False,
        "execution_authorized": False,
        "memory_write_authorized": False,
        "host_mutate_authorized": False,
    }


def will_status(store: Any, repo: str) -> dict[str, Any]:
    latest = store.get_setting(f"will_latest:{repo}", None) or {}
    principals = store.db.execute(
        "SELECT principal_id, display_name, created_at FROM will_principals WHERE repo=?",
        (repo,),
    ).fetchall()
    return {
        "schema_version": "cortex-will-status/1.0",
        "version": VERSION,
        "repo": repo,
        "principals": [dict(p) for p in principals],
        "latest_will_id": latest.get("will_id"),
        "latest_receipt_hash": latest.get("receipt_hash"),
        "latest_scopes": latest.get("scopes"),
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "policy_effect": False,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "CLAUSE_KINDS",
    "FORBIDDEN_SCOPES",
    "GLYPH",
    "SCHEMA",
    "SUPPORT_ORDER",
    "VERSION",
    "WILL_SCOPES",
    "issue_will",
    "register_will_principal",
    "verify_will",
    "will_status",
]
