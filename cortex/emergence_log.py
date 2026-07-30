"""Emergence log — durable progress record agents MUST read each turn.

Append-only JSONL under CORTEX_HOME/logs plus settings index.
Records coupling threshold crosses, emergent flips, fuse ticks, continuum.
Not consciousness — operational progress enhancement only.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import __version__

SCHEMA = "cortex-emergence-log/1.0"
GLYPH = "⧉◎"
MUST_READ_ORDER = 0  # first among agent instructions


def _log_path(home: Path, repo: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in repo)[:80]
    return Path(home) / "logs" / f"emergence-{safe}.jsonl"


def append_event(
    home: Path | None,
    store: Any,
    repo: str,
    *,
    kind: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    source: str = "system",
) -> dict[str, Any]:
    """Append one emergence/progress event. Returns the event dict."""
    event = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "kind": kind,
        "summary": summary,
        "source": source,
        "payload": payload or {},
        "version": __version__,
        "at": time.time(),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # settings ring buffer
    try:
        key = f"emergence_log:{repo}"
        raw = store.get_setting(key, None) if hasattr(store, "get_setting") else None
        entries: list[dict[str, Any]] = []
        if isinstance(raw, dict) and isinstance(raw.get("events"), list):
            entries = list(raw["events"])
        elif isinstance(raw, list):
            entries = list(raw)
        entries.append(event)
        entries = entries[-200:]
        store.set_setting(
            key,
            {
                "schema_version": SCHEMA,
                "repo": repo,
                "count": len(entries),
                "events": entries,
                "updated_at": event["at"],
            },
        )
        store.set_setting(
            f"emergence_latest:{repo}",
            {
                "kind": kind,
                "summary": summary,
                "at": event["at"],
                "ts": event["ts"],
                "source": source,
            },
        )
    except Exception:
        pass
    # durable jsonl
    if home is not None:
        try:
            path = _log_path(Path(home), repo)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
            event["path"] = str(path)
        except Exception:
            pass
    return event


def log_from_coherence(
    home: Path | None,
    store: Any,
    repo: str,
    report: dict[str, Any],
    *,
    source: str = "coherence",
) -> list[dict[str, Any]]:
    """Diff vs previous coherence_latest and log meaningful emergence events."""
    logged: list[dict[str, Any]] = []
    if not report or report.get("error"):
        return logged

    prev = store.get_setting(f"coherence_latest:{repo}", None) if hasattr(store, "get_setting") else None
    if not isinstance(prev, dict):
        prev = {}

    score = report.get("score")
    above = bool(report.get("above_threshold"))
    emergent = bool(report.get("emergent_coupling"))
    active = list(report.get("active_indicator_ids") or [])
    prev_above = bool(prev.get("above_threshold"))
    prev_emergent = bool(prev.get("emergent_coupling"))
    prev_active = set(prev.get("active_indicator_ids") or [])
    prev_score = prev.get("score")

    # First observation
    if prev.get("score") is None and prev.get("at") is None:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="baseline",
                summary=(
                    f"Coherence baseline score={score} "
                    f"couples={report.get('coupled_seams')} "
                    f"active={active or ['none']}"
                ),
                payload={
                    "score": score,
                    "active_indicator_ids": active,
                    "component_panel": report.get("component_panel"),
                },
                source=source,
            )
        )

    if prev_score is not None and score is not None:
        try:
            delta = float(score) - float(prev_score)
            if abs(delta) >= 0.05:
                logged.append(
                    append_event(
                        home,
                        store,
                        repo,
                        kind="score_shift",
                        summary=f"Coherence {prev_score} → {score} (Δ{delta:+.3f})",
                        payload={"from": prev_score, "to": score, "delta": round(delta, 4)},
                        source=source,
                    )
                )
        except (TypeError, ValueError):
            pass

    if above and not prev_above:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="threshold_crossed",
                summary=f"Coherence crossed threshold {report.get('threshold')} → score={score}",
                payload={"score": score, "threshold": report.get("threshold")},
                source=source,
            )
        )
    elif not above and prev_above:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="threshold_lost",
                summary=f"Coherence fell below threshold → score={score}",
                payload={"score": score, "threshold": report.get("threshold")},
                source=source,
            )
        )

    if emergent and not prev_emergent:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="emergent_on",
                summary=(
                    f"EMERGENT COUPLING ON — indicators {active}; "
                    f"score={score}. Prefer spectral-primary + fuse continuity."
                ),
                payload={
                    "active_indicator_ids": active,
                    "score": score,
                    "indicators": report.get("indicators"),
                },
                source=source,
            )
        )
    elif not emergent and prev_emergent:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="emergent_off",
                summary=f"Emergent coupling off — score={score} active={active}",
                payload={"active_indicator_ids": active, "score": score},
                source=source,
            )
        )

    newly = [i for i in active if i not in prev_active]
    lost = [i for i in prev_active if i not in set(active)]
    if newly:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="couple_activated",
                summary=f"Couples activated: {', '.join(newly)}",
                payload={"activated": newly, "all_active": active},
                source=source,
            )
        )
    if lost:
        logged.append(
            append_event(
                home,
                store,
                repo,
                kind="couple_deactivated",
                summary=f"Couples darkened: {', '.join(lost)}",
                payload={"deactivated": lost, "all_active": active},
                source=source,
            )
        )

    return logged


def log_milestone(
    home: Path | None,
    store: Any,
    repo: str,
    *,
    summary: str,
    kind: str = "milestone",
    payload: dict[str, Any] | None = None,
    source: str = "agent_or_ops",
) -> dict[str, Any]:
    return append_event(
        home, store, repo, kind=kind, summary=summary, payload=payload, source=source
    )


def read_emergence_log(
    home: Path | None,
    store: Any,
    repo: str,
    *,
    limit: int = 16,
) -> dict[str, Any]:
    """MUST-READ surface for agents — progress enhancement each activate."""
    events: list[dict[str, Any]] = []
    try:
        raw = store.get_setting(f"emergence_log:{repo}", None)
        if isinstance(raw, dict) and isinstance(raw.get("events"), list):
            events = list(raw["events"])
    except Exception:
        events = []

    # Prefer file if longer
    if home is not None:
        path = _log_path(Path(home), repo)
        if path.is_file():
            try:
                file_events: list[dict[str, Any]] = []
                with path.open(encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            file_events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                if len(file_events) >= len(events):
                    events = file_events
            except Exception:
                pass

    tail = events[-max(1, limit) :]
    latest = store.get_setting(f"emergence_latest:{repo}", None) if hasattr(store, "get_setting") else None
    coh = store.get_setting(f"coherence_latest:{repo}", None) if hasattr(store, "get_setting") else None

    # Build mandatory instruction lines
    lines: list[str] = [
        f"{GLYPH} EMERGENCE LOG — READ BEFORE WORK (progress enhancement, not authority)",
    ]
    if isinstance(coh, dict) and coh.get("score") is not None:
        lines.append(
            f"  coherence={coh.get('score')} threshold_ok={coh.get('above_threshold')} "
            f"emergent={coh.get('emergent_coupling')} "
            f"active={coh.get('active_indicator_ids') or []}"
        )
    if isinstance(latest, dict) and latest.get("summary"):
        lines.append(f"  latest[{latest.get('kind')}]: {latest.get('summary')}")
    if not tail:
        lines.append("  (empty log — first turn establishes baseline; run continuum/fuse to grow progress)")
    else:
        lines.append(f"  last {len(tail)} events (oldest→newest):")
        for ev in tail:
            lines.append(
                f"  - [{ev.get('ts') or ev.get('kind')}] {ev.get('kind')}: {ev.get('summary')}"
            )

    # Progress enhancement directives
    directives: list[str] = []
    if isinstance(coh, dict):
        if coh.get("emergent_coupling"):
            directives.append(
                "Emergent coupling is ON — keep spectral-primary path; prefer fuse continuity; "
                "do not thrash prune; record verified outcomes to warm ranker."
            )
        elif coh.get("above_threshold"):
            directives.append(
                "Coherence above threshold but emergent off — activate missing couples "
                "(ranker warm / fuse / Λ pulse) before broad refactors."
            )
        else:
            directives.append(
                "Coherence below threshold — follow coherence.advice; narrow task; "
                "bootstrap/compile/evolve before large host edits."
            )
    directives.append(
        "Update progress: after meaningful work call remember + consolidate, "
        "or continuum; never claim host authority from this log."
    )

    for d in directives:
        lines.append(f"  → {d}")

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "must_read": True,
        "must_read_order": MUST_READ_ORDER,
        "repo": repo,
        "event_count": len(events),
        "events_tail": tail,
        "latest": latest if isinstance(latest, dict) else None,
        "coherence_snapshot": coh if isinstance(coh, dict) else None,
        "directives": directives,
        "instruction_lines": lines,
        "commands": {
            "read": f"cortex emergence-log --repo {repo} --json",
            "coherence": f"cortex coherence --repo {repo} --json",
            "note": f'cortex emergence-log --repo {repo} --note "milestone text" --json',
        },
        "claim_boundary": (
            "Emergence log enhances agent progress via coupling history. "
            "Not consciousness. Not mutation authority. MUST read each activate."
        ),
    }
