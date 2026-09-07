"""Canonical structured edit intents compiled into exact patch proposals.

Models describe bounded preimage replacements. Cortex, not the model, computes
unified-diff coordinates. Compilation grants no execution or mutation authority.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .coding_workspace import create_patch_proposal

INTENT_SCHEMA = "cortex-structured-edit-intent/1.0"
INTENT_SCHEMA_V2 = "cortex-structured-edit-intent/2.0"
LEGACY_COMPILATION_SCHEMA = "cortex-edit-intent-compilation/1.0"
COMPILATION_SCHEMA = "cortex-edit-intent-compilation/2.0"
COMPILATION_SCHEMA_V21 = "cortex-edit-intent-compilation/2.1"
PARSER_SEMANTICS_STRICT = "strict-string-fields/2.0"
PARSER_SEMANTICS_LEGACY = "legacy-coercing/1.0"
MAX_EDITS = 16
MAX_TEXT_BYTES = 65_536


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse(payload: str | Mapping[str, Any], *, legacy: bool = False) -> dict[str, Any]:
    try:
        value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("edit intent must be one valid JSON object") from exc
    if not isinstance(value, Mapping):
        raise ValueError("edit intent must be one valid JSON object")
    if set(value) != {"schema_version", "summary", "edits"}:
        raise ValueError("edit intent contains missing or unknown top-level fields")
    schema = value.get("schema_version")
    if schema not in {INTENT_SCHEMA, INTENT_SCHEMA_V2}:
        raise ValueError("edit intent schema is invalid")
    if schema == INTENT_SCHEMA_V2 and legacy:
        raise ValueError("historical intent interpreted under new parser semantics")
    if not legacy and not isinstance(value.get("summary"), str):
        raise ValueError("edit summary must be a string")
    summary = str(value.get("summary") or "").strip()
    edits = value.get("edits")
    if not summary or len(summary) > 500 or not isinstance(edits, list) or not 1 <= len(edits) <= MAX_EDITS:
        raise ValueError("edit intent summary or edit count is invalid")
    normalized: list[dict[str, str]] = []
    for edit in edits:
        if not isinstance(edit, Mapping) or set(edit) != {"path", "old", "new"}:
            raise ValueError("each edit must contain exactly path, old, and new")
        if not legacy and any(not isinstance(edit[key], str) for key in ("path", "old", "new")):
            raise ValueError("edit fields must be strings")
        row = {key: str(edit[key]).replace("\r\n", "\n") for key in ("path", "old", "new")}
        if not row["path"] or not row["old"] or row["old"] == row["new"]:
            raise ValueError("edit path and distinct non-empty preimage are required")
        if len((row["old"] + row["new"]).encode("utf-8")) > MAX_TEXT_BYTES:
            raise ValueError("edit text exceeds the bounded limit")
        normalized.append(row)
    identity = INTENT_SCHEMA if legacy else schema
    return {"schema_version": identity, "summary": summary, "edits": normalized}


def _target(root: Path, relative: str, allowed: set[str]) -> Path:
    normalized = Path(relative).as_posix()
    if normalized not in allowed or normalized.startswith(("/", "../")) or "/../" in normalized:
        raise ValueError("edit target is outside the host-declared scope")
    path = (root / normalized).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("edit target escapes the repository") from exc
    if not path.is_file():
        raise ValueError("edit target is not a current file")
    return path


def _compile_edit_intent(
    root: str | Path,
    payload: str | Mapping[str, Any],
    *,
    allowed_targets: Sequence[str],
    legacy: bool = False,
    parser_semantics_id: str | None = None,
    allowed_intent_schema: str | None = None,
) -> dict[str, Any]:
    workspace = Path(root).resolve()
    intent = _parse(payload, legacy=legacy)
    if allowed_intent_schema and intent["schema_version"] != allowed_intent_schema:
        raise ValueError("edit intent schema is invalid")
    if parser_semantics_id == PARSER_SEMANTICS_LEGACY and not legacy:
        raise ValueError("historical intent interpreted under new parser semantics")
    if parser_semantics_id == PARSER_SEMANTICS_STRICT and legacy:
        raise ValueError("historical intent interpreted under new parser semantics")
    allowed = {Path(str(value)).as_posix() for value in allowed_targets}
    if not allowed:
        raise ValueError("host-declared target scope is required")
    originals: dict[str, str] = {}
    postimages: dict[str, str] = {}
    for edit in intent["edits"]:
        relative = Path(edit["path"]).as_posix()
        path = _target(workspace, relative, allowed)
        if relative not in originals:
            originals[relative] = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            postimages[relative] = originals[relative]
        current = postimages[relative]
        occurrences = current.count(edit["old"])
        if occurrences != 1:
            raise ValueError(f"edit preimage must resolve exactly once: {relative}:{occurrences}")
        postimages[relative] = current.replace(edit["old"], edit["new"], 1)
    chunks: list[str] = []
    for relative in sorted(originals):
        diff = list(difflib.unified_diff(
            originals[relative].splitlines(keepends=True),
            postimages[relative].splitlines(keepends=True),
            fromfile=f"a/{relative}", tofile=f"b/{relative}", lineterm="\n",
        ))
        if not diff:
            raise ValueError("compiled edit produced no source change")
        if not legacy:
            diff = [line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in diff]
        chunks.append(f"diff --git a/{relative} b/{relative}\n" + "".join(diff))
    patch = "".join(chunks)
    if not patch.endswith("\n"):
        patch += "\n"
    proposal = create_patch_proposal(workspace, patch, intent["summary"])
    emit_semantics = parser_semantics_id is not None
    material: dict[str, Any] = {
        "schema_version": (
            LEGACY_COMPILATION_SCHEMA if legacy else
            COMPILATION_SCHEMA_V21 if emit_semantics else COMPILATION_SCHEMA
        ),
        "compiler_id": "cortex.edit-intent.deterministic-replacement.v1" if legacy else "cortex.edit-intent.deterministic-replacement.v2",
        "intent": intent,
        "intent_hash": _sha(intent),
        "allowed_targets": sorted(allowed),
        "preimage_hashes": proposal["preimage_hashes"],
        "postimage_hashes": {
            relative: hashlib.sha256(postimages[relative].encode("utf-8")).hexdigest()
            for relative in sorted(postimages)
        },
        "proposal": proposal,
        "proposal_hash": proposal["proposal_hash"],
        "compiled_not_model_authored_diff": True,
        "operator_approval_required": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    if emit_semantics:
        material["parser_semantics_id"] = parser_semantics_id
        material["allowed_intent_schema"] = allowed_intent_schema or intent["schema_version"]
    material["compilation_hash"] = _sha(material)
    return material


def compile_edit_intent(
    root: str | Path,
    payload: str | Mapping[str, Any],
    *,
    allowed_targets: Sequence[str],
    parser_semantics_id: str | None = None,
    allowed_intent_schema: str | None = None,
) -> dict[str, Any]:
    """New compilations use strict v2; v1 remains available only for reconstruction.

    Default identity remains compilation/2.0. Parser semantics are explicit only
    when parser_semantics_id is supplied (compilation/2.1).
    """
    return _compile_edit_intent(
        root,
        payload,
        allowed_targets=allowed_targets,
        parser_semantics_id=parser_semantics_id,
        allowed_intent_schema=allowed_intent_schema,
    )


def verify_edit_intent_compilation(root: str | Path, compilation: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in compilation.items() if key != "compilation_hash"}
    allowed_schemas = {COMPILATION_SCHEMA, LEGACY_COMPILATION_SCHEMA, COMPILATION_SCHEMA_V21}
    if compilation.get("schema_version") not in allowed_schemas or compilation.get("compilation_hash") != _sha(body):
        errors.append("compilation_identity_invalid")
    try:
        rebuilt = _compile_edit_intent(
            root, compilation.get("intent") or {}, allowed_targets=compilation.get("allowed_targets") or (),
            legacy=compilation.get("schema_version") == LEGACY_COMPILATION_SCHEMA,
            parser_semantics_id=compilation.get("parser_semantics_id"),
            allowed_intent_schema=compilation.get("allowed_intent_schema"),
        )
    except (OSError, ValueError) as exc:
        errors.append("compilation_reconstruction_failed:" + str(exc))
    else:
        if rebuilt != dict(compilation):
            errors.append("compilation_reconstruction_mismatch")
    for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
        if compilation.get(field) is not False:
            errors.append(f"authority_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors}


__all__ = [
    "INTENT_SCHEMA",
    "INTENT_SCHEMA_V2",
    "COMPILATION_SCHEMA",
    "COMPILATION_SCHEMA_V21",
    "PARSER_SEMANTICS_LEGACY",
    "PARSER_SEMANTICS_STRICT",
    "compile_edit_intent",
    "verify_edit_intent_compilation",
]
