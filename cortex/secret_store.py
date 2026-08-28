"""Host-secret storage for Cortex provider credentials.

Secrets are resolved from the process environment or the operating-system
credential vault through ``keyring``. They never enter Cortex settings,
evidence, trajectories, logs, or model-catalog records.
"""

from __future__ import annotations

import os
from typing import Protocol


PROVIDER_ENVIRONMENT_KEYS = {
    "openai": "OPENAI_API_KEY",
    "xai": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
KEYRING_SERVICE = "Cortex.NativeAgentRuntime"


class SecretStoreError(RuntimeError):
    """A bounded secret-store failure safe to show to the operator."""


class SecretStore(Protocol):
    def get(self, provider: str) -> str | None: ...
    def set(self, provider: str, secret: str) -> None: ...
    def delete(self, provider: str) -> None: ...
    def describe(self, provider: str) -> dict[str, object]: ...


def _provider(value: str) -> str:
    provider = str(value or "").strip().lower()
    if provider not in PROVIDER_ENVIRONMENT_KEYS:
        raise SecretStoreError("unsupported provider")
    return provider


def _safe_tail(secret: str) -> str:
    return f"••••••••••••{secret[-4:]}" if len(secret) >= 4 else "••••••••••••"


class HostSecretStore:
    """Environment-first, OS-vault-backed credential resolution."""

    def _keyring(self):
        try:
            import keyring  # type: ignore[import-not-found]
        except ImportError as exc:
            raise SecretStoreError(
                "OS credential storage is unavailable; install Cortex with its UI dependencies"
            ) from exc
        return keyring

    def get(self, provider: str) -> str | None:
        name = _provider(provider)
        environment = str(os.environ.get(PROVIDER_ENVIRONMENT_KEYS[name], "")).strip()
        if environment:
            return environment
        try:
            value = self._keyring().get_password(KEYRING_SERVICE, name)
        except Exception as exc:  # keyring backends raise several platform types
            raise SecretStoreError("the operating-system credential store could not be read") from exc
        return str(value).strip() if value else None

    def set(self, provider: str, secret: str) -> None:
        name = _provider(provider)
        value = str(secret or "").strip()
        if not value:
            raise SecretStoreError("API key is required")
        try:
            self._keyring().set_password(KEYRING_SERVICE, name, value)
        except Exception as exc:
            raise SecretStoreError("the operating-system credential store rejected the key") from exc

    def delete(self, provider: str) -> None:
        name = _provider(provider)
        try:
            self._keyring().delete_password(KEYRING_SERVICE, name)
        except Exception:
            # Deletion is idempotent and never exposes backend detail.
            return

    def describe(self, provider: str) -> dict[str, object]:
        name = _provider(provider)
        environment_name = PROVIDER_ENVIRONMENT_KEYS[name]
        from_environment = bool(str(os.environ.get(environment_name, "")).strip())
        try:
            value = self.get(name)
            vault_available = True
        except SecretStoreError:
            value = None
            vault_available = False
        return {
            "configured": bool(value),
            "source": "environment" if from_environment else ("host_vault" if value else ("none" if vault_available else "vault_unavailable")),
            "masked": _safe_tail(value) if value else "",
            "environment_variable": environment_name,
            "host_vault_available": vault_available,
        }


class MemorySecretStore:
    """Process-only fixture store. Never used as a production fallback."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, provider: str) -> str | None:
        return self._values.get(_provider(provider))

    def set(self, provider: str, secret: str) -> None:
        name = _provider(provider)
        value = str(secret or "").strip()
        if not value:
            raise SecretStoreError("API key is required")
        self._values[name] = value

    def delete(self, provider: str) -> None:
        self._values.pop(_provider(provider), None)

    def describe(self, provider: str) -> dict[str, object]:
        value = self.get(provider)
        return {
            "configured": bool(value),
            "source": "process_fixture" if value else "none",
            "masked": _safe_tail(value) if value else "",
            "environment_variable": PROVIDER_ENVIRONMENT_KEYS[_provider(provider)],
        }


__all__ = [
    "HostSecretStore",
    "MemorySecretStore",
    "PROVIDER_ENVIRONMENT_KEYS",
    "SecretStore",
    "SecretStoreError",
]
