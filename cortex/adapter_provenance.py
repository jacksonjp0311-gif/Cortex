"""Host-controlled adapter evidence classification for Cortex v9.4.

Adapter identity is provenance, not evidence class. Fixture lineage is sealed
in code and checked across the complete MRO. Non-fixture adapters remain
unknown until a host principal registers one exact implementation, sanitized
runtime profile, and model identity against one execution boundary.

Registration proves only that the local host principal made the declaration.
It is not provider attestation and it does not prove what a remote provider
executed for any particular invocation.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "cortex-adapter-provenance/1.0"
HOST_MODEL_CLASSIFICATION_SCHEMA = "cortex-host-model-classification/1.0"
VERSION = "9.4.0"

EVIDENCE_UNKNOWN = "unknown"
EVIDENCE_SYNTHETIC = "synthetic"
EVIDENCE_SIMULATED = "simulated"
EVIDENCE_LIVE = "live_empirical"
EVIDENCE_ATTESTED = "empirically_attested"
EVIDENCE_LEGACY = "legacy_partial"

EVIDENCE_CLASSES = frozenset(
    {
        EVIDENCE_UNKNOWN,
        EVIDENCE_SYNTHETIC,
        EVIDENCE_SIMULATED,
        EVIDENCE_LIVE,
        EVIDENCE_ATTESTED,
        EVIDENCE_LEGACY,
    }
)
EVIDENCE_ORDER = {
    EVIDENCE_LEGACY: -1,
    EVIDENCE_UNKNOWN: 0,
    EVIDENCE_SYNTHETIC: 1,
    EVIDENCE_SIMULATED: 2,
    EVIDENCE_LIVE: 3,
    EVIDENCE_ATTESTED: 4,
}
BOUNDARY_CLASSES = {
    "simulation": EVIDENCE_SIMULATED,
    "external_api": EVIDENCE_LIVE,
    "local_inference_server": EVIDENCE_LIVE,
    "local_subprocess_model": EVIDENCE_LIVE,
}

PROVIDER_ATTESTATION_UNAVAILABLE = "not_available"
CLAIM_BOUNDARY = (
    "Host registration classifies a locally declared execution boundary; it is not "
    "provider attestation and does not prove a provider response."
)

# This object is intentionally not serializable. FixtureAdapter places it in
# its class dictionary. The MRO name fallback remains fail-closed even if a
# subclass shadows the marker.
FIXTURE_LINEAGE_MARKER = object()

_IDENTITY_FIELDS = (
    "provider_family",
    "model_id",
    "model_version",
    "adapter_id",
    "adapter_version",
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_\-.])(?:api[_-]?key|access[_-]?key|private[_-]?key|secret|password|"
    r"passwd|passphrase|token|credential|authorization|cookie|bearer|jwt)(?:$|[_\-.])",
    re.IGNORECASE,
)
_INLINE_SECRET_RE = re.compile(
    r"(?i)\b(bearer|basic)\s+[^\s,;]+|"
    r"\b(api[_-]?key|access[_-]?key|token|secret|password)=([^&\s,;]+)"
)
_LONG_PATH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-=]{24,}$")
_MAX_PROFILE_DEPTH = 8
_MAX_PROFILE_ITEMS = 128
_MAX_PROFILE_TEXT = 512


class AdapterProvenanceError(ValueError):
    """Raised when adapter evidence provenance cannot be established."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_identity(store: Any, repo: str) -> str:
    row = store.db.execute(
        "SELECT repository_id FROM repositories WHERE name=?", (str(repo),)
    ).fetchone()
    if row is None or not str(row["repository_id"] or ""):
        raise AdapterProvenanceError(f"Unknown repository: {repo}")
    return str(row["repository_id"])


def _principal(
    store: Any,
    repo: str,
    principal_id: str,
    secret: str,
) -> Mapping[str, Any]:
    row = store.db.execute(
        "SELECT * FROM will_principals WHERE repo=? AND principal_id=?",
        (str(repo), str(principal_id)),
    ).fetchone()
    if row is None:
        raise AdapterProvenanceError("host principal is not registered")
    supplied = hashlib.sha256(str(secret).encode("utf-8")).hexdigest()
    if not secret or supplied != str(row["secret_hash"] or ""):
        raise AdapterProvenanceError("host principal secret mismatch")
    return dict(row)


def is_fixture_lineage(adapter: Any) -> bool:
    """Return true for FixtureAdapter and every subclass, despite field spoofing."""

    try:
        lineage = tuple(type(adapter).__mro__)
    except Exception:
        lineage = ()
    for base in lineage:
        if base.__dict__.get("_cortex_evidence_marker") is FIXTURE_LINEAGE_MARKER:
            return True
        if (
            str(getattr(base, "__module__", "")) == "cortex.model_circulation"
            and str(getattr(base, "__qualname__", "")) == "FixtureAdapter"
        ):
            return True
    return False


