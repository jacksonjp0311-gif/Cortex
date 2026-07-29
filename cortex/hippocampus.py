from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any


def _active_path(home: Path, repo: str) -> Path:
    safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in repo)
    return home / "sessions" / f"{safe}-active.json"


def begin_session(
    home: Path,
    store: Any,
    repo: str,
    task: str,
    files: list[str] | None = None,
) -> dict[str, Any]:
    session_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    payload = {
        "schema_version": "1.0",
        "session_id": session_id,
        "repo": repo,
        "task": task,
        "focus_files": files or [],
        "started_at": time.time(),
        "updated_at": time.time(),
        "state_hash": hashlib.sha256(f"{repo}|{task}|{session_id}".encode("utf-8")).hexdigest(),
    }
    path = _active_path(home, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    store.start_session(session_id, repo, task, {"focus_files": files or []})
    store.add_event(session_id, repo, "focus", task, {"files": files or []})
    return payload


def active_session(home: Path, repo: str) -> dict[str, Any] | None:
    path = _active_path(home, repo)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def remember(
    home: Path,
    store: Any,
    repo: str,
    kind: str,
    text: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    token_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    # v6.2 multi-agent gate (opt-in mode only)
    try:
        from .agents.tokens import require_scope

        gate = require_scope(
            store, repo, token_id=token_id, scope="memory.remember"
        )
        if gate.get("required") and not gate.get("valid"):
            return {
                "recorded": False,
                "blocked": True,
                "reason": gate.get("reason") or "token_invalid",
                "token_gate": gate,
                "claim_boundary": "Multi-agent remember requires capability token.",
            }
        if gate.get("agent_id"):
            agent_id = agent_id or gate.get("agent_id")
    except Exception:
        pass
    active = active_session(home, repo)
    resolved_session = session_id or (active or {}).get("session_id")
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta = dict(metadata or {})
    meta.setdefault("text_hash", text_hash)
    if agent_id:
        meta["agent_id"] = agent_id
    if token_id:
        meta["token_id"] = token_id
    # Idempotent within session: same kind+text_hash is a duplicate skip.
    if resolved_session:
        for event in store.events(repo, resolved_session):
            if event["kind"] != kind:
                continue
            existing_meta = event["metadata"]
            if isinstance(existing_meta, str):
                try:
                    existing_meta = json.loads(existing_meta or "{}")
                except json.JSONDecodeError:
                    existing_meta = {}
            if (existing_meta or {}).get("text_hash") == text_hash or event["text"] == text:
                return {
                    "recorded": False,
                    "duplicate": True,
                    "status": "duplicate_skip",
                    "repo": repo,
                    "session_id": resolved_session,
                    "kind": kind,
                    "text_hash": text_hash,
                }
    store.add_event(resolved_session, repo, kind, text, meta)
    if active:
        active["updated_at"] = time.time()
        active["last_event_kind"] = kind
        active["last_event_hash"] = text_hash
        _active_path(home, repo).write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")
    # Living organism: each memory continues the co-process pulse (diastole).
    organism_beat: dict[str, Any] | None = None
    try:
        from . import __version__
        from .organism import beat

        organism_beat = beat(
            home,
            store,
            repo,
            kind=kind,
            text=text,
            phase="diastole",
            cortex_version=__version__,
        )
    except Exception:
        organism_beat = None
    return {
        "recorded": True,
        "duplicate": False,
        "status": "recorded",
        "repo": repo,
        "session_id": resolved_session,
        "kind": kind,
        "text_hash": text_hash,
        "organism": organism_beat,
        "organism_pulse": (organism_beat or {}).get("pulse"),
    }


def clear_active(home: Path, repo: str) -> None:
    path = _active_path(home, repo)
    if path.exists():
        path.unlink()
