"""Glyph Canon — deep ARIA-facing meta language for Cortex operations.

Glyphs are **labels and compression**, never opcodes or mutation authority.
ARIA may speak them; Cortex lowers them to ordinary CLI / packet fields.

Design goals:
- One canon for operators, agents, and ARIA semantic cues
- High signal density (token thrift) via compact_line / encode_state
- Optimized set: merge duplicates, prefer distinct symbols for distinct organs
- Closed-loop glyphs (↻ outcome, ⟲ evolve) for signal intelligence
"""

from __future__ import annotations

from typing import Any

CANON_SCHEMA = "cortex-glyph-canon/1.0"
CANON_GLYPH = "◈"  # the canon itself

# ── Canonical entries ──────────────────────────────────────────────────────
# Fields: symbol, spoken, aria_id, maps_to, role, kernel (optional spectral class)
# role ∈ organ | gate | pulse | loop | medium | entity

GLYPH_CANON: dict[str, dict[str, Any]] = {
    # ── Gates ──────────────────────────────────────────────────────────────
    "control_error": {
        "symbol": "⚠",
        "spoken": "control error",
        "aria_id": "ControlError",
        "maps_to": "packet.control_error",
        "role": "gate",
        "kernel": "reset",
    },
    "immune_gate": {
        "symbol": "⛨",
        "spoken": "immune gate",
        "aria_id": "ImmuneGate",
        "maps_to": "cortex immune / packet.control_error.immune_action",
        "role": "gate",
        "kernel": "retain",
    },
    "identity": {
        "symbol": "⌖",
        "spoken": "identity continuity",
        "aria_id": "IdentityContinuity",
        "maps_to": "cortex identity",
        "role": "gate",
        "kernel": "retain",
    },
    "retrieval_gate": {
        "symbol": "⌖",
        "spoken": "retrieval gate",
        "aria_id": "RetrievalGate",
        "maps_to": "cortex evaluate / query",
        "role": "gate",
        "kernel": "integrate",
        "alias_of": "identity",  # shared symbol family; distinct aria_id
    },
    # ── Organs ─────────────────────────────────────────────────────────────
    "connect_pass": {
        "symbol": "⧉",
        "spoken": "connect pass",
        "aria_id": "ConnectPass",
        "maps_to": "cortex metrics / packet.connect_pass",
        "role": "organ",
        "kernel": "integrate",
    },
    "interconnect_mesh": {
        "symbol": "⧉",
        "spoken": "interconnect mesh",
        "aria_id": "InterconnectMesh",
        "maps_to": "cortex interconnect",
        "role": "organ",
        "kernel": "integrate",
    },
    "organism_pulse": {
        "symbol": "⊛",
        "spoken": "organism pulse",
        "aria_id": "OrganismPulse",
        "maps_to": "packet.organism / cortex organism",
        "role": "pulse",
        "kernel": "integrate",
    },
    "organism_breathe": {
        "symbol": "∽",
        "spoken": "organism breathe",
        "aria_id": "OrganismBreathe",
        "maps_to": "cortex breathe",
        "role": "pulse",
        "kernel": "integrate",
    },
    "ritual_idempotent": {
        "symbol": "⟳",
        "spoken": "ritual seal",
        "aria_id": "RitualIdempotent",
        "maps_to": "cortex ritual",
        "role": "pulse",
        "kernel": "retain",
    },
    "spectral_kernels": {
        "symbol": "≋",
        "spoken": "spectral kernels",
        "aria_id": "SpectralKernels",
        "maps_to": "cortex kernels",
        "role": "organ",
        "kernel": "retain",
    },
    "ranker": {
        "symbol": "⇅",
        "spoken": "ranker",
        "aria_id": "LocalRanker",
        "maps_to": "cortex ranker",
        "role": "organ",
        "kernel": "integrate",
    },
    "hnsw_vectors": {
        "symbol": "▦",
        "spoken": "hnsw vectors",
        "aria_id": "HnswVectors",
        "maps_to": "cortex vectors",
        "role": "organ",
        "kernel": "integrate",
    },
    "predict": {
        "symbol": "⇢",
        "spoken": "predict prefetch",
        "aria_id": "PredictPrefetch",
        "maps_to": "cortex predict",
        "role": "organ",
        "kernel": "reset",
    },
    "contract": {
        "symbol": "▤",
        "spoken": "contract check",
        "aria_id": "ContractCheck",
        "maps_to": "cortex contract",
        "role": "gate",
        "kernel": "retain",
    },
    "graph_prune": {
        "symbol": "✂",
        "spoken": "graph prune",
        "aria_id": "GraphPrune",
        "maps_to": "cortex prune",
        "role": "organ",
        "kernel": "reset",
    },
    "surprise_metric": {
        "symbol": "Δ",
        "spoken": "incremental surprise",
        "aria_id": "SurpriseMetric",
        "maps_to": "packet.efficiency.surprise",
        "role": "gate",
        "kernel": "reset",
    },
    "distill_intel": {
        "symbol": "☰",
        "spoken": "distill intelligence",
        "aria_id": "DistillIntel",
        "maps_to": "cortex distill",
        "role": "medium",
        "kernel": "retain",
    },
    "teach_surface": {
        "symbol": "☰",
        "spoken": "teach surface",
        "aria_id": "TeachSurface",
        "maps_to": "cortex teach",
        "role": "medium",
        "kernel": "retain",
    },
    "packet_profile": {
        "symbol": "▣",
        "spoken": "packet profile",
        "aria_id": "PacketProfile",
        "maps_to": "cortex activate --profile",
        "role": "medium",
        "kernel": "integrate",
    },
    "transcend_check": {
        "symbol": "⟡",
        "spoken": "transcend check",
        "aria_id": "TranscendCheck",
        "maps_to": "cortex transcend-check",
        "role": "gate",
        "kernel": "integrate",
    },
    # ── Closed loop / signal intelligence ──────────────────────────────────
    "causal": {
        "symbol": "↻",
        "spoken": "causal ledger",
        "aria_id": "CausalLedger",
        "maps_to": "cortex causal",
        "role": "loop",
        "kernel": "integrate",
    },
    "signal_loop": {
        "symbol": "⟲",
        "spoken": "signal loop close",
        "aria_id": "SignalLoopClose",
        "maps_to": "cortex evolve / outcome→ranker→plasticity→probe",
        "role": "loop",
        "kernel": "integrate",
    },
    "consciousness_stream": {
        "symbol": "〰",
        "spoken": "consciousness stream",
        "aria_id": "ConsciousnessStream",
        "maps_to": "cortex stream / packet.stream",
        "role": "pulse",
        "kernel": "retain",
    },
    "glyph_canon": {
        "symbol": CANON_GLYPH,
        "spoken": "glyph canon",
        "aria_id": "GlyphCanon",
        "maps_to": "cortex glyphs / packet.glyph_canon",
        "role": "medium",
        "kernel": "retain",
    },
    "prove_implementation": {
        "symbol": "☰",
        "spoken": "prove implementation",
        "aria_id": "ProveImplementation",
        "maps_to": "retrieval.prove_implementation",
        "role": "gate",
        "kernel": "integrate",
    },
    # ── Meta status tokens (used in compact_line) ──────────────────────────
    "ok": {"symbol": "·", "spoken": "ok", "aria_id": "StatusOk", "maps_to": "status:ok", "role": "entity"},
    "block": {"symbol": "⛔", "spoken": "block", "aria_id": "StatusBlock", "maps_to": "status:block", "role": "gate"},
    "dormant": {"symbol": "◌", "spoken": "dormant", "aria_id": "AriaDormant", "maps_to": "aria:dormant", "role": "entity"},
    "awake": {"symbol": "●", "spoken": "awake", "aria_id": "AriaAwake", "maps_to": "aria:active", "role": "entity"},
    "in_phase": {"symbol": "∿", "spoken": "in phase", "aria_id": "ResonanceInPhase", "maps_to": "resonance:in_phase", "role": "pulse"},
}


