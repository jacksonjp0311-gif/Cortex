"""Body hygiene telemetry — graph mass, prune advice, home stability (WP-C)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .glyphs.canon import compact_line, phrase
from .identity import home_looks_temporary
from .prune import policy_preview
from .ranker.model import ranker_status


def body_hygiene(
    home: Path,
    store: Any,
    repo: str,
    *,
    config: Any | None = None,
) -> dict[str, Any]:
    """Read-only hygiene snapshot for large graphs."""

    nodes = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_nodes WHERE repo=?", (repo,)
    ).fetchone()["c"]
    synapses = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_synapses WHERE repo=?", (repo,)
    ).fetchone()["c"]
    weak = store.db.execute(
        """
        SELECT COUNT(*) AS c FROM neural_synapses
        WHERE repo=? AND weight < 0.12 AND update_count = 0
        """,
        (repo,),
    ).fetchone()["c"]
    aria_nodes = 0
    try:
        for row in store.neural_nodes(repo):
            path = str(row["path"] or "").replace("\\", "/")
            if "aria_meta" in path:
                aria_nodes += 1
    except Exception:
        aria_nodes = 0

    config_home = None
    if config is not None:
        config_home = getattr(config, "cortex_home", None)
    temporary = home_looks_temporary(home) or home_looks_temporary(config_home)
    ranker = ranker_status(store, repo)

    preview = policy_preview(store, repo)
    soft_would = int(
        ((preview.get("policies") or {}).get("integrate_soft") or {}).get("would_prune")
        or 0
    )
    safe_would = int(
        ((preview.get("policies") or {}).get("safe") or {}).get("would_prune") or 0
    )
    recommended = preview.get("recommended") or "safe"

    advice: list[str] = []
    if temporary:
        advice.append("bind_stable_CORTEX_HOME")
    # Align advice with prune policy preview (v6.10)
    if soft_would >= 50:
        advice.append(f"prune_policy_integrate_soft_would_{soft_would}")
    elif safe_would > 0:
        advice.append(f"prune_policy_safe_would_{safe_would}")
    elif nodes >= 800 and weak == 0 and soft_would == 0:
        advice.append("graph_large_but_healthy_weights")
    elif nodes >= 800 and soft_would == 0:
        advice.append("graph_large_prune_not_indicated")
    if int(ranker.get("train_count") or 0) == 0:
        advice.append("run_signal_harness_or_evolve")
    if not advice:
        advice.append("hold_course")

    try:
        body_phrase = phrase("body_hygiene")
        glyph_line = body_phrase.get("line")
    except Exception:
        glyph_line = compact_line(["graph_prune", "spectral_kernels", "identity"])

    return {
        "schema_version": "cortex-body-hygiene/1.1",
        "glyph": "✂",
        "glyph_line": glyph_line,
        "repo": repo,
        "home": {
            "path": str(home),
            "temporary": temporary,
            "config_cortex_home": config_home,
        },
        "graph": {
            "nodes": int(nodes),
            "synapses": int(synapses),
            "weak_unused": int(weak),
            "aria_path_nodes": int(aria_nodes),
        },
        "prune_preview": preview,
        "recommended_prune_policy": recommended,
        "ranker": {
            "train_count": ranker.get("train_count"),
            "frozen": ranker.get("frozen"),
        },
        "advice": advice,
        "commands": {
            "prune_dry_safe": f"cortex prune --repo {repo} --policy safe --dry-run --json",
            "prune_dry_integrate_soft": (
                f"cortex prune --repo {repo} --policy integrate_soft --dry-run --json"
            ),
            "graph_stats": f"cortex graph --repo {repo} --stats --json",
            "kernels": f"cortex kernels --repo {repo} --json",
            "identity": f"cortex identity --repo {repo} --json",
            "harness": f"cortex harness --repo {repo} --json",
        },
        "claim_boundary": (
            "Hygiene is recommend-only telemetry; prune never deletes evidence rows."
        ),
    }
