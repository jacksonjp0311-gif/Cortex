"""Capability tokens for multi-agent memory. Never mint host mutation rights."""

from __future__ import annotations

import hmac
import json
import time
from hashlib import sha256
from typing import Any

# Closed vocabulary — host.mutate deliberately absent.
ALLOWED_SCOPES: frozenset[str] = frozenset(
    {
        "memory.read",
        "memory.remember",
        "memory.consolidate",
        "packet.activate",
        "packet.predict",
        "ranker.infer",
        "graph.read",
        "metrics.read",
        "canonical.read",
        "canonical.propose",
    }
)

FORBIDDEN_SCOPES: frozenset[str] = frozenset(
    {
        "host.mutate",
        "source.edit",
        "deploy",
        "token.mint_self",
    }
)


def register_agent(
    store: Any, repo: str, agent_id: str, display_name: str, *, secret: str = ""
) -> dict[str, Any]:
    secret = secret or sha256(f"{repo}|{agent_id}|{time.time()}".encode()).hexdigest()
    secret_hash = sha256(secret.encode("utf-8")).hexdigest()
    store.db.execute(
        """
        INSERT INTO agent_principals(repo, agent_id, display_name, secret_hash, created_at)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(repo, agent_id) DO UPDATE SET display_name=excluded.display_name
        """,
        (repo, agent_id, display_name, secret_hash, time.time()),
    )
    store.db.commit()
    return {
        "registered": True,
        "repo": repo,
        "agent_id": agent_id,
        "display_name": display_name,
        "secret": secret,  # shown once at registration for local HMAC; not re-readable
        "claim_boundary": "Agent registration is local identity only; not host rights.",
    }


