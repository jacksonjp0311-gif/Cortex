"""Contact — strike the fork against foreign hosts and self-mirror.

Contact is the transcendence test: coherence outside the cathedral.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from .mirror import run_mirror
from .resonance import resonance_intensity


def run_contact(
    home: Path,
    store: Any,
    *,
    root: Path | None = None,
    include_foreign: bool = True,
) -> dict[str, Any]:
    """Mirror + fluency + foreign matrix → unified resonance field."""

    root = (root or Path.cwd()).resolve()
    t0 = time.perf_counter()
    mirror = run_mirror(home, store, root=root, repo_name="CortexContact")
    mirror_s = time.perf_counter() - t0

    corpus = (
        root / "benchmarks" / "corpora" / "aria_fluency.json"
        if (root / "benchmarks" / "corpora" / "aria_fluency.json").is_file()
        else Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "corpora"
        / "aria_fluency.json"
    )
    fluency = (
        evaluate_aria_corpus(load_aria_corpus(corpus))
        if corpus.is_file()
        else {"cases": 0, "false_wakes": 1, "missed_wakes": 1, "passed": 0}
    )
    fluency_perfect = (
        fluency.get("false_wakes", 1) == 0
        and fluency.get("missed_wakes", 1) == 0
        and fluency.get("cases", 0) >= 40
    )

    foreign: dict[str, Any] = {"all_passed": True, "passed": 0, "total": 0, "hosts": []}
    if include_foreign:
        # Import lazily so mirror-only installs stay light.
        import sys

        benchmarks = str(root / "benchmarks")
        if benchmarks not in sys.path:
            sys.path.insert(0, str(root))
        from benchmarks.foreign_host_matrix import run_matrix

        foreign = run_matrix()

    foreign_rate = (
        foreign["passed"] / foreign["total"] if foreign.get("total") else 1.0
    )

    flat: dict[str, Any] = {}
    for note in mirror.get("notes", []):
        if isinstance(note, dict):
            flat.update(note)

    savings = float(
        ((flat.get("work_proxy") or {}).get("estimated_bootstrap_savings_ratio"))
        or 0.0
    )
    deferred_boot = int(flat.get("deferred_after_boot") or 0)
    deferred_generic = int(flat.get("deferred_after_generic") or 0)
    deferred_holds = deferred_generic >= max(0, deferred_boot - 5) if deferred_boot else True
    aria_evidence = int(flat.get("aria_evidence_count") or 0)
    geometry = flat.get("geometry") or {}
    geometry_zp = bool(geometry.get("zero_point", True))
    timings = mirror.get("timings") or {}

    field = resonance_intensity(
        glow=bool(mirror.get("glow")) and foreign.get("all_passed", True),
        break_count=int(mirror.get("break_count") or 0)
        + (0 if foreign.get("all_passed", True) else 1),
        savings_ratio=savings,
        deferred_holds=deferred_holds,
        aria_evidence_count=aria_evidence,
        geometry_zero_point=geometry_zp,
        fluency_perfect=fluency_perfect,
        foreign_pass_rate=foreign_rate,
        generic_activate_s=float(timings.get("generic_activate_s") or 0.0),
        aria_activate_s=float(timings.get("aria_activate_s") or 0.0),
        bootstrap_s=float(timings.get("bootstrap_s") or 0.0),
    )

    # Contact can fail even if mirror glows alone.
    contact_breaks = list(mirror.get("breaks") or [])
    if not foreign.get("all_passed", True):
        contact_breaks.append(
            {
                "id": "foreign-contact-failed",
                "hosts": [
                    host
                    for host in foreign.get("hosts", [])
                    if not host.get("pass")
                ],
            }
        )
    if not fluency_perfect:
        contact_breaks.append(
            {
                "id": "fluency-imperfect",
                "false_wakes": fluency.get("false_wakes"),
                "missed_wakes": fluency.get("missed_wakes"),
            }
        )

    bright = field["glow"] and field["glow_intensity"] >= 0.90
    return {
        "schema_version": "cortex-contact/1.0",
        "mirror_seconds": round(mirror_s, 4),
        "mirror": {
            "glow": mirror.get("glow"),
            "break_count": mirror.get("break_count"),
            "timings": timings,
        },
        "fluency": {
            "cases": fluency.get("cases"),
            "passed": fluency.get("passed"),
            "false_wakes": fluency.get("false_wakes"),
            "missed_wakes": fluency.get("missed_wakes"),
            "perfect": fluency_perfect,
        },
        "foreign": foreign,
        "resonance": field,
        "glow": field["glow"] and not contact_breaks,
        "glow_intensity": field["glow_intensity"],
        "brightness": field["brightness"],
        "bright": bright,
        "break_count": len(contact_breaks),
        "breaks": contact_breaks,
        "claim_boundary": (
            "Contact proves local organ behavior under controlled foreign stress; "
            "it does not prove production multi-repo quality or grant authority."
        ),
    }
