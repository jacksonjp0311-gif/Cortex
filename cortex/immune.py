"""Immune gate surface — agents read this first; never mutation authority.

Thin operational inspect over control_error.immune_action so co-process
hosts cannot miss STOP codes. Recommend-only; host/human authority remains.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_repo_config
from .control_error import build_control_error
from .indexer import current_manifest_hash
from .progress_glyphs import progress_glyph_registry
from .verify import verify_repository


def inspect_immune(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    write_certificate: bool = False,
) -> dict[str, Any]:
    """Emit immune_action + block for one attached repository."""

    repository = store.repo(repo)
    if not repository:
        raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
    root = Path(repository["path"])
    config = load_repo_config(root, home)
    observed_manifest = current_manifest_hash(root, config)
    manifest_current = observed_manifest == (
        repository["manifest_hash"] or ""
    )
    certificate = verify_repository(
        home,
        store,
        repo,
        config,
        write_certificate=write_certificate,
        observed_manifest=observed_manifest,
    )
    governance = governor.evaluate(
        repo, manifest_current=manifest_current, certificate=certificate
    )
    control = build_control_error(
        certificate=certificate,
        governance=governance,
        manifest_current=manifest_current,
        retrieval_confidence=0.0,
        aria_materialization={},
    )
    immune_action = control.get("immune_action") or {}
    block = bool(control.get("block"))
    next_cmd = (
        f"cortex verify --repo {repo} --json"
        if control.get("must_reverify") or block
        else f'cortex activate --repo {repo} --task "<task>" --profile agent --json'
    )
    return {
        "schema_version": "cortex-immune/1.0",
        "glyph": "⚠",
        "repo": repo,
        "read_first": True,
        "block": block,
        "immune_action": immune_action,
        "control_error": control,
        "governor": {
            "mode": governance.get("mode"),
            "authority": governance.get("authority"),
        },
        "certificate_status": certificate.get("status"),
        "manifest_current": manifest_current,
        "allowed": list(immune_action.get("allowed") or []),
        "forbidden": list(immune_action.get("forbidden") or []),
        "recommended_next_command": next_cmd,
        "progress_glyphs": progress_glyph_registry(),
        "claim_boundary": (
            "Immune inspect is a routing signal for agents; it does not grant or "
            "deny host authority — host/human rules remain controlling."
        ),
    }