def adapter_implementation_digest(adapter: Any) -> str:
    """Bind registration to an exact executable type, not declared identity strings."""

    adapter_type = type(adapter)
    invoke = getattr(adapter_type, "invoke", None)
    code = getattr(invoke, "__code__", None)
    try:
        source = inspect.getsource(adapter_type)
    except (OSError, TypeError):
        source = ""
    code_material = {
        "bytecode": bytes(code.co_code).hex() if code is not None else "",
        "constants": [repr(item) for item in code.co_consts] if code is not None else [],
        "names": list(code.co_names) if code is not None else [],
        "defaults": [repr(item) for item in (getattr(invoke, "__defaults__", None) or ())],
    }
    return _sha(
        {
            "module": str(adapter_type.__module__),
            "qualname": str(adapter_type.__qualname__),
            "source_hash": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "invoke": code_material,
        }
    )


def _is_sensitive_key(key: str) -> bool:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", camel_split).strip("_")
    return bool(_SENSITIVE_KEY_RE.search(normalized)) or normalized.endswith("_key")


def _sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<redacted-url>"
    if not parsed.scheme or not parsed.netloc:
        return value
    host = str(parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = f"{host}:{port}" if port is not None else host
    safe_segments: list[str] = []
    for segment in parsed.path.split("/"):
        safe_segments.append("<redacted-segment>" if _LONG_PATH_TOKEN_RE.fullmatch(segment) else segment)
    path = "/".join(safe_segments)
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def _sanitize_text(value: str) -> str:
    text = str(value)
    if "://" in text:
        text = _sanitize_url(text)
    text = _INLINE_SECRET_RE.sub("<redacted>", text)
    if len(text) > _MAX_PROFILE_TEXT:
        return text[:_MAX_PROFILE_TEXT] + "<truncated>"
    return text


def _sanitize_profile(
    value: Any,
    *,
    key: str = "",
    depth: int = 0,
    seen: set[int] | None = None,
) -> Any:
    """Return bounded JSON material while removing common credential surfaces."""

    if _is_sensitive_key(key):
        return "<redacted>"
    if depth >= _MAX_PROFILE_DEPTH:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else "<non-finite>"
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"type": "bytes", "length": len(value)}

    active = seen if seen is not None else set()
    object_id = id(value)
    if object_id in active:
        return "<cycle>"
    active.add(object_id)
    try:
        if isinstance(value, Mapping):
            items = sorted(((str(k), v) for k, v in value.items()), key=lambda item: item[0])
            return {
                name: _sanitize_profile(
                    item,
                    key=name,
                    depth=depth + 1,
                    seen=active,
                )
                for name, item in items[:_MAX_PROFILE_ITEMS]
            }
        if isinstance(value, Sequence):
            return [
                _sanitize_profile(item, depth=depth + 1, seen=active)
                for item in list(value)[:_MAX_PROFILE_ITEMS]
            ]
        if isinstance(value, (set, frozenset)):
            items = [
                _sanitize_profile(item, depth=depth + 1, seen=active)
                for item in list(value)[:_MAX_PROFILE_ITEMS]
            ]
            return sorted(items, key=_canonical)
        value_type = type(value)
        return {"type": f"{value_type.__module__}.{value_type.__qualname__}"}
    finally:
        active.discard(object_id)


def _identity_value(value: Any, field: str, *, required: bool) -> str:
    text = str(value or "").strip()
    if not text and required:
        raise AdapterProvenanceError(f"adapter {field} is required for host registration")
    if any(char in text for char in ("\x00", "\r", "\n")) or len(text) > 256:
        raise AdapterProvenanceError(f"adapter {field} is not a bounded identity value")
    return text or "undeclared"


def _host_model_classification(
    *,
    model_family: str | None,
    capability_class: str | None,
    principal_id: str,
) -> dict[str, Any] | None:
    """Normalize an optional principal-controlled model classification.

    Adapter attributes and model responses are deliberately not consulted.
    Supplying either field requires both, preventing a partial class surface
    from silently entering cross-model diversity analysis.
    """

    if model_family is None and capability_class is None:
        return None
    family = _identity_value(model_family, "model_family", required=True)
    capability = _identity_value(
        capability_class, "capability_class", required=True
    )
    return {
        "schema_version": HOST_MODEL_CLASSIFICATION_SCHEMA,
        "state": "host_registered",
        "model_family": family,
        "capability_class": capability,
        "principal_id": str(principal_id),
        "authority_basis": "host_principal_registration",
        "adapter_or_model_self_assertion_used": False,
        "provider_attestation_claimed": False,
    }


