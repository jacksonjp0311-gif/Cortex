"""Governed multi-agent shared memory — capability tokens; no host.mutate."""

from .tokens import (
    ALLOWED_SCOPES,
    FORBIDDEN_SCOPES,
    mint_token,
    multi_agent_enabled,
    register_agent,
    require_scope,
    resolve_conflict,
    revoke_token,
    set_multi_agent_mode,
    validate_token,
)

__all__ = [
    "ALLOWED_SCOPES",
    "FORBIDDEN_SCOPES",
    "mint_token",
    "multi_agent_enabled",
    "register_agent",
    "require_scope",
    "resolve_conflict",
    "revoke_token",
    "set_multi_agent_mode",
    "validate_token",
]
