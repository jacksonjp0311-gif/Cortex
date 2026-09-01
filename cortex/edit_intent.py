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
COMPILATION_SCHEMA = "cortex-edit-intent-compilation/1.0"
MAX_EDITS = 16
MAX_TEXT_BYTES = 65_536


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("edit intent must be one valid JSON object") from exc
    if set(value) != {"schema_version", "summary", "edits"}:
        raise ValueError("edit intent contains missing or unknown top-level fields")
    if value.get("schema_version") != INTENT_SCHEMA:
        raise ValueError("edit intent schema is invalid")
    summary = str(value.get("summary") or "").strip()
    edits = value.get("edits")
    if not summary or len(summary) > 500 or not isinstance(edits, list) or not 1 <= len(edits) <= MAX_EDITS:
        raise ValueError("edit intent summary or edit count is invalid")
    normalized: list[dict[str, str]] = []
    for edit in edits:
        if not isinstance(edit, Mapping) or set(edit) != {"path", "old", "new"}:
            raise ValueError("each edit must contain exactly path, old, and new")
        row = {key: str(edit[key]).replace("\r\n", "\n") for key in ("path", "old", "new")}
        if not row["path"] or not row["old"] or row["old"] == row["new"]:
            raise ValueError("edit path and distinct non-empty preimage are required")
        if len((row["old"] + row["new"]).encode("utf-8")) > MAX_TEXT_BYTES:
            raise ValueError("edit text exceeds the bounded limit")
        normalized.append(row)
    return {"schema_version": INTENT_SCHEMA, "summary": summary, "edits": normalized}


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


def compile_edit_intent(
    root: str | Path,
    payload: str | Mapping[str, Any],
    *,
    allowed_targets: Sequence[str],
) -> dict[str, Any]:
    workspace = Path(root).resolve()
    intent = _parse(payload)
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
        chunks.append(f"diff --git a/{relative} b/{relative}\n" + "".join(diff))
    patch = "".join(chunks)
    if not patch.endswith("\n"):
        patch += "\n"
    proposal = create_patch_proposal(workspace, patch, intent["summary"])
    material: dict[str, Any] = {
        "schema_version": COMPILATION_SCHEMA,
        "compiler_id": "cortex.edit-intent.deterministic-replacement.v1",
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
    material["compilation_hash"] = _sha(material)
    return material


def verify_edit_intent_compilation(root: str | Path, compilation: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in compilation.items() if key != "compilation_hash"}
    if compilation.get("schema_version") != COMPILATION_SCHEMA or compilation.get("compilation_hash") != _sha(body):
        errors.append("compilation_identity_invalid")
    try:
        rebuilt = compile_edit_intent(
            root, compilation.get("intent") or {}, allowed_targets=compilation.get("allowed_targets") or ()
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


__all__ = ["INTENT_SCHEMA", "COMPILATION_SCHEMA", "compile_edit_intent", "verify_edit_intent_compilation"]
