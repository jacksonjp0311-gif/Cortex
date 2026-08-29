"""Canonical provider-neutral tool manifests and execution receipts.

Tools expose bounded host capabilities.  A model may request a registered tool,
but it cannot register one, widen a grant, approve execution, or convert a tool
result into truth or authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MANIFEST_SCHEMA = "cortex-tool-manifest/1.0"
EXECUTION_SCHEMA = "cortex-tool-execution-receipt/1.0"
GRANT_SCHEMA = "cortex-agent-capability-grant/2.0"
AUTHORITY_CLASSES = {"observational", "analytical", "proposal", "execution", "mutation", "external"}
EXECUTION_STATUSES = {"completed", "failed", "denied", "cancelled"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def safe(value: Any) -> Any:
    return json.loads(canonical(value))


@dataclass(frozen=True)
class ToolManifest:
    tool_id: str
    version: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    authority_class: str
    side_effects: tuple[str, ...] = ()
    requires_explicit_scope: bool = False
    supports_cancellation: bool = False
    network_access: bool = False
    secret_access: bool = False

    def material(self) -> dict[str, Any]:
        tool_id = str(self.tool_id or "").strip()
        version = str(self.version or "").strip()
        authority = str(self.authority_class or "").strip()
        if not tool_id or not version:
            raise ValueError("tool manifest requires tool_id and version")
        if authority not in AUTHORITY_CLASSES:
            raise ValueError("tool manifest authority class is invalid")
        return {
            "schema_version": MANIFEST_SCHEMA,
            "tool_id": tool_id,
            "version": version,
            "description": str(self.description or "").strip(),
            "input_schema": safe(dict(self.input_schema)),
            "output_schema": safe(dict(self.output_schema)),
            "authority_class": authority,
            "side_effects": sorted({str(value) for value in self.side_effects}),
            "requires_explicit_scope": bool(self.requires_explicit_scope),
            "supports_cancellation": bool(self.supports_cancellation),
            "network_access": bool(self.network_access),
            "secret_access": bool(self.secret_access),
            "provider_neutral": True,
            "model_registration_authorized": False,
            "authority_granting": False,
        }

    @property
    def manifest_hash(self) -> str:
        return digest(self.material())

    def descriptor(self) -> dict[str, Any]:
        return {**self.material(), "manifest_hash": self.manifest_hash}

    def provider_definition(self) -> dict[str, Any]:
        return {
            "name": self.tool_id,
            "description": self.description,
            "input_schema": safe(dict(self.input_schema)),
            "manifest_hash": self.manifest_hash,
            "authority_class": self.authority_class,
        }

    @classmethod
    def from_descriptor(cls, descriptor: Mapping[str, Any]) -> "ToolManifest":
        manifest = cls(
            tool_id=str(descriptor.get("tool_id") or ""),
            version=str(descriptor.get("version") or ""),
            description=str(descriptor.get("description") or ""),
            input_schema=dict(descriptor.get("input_schema") or {}),
            output_schema=dict(descriptor.get("output_schema") or {}),
            authority_class=str(descriptor.get("authority_class") or ""),
            side_effects=tuple(str(value) for value in descriptor.get("side_effects") or ()),
            requires_explicit_scope=bool(descriptor.get("requires_explicit_scope")),
            supports_cancellation=bool(descriptor.get("supports_cancellation")),
            network_access=bool(descriptor.get("network_access")),
            secret_access=bool(descriptor.get("secret_access")),
        )
        if descriptor.get("manifest_hash") != manifest.manifest_hash:
            raise ValueError("tool manifest descriptor hash is invalid")
        return manifest


class ToolCatalog:
    """Host-owned immutable-by-identity manifest catalog."""

    def __init__(self, manifests: tuple[ToolManifest, ...] = ()) -> None:
        self._manifests: dict[str, ToolManifest] = {}
        for manifest in manifests:
            self.register(manifest)

    def register(self, manifest: ToolManifest) -> None:
        existing = self._manifests.get(manifest.tool_id)
        if existing and existing.manifest_hash != manifest.manifest_hash:
            raise ValueError("tool identity already has different manifest content")
        self._manifests[manifest.tool_id] = manifest

    def resolve(self, tool_id: str) -> ToolManifest | None:
        return self._manifests.get(str(tool_id))

    def descriptors(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._manifests[key].descriptor() for key in sorted(self._manifests))


def _type_matches(value: Any, declared: str) -> bool:
    if declared == "string":
        return isinstance(value, str)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "array":
        return isinstance(value, list)
    if declared == "object":
        return isinstance(value, Mapping)
    return False


def validate_arguments(manifest: ToolManifest, arguments: Mapping[str, Any]) -> list[str]:
    """Validate the conservative JSON-schema subset used by native tools."""
    schema = manifest.input_schema
    errors: list[str] = []
    if schema.get("type") != "object":
        return ["manifest_input_schema_unsupported"]
    properties = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
    required = {str(value) for value in schema.get("required") or ()}
    unknown = sorted(set(arguments) - set(properties))
    if unknown:
        errors.extend(f"argument_unknown:{key}" for key in unknown)
    for key in sorted(required):
        if key not in arguments:
            errors.append(f"argument_required:{key}")
    for key, value in arguments.items():
        declaration = properties.get(key)
        if not isinstance(declaration, Mapping):
            continue
        declared_type = str(declaration.get("type") or "")
        if not _type_matches(value, declared_type):
            errors.append(f"argument_type:{key}:{declared_type}")
            continue
        if declared_type == "array":
            item_type = str((declaration.get("items") or {}).get("type") or "") if isinstance(declaration.get("items"), Mapping) else ""
            if item_type and any(not _type_matches(item, item_type) for item in value):
                errors.append(f"argument_item_type:{key}:{item_type}")
        if declared_type in {"integer", "number"}:
            if declaration.get("minimum") is not None and value < declaration["minimum"]:
                errors.append(f"argument_minimum:{key}")
            if declaration.get("maximum") is not None and value > declaration["maximum"]:
                errors.append(f"argument_maximum:{key}")
    return errors


def validate_output(manifest: ToolManifest, output: Any) -> list[str]:
    """Validate the deliberately small output-schema surface used by tools."""
    schema = manifest.output_schema
    declarations = schema.get("oneOf") if isinstance(schema.get("oneOf"), list) else [schema]
    allowed = {
        str(item.get("type") or "")
        for item in declarations
        if isinstance(item, Mapping)
    }
    if not allowed or not any(_type_matches(output, declared) for declared in allowed):
        return ["output_type_invalid"]
    return []


def create_execution_receipt(
    *,
    tool_call_id: str,
    manifest: ToolManifest,
    capability_grant_hash: str,
    arguments: Mapping[str, Any],
    status: str,
    output: Any,
    started_at: float,
    completed_at: float,
) -> dict[str, Any]:
    if status not in EXECUTION_STATUSES:
        raise ValueError("tool execution status is invalid")
    normalized_arguments = safe(dict(arguments))
    normalized_output = safe(output)
    body = {
        "schema_version": EXECUTION_SCHEMA,
        "tool_call_id": str(tool_call_id),
        "tool_name": manifest.tool_id,
        "tool_version": manifest.version,
        "manifest_hash": manifest.manifest_hash,
        "capability_grant_hash": str(capability_grant_hash),
        "authority_class": manifest.authority_class,
        "arguments": normalized_arguments,
        "arguments_hash": digest(normalized_arguments),
        "status": status,
        "output": normalized_output,
        "output_hash": digest(normalized_output),
        "trusted": False,
        "started_at": float(started_at),
        "completed_at": float(completed_at),
        "elapsed_ms": round(max(0.0, float(completed_at) - float(started_at)) * 1000.0, 3),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    body["result_hash"] = digest(body)
    return body


def verify_execution_receipt(
    receipt: Mapping[str, Any],
    catalog: ToolCatalog,
    capability_grant: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    material = {key: value for key, value in dict(receipt).items() if key != "result_hash"}
    if receipt.get("schema_version") != EXECUTION_SCHEMA:
        errors.append("execution_schema_invalid")
    if receipt.get("result_hash") != digest(material):
        errors.append("execution_hash_invalid")
    manifest = catalog.resolve(str(receipt.get("tool_name") or ""))
    if manifest is None:
        if receipt.get("status") != "denied" or receipt.get("manifest_hash") not in {None, ""}:
            errors.append("manifest_missing")
    else:
        if receipt.get("manifest_hash") != manifest.manifest_hash or receipt.get("tool_version") != manifest.version:
            errors.append("manifest_binding_invalid")
        if receipt.get("authority_class") != manifest.authority_class:
            errors.append("authority_class_invalid")
        arguments = receipt.get("arguments") if isinstance(receipt.get("arguments"), Mapping) else {}
        errors.extend(validate_arguments(manifest, arguments))
        errors.extend(validate_output(manifest, receipt.get("output")))
    if receipt.get("arguments_hash") != digest(receipt.get("arguments")):
        errors.append("arguments_hash_invalid")
    if receipt.get("output_hash") != digest(receipt.get("output")):
        errors.append("output_hash_invalid")
    grant_material = dict(capability_grant)
    if receipt.get("capability_grant_hash") != digest(grant_material):
        errors.append("capability_grant_binding_invalid")
    if receipt.get("tool_name") not in set(grant_material.get("allowed_tools") or ()) and receipt.get("status") != "denied":
        errors.append("tool_not_granted")
    if receipt.get("status") not in EXECUTION_STATUSES:
        errors.append("execution_status_invalid")
    if float(receipt.get("completed_at") or 0.0) < float(receipt.get("started_at") or 0.0):
        errors.append("execution_chronology_invalid")
    for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
        if receipt.get(field) is not False:
            errors.append(f"authority_open:{field}")
    return {"valid": not errors, "errors": errors, "manifest_hash": manifest.manifest_hash if manifest else None}


__all__ = [
    "AUTHORITY_CLASSES", "EXECUTION_SCHEMA", "GRANT_SCHEMA", "MANIFEST_SCHEMA",
    "ToolCatalog", "ToolManifest", "canonical", "create_execution_receipt",
    "digest", "safe", "validate_arguments", "validate_output", "verify_execution_receipt",
]
