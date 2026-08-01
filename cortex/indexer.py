from __future__ import annotations

import fnmatch
import hashlib
import os
import time
from pathlib import Path
from typing import Any, Iterator

from .aria_meta.substrate import (
    ARIA_SUBSTRATE_DEFERRED_STATUS,
    classify_aria_task,
    is_aria_anchor_path,
    is_internal_aria_path,
    load_aria_cue_profile,
    should_defer_aria_indexing,
    substrate_work_proxy,
)
from .config import RUNTIME_EVIDENCE_HINTS, SPECIAL_TEXT_FILES, RepoConfig
from .embeddings import get_embedder
from .parsers import classify_file, language_for, parse_structure


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    sample = data[:8192]
    if not sample:
        return False
    control = sum(byte < 9 or (13 < byte < 32) for byte in sample)
    return control / len(sample) > 0.20


def should_exclude(relative: str, config: RepoConfig) -> bool:
    normalized = relative.replace("\\", "/").strip("/")
    parts = normalized.split("/") if normalized else []
    for pattern in config.exclude:
        clean = pattern.replace("\\", "/").strip("/")
        if not clean:
            continue
        if clean in parts or normalized == clean or normalized.startswith(clean + "/"):
            return True
        if fnmatch.fnmatch(normalized, clean):
            return True
    return False


def is_supported_text(path: Path, config: RepoConfig) -> bool:
    name = path.name
    suffix = path.suffix.lower()
    if name in SPECIAL_TEXT_FILES:
        return True
    if name.lower().startswith(("readme", "license", "changelog")):
        return True
    return suffix in {extension.lower() for extension in config.include_extensions}


def walk_repository(root: Path, config: RepoConfig) -> Iterator[tuple[Path, str]]:
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        relative_dir = current.relative_to(root).as_posix()
        kept: list[str] = []
        for dirname in dirnames:
            candidate = f"{relative_dir}/{dirname}" if relative_dir != "." else dirname
            if not should_exclude(candidate, config):
                kept.append(dirname)
        dirnames[:] = kept
        for filename in filenames:
            path = current / filename
            relative = path.relative_to(root).as_posix()
            if not should_exclude(relative, config):
                yield path, relative


def chunk_text(text: str, max_chars: int, overlap_lines: int) -> Iterator[tuple[int, int, int, str]]:
    lines = text.splitlines()
    if not lines:
        yield 0, 1, 1, ""
        return
    start = 0
    chunk_index = 0
    while start < len(lines):
        end = start
        size = 0
        while end < len(lines):
            next_size = len(lines[end]) + 1
            if end > start and size + next_size > max_chars:
                break
            size += next_size
            end += 1
        body = "\n".join(lines[start:end])
        yield chunk_index, start + 1, max(start + 1, end), body
        chunk_index += 1
        if end >= len(lines):
            break
        start = max(start + 1, end - overlap_lines)


def _authoritative(relative: str, config: RepoConfig) -> bool:
    normalized = relative.replace("\\", "/")
    return any(
        normalized == path or normalized.startswith(path.rstrip("/") + "/")
        for path in config.authoritative_paths
    )


