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
import math
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-will/1.0"
VERSION = "8.9.2"
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


def _policy_key(repo: str) -> str:
    return f"will_default_policy:{repo}"


def set_default_will_policy(
    store: Any,
    repo: str,
    *,
    principal_id: str,
    clauses: Sequence[Mapping[str, Any]] | None = None,
    scopes: Sequence[str] | None = None,
    intent_summary: str = "",
    max_retain: int | None = 8,
    min_support: str = "medium",
    admit_types: Sequence[str] | None = None,
    forbid_types: Sequence[str] | None = None,
    ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Persist durable default admit policy (no secret; not a will receipt)."""
    principal_id = str(principal_id or "").strip()
    if not principal_id:
        raise ValueError("principal_id required for default will policy")
    clause_list = list(_normalize_clauses(clauses)) if clauses else []
    if admit_types:
        types = [str(t).strip() for t in admit_types if str(t).strip()]
        clause_list.append(
            {
                "clause_id": "policy_admit_type",
                "kind": "admit_type",
                "candidate_types": types,
                "candidate_ids": [],
                "transition_classes": [],
                "max_retain": None,
                "min_support": None,
                "priority": 1,
                "notes": "durable_default",
            }
        )
        clause_list.append(
            {
                "clause_id": "policy_prioritize_type",
                "kind": "prioritize_type",
                "candidate_types": types,
                "candidate_ids": [],
                "transition_classes": [],
                "max_retain": None,
                "min_support": None,
                "priority": 2,
                "notes": "durable_default",
            }
        )
    if forbid_types:
        clause_list.append(
            {
                "clause_id": "policy_forbid_type",
                "kind": "forbid_type",
                "candidate_types": [
                    str(t).strip() for t in forbid_types if str(t).strip()
                ],
                "candidate_ids": [],
                "transition_classes": [],
                "max_retain": None,
                "min_support": None,
                "priority": 0,
                "notes": "durable_default",
            }
        )
    if max_retain is not None:
        clause_list.append(
            {
                "clause_id": "policy_cap_retain",
                "kind": "cap_retain",
                "candidate_types": [],
                "candidate_ids": [],
                "transition_classes": [],
                "max_retain": int(max_retain),
                "min_support": None,
                "priority": 0,
                "notes": "durable_default",
            }
        )
    if min_support:
        clause_list.append(
            {
                "clause_id": "policy_min_support",
                "kind": "prefer_support_min",
                "candidate_types": [],
                "candidate_ids": [],
                "transition_classes": [],
                "max_retain": None,
                "min_support": str(min_support),
                "priority": 0,
                "notes": "durable_default",
            }
        )
    # Re-normalize in case callers mixed shapes.
    clause_list = _normalize_clauses(clause_list)
    scope_list = _normalize_scopes(scopes)
    policy = {
        "schema_version": "cortex-will-default-policy/1.0",
        "version": VERSION,
        "repo": repo,
        "principal_id": principal_id,
        "scopes": scope_list,
        "clauses": clause_list,
        "intent_summary": str(intent_summary or "durable default will policy"),
        "ttl_seconds": int(ttl_seconds),
        "updated_at": time.time(),
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    store.set_setting(_policy_key(repo), policy)
    # Rotation tip — last N policies for audit, not secrets.
    history = list(store.get_setting(f"will_default_policy_history:{repo}", []) or [])
    history.append(
        {
            "principal_id": principal_id,
            "updated_at": policy["updated_at"],
            "clause_count": len(clause_list),
            "scopes": scope_list,
            "intent_summary": policy["intent_summary"],
        }
    )
    store.set_setting(f"will_default_policy_history:{repo}", history[-32:])
    return policy


def get_default_will_policy(store: Any, repo: str) -> dict[str, Any] | None:
    raw = store.get_setting(_policy_key(repo), None)
    return dict(raw) if isinstance(raw, Mapping) else None


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
    use_default_policy: bool = True,
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
    default_policy = get_default_will_policy(store, repo) if use_default_policy else None
    used_default = False
    if (not clauses or len(list(clauses)) == 0) and default_policy:
        if str(default_policy.get("principal_id") or "") in {"", principal_id}:
            clauses = list(default_policy.get("clauses") or ())
            if scopes is None:
                scopes = list(default_policy.get("scopes") or ())
            if not intent_summary:
                intent_summary = str(default_policy.get("intent_summary") or "")
            if ttl_seconds == 86_400 and default_policy.get("ttl_seconds"):
                ttl_seconds = int(default_policy.get("ttl_seconds") or ttl_seconds)
            used_default = True
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
        "from_default_policy": used_default,
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
        except Exception as exc:
            return {
                **receipt,
                "issued": False,
                "canonical_persistence": "failed",
                "canonical_persistence_error": f"{type(exc).__name__}:{exc}",
                "persisted": False,
                "advisory_only": True,
            }
        store.set_setting(f"will_latest:{repo}", receipt)
        receipt = {**receipt, "canonical_persistence": "committed", "persisted": True}
    else:
        receipt = {**receipt, "canonical_persistence": "not_requested", "persisted": False}
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

    try:
        not_before = float(will.get("not_before") or 0)
        not_after = float(will.get("not_after") or 0)
        checks["finite_time"] = math.isfinite(not_before) and math.isfinite(not_after)
    except (TypeError, ValueError, OverflowError):
        not_before, not_after = 0.0, 0.0
        checks["finite_time"] = False
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
            "from_default_policy",
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

    # A structurally plausible mapping is not a current will.  Bind the
    # verification to the immutable canonical receipt when available and
    # verify its non-circular receipt identity independently.
    receipt_hash = str(will.get("receipt_hash") or "")
    canonical_row = None
    if receipt_hash and hasattr(store, "get_will_receipt_by_hash"):
        canonical_row = store.get_will_receipt_by_hash(repo, receipt_hash)
    checks["receipt_hash_present"] = len(receipt_hash) == 64
    checks["canonical_receipt"] = canonical_row is not None
    checks["canonical_identity"] = bool(
        canonical_row is not None
        and str(canonical_row.get("receipt_hash") or "") == receipt_hash
        and canonical_row.get("will_id") == will.get("will_id")
        and canonical_row.get("principal_id") == will.get("principal_id")
        and canonical_row.get("repo") == repo
    )
    if canonical_row is not None:
        # Canonical JSON equality catches mutation while preserving legacy
        # rows as an explicit non-current/partial result.
        checks["canonical_body"] = all(
            will.get(key) == value for key, value in canonical_row.items()
        )
    else:
        checks["canonical_body"] = False

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
            "finite_time",
            "time_window",
            "session_bound",
            "epoch_bound",
            "principal_registered",
            "no_host_mutate",
            "no_execution",
            "no_invent",
            "no_alter_evidence",
            "signature",
            "receipt_hash_present",
            "canonical_receipt",
            "canonical_identity",
            "canonical_body",
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
        "receipt_hash_valid": checks.get("canonical_identity", False) and checks.get("canonical_body", False),
        "principal_bound": checks.get("canonical_identity", False) and bool(principal),
        "will_state": "current_verified" if verified else ("expired" if not checks.get("time_window") else "unverified"),
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
    policy = get_default_will_policy(store, repo)
    history = list(store.get_setting(f"will_default_policy_history:{repo}", []) or [])
    return {
        "schema_version": "cortex-will-status/1.1",
        "version": VERSION,
        "repo": repo,
        "principals": [dict(p) for p in principals],
        "latest_will_id": latest.get("will_id"),
        "latest_receipt_hash": latest.get("receipt_hash"),
        "latest_scopes": latest.get("scopes"),
        "default_policy": policy,
        "default_policy_history_len": len(history),
        "default_policy_history_tip": history[-1] if history else None,
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
    "get_default_will_policy",
    "issue_will",
    "set_default_will_policy",
    "register_will_principal",
    "verify_will",
    "will_status",
]