def _host_identity(adapter: Any, *, strict: bool) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in _IDENTITY_FIELDS:
        try:
            value = getattr(adapter, field, "")
        except Exception:
            value = ""
        values[field] = _identity_value(
            value,
            field,
            required=strict and field in {"provider_family", "model_id", "adapter_id"},
        )
    return values


def _runtime_profile(adapter: Any, identity: Mapping[str, str]) -> dict[str, Any]:
    try:
        raw_state = vars(adapter)
    except (TypeError, ValueError):
        raw_state = {}
    adapter_type = type(adapter)
    return {
        "adapter_type": f"{adapter_type.__module__}.{adapter_type.__qualname__}",
        "model_identity": dict(identity),
        "configuration": _sanitize_profile(dict(raw_state)),
    }


def _profile_binding(adapter: Any, *, strict_identity: bool) -> dict[str, Any]:
    identity = _host_identity(adapter, strict=strict_identity)
    runtime_profile = _runtime_profile(adapter, identity)
    implementation_digest = adapter_implementation_digest(adapter)
    runtime_profile_digest = _sha(runtime_profile)
    host_identity_digest = _sha(identity)
    binding_material = {
        "implementation_digest": implementation_digest,
        "runtime_profile_digest": runtime_profile_digest,
        "host_identity_digest": host_identity_digest,
    }
    return {
        **binding_material,
        "binding_digest": _sha(binding_material),
        "host_identity": identity,
        "runtime_profile": runtime_profile,
    }


