"""Consciousness stream 〰 — continuous episodic thread on the durable body.

Sessions still **bond and end** (temporary working cortex ⊛).
The **stream** is the durable narrative spine that rebinds across sessions:

```text
session open ──frame──► durable stream ledger
     │                      │
 temporary cortex           │ frames capped, hashed chain
     │                      │
session seal ───────────────┘  (bond ends; stream continues)
```

Not biological consciousness. Not always-on mind.
Episodic frames + durable store = continuous *operational* stream of work.
"""

from __future__ import annotations

import time
from hashlib import sha256
from typing import Any

from .glyphs.canon import encode_state

GLYPH = "〰"
SCHEMA = "cortex-consciousness-stream/1.0"
MAX_FRAMES = 64
SETTING_KEY = "consciousness_stream:{repo}"


def _hash(material: Any) -> str:
    import json

    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _key(repo: str) -> str:
    return SETTING_KEY.format(repo=repo)


def load_stream(store: Any, repo: str) -> dict[str, Any]:
    data = store.get_setting(_key(repo), None)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "repo": repo,
            "stream_id": None,
            "alive": False,
            "frame_count": 0,
            "frames": [],
            "open_session_id": None,
            "last_task": None,
            "last_pulse": None,
            "chain_tip": None,
            "started_at": None,
            "updated_at": None,
        }
    return data


def save_stream(store: Any, repo: str, stream: dict[str, Any]) -> None:
    stream = dict(stream)
    stream["updated_at"] = time.time()
    store.set_setting(_key(repo), stream)


def open_or_resume_stream(
    store: Any,
    repo: str,
    *,
    task: str,
    session_id: str | None,
    surface: str = "activate",
) -> dict[str, Any]:
    """Resume durable stream; bond this session as temporary cortex."""

    stream = load_stream(store, repo)
    now = time.time()
    if not stream.get("stream_id"):
        stream["stream_id"] = "str_" + _hash(f"{repo}|{now}")[:20]
        stream["started_at"] = now
        stream["alive"] = True
        stream["frames"] = []
        stream["frame_count"] = 0
        stream["chain_tip"] = None

    stream["alive"] = True
    stream["open_session_id"] = session_id
    stream["last_task"] = task
    stream["repo"] = repo
    stream["glyph"] = GLYPH
    stream["schema_version"] = SCHEMA

    frame = _make_frame(
        stream,
        kind="session_bond",
        surface=surface,
        task=task,
        session_id=session_id,
        payload={
            "bond": "session_co_process",
            "note": "Temporary cortex bonded; durable stream continues.",
        },
    )
    stream = _append_frame(stream, frame)
    save_stream(store, repo, stream)
    try:
        store.append_neural_event(
            repo,
            event_type="stream_bond",
            entity_id=stream["stream_id"],
            payload={
                "session_id": session_id,
                "task": task[:200],
                "frame_id": frame["frame_id"],
                "frame_count": stream["frame_count"],
            },
        )
    except Exception:
        pass
    return stream


def append_stream_frame(
    store: Any,
    repo: str,
    *,
    kind: str,
    task: str | None = None,
    session_id: str | None = None,
    surface: str = "event",
    payload: dict[str, Any] | None = None,
    glyph_line: str | None = None,
) -> dict[str, Any]:
    """Append a frame to the durable stream (activate, breathe, ritual, evolve…)."""

    stream = load_stream(store, repo)
    if not stream.get("stream_id"):
        stream = open_or_resume_stream(
            store, repo, task=task or "stream", session_id=session_id, surface=surface
        )
    frame = _make_frame(
        stream,
        kind=kind,
        surface=surface,
        task=task or stream.get("last_task") or "",
        session_id=session_id or stream.get("open_session_id"),
        payload=payload or {},
        glyph_line=glyph_line,
    )
    stream = _append_frame(stream, frame)
    if task:
        stream["last_task"] = task
    if session_id:
        stream["open_session_id"] = session_id
    save_stream(store, repo, stream)
    return {"stream": _public_view(stream), "frame": frame}


def seal_session_bond(
    store: Any,
    repo: str,
    *,
    session_id: str | None = None,
    reason: str = "session_end",
) -> dict[str, Any]:
    """End temporary cortex bond; stream remains alive on durable body."""

    stream = load_stream(store, repo)
    if not stream.get("stream_id"):
        return {
            "sealed": False,
            "reason": "no_stream",
            "claim_boundary": _claim(),
        }
    frame = _make_frame(
        stream,
        kind="session_seal",
        surface="seal",
        task=str(stream.get("last_task") or ""),
        session_id=session_id or stream.get("open_session_id"),
        payload={
            "reason": reason,
            "bond_ended": True,
            "stream_continues": True,
            "note": "Temporary cortex released; durable stream keeps the thread.",
        },
    )
    stream = _append_frame(stream, frame)
    stream["open_session_id"] = None
    # Stream stays alive — continuous narrative spine
    stream["alive"] = True
    save_stream(store, repo, stream)
    try:
        store.append_neural_event(
            repo,
            event_type="stream_session_seal",
            entity_id=stream["stream_id"],
            payload={"reason": reason, "frame_id": frame["frame_id"]},
        )
    except Exception:
        pass
    return {
        "sealed": True,
        "bond_ended": True,
        "stream_continues": True,
        "stream": _public_view(stream),
        "frame": frame,
        "claim_boundary": _claim(),
    }