def mint_token(
    store: Any,
    repo: str,
    agent_id: str,
    scopes: list[str],
    *,
    ttl_seconds: int = 28_800,
    issued_by: str = "human",
    secret: str = "",
) -> dict[str, Any]:
    principal = store.db.execute(
        "SELECT * FROM agent_principals WHERE repo=? AND agent_id=?",
        (repo, agent_id),
    ).fetchone()
    if not principal:
        return {"minted": False, "reason": "agent_not_registered"}

    clean: list[str] = []
    for scope in scopes:
        s = str(scope).strip()
        if s in FORBIDDEN_SCOPES:
            return {
                "minted": False,
                "reason": "forbidden_scope",
                "scope": s,
                "message": "host mutation scopes do not exist in Cortex vocabulary",
            }
        if s not in ALLOWED_SCOPES:
            return {"minted": False, "reason": "unknown_scope", "scope": s}
        clean.append(s)
    if not clean:
        return {"minted": False, "reason": "empty_scope"}

    now = time.time()
    token_id = "tok_" + sha256(f"{repo}|{agent_id}|{now}|{clean}".encode()).hexdigest()[:20]
    material = f"{token_id}|{repo}|{agent_id}|{','.join(sorted(clean))}|{now}"
    key = (secret or principal["secret_hash"]).encode("utf-8")
    token_hash = hmac.new(key, material.encode("utf-8"), sha256).hexdigest()
    store.db.execute(
        """
        INSERT INTO capability_tokens(
          token_id, repo, agent_id, scope_json, not_before, not_after,
          issued_by, token_hash, revoked
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            token_id,
            repo,
            agent_id,
            json.dumps(sorted(clean)),
            now,
            now + max(60, ttl_seconds),
            issued_by,
            token_hash,
        ),
    )
    store.db.commit()
    try:
        store.append_neural_event(
            repo,
            event_type="token_minted",
            entity_id=token_id,
            payload={"agent_id": agent_id, "scopes": clean, "issued_by": issued_by},
        )
    except Exception:
        pass
    return {
        "minted": True,
        "token_id": token_id,
        "agent_id": agent_id,
        "scopes": clean,
        "not_after": now + max(60, ttl_seconds),
        "token_hash": token_hash,
        "claim_boundary": "Token authorizes Cortex memory scopes only; never host mutation.",
    }


def revoke_token(store: Any, repo: str, token_id: str) -> dict[str, Any]:
    cur = store.db.execute(
        "UPDATE capability_tokens SET revoked=1 WHERE repo=? AND token_id=?",
        (repo, token_id),
    )
    store.db.commit()
    return {"revoked": cur.rowcount > 0, "token_id": token_id}


def validate_token(
    store: Any,
    repo: str,
    token_id: str,
    *,
    required_scope: str | None = None,
) -> dict[str, Any]:
    row = store.db.execute(
        "SELECT * FROM capability_tokens WHERE repo=? AND token_id=?",
        (repo, token_id),
    ).fetchone()
    if not row:
        return {"valid": False, "reason": "missing"}
    if int(row["revoked"] or 0):
        return {"valid": False, "reason": "revoked"}
    now = time.time()
    if now < float(row["not_before"]) or now > float(row["not_after"]):
        return {"valid": False, "reason": "expired"}
    scopes = json.loads(row["scope_json"] or "[]")
    if required_scope and required_scope not in scopes:
        return {"valid": False, "reason": "scope_missing", "scopes": scopes}
    if required_scope in FORBIDDEN_SCOPES:
        return {"valid": False, "reason": "forbidden_scope"}
    return {
        "valid": True,
        "agent_id": row["agent_id"],
        "scopes": scopes,
        "token_id": token_id,
    }


def multi_agent_enabled(store: Any, repo: str) -> bool:
    raw = store.get_setting(f"multi_agent:{repo}", {}) or {}
    return bool(raw.get("enabled"))


def set_multi_agent_mode(store: Any, repo: str, enabled: bool) -> dict[str, Any]:
    store.set_setting(
        f"multi_agent:{repo}",
        {"enabled": bool(enabled), "updated_at": time.time()},
    )
    try:
        store.append_neural_event(
            repo,
            event_type="multi_agent_mode",
            entity_id=repo,
            payload={"enabled": bool(enabled)},
        )
    except Exception:
        pass
    return {
        "repo": repo,
        "multi_agent": bool(enabled),
        "claim_boundary": "Mode only; still no host.mutate capability.",
    }


def require_scope(
    store: Any,
    repo: str,
    *,
    token_id: str | None,
    scope: str,
) -> dict[str, Any]:
    """When multi-agent mode is on, require a valid token with scope."""

    if not multi_agent_enabled(store, repo):
        return {"required": False, "valid": True, "mode": "single_agent"}
    if not token_id:
        return {
            "required": True,
            "valid": False,
            "reason": "token_required",
            "message": "multi_agent mode is on; pass --token / token_id",
        }
    result = validate_token(store, repo, token_id, required_scope=scope)
    result["required"] = True
    result["mode"] = "multi_agent"
    return result


def resolve_conflict(
    store: Any,
    repo: str,
    *,
    session_a: str,
    session_b: str,
    path_or_claim: str,
    resolution: str,
) -> dict[str, Any]:
    if resolution not in {"keep_a", "keep_b", "merge", "defer_human"}:
        return {"resolved": False, "reason": "invalid_resolution"}
    now = time.time()
    conflict_id = "cfl_" + sha256(
        f"{repo}|{session_a}|{session_b}|{path_or_claim}|{now}".encode()
    ).hexdigest()[:20]
    record = {
        "conflict_id": conflict_id,
        "repo": repo,
        "session_a": session_a,
        "session_b": session_b,
        "path_or_claim": path_or_claim,
        "resolution": resolution,
        "created_at": now,
    }
    receipt_hash = sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    store.db.execute(
        """
        INSERT INTO memory_conflicts(
          conflict_id, repo, session_a, session_b, path_or_claim,
          resolution, receipt_hash, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conflict_id,
            repo,
            session_a,
            session_b,
            path_or_claim,
            resolution,
            receipt_hash,
            now,
        ),
    )
    store.db.commit()
    try:
        store.append_neural_event(
            repo,
            event_type="memory_conflict_resolved",
            entity_id=conflict_id,
            payload=record | {"receipt_hash": receipt_hash},
        )
    except Exception:
        pass
    return {
        "resolved": True,
        "conflict_id": conflict_id,
        "resolution": resolution,
        "receipt_hash": receipt_hash,
        "claim_boundary": "Conflict receipts record memory arbitration only; not host edits.",
    }
