"""Repository identity continuity — same path ≠ automatic same memory namespace.

CortexV5CI vs CortexTeach on one filesystem path are distinct durable bodies
unless an explicit identity check/merge is performed. Recommend-only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA = "cortex-identity/1.0"
GLYPH = "⌖"

# Path markers that indicate a non-durable Cortex home (CI scratch, OS temp).
_TEMP_HOME_MARKERS = (
    "/temp/",
    "\\temp\\",
    "/tmp/",
    "\\tmp\\",
    "/tmpdir",
    "\\tmpdir",
    "appdata\\local\\temp",
    "appdata/local/temp",
    "/var/folders/",  # macOS temp
    "temporarydirectory",
    "/pytest-",
    "\\pytest-",
)


def home_looks_temporary(home: Path | str | None) -> bool:
    """True when home path is likely OS/CI temporary storage."""

    if not home:
        return False
    normalized = str(Path(home).expanduser()).replace("\\", "/").casefold()
    return any(marker in normalized for marker in _TEMP_HOME_MARKERS)


def _row_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {
            "name": row["name"],
            "repository_id": row["repository_id"],
            "path": row["path"],
            "bootstrap_status": row["bootstrap_status"],
            "manifest_hash": row["manifest_hash"],
        }


def continuity_check(
    store: Any,
    *,
    repo: str | None = None,
    path: Path | str | None = None,
    cortex_home: Path | str | None = None,
) -> dict[str, Any]:
    """Report identity aliases and continuity boundaries for a repo or path."""

    primary = store.repo(repo) if repo else None
    resolved: str | None = None
    if path is not None:
        resolved = str(Path(path).expanduser().resolve())
    elif primary is not None:
        resolved = str(primary["path"])

    path_aliases: list[dict[str, Any]] = []
    id_aliases: list[dict[str, Any]] = []
    if resolved:
        for row in store.repos():
            if str(row["path"]) == resolved:
                path_aliases.append(_row_dict(row))
    if primary is not None:
        rid = primary["repository_id"]
        for row in store.repos():
            if row["repository_id"] == rid:
                id_aliases.append(_row_dict(row))

    path_names = {a.get("name") for a in path_aliases}
    id_names = {a.get("name") for a in id_aliases}
    multi_name_same_path = len(path_names) > 1
    multi_name_same_id = len(id_names) > 1
    # Different names, same path, different repository_id = hard continuity boundary
    ids_on_path = {a.get("repository_id") for a in path_aliases}
    split_identity = multi_name_same_path and len(ids_on_path) > 1

    home_path: str | None = None
    if cortex_home is not None:
        home_path = str(Path(cortex_home).expanduser())
    else:
        try:
            home_path = str(getattr(store, "home", None) or "")
            if not home_path:
                home_path = None
        except Exception:
            home_path = None
    temporary_home = home_looks_temporary(home_path)

    warnings: list[str] = []
    if multi_name_same_path:
        warnings.append(
            "multiple_repo_names_share_filesystem_path — durable memory namespaces "
            "are separate; do not merge teaching mass without explicit check"
        )
    if split_identity:
        warnings.append(
            "same_path_different_repository_id — hard continuity boundary "
            "(e.g. CortexV5CI vs CortexTeach)"
        )
    if multi_name_same_id and multi_name_same_path:
        warnings.append(
            "alias_names_same_id — names share repository_id; still treat as one body"
        )
    if temporary_home:
        warnings.append(
            "cortex_home_looks_temporary — cross-process memory continuity depends on "
            "this home surviving; prefer a stable CORTEX_HOME (e.g. ~/.cortex) and re-bootstrap"
        )

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "path": resolved,
        "primary": _row_dict(primary) if primary else None,
        "path_aliases": path_aliases,
        "id_aliases": id_aliases,
        "cortex_home": home_path,
        "continuity": {
            "multi_name_same_path": multi_name_same_path,
            "split_identity": split_identity,
            "temporary_home": temporary_home,
            "safe_to_assume_same_memory": (
                not multi_name_same_path
                or (len(ids_on_path) == 1 and not split_identity)
            ),
        },
        "warnings": warnings,
        "claim_boundary": (
            "Identity continuity is namespace hygiene; it grants no mutation rights "
            "and does not auto-merge durable memory."
        ),
    }


def warn_on_attach(
    store: Any, name: str, repository_id: str, path: Path
) -> list[str]:
    """Return warnings when attaching a name onto a path already used by others."""

    report = continuity_check(store, repo=None, path=path)
    warnings = list(report.get("warnings") or [])
    for alias in report.get("path_aliases") or []:
        if alias.get("name") and alias.get("name") != name:
            if alias.get("repository_id") != repository_id:
                warnings.append(
                    f"path_already_bound_as:{alias.get('name')} "
                    f"id={alias.get('repository_id')} — separate durable body"
                )
            else:
                warnings.append(
                    f"path_alias_name:{alias.get('name')} shares repository_id"
                )
    return list(dict.fromkeys(warnings))