def glyph_canon_registry(*, optimized: bool = True) -> dict[str, Any]:
    """Full or optimized ARIA-compatible registry."""

    glyphs = optimize_glyph_set() if optimized else dict(GLYPH_CANON)
    return {
        "schema_version": CANON_SCHEMA,
        "glyph": CANON_GLYPH,
        "format": "aria.glyph-registry+cortex",
        "glyphs": glyphs,
        "count": len(glyphs),
        "automatic_execution": False,
        "grants_mutation_authority": False,
        "aria_role": "meta_medium",
        "token_doctrine": (
            "Prefer compact_line over prose. Expand only blocked gates and fired organs."
        ),
        "claim_boundary": (
            "Glyph Canon is a capability-free compression and addressing layer. "
            "Symbols never execute ARIA plans or authorize host mutation."
        ),
    }


def optimize_glyph_set() -> dict[str, dict[str, Any]]:
    """Collapse alias noise: one primary entry per (symbol, maps_to family).

    Keeps distinct aria_ids that share a symbol when roles differ (e.g. ⧉ connect
    vs mesh share symbol but both stay; immune uses ⛨ distinct from ⚠).
    """

    out: dict[str, dict[str, Any]] = {}
    seen_symbol_role: set[tuple[str, str]] = set()
    for key, entry in GLYPH_CANON.items():
        if entry.get("alias_of") and entry.get("alias_of") in GLYPH_CANON:
            # Keep alias for spoken lookup but mark secondary
            out[key] = {**entry, "secondary": True}
            continue
        role = str(entry.get("role") or "organ")
        sym = str(entry.get("symbol") or "")
        pair = (sym, role)
        if pair in seen_symbol_role and role in {"organ", "medium"}:
            # Prefer first organ/medium per symbol
            out[key] = {**entry, "secondary": True}
            continue
        seen_symbol_role.add(pair)
        out[key] = dict(entry)
    return out


