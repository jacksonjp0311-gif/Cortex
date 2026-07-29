"""Transcend-check — falsify operational transcendence on this repository only."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from .bootstrap import bootstrap_repository
from .config import ensure_home
from .context import _agent_instructions, _agent_protocol
from .control_error import build_control_error
from .governor import Governor
from .mirror import run_mirror
from .progress_glyphs import progress_glyph_registry
from .session_ritual import run_session_ritual
from .store import Store


def run_transcend_check(
    home: Path | None = None,
    store: Any | None = None,
    *,
    root: Path | None = None,
    run_mirror_glow: bool = True,
) -> dict[str, Any]:
    """Assert packet protocol, red modes, ritual, and optional mirror glow."""

    root = (root or Path.cwd()).resolve()
    owns_store = store is None
    if home is None:
        home = ensure_home(Path(tempfile.mkdtemp(prefix="cortex-transcend-")) / "home")
    if store is None:
        store = Store(home / "cortex.db")
    governor = Governor(home, store)
    breaks: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []

    # Protocol surface unit checks (no host required)
    ro = _agent_instructions({}, {"mode": "read_only"})
    if not any("READ_ONLY" in line for line in ro):
        breaks.append({"id": "red_mode_instructions_missing"})
    proto_ro = _agent_protocol(
        repo="x",
        task="t",
        aria_materialization={},
        governance={"mode": "read_only"},
        deferred_remaining=0,
    )
    if proto_ro["state"].get("work_allowed") is not False:
        breaks.append({"id": "read_only_work_allowed"})
    if "repository_mutation" not in (proto_ro.get("hard_stops") or []):
        breaks.append({"id": "read_only_hard_stops"})
    notes.append({"red_mode": "ok" if not breaks else "failed"})

    # Immune action codes agents cannot miss (control_error 1.1)
    stop = build_control_error(
        certificate={"status": "verified"},
        governance={"mode": "read_only"},
        manifest_current=True,
        retrieval_confidence=0.9,
        aria_materialization={"mode": "dormant"},
    )
    if not stop.get("block") or stop.get("immune_action", {}).get("code") != "STOP_NO_HOST_MUTATION":
        breaks.append({"id": "immune_stop_read_only", "value": stop.get("immune_action")})
    reverify = build_control_error(
        certificate={"status": "failed"},
        governance={"mode": "normal"},
        manifest_current=False,
        retrieval_confidence=0.5,
        aria_materialization={"mode": "dormant"},
    )
    if not reverify.get("block") or reverify.get("immune_action", {}).get("code") not in {
        "STOP_REVERIFY_REQUIRED",
        "STOP_NO_HOST_MUTATION",
    }:
        breaks.append({"id": "immune_stop_reverify", "value": reverify.get("immune_action")})
    proceed = build_control_error(
        certificate={"status": "verified"},
        governance={"mode": "normal"},
        manifest_current=True,
        retrieval_confidence=0.9,
        aria_materialization={"mode": "dormant"},
    )
    if proceed.get("block") or proceed.get("immune_action", {}).get("code") != "PROCEED_UNDER_HOST_AUTHORITY":
        breaks.append({"id": "immune_proceed_open", "value": proceed.get("immune_action")})
    notes.append(
        {
            "immune": {
                "stop": stop.get("immune_action", {}).get("code"),
                "reverify": reverify.get("immune_action", {}).get("code"),
                "proceed": proceed.get("immune_action", {}).get("code"),
            }
        }
    )

    # Ritual on a tiny synthetic host inside the check (not Desktop scan)
    tiny = Path(tempfile.mkdtemp(prefix="transcend-host-"))
    (tiny / "README.md").write_text("# T\n\n## API\n\nRun.\n", encoding="utf-8")
    (tiny / "app.py").write_text("def run() -> str:\n    return 'ok'\n", encoding="utf-8")
    bootstrap_repository(home, store, tiny, "TranscendHost")
    ritual = run_session_ritual(
        home,
        store,
        governor,
        "TranscendHost",
        "Close transcend ritual",
        memories=[
            {
                "kind": "discovery",
                "text": "Transcend check validates ritual idempotency and protocol",
            }
        ],
        consolidate_session=True,
    )
    if ritual.get("activation") not in {"ready", "read_only"}:
        breaks.append({"id": "ritual_activation", "value": ritual.get("activation")})
    if not ritual.get("remembered"):
        breaks.append({"id": "ritual_remember"})
    cons = ritual.get("consolidate") or {}
    if cons.get("created") is not True and cons.get("status") not in {
        "created",
        "nothing_to_consolidate",
        "duplicate_skip",
    }:
        # created True expected when memories present
        if not cons.get("created"):
            breaks.append({"id": "ritual_consolidate", "value": cons})
    # Idempotent second remember
    from .hippocampus import remember

    first = remember(
        home,
        store,
        "TranscendHost",
        "discovery",
        "idempotent-event-key-test",
        session_id=ritual.get("session_id"),
    )
    second = remember(
        home,
        store,
        "TranscendHost",
        "discovery",
        "idempotent-event-key-test",
        session_id=ritual.get("session_id"),
    )
    if second.get("duplicate") is not True and second.get("recorded") is True:
        # second should be duplicate if first recorded
        if first.get("recorded") and not second.get("duplicate"):
            breaks.append({"id": "remember_not_idempotent", "first": first, "second": second})
    notes.append({"ritual": cons, "remember_idempotent": second.get("duplicate")})

    # Fluency perfect
    corpus = root / "benchmarks" / "corpora" / "aria_fluency.json"
    if corpus.is_file():
        fluency = evaluate_aria_corpus(load_aria_corpus(corpus))
        if fluency.get("false_wakes") or fluency.get("missed_wakes"):
            breaks.append({"id": "fluency", "fluency": fluency})
        notes.append(
            {
                "fluency_cases": fluency.get("cases"),
                "false_wakes": fluency.get("false_wakes"),
            }
        )

    # Glyph registry present
    glyphs = progress_glyph_registry()
    if len(glyphs.get("glyphs") or {}) < 7:
        breaks.append({"id": "progress_glyphs_incomplete"})

    # v5 capability surface falsification (local unit-level; no host mutation)
    try:
        from .agents.tokens import ALLOWED_SCOPES, FORBIDDEN_SCOPES
        from .contract.check import DEFAULT_CONTRACT, STRICT_CONTRACT, check_contract
        from .ranker.model import FEATURE_NAMES, default_weights, score_features
        from .vectors.hnsw import HNSWIndex

        if "host.mutate" in ALLOWED_SCOPES or "host.mutate" not in FORBIDDEN_SCOPES:
            breaks.append({"id": "v5_host_mutate_scope_exists"})
        w = default_weights()
        if len(w) != len(FEATURE_NAMES):
            breaks.append({"id": "v5_ranker_feature_dim"})
        s = score_features({"weights": w, "bias": 0.0}, [0.5] * len(FEATURE_NAMES))
        if not (0.0 <= s <= 1.0):
            breaks.append({"id": "v5_ranker_score_range"})
        idx = HNSWIndex(dim=4, M=4, seed=1)
        idx.build([("a", [1.0, 0.0, 0.0, 0.0]), ("b", [0.9, 0.1, 0.0, 0.0])])
        hits = idx.search([1.0, 0.0, 0.0, 0.0], k=1)
        if not hits or hits[0][0] != "a":
            breaks.append({"id": "v5_hnsw_search"})
        ro_pkt = {
            "authority": {"cortex_may_mutate": False},
            "claim_boundary": "x",
            "operational_state": {"evidence_ids": [1]},
            "governor": {"mode": "read_only"},
        }
        strict_fail = check_contract(ro_pkt, contract=STRICT_CONTRACT)
        if strict_fail.get("passed"):
            breaks.append({"id": "v5_strict_contract_should_fail_readonly"})
        ok_pkt = {
            "authority": {"cortex_may_mutate": False, "packet_is_not_authorization": True},
            "claim_boundary": "x",
            "operational_state": {"evidence_ids": [1]},
            "governor": {"mode": "normal"},
            "control_error": {"block": False},
        }
        default_ok = check_contract(ok_pkt, contract=DEFAULT_CONTRACT)
        if not default_ok.get("passed"):
            breaks.append({"id": "v5_default_contract_should_pass", "breaks": default_ok.get("breaks")})
        notes.append({"v5_surfaces": "ok"})
    except Exception as exc:
        breaks.append({"id": "v5_surface_exception", "error": f"{type(exc).__name__}: {exc}"})

    mirror_result: dict[str, Any] | None = None
    if run_mirror_glow:
        # Separate home so mirror bootstrap isolation stays clean
        m_home = ensure_home(Path(tempfile.mkdtemp(prefix="tx-mirror-")) / "home")
        m_store = Store(m_home / "cortex.db")
        try:
            mirror_result = run_mirror(m_home, m_store, root=root, repo_name="TxMirror")
            if not mirror_result.get("glow"):
                breaks.append(
                    {
                        "id": "mirror_not_glow",
                        "breaks": mirror_result.get("breaks"),
                    }
                )
            notes.append(
                {
                    "mirror_glow": mirror_result.get("glow"),
                    "mirror_intensity": mirror_result.get("glow_intensity"),
                }
            )
        finally:
            m_store.close()

    if owns_store:
        store.close()

    passed = len(breaks) == 0
    return {
        "schema_version": "cortex-transcend-check/2.0",
        "glyph": "⟡",
        "passed": passed,
        "break_count": len(breaks),
        "breaks": breaks,
        "notes": notes,
        "progress_glyphs": glyphs,
        "mirror": (
            {
                "glow": (mirror_result or {}).get("glow"),
                "intensity": (mirror_result or {}).get("glow_intensity"),
            }
            if mirror_result
            else None
        ),
        "definition": (
            "Agent can run from packet alone, obey immune_action, close with ritual, "
            "mirror stays bright; v5 ranker/HNSW/contracts/agent scopes falsify safely; "
            "no host.mutate path; no unsolicited foreign hosts."
        ),
        "claim_boundary": (
            "Transcend-check is local operational falsification; not consciousness "
            "or multi-repo production certification."
        ),
    }