def _progress(msg: str) -> None:
    """Heartbeat so long first-index does not look hung (stderr, line-buffered)."""
    if os.environ.get("CORTEX_INDEX_QUIET", "").strip() in {"1", "true", "yes"}:
        return
    try:
        import sys

        sys.stderr.write(f"   … {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass


def scan_repository(root: Path, config: RepoConfig) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    excluded_roots = sorted(set(config.exclude))
    _progress(f"scanning {root.name} (first attach can take a minute)…")
    n = 0
    last_beat = time.time()
    for path, relative in walk_repository(root, config):
        n += 1
        now = time.time()
        if n == 1 or n % 200 == 0 or (now - last_beat) >= 3.0:
            _progress(f"scanned {n} paths…")
            last_beat = now
        try:
            stat = path.stat()
        except OSError as exc:
            files.append({"path": relative, "status": "unreadable", "reason": str(exc)})
            continue
        record: dict[str, Any] = {
            "path": relative,
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "authoritative": _authoritative(relative, config),
        }
        if stat.st_size > config.max_file_bytes:
            record.update({"status": "oversized", "reason": "max_file_bytes exceeded"})
        elif not is_supported_text(path, config):
            record.update({"status": "unsupported", "reason": "unsupported extension or format"})
        else:
            try:
                raw = path.read_bytes()
                if is_binary(raw):
                    record.update({"status": "binary", "reason": "binary content detected"})
                else:
                    record.update({"status": "eligible", "content_hash": sha256_bytes(raw)})
            except OSError as exc:
                record.update({"status": "unreadable", "reason": str(exc)})
        files.append(record)
    _progress(f"scan complete — {len(files)} files catalogued")
    manifest_material = [
        f"{item['path']}|{item['status']}|{item.get('content_hash', '')}|{item.get('size_bytes', 0)}"
        for item in sorted(files, key=lambda item: item["path"])
    ]
    manifest_hash = sha256_bytes("\n".join(manifest_material).encode("utf-8"))
    return {
        "root": str(root),
        "scanned_at": time.time(),
        "files": files,
        "excluded_rules": excluded_roots,
        "manifest_hash": manifest_hash,
    }


def _index_file_body(
    store: Any,
    repo_name: str,
    root: Path,
    relative: str,
    item: dict[str, Any],
    *,
    kind: str,
    language: str,
    content_hash: str,
    config: RepoConfig,
    embedder: Any,
    indexing_tier: str,
) -> tuple[int, int, int]:
    """Fully index one file. Returns (chunks, symbols, edges)."""

    path = root / relative
    text = path.read_text(encoding="utf-8", errors="replace")
    store.remove_path(repo_name, relative)
    chunks = 0
    for chunk_index, start_line, end_line, body in chunk_text(
        text, config.chunk_chars, config.chunk_overlap_lines
    ):
        chunk_hash = sha256_bytes(body.encode("utf-8"))
        vector = embedder.encode_one(body)
        store.upsert_memory(
            repo=repo_name,
            path=relative,
            chunk_index=chunk_index,
            start_line=start_line,
            end_line=end_line,
            kind=kind,
            text=body,
            content_hash=chunk_hash,
            vector=vector,
            embedding_model=embedder.name,
            metadata={
                "file_hash": content_hash,
                "language": language,
                "authoritative": item.get("authoritative", False),
                "indexing_tier": indexing_tier,
                "neural_region": (
                    "internal_aria_substrate"
                    if is_internal_aria_path(relative)
                    else "repository"
                ),
            },
        )
        chunks += 1

    symbols, edges = parse_structure(text, relative, language)
    for symbol in symbols:
        store.add_symbol(repo_name, relative, symbol)
    for edge in edges:
        store.add_edge(repo_name, edge.to_dict())
    store.upsert_file({
        "repo": repo_name,
        "path": relative,
        "kind": kind,
        "language": language,
        "size_bytes": item["size_bytes"],
        "mtime_ns": item["mtime_ns"],
        "content_hash": content_hash,
        "status": "indexed",
        "authoritative": item.get("authoritative", False),
        "metadata": {
            "encoding": "utf-8",
            "replacement_errors": True,
            "indexing_tier": indexing_tier,
            "neural_region": (
                "internal_aria_substrate"
                if is_internal_aria_path(relative)
                else "repository"
            ),
        },
    })
    return chunks, len(symbols), len(edges)


def index_repository(
    store: Any,
    repo_name: str,
    config: RepoConfig,
    force: bool = False,
    *,
    materialize_aria: bool = False,
) -> dict[str, Any]:
    repository = store.repo(repo_name)
    if not repository:
        raise ValueError(f"Unknown repository: {repo_name}")
    root = Path(repository["path"])
    if not root.exists():
        raise FileNotFoundError(root)

    manifest = scan_repository(root, config)
    embedder = get_embedder()
    live_paths: set[str] = set()
    indexed_files = 0
    unchanged_files = 0
    unsupported_files = 0
    failed_files = 0
    deferred_files = 0
    deferred_unchanged = 0
    indexed_chunks = 0
    structural_edges = 0
    symbols_found = 0
    indexing_mode = getattr(config, "aria_substrate_indexing", "deferred")
    if materialize_aria:
        indexing_mode = "eager"

    total = len(manifest["files"])
    eligible = sum(1 for f in manifest["files"] if f.get("status") == "eligible")
    _progress(f"indexing {eligible} eligible / {total} total…")
    last_beat = time.time()
    for i, item in enumerate(manifest["files"], start=1):
        relative = item["path"]
        live_paths.add(relative)
        now = time.time()
        if i == 1 or i % 50 == 0 or (now - last_beat) >= 3.0:
            _progress(f"indexed {indexed_files} files ({i}/{total})…")
            last_beat = now
        path = root / relative
        status = item["status"]
        existing = store.file(repo_name, relative)
        language = language_for(path)
        kind = classify_file(path, relative, RUNTIME_EVIDENCE_HINTS)
        content_hash = item.get("content_hash", "")

        if status != "eligible":
            store.upsert_file({
                "repo": repo_name,
                "path": relative,
                "kind": kind,
                "language": language,
                "size_bytes": item.get("size_bytes", 0),
                "mtime_ns": item.get("mtime_ns", 0),
                "content_hash": content_hash,
                "status": status,
                "authoritative": item.get("authoritative", False),
                "metadata": {"reason": item.get("reason", "")},
            })
            unsupported_files += 1
            continue

        defer = should_defer_aria_indexing(relative, indexing_mode)
        if defer:
            unchanged_deferred = (
                not force
                and existing is not None
                and existing["content_hash"] == content_hash
                and existing["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS
            )
            if unchanged_deferred:
                deferred_unchanged += 1
                deferred_files += 1
                continue
            # Inventory-only: known, hash-verified, not chunked or embedded.
            store.remove_path(repo_name, relative)
            store.upsert_file({
                "repo": repo_name,
                "path": relative,
                "kind": kind,
                "language": language,
                "size_bytes": item.get("size_bytes", 0),
                "mtime_ns": item.get("mtime_ns", 0),
                "content_hash": content_hash,
                "status": ARIA_SUBSTRATE_DEFERRED_STATUS,
                "authoritative": item.get("authoritative", False),
                "metadata": {
                    "indexing_tier": "deferred",
                    "neural_region": "internal_aria_substrate",
                    "dormant_by_default": True,
                    "materialize_on": "aria_active_task",
                },
            })
            deferred_files += 1
            continue

        expected_status = "indexed"
        unchanged = (
            not force
            and existing is not None
            and existing["content_hash"] == content_hash
            and existing["status"] == expected_status
        )
        if unchanged:
            unchanged_files += 1
            continue

        try:
            tier = (
                "anchor"
                if is_aria_anchor_path(relative)
                else "eager_substrate"
                if is_internal_aria_path(relative)
                else "repository"
            )
            chunks, sym_count, edge_count = _index_file_body(
                store,
                repo_name,
                root,
                relative,
                item,
                kind=kind,
                language=language,
                content_hash=content_hash,
                config=config,
                embedder=embedder,
                indexing_tier=tier,
            )
            indexed_chunks += chunks
            symbols_found += sym_count
            structural_edges += edge_count
            indexed_files += 1
        except Exception as exc:
            store.upsert_file({
                "repo": repo_name,
                "path": relative,
                "kind": kind,
                "language": language,
                "size_bytes": item.get("size_bytes", 0),
                "mtime_ns": item.get("mtime_ns", 0),
                "content_hash": content_hash,
                "status": "failed",
                "authoritative": item.get("authoritative", False),
                "metadata": {"error": f"{type(exc).__name__}: {exc}"},
            })
            failed_files += 1

    removed_files = store.delete_missing_files(repo_name, live_paths)
    store.update_repo_state(
        repo_name,
        manifest_hash=manifest["manifest_hash"],
        indexed=True,
        metadata={"excluded_rules": manifest["excluded_rules"]},
    )
    store.commit()

    rows = store.files(repo_name)
    eligible = sum(item["status"] == "eligible" for item in manifest["files"])
    indexed_total = sum(row["status"] == "indexed" for row in rows)
    deferred_total = sum(row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS for row in rows)
    # Coverage of the *active* indexing duty: indexed vs required-now (excludes deferred).
    required_now = indexed_total + sum(row["status"] == "failed" for row in rows)
    coverage = indexed_total / required_now if required_now else 1.0
    # Recount anchors / repo from store for stable telemetry after incremental runs.
    aria_indexed = sum(
        1
        for row in rows
        if row["status"] == "indexed" and is_internal_aria_path(row["path"])
    )
    aria_anchor_total = sum(
        1
        for row in rows
        if is_aria_anchor_path(row["path"]) and row["status"] == "indexed"
    )
    repo_indexed_total = sum(
        1
        for row in rows
        if row["status"] == "indexed" and not is_internal_aria_path(row["path"])
    )
    work = substrate_work_proxy(
        repository_indexed=repo_indexed_total,
        aria_anchors_indexed=aria_anchor_total,
        aria_deferred=deferred_total,
        aria_materialized=max(0, aria_indexed - aria_anchor_total),
    )
    return {
        "repo": repo_name,
        "root": str(root),
        "manifest_hash": manifest["manifest_hash"],
        "discovered_files": len(manifest["files"]),
        "eligible_files": eligible,
        "indexed_files_this_run": indexed_files,
        "indexed_files_total": indexed_total,
        "unchanged_files": unchanged_files,
        "unsupported_or_excluded_files": unsupported_files,
        "failed_files": failed_files,
        "removed_files": removed_files,
        "chunks_indexed": indexed_chunks,
        "symbols_found": symbols_found,
        "structural_edges_found": structural_edges,
        "index_coverage": round(coverage, 6),
        "excluded_rules": manifest["excluded_rules"],
        "aria_substrate": {
            "indexing_mode": "eager" if materialize_aria else indexing_mode,
            "anchors_indexed": aria_anchor_total,
            "deferred_files": deferred_total,
            "deferred_unchanged": deferred_unchanged,
            "substrate_indexed": aria_indexed,
            "work_proxy": work,
        },
    }


def materialize_aria_substrate(
    store: Any, repo_name: str, config: RepoConfig, *, force: bool = False
) -> dict[str, Any]:
    """Fully index deferred internal ARIA files (certificate-deferred → searchable)."""

    result = index_repository(
        store, repo_name, config, force=force, materialize_aria=True
    )
    result["materialized"] = True
    return result


def ensure_aria_substrate_materialized(
    store: Any,
    repo_name: str,
    config: RepoConfig,
    task: str,
) -> dict[str, Any]:
    """If the task wakes ARIA and deferred files remain, materialize them once."""

    profile = load_aria_cue_profile(store, repo_name)
    classification = classify_aria_task(task, profile["cues"])
    deferred = [
        row
        for row in store.files(repo_name)
        if row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS
    ]
    if classification["mode"] != "active":
        return {
            "mode": "dormant",
            "materialized": False,
            "deferred_remaining": len(deferred),
            "classification": classification,
        }
    if not deferred:
        return {
            "mode": "active",
            "materialized": False,
            "already_ready": True,
            "deferred_remaining": 0,
            "classification": classification,
        }
    index_result = materialize_aria_substrate(store, repo_name, config, force=False)
    return {
        "mode": "active",
        "materialized": True,
        "already_ready": False,
        "deferred_remaining": 0,
        "classification": classification,
        "index": index_result,
    }


def current_manifest_hash(root: Path, config: RepoConfig) -> str:
    return scan_repository(root, config)["manifest_hash"]