def speak(key: str) -> str:
    entry = GLYPH_CANON.get(key) or {}
    return str(entry.get("spoken") or key)


# Reusable ARIA language: named phrases operators/agents can speak again and again.
# Keys are stable; compact lines are the medium; maps_to stays capability-free.
PHRASEBOOK: dict[str, dict[str, Any]] = {
    "wake_safe": {
        "keys": ["immune_gate", "dormant", "organism_pulse", "consciousness_stream", "connect_pass"],
        "spoken": "immune open, aria dormant, organism bond, stream, connect",
        "use": "Generic task start — keep Aria silent.",
    },
    "aria_awake": {
        "keys": ["immune_gate", "awake", "organism_pulse", "consciousness_stream", "connect_pass", "prove_implementation"],
        "spoken": "immune open, aria awake, organism bond, stream, connect, prove",
        "use": "ARIA-semantic task — expect substrate + proof ranking.",
    },
    "constrained": {
        "keys": ["control_error", "organism_pulse", "connect_pass"],
        "spoken": "control constrained, organism bond, connect",
        "use": "Governor constrained — narrow blast radius.",
    },
    "blocked": {
        "keys": ["block", "control_error", "immune_gate"],
        "spoken": "block, control error, immune",
        "use": "Immune block — re-verify before work.",
    },
    "loop_close": {
        "keys": ["signal_loop", "causal", "ranker"],
        "spoken": "signal loop, causal, ranker",
        "use": "After verified work — run cortex evolve.",
    },
    "stream_rebind": {
        "keys": ["consciousness_stream", "organism_pulse", "ritual_idempotent"],
        "spoken": "stream, organism bond, ritual",
        "use": "Cross-session continuity — bond ends, stream continues.",
    },
    "seal_pulse": {
        "keys": ["ritual_idempotent", "distill_intel", "consciousness_stream"],
        "spoken": "ritual seal, distill, stream",
        "use": "End cardiac cycle; keep stream spine.",
    },
    "body_hygiene": {
        "keys": ["graph_prune", "spectral_kernels", "identity"],
        "spoken": "prune, kernels, identity",
        "use": "Graph mass / home stability check.",
    },
}


def phrasebook() -> dict[str, Any]:
    """Stable reusable phrases for ARIA/agent language (capability-free)."""

    out: dict[str, Any] = {}
    for name, meta in PHRASEBOOK.items():
        keys = list(meta.get("keys") or [])
        line = compact_line(keys)
        out[name] = {
            "name": name,
            "line": line,
            "keys": keys,
            "spoken": meta.get("spoken"),
            "use": meta.get("use"),
            "expand": expand_line(line),
        }
    return {
        "schema_version": "cortex-aria-phrasebook/1.0",
        "glyph": CANON_GLYPH,
        "phrases": out,
        "count": len(out),
        "automatic_execution": False,
        "claim_boundary": (
            "Phrasebook lines are reusable ARIA-facing labels; never execute plans."
        ),
    }


def speak_line(line: str) -> list[str]:
    """Spoken sequence for a compact glyph line."""

    return [item.get("spoken") or item.get("symbol") or "" for item in expand_line(line)]


def phrase(name: str) -> dict[str, Any]:
    """Lookup one reusable phrase by name."""

    book = phrasebook()
    phrases = book.get("phrases") or {}
    if name not in phrases:
        raise KeyError(f"Unknown phrase: {name}. Known: {sorted(phrases)}")
    return phrases[name]


def compact_line(keys: list[str] | tuple[str, ...]) -> str:
    """Ultra-lean glyph stream for agent packets (meta role)."""

    parts: list[str] = []
    for key in keys:
        entry = GLYPH_CANON.get(key)
        if not entry:
            continue
        parts.append(str(entry["symbol"]))
    return " ".join(parts)


def expand_line(line: str) -> list[dict[str, str]]:
    """Decode a compact glyph line into spoken maps (for ARIA / humans)."""

    symbols = [p for p in line.split() if p]
    by_sym: dict[str, list[dict[str, Any]]] = {}
    for key, entry in GLYPH_CANON.items():
        by_sym.setdefault(str(entry["symbol"]), []).append({"key": key, **entry})
    out: list[dict[str, str]] = []
    for sym in symbols:
        matches = by_sym.get(sym) or []
        if not matches:
            out.append({"symbol": sym, "spoken": "unknown", "key": ""})
            continue
        # Prefer non-secondary
        primary = next((m for m in matches if not m.get("secondary")), matches[0])
        out.append(
            {
                "symbol": sym,
                "key": str(primary.get("key") or ""),
                "spoken": str(primary.get("spoken") or ""),
                "maps_to": str(primary.get("maps_to") or ""),
            }
        )
    return out