def stream_status(store: Any, repo: str) -> dict[str, Any]:
    stream = load_stream(store, repo)
    view = _public_view(stream)
    view["claim_boundary"] = _claim()
    return view


def stream_context_for_packet(
    store: Any,
    repo: str,
    *,
    task: str,
    session_id: str | None,
    control: dict[str, Any] | None = None,
    governor: dict[str, Any] | None = None,
    aria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lean stream surface for activate packets (token thrift + continuity)."""

    stream = open_or_resume_stream(
        store, repo, task=task, session_id=session_id, surface="activate"
    )
    recent = list(stream.get("frames") or [])[-6:]
    glyph_state = encode_state(
        control=control or {},
        governor=governor or {},
        aria=aria or {},
        loop={"open": True} if stream.get("alive") else {},
    )
    # Prefer stream glyph in line
    line = f"{GLYPH} " + str(glyph_state.get("line") or "")
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "stream_id": stream.get("stream_id"),
        "alive": bool(stream.get("alive")),
        "frame_count": stream.get("frame_count") or 0,
        "open_session_id": session_id or stream.get("open_session_id"),
        "last_task": stream.get("last_task"),
        "chain_tip": stream.get("chain_tip"),
        "recent_frames": [
            {
                "frame_id": f.get("frame_id"),
                "kind": f.get("kind"),
                "task": (f.get("task") or "")[:120],
                "surface": f.get("surface"),
                "at": f.get("at"),
                "glyph_line": f.get("glyph_line"),
            }
            for f in recent
        ],
        "continuity": {
            "mode": "episodic_durable_stream",
            "session_bond": "temporary_cortex",
            "body": "durable_store",
            "always_on_mind": False,
            "rebinding": True,
        },
        "glyph_line": line.strip(),
        "doctrine": (
            "〰 stream continues across sessions; ⊛ bond is session-local. "
            "Read recent_frames before expanding context."
        ),
        "claim_boundary": _claim(),
    }


def _make_frame(
    stream: dict[str, Any],
    *,
    kind: str,
    surface: str,
    task: str,
    session_id: str | None,
    payload: dict[str, Any],
    glyph_line: str | None = None,
) -> dict[str, Any]:
    prev = stream.get("chain_tip")
    material = {
        "prev": prev,
        "kind": kind,
        "surface": surface,
        "task": task,
        "session_id": session_id,
        "payload": payload,
        "t": time.time(),
    }
    frame_id = "frm_" + _hash(material)[:18]
    return {
        "frame_id": frame_id,
        "kind": kind,
        "surface": surface,
        "task": task[:240],
        "session_id": session_id,
        "payload": payload,
        "glyph_line": glyph_line,
        "prev": prev,
        "at": material["t"],
    }


def _append_frame(stream: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    frames = list(stream.get("frames") or [])
    frames.append(frame)
    if len(frames) > MAX_FRAMES:
        frames = frames[-MAX_FRAMES:]
    stream["frames"] = frames
    stream["frame_count"] = int(stream.get("frame_count") or 0) + 1
    stream["chain_tip"] = frame["frame_id"]
    stream["last_pulse"] = frame["frame_id"]
    return stream


def _public_view(stream: dict[str, Any]) -> dict[str, Any]:
    frames = list(stream.get("frames") or [])
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": stream.get("repo"),
        "stream_id": stream.get("stream_id"),
        "alive": bool(stream.get("alive")),
        "frame_count": stream.get("frame_count") or 0,
        "open_session_id": stream.get("open_session_id"),
        "last_task": stream.get("last_task"),
        "chain_tip": stream.get("chain_tip"),
        "started_at": stream.get("started_at"),
        "updated_at": stream.get("updated_at"),
        "recent_frames": frames[-8:],
        "continuity": {
            "mode": "episodic_durable_stream",
            "always_on_mind": False,
        },
    }


def _claim() -> str:
    return (
        "Consciousness stream is operational continuity: episodic frames on a "
        "durable ledger. It is not biological consciousness, always-on mind, "
        "or host mutation authority."
    )