def ensure_adapter_provenance_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS model_adapter_registrations(
            registration_id TEXT PRIMARY KEY CHECK(length(registration_id) = 64),
            registration_hash TEXT NOT NULL CHECK(length(registration_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            implementation_digest TEXT NOT NULL CHECK(length(implementation_digest) = 64),
            runtime_profile_digest TEXT NOT NULL,
            host_identity_digest TEXT NOT NULL,
            binding_digest TEXT NOT NULL,
            boundary_kind TEXT NOT NULL,
            evidence_class TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            principal_secret_hash TEXT NOT NULL CHECK(length(principal_secret_hash) = 64),
            registration_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, binding_digest)
        );
        CREATE INDEX IF NOT EXISTS idx_model_adapter_registrations_repo
            ON model_adapter_registrations(repo, implementation_digest, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS model_adapter_registrations_no_update
        BEFORE UPDATE ON model_adapter_registrations BEGIN
            SELECT RAISE(ABORT, 'adapter registrations cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS model_adapter_registrations_no_delete
        BEFORE DELETE ON model_adapter_registrations BEGIN
            SELECT RAISE(ABORT, 'adapter registrations cannot be deleted');
        END;
        """
    )
    columns = {
        str(row[1])
        for row in store.db.execute("PRAGMA table_info(model_adapter_registrations)").fetchall()
    }
    for name in ("runtime_profile_digest", "host_identity_digest", "binding_digest"):
        if name not in columns:
            store.db.execute(f"ALTER TABLE model_adapter_registrations ADD COLUMN {name} TEXT")
    store.db.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_model_adapter_registration_binding
           ON model_adapter_registrations(repository_id, binding_digest)
           WHERE binding_digest IS NOT NULL"""
    )
    store.db.commit()


def _registration_material(body: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in body.items()
        if key not in {"registration_id", "registration_hash", "inserted", "duplicate"}
    }


def _authentication_digest(
    *,
    repository_id: str,
    repo: str,
    principal_id: str,
    principal: Mapping[str, Any],
) -> str:
    # The principal verifier is consumed only to prove this call. Only a digest
    # of the registration-time event is retained, so later secret rotation does
    # not rewrite history or invalidate the sealed registration.
    return _sha(
        {
            "method": "host_principal_secret",
            "repository_id": repository_id,
            "repo": repo,
            "principal_id": principal_id,
            "principal_created_at": float(principal.get("created_at") or 0.0),
            "registration_time_verifier": str(principal.get("secret_hash") or ""),
        }
    )


def _load_registration_json(row: Mapping[str, Any]) -> dict[str, Any] | None:
    try:
        body = json.loads(str(row["registration_json"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return dict(body) if isinstance(body, Mapping) else None


def register_adapter_provenance(
    store: Any,
    repo: str,
    adapter: Any,
    *,
    boundary_kind: str,
    principal_id: str,
    principal_secret: str,
    endpoint_descriptor: Mapping[str, Any] | None = None,
    model_family: str | None = None,
    capability_class: str | None = None,
) -> dict[str, Any]:
    """Host-authenticate one exact adapter/profile and execution boundary."""

    ensure_adapter_provenance_tables(store)
    if boundary_kind not in BOUNDARY_CLASSES:
        raise AdapterProvenanceError("unsupported adapter execution boundary")
    if is_fixture_lineage(adapter):
        raise AdapterProvenanceError(
            "fixture lineage is permanently synthetic and is not registrable"
        )
    principal = _principal(store, repo, principal_id, principal_secret)
    repository_id = _repo_identity(store, repo)
    binding = _profile_binding(adapter, strict_identity=True)
    evidence_class = BOUNDARY_CLASSES[boundary_kind]
    classification = _host_model_classification(
        model_family=model_family,
        capability_class=capability_class,
        principal_id=str(principal_id),
    )
    safe_endpoint = _sanitize_profile(dict(endpoint_descriptor or {}))
    endpoint_profile_digest = _sha(safe_endpoint)

    rows = store.db.execute(
        """SELECT * FROM model_adapter_registrations
           WHERE repository_id=? AND repo=? AND implementation_digest=?
             AND runtime_profile_digest=?
           ORDER BY created_at""",
        (
            repository_id,
            repo,
            binding["implementation_digest"],
            binding["runtime_profile_digest"],
        ),
    ).fetchall()
    for row in rows:
        prior = _load_registration_json(row)
        if prior is None:
            raise AdapterProvenanceError("existing adapter registration is unreadable")
        if str(prior.get("host_identity_digest") or "") != binding["host_identity_digest"]:
            raise AdapterProvenanceError(
                "adapter implementation/profile already has a conflicting host identity"
            )
        if str(prior.get("boundary_kind") or "") != boundary_kind:
            raise AdapterProvenanceError(
                "adapter implementation/profile already has a conflicting boundary class"
            )
        if str(prior.get("endpoint_profile_digest") or "") != endpoint_profile_digest:
            raise AdapterProvenanceError(
                "adapter implementation/profile registration is immutable"
            )
        if prior.get("host_model_classification") != classification:
            raise AdapterProvenanceError(
                "adapter implementation/profile has an immutable host model classification"
            )
        check = verify_adapter_registration(store, repo, str(prior.get("registration_id") or ""))
        if check.get("valid") is not True:
            raise AdapterProvenanceError("existing adapter registration failed verification")
        return {**prior, "inserted": False, "duplicate": True}

    created_at = time.time()
    principal_authentication_digest = _authentication_digest(
        repository_id=repository_id,
        repo=repo,
        principal_id=str(principal_id),
        principal=principal,
    )
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": repository_id,
        "implementation_digest": binding["implementation_digest"],
        "runtime_profile_digest": binding["runtime_profile_digest"],
        "host_identity_digest": binding["host_identity_digest"],
        "binding_digest": binding["binding_digest"],
        "host_identity": binding["host_identity"],
        "runtime_profile": binding["runtime_profile"],
        "boundary_kind": boundary_kind,
        "evidence_class": evidence_class,
        "principal_id": str(principal_id),
        "principal_authentication_digest": principal_authentication_digest,
        "authentication_method": "host_principal_secret_at_registration",
        "endpoint_descriptor": safe_endpoint,
        "endpoint_profile_digest": endpoint_profile_digest,
        "provider_attestation": PROVIDER_ATTESTATION_UNAVAILABLE,
        "provider_attestation_claimed": False,
        "trust_basis": "host_principal_registration",
        "claim_boundary": CLAIM_BOUNDARY,
        "created_at": created_at,
    }
    # Omit the surface for legacy/unclassified registrations so the canonical
    # identity law of pre-v9.5 registrations remains byte-for-byte unchanged.
    if classification is not None:
        material["host_model_classification"] = classification
        material["host_model_classification_digest"] = _sha(classification)
    registration_hash = _sha(material)
    body = {
        **material,
        "registration_id": registration_hash,
        "registration_hash": registration_hash,
    }
    with store.transaction() as conn:
        conflict = conn.execute(
            """SELECT boundary_kind FROM model_adapter_registrations
               WHERE repository_id=? AND binding_digest=?""",
            (repository_id, binding["binding_digest"]),
        ).fetchone()
        if conflict is not None:
            raise AdapterProvenanceError(
                "adapter implementation/profile registration raced with another boundary"
            )
        conn.execute(
            """INSERT INTO model_adapter_registrations(
                registration_id, registration_hash, repository_id, repo,
                implementation_digest, runtime_profile_digest,
                host_identity_digest, binding_digest, boundary_kind,
                evidence_class, principal_id, principal_secret_hash,
                registration_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body["registration_id"],
                body["registration_hash"],
                repository_id,
                repo,
                binding["implementation_digest"],
                binding["runtime_profile_digest"],
                binding["host_identity_digest"],
                binding["binding_digest"],
                boundary_kind,
                evidence_class,
                str(principal_id),
                principal_authentication_digest,
                _canonical(body),
                created_at,
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def _registration(
    store: Any,
    repo: str,
    binding: Mapping[str, Any],
) -> dict[str, Any] | None:
    # Resolution must not execute DDL or commit a caller-owned transaction.
    # Store initialization and the explicit registration write path own schema
    # creation; an absent table is an unresolved registration, never evidence.
    if store.db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='model_adapter_registrations'"
    ).fetchone() is None:
        return None
    repository_id = _repo_identity(store, repo)
    rows = store.db.execute(
        """SELECT * FROM model_adapter_registrations
           WHERE repository_id=? AND repo=? AND implementation_digest=?
             AND runtime_profile_digest=? AND host_identity_digest=?
             AND binding_digest=?
           ORDER BY created_at""",
        (
            repository_id,
            repo,
            binding["implementation_digest"],
            binding["runtime_profile_digest"],
            binding["host_identity_digest"],
            binding["binding_digest"],
        ),
    ).fetchall()
    if len(rows) != 1:
        return None
    body = _load_registration_json(rows[0])
    if body is None:
        return None
    body["ledger_registration_hash"] = str(rows[0]["registration_hash"] or "")
    return body


def verify_adapter_registration(
    store: Any,
    repo: str,
    registration_id: str,
) -> dict[str, Any]:
    if store.db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='model_adapter_registrations'"
    ).fetchone() is None:
        return {"valid": False, "errors": ["adapter_registration_ledger_missing"]}
    repository_id = _repo_identity(store, repo)
    row = store.db.execute(
        """SELECT * FROM model_adapter_registrations
           WHERE repository_id=? AND repo=? AND registration_id=?""",
        (repository_id, repo, str(registration_id)),
    ).fetchone()
    if row is None:
        return {"valid": False, "errors": ["adapter_registration_missing"]}
    body = _load_registration_json(row)
    if body is None:
        return {"valid": False, "errors": ["adapter_registration_json_invalid"]}

    errors: list[str] = []
    material = _registration_material(body)
    expected = _sha(material)
    body_id = str(body.get("registration_id") or "")
    body_hash = str(body.get("registration_hash") or "")
    if expected != body_id or expected != body_hash:
        errors.append("adapter_registration_hash_invalid")
    if str(row["registration_id"] or "") != body_id:
        errors.append("adapter_registration_ledger_id_invalid")
    if str(row["registration_hash"] or "") != body_hash:
        errors.append("adapter_registration_ledger_hash_invalid")
    if (
        str(body.get("repository_id") or "") != repository_id
        or str(body.get("repo") or "") != repo
    ):
        errors.append("adapter_registration_repository_invalid")
    if body.get("schema_version") != SCHEMA or body.get("version") != VERSION:
        errors.append("adapter_registration_schema_invalid")

    boundary_kind = str(body.get("boundary_kind") or "")
    evidence_class = str(body.get("evidence_class") or "")
    if evidence_class != BOUNDARY_CLASSES.get(boundary_kind):
        errors.append("adapter_registration_boundary_invalid")
    if evidence_class == EVIDENCE_ATTESTED:
        errors.append("adapter_registration_provider_attestation_unavailable")

    runtime_profile = body.get("runtime_profile")
    host_identity = body.get("host_identity")
    endpoint_descriptor = body.get("endpoint_descriptor")
    if not isinstance(runtime_profile, Mapping) or _sha(runtime_profile) != str(
        body.get("runtime_profile_digest") or ""
    ):
        errors.append("adapter_registration_runtime_profile_invalid")
    if not isinstance(host_identity, Mapping) or _sha(host_identity) != str(
        body.get("host_identity_digest") or ""
    ):
        errors.append("adapter_registration_host_identity_invalid")
    if not isinstance(endpoint_descriptor, Mapping) or _sha(endpoint_descriptor) != str(
        body.get("endpoint_profile_digest") or ""
    ):
        errors.append("adapter_registration_endpoint_profile_invalid")
    if isinstance(runtime_profile, Mapping):
        if _sanitize_profile(runtime_profile) != dict(runtime_profile):
            errors.append("adapter_registration_runtime_profile_unsanitized")
        if dict(runtime_profile.get("model_identity") or {}) != dict(host_identity or {}):
            errors.append("adapter_registration_identity_profile_mismatch")
    if isinstance(endpoint_descriptor, Mapping) and _sanitize_profile(
        endpoint_descriptor
    ) != dict(endpoint_descriptor):
        errors.append("adapter_registration_endpoint_profile_unsanitized")
    if isinstance(host_identity, Mapping):
        for field in ("provider_family", "model_id", "adapter_id"):
            if str(host_identity.get(field) or "") in {"", "undeclared"}:
                errors.append("adapter_registration_host_identity_incomplete")

    classification = body.get("host_model_classification")
    classification_digest = str(
        body.get("host_model_classification_digest") or ""
    )
    if classification is None:
        if classification_digest:
            errors.append("adapter_model_classification_body_missing")
        classification_result = {
            "schema_version": HOST_MODEL_CLASSIFICATION_SCHEMA,
            "state": "legacy_partial",
            "model_family": "",
            "capability_class": "",
            "authority_basis": "unavailable_in_legacy_registration",
            "adapter_or_model_self_assertion_used": False,
        }
    elif not isinstance(classification, Mapping):
        errors.append("adapter_model_classification_invalid")
        classification_result = {}
    else:
        classification_result = dict(classification)
        if _sha(classification_result) != classification_digest:
            errors.append("adapter_model_classification_hash_invalid")
        if (
            classification_result.get("schema_version")
            != HOST_MODEL_CLASSIFICATION_SCHEMA
            or classification_result.get("state") != "host_registered"
            or classification_result.get("authority_basis")
            != "host_principal_registration"
            or classification_result.get("adapter_or_model_self_assertion_used")
            is not False
            or classification_result.get("provider_attestation_claimed") is not False
        ):
            errors.append("adapter_model_classification_semantics_invalid")
        for field in ("model_family", "capability_class"):
            try:
                normalized = _identity_value(
                    classification_result.get(field), field, required=True
                )
            except AdapterProvenanceError:
                errors.append(f"adapter_model_classification_{field}_invalid")
            else:
                if normalized != str(classification_result.get(field) or ""):
                    errors.append(
                        f"adapter_model_classification_{field}_not_canonical"
                    )
        if str(classification_result.get("principal_id") or "") != str(
            body.get("principal_id") or ""
        ):
            errors.append("adapter_model_classification_principal_mismatch")

    binding_material = {
        "implementation_digest": str(body.get("implementation_digest") or ""),
        "runtime_profile_digest": str(body.get("runtime_profile_digest") or ""),
        "host_identity_digest": str(body.get("host_identity_digest") or ""),
    }
    if _sha(binding_material) != str(body.get("binding_digest") or ""):
        errors.append("adapter_registration_binding_invalid")

    row_checks = {
        "implementation_digest": "adapter_registration_implementation_ledger_invalid",
        "runtime_profile_digest": "adapter_registration_runtime_ledger_invalid",
        "host_identity_digest": "adapter_registration_identity_ledger_invalid",
        "binding_digest": "adapter_registration_binding_ledger_invalid",
        "boundary_kind": "adapter_registration_boundary_ledger_invalid",
        "evidence_class": "adapter_registration_evidence_ledger_invalid",
        "principal_id": "adapter_registration_principal_ledger_invalid",
    }
    for field, error in row_checks.items():
        if str(row[field] or "") != str(body.get(field) or ""):
            errors.append(error)
    if str(row["principal_secret_hash"] or "") != str(
        body.get("principal_authentication_digest") or ""
    ):
        errors.append("adapter_registration_authentication_ledger_invalid")
    if float(row["created_at"] or 0.0) != float(body.get("created_at") or 0.0):
        errors.append("adapter_registration_time_ledger_invalid")
    if (
        body.get("provider_attestation") != PROVIDER_ATTESTATION_UNAVAILABLE
        or body.get("provider_attestation_claimed") is not False
    ):
        errors.append("adapter_registration_provider_attestation_claim_invalid")
    if body.get("trust_basis") != "host_principal_registration":
        errors.append("adapter_registration_trust_basis_invalid")
    if len(str(body.get("principal_authentication_digest") or "")) != 64:
        errors.append("adapter_registration_authentication_invalid")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "registration_id": registration_id,
        "registration_hash": body_hash,
        "implementation_digest": body.get("implementation_digest"),
        "runtime_profile_digest": body.get("runtime_profile_digest"),
        "host_identity_digest": body.get("host_identity_digest"),
        "binding_digest": body.get("binding_digest"),
        # This is a verified projection of the immutable registration row,
        # not an adapter/model declaration.  Keeping it out of the historical
        # registration hash law preserves existing receipts while allowing
        # new evidence analysis to retain principal dependence.
        "principal_id": str(body.get("principal_id") or ""),
        "host_identity": dict(host_identity or {}),
        "host_model_classification": classification_result,
        "host_model_classification_digest": classification_digest or None,
        "evidence_class": evidence_class,
        "boundary_kind": boundary_kind,
        "provider_attestation": body.get("provider_attestation"),
        "provider_attestation_claimed": body.get("provider_attestation_claimed"),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _unknown_provenance(binding: Mapping[str, Any], *, state: str = "unregistered") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "evidence_class": EVIDENCE_UNKNOWN,
        "evidence_state": state,
        "execution_boundary": "unknown",
        "implementation_digest": binding["implementation_digest"],
        "runtime_profile_digest": binding["runtime_profile_digest"],
        "host_identity_digest": binding["host_identity_digest"],
        "binding_digest": binding["binding_digest"],
        "registration_id": None,
        "trust_basis": "none" if state == "unregistered" else "invalid_registration",
        "provider_attestation": "unknown",
        "provider_attestation_claimed": False,
        "host_model_classification": {
            "schema_version": HOST_MODEL_CLASSIFICATION_SCHEMA,
            "state": "unknown",
            "model_family": "",
            "capability_class": "",
            "authority_basis": "none",
            "adapter_or_model_self_assertion_used": False,
        },
        "empirical": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def resolve_adapter_provenance(store: Any, repo: str, adapter: Any) -> dict[str, Any]:
    implementation_digest = adapter_implementation_digest(adapter)
    if is_fixture_lineage(adapter):
        return {
            "schema_version": SCHEMA,
            "evidence_class": EVIDENCE_SYNTHETIC,
            "evidence_state": "structural_only",
            "execution_boundary": "in_process_fixture",
            "implementation_digest": implementation_digest,
            "registration_id": None,
            "trust_basis": "sealed_fixture_lineage",
            "provider_attestation": "not_applicable",
            "provider_attestation_claimed": False,
            "host_model_classification": {
                "schema_version": HOST_MODEL_CLASSIFICATION_SCHEMA,
                "state": "synthetic_not_classified",
                "model_family": "",
                "capability_class": "",
                "authority_basis": "sealed_fixture_lineage",
                "adapter_or_model_self_assertion_used": False,
            },
            "empirical": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    binding = _profile_binding(adapter, strict_identity=False)
    registration = _registration(store, repo, binding)
    if registration is None:
        return _unknown_provenance(binding)
    verification = verify_adapter_registration(
        store,
        repo,
        str(registration.get("registration_id") or ""),
    )
    if verification.get("valid") is not True:
        result = _unknown_provenance(binding, state="registration_invalid")
        result["registration_id"] = registration.get("registration_id")
        return result
    evidence_class = str(registration.get("evidence_class") or EVIDENCE_UNKNOWN)
    return {
        "schema_version": SCHEMA,
        "evidence_class": evidence_class,
        "evidence_state": "host_registered",
        "execution_boundary": str(registration.get("boundary_kind") or "unknown"),
        "implementation_digest": binding["implementation_digest"],
        "runtime_profile_digest": binding["runtime_profile_digest"],
        "host_identity_digest": binding["host_identity_digest"],
        "binding_digest": binding["binding_digest"],
        "host_identity": dict(registration.get("host_identity") or {}),
        "principal_id": str(verification.get("principal_id") or ""),
        "host_model_classification": dict(
            registration.get("host_model_classification")
            or verification.get("host_model_classification")
            or {}
        ),
        "host_model_classification_digest": registration.get(
            "host_model_classification_digest"
        ),
        "registration_id": registration.get("registration_id"),
        "registration_hash": registration.get("registration_hash"),
        "trust_basis": "host_principal_registration",
        "provider_attestation": PROVIDER_ATTESTATION_UNAVAILABLE,
        "provider_attestation_claimed": False,
        "empirical": evidence_class == EVIDENCE_LIVE,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_adapter_provenance(
    store: Any,
    repo: str,
    provenance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        return {
            "valid": True,
            "evidence_class": EVIDENCE_LEGACY,
            "evidence_state": "legacy_partial",
            "empirical": False,
            "errors": [],
        }
    evidence_class = str(provenance.get("evidence_class") or EVIDENCE_UNKNOWN)
    errors: list[str] = []
    verified_principal_id = ""
    classification_projection = dict(
        provenance.get("host_model_classification") or {}
    )
    if evidence_class not in EVIDENCE_CLASSES:
        errors.append("adapter_evidence_class_invalid")
    if evidence_class == EVIDENCE_SYNTHETIC:
        if str(provenance.get("trust_basis") or "") != "sealed_fixture_lineage":
            errors.append("synthetic_fixture_lineage_invalid")
        if provenance.get("empirical") is not False:
            errors.append("synthetic_empirical_flag_invalid")
        if provenance.get("registration_id") not in {None, ""}:
            errors.append("synthetic_registration_invalid")
        synthetic_classification = provenance.get("host_model_classification")
        if not isinstance(synthetic_classification, Mapping) or (
            str(synthetic_classification.get("state") or "")
            != "synthetic_not_classified"
            or str(synthetic_classification.get("model_family") or "")
            or str(synthetic_classification.get("capability_class") or "")
        ):
            errors.append("synthetic_model_classification_invalid")
    elif evidence_class in {EVIDENCE_LIVE, EVIDENCE_ATTESTED, EVIDENCE_SIMULATED}:
        registration_id = str(provenance.get("registration_id") or "")
        check = verify_adapter_registration(store, repo, registration_id)
        if check.get("valid") is True:
            verified_principal_id = str(check.get("principal_id") or "")
        if check.get("valid") is not True:
            errors.extend(str(item) for item in check.get("errors") or ())
        comparisons = {
            "evidence_class": "adapter_evidence_registration_mismatch",
            "implementation_digest": "adapter_implementation_registration_mismatch",
            "runtime_profile_digest": "adapter_runtime_profile_registration_mismatch",
            "host_identity_digest": "adapter_host_identity_registration_mismatch",
            "binding_digest": "adapter_binding_registration_mismatch",
            "registration_hash": "adapter_registration_hash_mismatch",
            "host_model_classification_digest": (
                "adapter_model_classification_registration_mismatch"
            ),
        }
        for field, error in comparisons.items():
            if str(check.get(field) or "") != str(provenance.get(field) or ""):
                errors.append(error)
        if dict(check.get("host_identity") or {}) != dict(
            provenance.get("host_identity") or {}
        ):
            errors.append("adapter_host_identity_material_mismatch")
        if "host_model_classification" in provenance and dict(
            check.get("host_model_classification") or {}
        ) != classification_projection:
            errors.append("adapter_model_classification_material_mismatch")
        elif "host_model_classification" not in provenance:
            # Historical v9.4 invocation receipts predate this projection.
            # Preserve their original identity and expose the registration's
            # typed legacy/unknown classification without pretending a modern
            # model-family proof was present in the invocation.
            classification_projection = dict(
                check.get("host_model_classification") or {}
            )
        # New provenance carries the principal explicitly.  Historical
        # receipts may omit this projection and remain structurally valid,
        # but they cannot satisfy v9.5 independence analysis because that
        # analysis treats the missing axis as unresolved.
        supplied_principal = str(provenance.get("principal_id") or "")
        if supplied_principal and supplied_principal != str(
            check.get("principal_id") or ""
        ):
            errors.append("adapter_principal_registration_mismatch")
        if str(check.get("boundary_kind") or "") != str(
            provenance.get("execution_boundary") or ""
        ):
            errors.append("adapter_boundary_registration_mismatch")
        if evidence_class == EVIDENCE_ATTESTED:
            errors.append("provider_attestation_not_available")
        if (
            provenance.get("provider_attestation") != PROVIDER_ATTESTATION_UNAVAILABLE
            or provenance.get("provider_attestation_claimed") is not False
        ):
            errors.append("provider_attestation_claim_invalid")
        expected_empirical = evidence_class == EVIDENCE_LIVE
        if provenance.get("empirical") is not expected_empirical:
            errors.append("adapter_empirical_flag_invalid")
        if provenance.get("trust_basis") != "host_principal_registration":
            errors.append("adapter_trust_basis_invalid")
    elif evidence_class == EVIDENCE_UNKNOWN:
        if provenance.get("empirical") is True:
            errors.append("unknown_adapter_cannot_be_empirical")
        if provenance.get("registration_id") not in {None, ""}:
            errors.append("unknown_adapter_registration_invalid")
        classification = provenance.get("host_model_classification")
        if isinstance(classification, Mapping) and (
            str(classification.get("model_family") or "")
            or str(classification.get("capability_class") or "")
        ):
            errors.append("unknown_adapter_model_classification_forbidden")
    return {
        "valid": not errors,
        "evidence_class": evidence_class,
        "evidence_state": str(provenance.get("evidence_state") or "unknown"),
        "empirical": evidence_class == EVIDENCE_LIVE and not errors,
        "errors": sorted(set(errors)),
        "host_model_classification": classification_projection,
        "principal_id": verified_principal_id,
    }


def evidence_satisfies(observed: str, minimum: str) -> bool:
    return EVIDENCE_ORDER.get(str(observed), -1) >= EVIDENCE_ORDER.get(str(minimum), 99)


__all__ = [
    "BOUNDARY_CLASSES",
    "CLAIM_BOUNDARY",
    "EVIDENCE_ATTESTED",
    "EVIDENCE_CLASSES",
    "EVIDENCE_LEGACY",
    "EVIDENCE_LIVE",
    "EVIDENCE_ORDER",
    "EVIDENCE_SIMULATED",
    "EVIDENCE_SYNTHETIC",
    "EVIDENCE_UNKNOWN",
    "FIXTURE_LINEAGE_MARKER",
    "HOST_MODEL_CLASSIFICATION_SCHEMA",
    "PROVIDER_ATTESTATION_UNAVAILABLE",
    "SCHEMA",
    "VERSION",
    "AdapterProvenanceError",
    "adapter_implementation_digest",
    "ensure_adapter_provenance_tables",
    "evidence_satisfies",
    "is_fixture_lineage",
    "register_adapter_provenance",
    "resolve_adapter_provenance",
    "verify_adapter_provenance",
    "verify_adapter_registration",
]