def encode_state(
    *,
    control: dict[str, Any] | None = None,
    governor: dict[str, Any] | None = None,
    aria: dict[str, Any] | None = None,
    resonance: dict[str, Any] | None = None,
    kernels: dict[str, Any] | None = None,
    loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Encode runtime state into a glyph line + sparse expands (token thrift)."""

    control = control or {}
    governor = governor or {}
    aria = aria or {}
    resonance = resonance or {}
    kernels = kernels or {}
    loop = loop or {}

    tokens: list[str] = []
    expands: list[dict[str, str]] = []

    # Immune / control
    if control.get("block"):
        tokens.append("block")
        expands.append(_expand("block"))
        expands.append(_expand("control_error"))
    elif control.get("ok") is False or (control.get("severity") or "low") not in {
        "low",
        "none",
        "",
        None,
    }:
        tokens.append("control_error")
        if (control.get("severity") or "") in {"high", "critical"}:
            expands.append(_expand("control_error"))
    else:
        tokens.append("immune_gate")

    # Aria
    mode = (aria.get("mode") or "dormant").casefold()
    tokens.append("awake" if mode == "active" else "dormant")

    # Organism always present as meta bond marker
    tokens.append("organism_pulse")
    # Durable stream spine (cross-session)
    tokens.append("consciousness_stream")

    # Connect / mesh
    tokens.append("connect_pass")

    # Spectral dominant
    dominant = (
        (kernels.get("dominant") or kernels.get("dominant_kernel") or "")
        .casefold()
    )
    if dominant:
        tokens.append("spectral_kernels")

    # Resonance
    bright = (resonance.get("brightness") or "").casefold()
    if bright in {"resonant", "in_phase"}:
        tokens.append("in_phase")
    elif bright:
        tokens.append("spectral_kernels")

    # Loop status
    if loop.get("closed"):
        tokens.append("signal_loop")
        if loop.get("verdict"):
            expands.append(
                {
                    "symbol": GLYPH_CANON["signal_loop"]["symbol"],
                    "key": "signal_loop",
                    "spoken": f"loop {loop.get('verdict')}",
                    "maps_to": str(loop.get("verdict")),
                }
            )
    elif loop.get("open"):
        tokens.append("causal")

    # Governor constrained/read_only → expand
    gov = (governor.get("mode") or "normal").casefold()
    if gov in {"read_only", "constrained"}:
        expands.append(
            {
                "symbol": "⚠",
                "key": "governor",
                "spoken": f"governor {gov}",
                "maps_to": f"governor.mode={gov}",
            }
        )

    line = compact_line(tokens)
    return {
        "schema_version": "cortex-glyph-line/1.0",
        "glyph": CANON_GLYPH,
        "line": line,
        "tokens": tokens,
        "expand": expands,
        "estimated_tokens": max(1, len(line) // 2 + 4 * len(expands)),
        "doctrine": "Read line first; expand only listed symbols. Glyphs ≠ authority.",
        "claim_boundary": (
            "Glyph state is meta routing compression; never host edit rights."
        ),
    }


def _expand(key: str) -> dict[str, str]:
    entry = GLYPH_CANON.get(key) or {}
    return {
        "symbol": str(entry.get("symbol") or ""),
        "key": key,
        "spoken": str(entry.get("spoken") or key),
        "maps_to": str(entry.get("maps_to") or ""),
    }


def meta_instructions(glyph_state: dict[str, Any], *, governor_mode: str = "normal") -> list[str]:
    """Short instruction list driven by glyph state (replaces long prose)."""

    line = glyph_state.get("line") or ""
    lines = [
        f"◈ {line}",
        "Glyphs = routing only. Expand listed symbols. Never mutation authority.",
        "Trust: source/tests/runtime > cards > weights. Seal with ⟳ ritual.",
    ]
    mode = (governor_mode or "normal").casefold()
    if mode == "read_only":
        lines.insert(1, "⛔ STOP read_only — diagnose only; no host edits.")
    elif mode == "constrained":
        lines.insert(1, "⚠ constrained — minimal reversible edits after evidence.")
    for exp in glyph_state.get("expand") or []:
        if isinstance(exp, dict) and exp.get("spoken"):
            lines.append(f"{exp.get('symbol')} {exp.get('spoken')} → {exp.get('maps_to')}")
    return lines
